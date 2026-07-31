package services

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strings"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/AyushSaha184/Eval_MCP/pkg/eval"
	"github.com/AyushSaha184/Eval_MCP/pkg/judge"
	"github.com/AyushSaha184/Eval_MCP/pkg/metrics"
	"github.com/AyushSaha184/Eval_MCP/pkg/queue"
	"github.com/AyushSaha184/Eval_MCP/pkg/storage"
	"github.com/google/uuid"
)

type Services struct {
	cfg     *config.Config
	store   *storage.MemoryStore
	queue   queue.Queue
	llm     *eval.LLMRunner
	judge   *judge.GeminiJudge
}

func NewServices(cfg *config.Config, store *storage.MemoryStore, q queue.Queue) *Services {
	return &Services{
		cfg:     cfg,
		store:   store,
		queue:   q,
		llm:     eval.NewLLMRunner(cfg),
		judge:   judge.NewGeminiJudge(cfg),
	}
}

func (s *Services) Store() *storage.MemoryStore {
	return s.store
}

func generateRunID() string {
	return "run_" + strings.ReplaceAll(uuid.New().String(), "-", "")[:16]
}

func buildCacheKey(projID string, runType domain.RunType, metrics []string, promptSnap, datasetSnap map[string]interface{}) string {
	mCopy := append([]string(nil), metrics...)
	sort.Strings(mCopy)
	h := sha256.New()
	pStr, _ := json.Marshal(promptSnap)
	dStr, _ := json.Marshal(datasetSnap)
	h.Write([]byte(projID + ":" + string(runType) + ":" + strings.Join(mCopy, ",") + ":" + string(pStr) + ":" + string(dStr)))
	return hex.EncodeToString(h.Sum(nil))[:32]
}

// RunEvalSuite queues prompt evaluation.
func (s *Services) RunEvalSuite(ctx context.Context, req domain.RunEvalRequest) (*domain.RunQueued, error) {
	proj, err := s.store.GetOrCreateProject(req.Project)
	if err != nil {
		return nil, err
	}

	var prompt domain.Prompt
	if req.PromptReference != nil && req.PromptReference.PromptID != "" {
		p, found := s.store.GetPrompt(req.PromptReference.PromptID)
		if found {
			prompt = p
		}
	} else if req.PromptReference != nil && req.PromptReference.PromptKey != "" {
		ver := 0
		if req.PromptReference.Version != nil {
			ver = *req.PromptReference.Version
		}
		p, found := s.store.GetPromptByKeyAndVersion(proj.ID, req.PromptReference.PromptKey, ver)
		if found {
			prompt = p
		}
	} else if req.AdHocPrompt != nil {
		prompt = domain.Prompt{
			PromptKey:    req.AdHocPrompt.PromptKey,
			Content:      req.AdHocPrompt.Content,
			SystemPrompt: req.AdHocPrompt.SystemPrompt,
			Metadata:     req.AdHocPrompt.Metadata,
		}
	}

	ds, cases, found := s.store.GetDataset(proj.ID, req.DatasetReference.DatasetName)
	if !found && req.DatasetReference.DatasetID != "" {
		ds, cases, found = s.store.GetDataset(proj.ID, req.DatasetReference.DatasetID)
	}
	if !found {
		return nil, fmt.Errorf("dataset '%s' not found", req.DatasetReference.DatasetName)
	}

	promptSnap := map[string]interface{}{
		"content":       prompt.Content,
		"system_prompt": prompt.SystemPrompt,
		"prompt_key":    prompt.PromptKey,
	}
	datasetSnap := map[string]interface{}{
		"dataset_id":   ds.ID,
		"dataset_name": ds.DatasetName,
	}

	cacheKey := buildCacheKey(proj.ID, domain.RunTypePromptEval, req.Metrics, promptSnap, datasetSnap)
	if !req.ForceRerun {
		if cached := s.store.FindCachedRun(proj.ID, cacheKey, domain.RunTypePromptEval); cached != nil {
			return &domain.RunQueued{
				RunID:       cached.RunID,
				Status:      cached.Status,
				Cached:      true,
				CacheKey:    cacheKey,
				SourceRunID: cached.RunID,
			}, nil
		}
	}

	runID := generateRunID()
	evalRun := domain.EvalRun{
		RunID:            runID,
		ProjectID:        proj.ID,
		RunType:          domain.RunTypePromptEval,
		Status:           domain.StatusQueued,
		TriggerSource:    req.TriggerSource,
		TriggeredBy:      req.TriggeredBy,
		MetricsRequested: req.Metrics,
		CacheKey:         cacheKey,
		TotalCases:       len(cases),
		ProcessedCases:   0,
		PromptSnapshot:   promptSnap,
		DatasetSnapshot:  datasetSnap,
		ModelConfigSnapshot: map[string]interface{}{
			"provider":    req.ModelConfig.Provider,
			"model_name":  req.ModelConfig.ModelName,
			"temperature": req.ModelConfig.Temperature,
			"max_tokens":  req.ModelConfig.MaxTokens,
			"extra":       req.ModelConfig.Extra,
		},
		RuntimeConfigSnapshot: map[string]interface{}{
			"max_concurrency":       req.RuntimeConfig.MaxConcurrency,
			"timeout_seconds":       req.RuntimeConfig.TimeoutSeconds,
			"selected_case_indices": req.RuntimeConfig.SelectedCaseIndices,
		},
	}

	s.store.SaveRun(evalRun)
	_ = s.queue.Enqueue(ctx, runID)

	return &domain.RunQueued{
		RunID:    runID,
		Status:   domain.StatusQueued,
		Cached:   false,
		CacheKey: cacheKey,
	}, nil
}

// ScoreRagPipeline queues RAG pipeline scoring.
func (s *Services) ScoreRagPipeline(ctx context.Context, req domain.RagScoreRequest) (*domain.RunQueued, error) {
	proj, err := s.store.GetOrCreateProject(req.Project)
	if err != nil {
		return nil, err
	}

	var ds domain.Dataset
	var cases []domain.DatasetCase

	if len(req.Cases) > 0 {
		dsName := req.DatasetName
		if dsName == "" {
			dsName = "rag_inline_dataset"
		}
		var caseInputs []domain.DatasetCaseInput
		for _, c := range req.Cases {
			caseInputs = append(caseInputs, domain.DatasetCaseInput{
				InputText:      c.Query,
				ExpectedOutput: c.ExpectedOutput,
				Context:        c.ExpectedContext,
				Metadata:       c.Metadata,
			})
		}
		ds, cases = s.store.SaveDataset(domain.Dataset{
			ProjectID:   proj.ID,
			DatasetName: dsName,
			VersionHash: "inline",
		}, caseInputs)
	} else if req.DatasetReference != nil {
		var found bool
		ds, cases, found = s.store.GetDataset(proj.ID, req.DatasetReference.DatasetName)
		if !found {
			return nil, fmt.Errorf("dataset not found")
		}
	}

	datasetSnap := map[string]interface{}{
		"dataset_id":   ds.ID,
		"dataset_name": ds.DatasetName,
	}

	cacheKey := buildCacheKey(proj.ID, domain.RunTypeRagEval, req.Metrics, nil, datasetSnap)
	runID := generateRunID()

	evalRun := domain.EvalRun{
		RunID:            runID,
		ProjectID:        proj.ID,
		RunType:          domain.RunTypeRagEval,
		Status:           domain.StatusQueued,
		TriggerSource:    req.TriggerSource,
		TriggeredBy:      req.TriggeredBy,
		MetricsRequested: req.Metrics,
		CacheKey:         cacheKey,
		TotalCases:       len(cases),
		ProcessedCases:   0,
		DatasetSnapshot:  datasetSnap,
		RetrieverConfigSnapshot: map[string]interface{}{
			"provider":   req.RetrieverConfig.Provider,
			"index_name": req.RetrieverConfig.IndexName,
			"top_k":      req.RetrieverConfig.TopK,
			"extra":      req.RetrieverConfig.Extra,
		},
		ModelConfigSnapshot: map[string]interface{}{
			"provider":   req.ModelConfig.Provider,
			"model_name": req.ModelConfig.ModelName,
		},
	}

	s.store.SaveRun(evalRun)
	_ = s.queue.Enqueue(ctx, runID)

	return &domain.RunQueued{
		RunID:    runID,
		Status:   domain.StatusQueued,
		Cached:   false,
		CacheKey: cacheKey,
	}, nil
}

// ComparePromptVersions compares two prompts against a dataset.
func (s *Services) ComparePromptVersions(ctx context.Context, req domain.CompareRequest) (*domain.CompareResponse, error) {
	baseRun, err := s.RunEvalSuite(ctx, domain.RunEvalRequest{
		Project:          req.Project,
		PromptReference:  &req.BaselinePromptReference,
		DatasetReference: req.DatasetReference,
		Metrics:          req.Metrics,
		ModelConfig:      req.ModelConfig,
		RuntimeConfig:    req.RuntimeConfig,
		ForceRerun:       req.ForceRerun,
	})
	if err != nil {
		return nil, err
	}

	candRun, err := s.RunEvalSuite(ctx, domain.RunEvalRequest{
		Project:          req.Project,
		PromptReference:  &req.CandidatePromptReference,
		DatasetReference: req.DatasetReference,
		Metrics:          req.Metrics,
		ModelConfig:      req.ModelConfig,
		RuntimeConfig:    req.RuntimeConfig,
		ForceRerun:       req.ForceRerun,
	})
	if err != nil {
		return nil, err
	}

	baseCases := s.store.GetCaseResults(baseRun.RunID)
	candCases := s.store.GetCaseResults(candRun.RunID)
	baseMetrics := aggregateCaseMetrics(baseCases)
	candMetrics := aggregateCaseMetrics(candCases)

	var deltas []domain.MetricDelta
	var improved, regressed, unchanged []string

	allMetrics := make(map[string]bool)
	for m := range baseMetrics {
		allMetrics[m] = true
	}
	for m := range candMetrics {
		allMetrics[m] = true
	}

	for mName := range allMetrics {
		bScore, bHas := baseMetrics[mName]
		cScore, cHas := candMetrics[mName]
		def, _ := metrics.GetMetricDefinition(mName)

		var bPtr, cPtr, dPtr *float64
		if bHas {
			bPtr = &bScore
		}
		if cHas {
			cPtr = &cScore
		}
		var isImp, isReg bool

		if bHas && cHas {
			dVal := math.Round((cScore-bScore)*1000000) / 1000000
			dPtr = &dVal
			if math.Abs(dVal) < 1e-6 {
				unchanged = append(unchanged, mName)
			} else if def.Direction == domain.HigherIsBetter {
				if cScore > bScore {
					isImp = true
					improved = append(improved, mName)
				} else {
					isReg = true
					regressed = append(regressed, mName)
				}
			} else {
				if cScore < bScore {
					isImp = true
					improved = append(improved, mName)
				} else {
					isReg = true
					regressed = append(regressed, mName)
				}
			}
		}

		deltas = append(deltas, domain.MetricDelta{
			MetricName:     mName,
			Direction:      def.Direction,
			BaselineScore:  bPtr,
			CandidateScore: cPtr,
			Delta:          dPtr,
			Improved:       isImp,
			Regressed:      isReg,
		})
	}

	status := "completed"
	if len(baseCases) == 0 || len(candCases) == 0 {
		status = "pending"
	}

	return &domain.CompareResponse{
		Status:           status,
		BaselineRunID:    baseRun.RunID,
		CandidateRunID:   candRun.RunID,
		Deltas:           deltas,
		ImprovedMetrics:  improved,
		RegressedMetrics: regressed,
		UnchangedMetrics: unchanged,
	}, nil
}

// DetectRegression detects metric regressions.
func (s *Services) DetectRegression(req domain.RegressionRequest) (*domain.RegressionResponse, error) {
	candRun, found := s.store.GetRun(req.CandidateRunID)
	if !found {
		return nil, fmt.Errorf("candidate run '%s' not found", req.CandidateRunID)
	}

	baseRunID := req.BaselineRunID
	if baseRunID == "" {
		proj, _ := s.store.GetOrCreateProject(candRun.ProjectID)
		baseRunID = proj.DefaultBaselineRunID
	}
	if baseRunID == "" {
		return nil, fmt.Errorf("no baseline run specified or set for project")
	}

	baseRun, found := s.store.GetRun(baseRunID)
	if !found {
		return nil, fmt.Errorf("baseline run '%s' not found", baseRunID)
	}

	overrides := make(map[string]float64)
	for _, t := range req.Thresholds {
		overrides[t.MetricName] = t.AllowedDelta
	}

	baseCases := s.store.GetCaseResults(baseRun.RunID)
	candCases := s.store.GetCaseResults(candRun.RunID)

	var outcomes []domain.RegressionMetricOutcome
	isRegression := false

	baseMetrics := aggregateCaseMetrics(baseCases)
	candMetrics := aggregateCaseMetrics(candCases)

	allMetrics := make(map[string]bool)
	for m := range baseMetrics {
		allMetrics[m] = true
	}
	for m := range candMetrics {
		allMetrics[m] = true
	}

	for mName := range allMetrics {
		bScore, bHas := baseMetrics[mName]
		cScore, cHas := candMetrics[mName]
		if !bHas || !cHas {
			continue
		}

		def, _ := metrics.GetMetricDefinition(mName)
		delta := math.Round((cScore-bScore)*1000000) / 1000000
		allowed, hasCustom := overrides[mName]
		if !hasCustom && def.DefaultThreshold != nil {
			allowed = 0.05
		}

		regressed := false
		if math.Abs(cScore-bScore) > 1e-6 {
			if def.Direction == domain.HigherIsBetter {
				regressed = cScore < (bScore - allowed)
			} else {
				regressed = cScore > (bScore + allowed)
			}
		}

		if regressed {
			isRegression = true
		}

		outcomes = append(outcomes, domain.RegressionMetricOutcome{
			MetricName:     mName,
			BaselineScore:  &bScore,
			CandidateScore: &cScore,
			Delta:          &delta,
			Direction:      def.Direction,
			AllowedDelta:   allowed,
			Regressed:      regressed,
		})
	}

	return &domain.RegressionResponse{
		BaselineRunID:   baseRun.RunID,
		CandidateRunID:  candRun.RunID,
		IsRegression:    isRegression,
		AffectedMetrics: outcomes,
	}, nil
}

func aggregateCaseMetrics(cases []domain.EvalCaseResult) map[string]float64 {
	sums := make(map[string]float64)
	counts := make(map[string]int)

	for _, c := range cases {
		for _, m := range c.Metrics {
			sums[m.MetricName] += m.Score
			counts[m.MetricName]++
		}
	}

	res := make(map[string]float64)
	for m, sum := range sums {
		cnt := counts[m]
		if cnt > 0 {
			res[m] = sum / float64(cnt)
		}
	}
	return res
}

// QueueSuggestion queues prompt improvement suggestions.
func (s *Services) QueueSuggestion(ctx context.Context, req domain.SuggestFixRequest) (*domain.RunQueued, error) {
	run, found := s.store.GetRun(req.RunID)
	if !found {
		return nil, fmt.Errorf("run '%s' not found", req.RunID)
	}

	sugRunID := generateRunID()
	cacheKey := "sug_" + req.RunID

	evalRun := domain.EvalRun{
		RunID:            sugRunID,
		ProjectID:        run.ProjectID,
		RunType:          domain.RunTypeSuggestionEval,
		Status:           domain.StatusQueued,
		TriggerSource:    domain.TriggerSourceAPI,
		TriggeredBy:      "suggestion_service",
		MetricsRequested: []string{},
		CacheKey:         cacheKey,
		TotalCases:       1,
		RuntimeConfigSnapshot: map[string]interface{}{
			"referenced_run_id": req.RunID,
			"case_limit":        req.CaseLimit,
			"cluster_limit":     req.ClusterLimit,
			"model_name":        req.ModelName,
		},
	}

	s.store.SaveRun(evalRun)
	_ = s.queue.Enqueue(ctx, sugRunID)

	return &domain.RunQueued{
		RunID:    sugRunID,
		Status:   domain.StatusQueued,
		Cached:   false,
		CacheKey: cacheKey,
	}, nil
}

// RerunFailedCases reruns failed test cases.
func (s *Services) RerunFailedCases(ctx context.Context, req domain.RerunFailedRequest) (*domain.RunQueued, error) {
	srcRun, found := s.store.GetRun(req.RunID)
	if !found {
		return nil, fmt.Errorf("run '%s' not found", req.RunID)
	}

	cases := s.store.GetCaseResults(srcRun.RunID)
	var failedIndices []int
	for _, c := range cases {
		if c.Status == domain.CaseFailed || c.Status == domain.CaseError {
			failedIndices = append(failedIndices, c.CaseIndex)
		}
	}

	if len(failedIndices) == 0 {
		return nil, fmt.Errorf("no failed cases to rerun")
	}

	dsName, _ := srcRun.DatasetSnapshot["dataset_name"].(string)
	content, _ := srcRun.PromptSnapshot["content"].(string)
	sysPrompt, _ := srcRun.PromptSnapshot["system_prompt"].(string)
	promptKey, _ := srcRun.PromptSnapshot["prompt_key"].(string)

	provider, _ := srcRun.ModelConfigSnapshot["provider"].(string)
	modelName, _ := srcRun.ModelConfigSnapshot["model_name"].(string)

	return s.RunEvalSuite(ctx, domain.RunEvalRequest{
		Project:          srcRun.ProjectID,
		DatasetReference: domain.DatasetReference{DatasetName: dsName},
		AdHocPrompt: &domain.AdHocPrompt{
			PromptKey:    promptKey,
			Content:      content,
			SystemPrompt: sysPrompt,
		},
		ModelConfig: domain.ModelConfig{
			Provider:  provider,
			ModelName: modelName,
		},
		Metrics:       srcRun.MetricsRequested,
		RuntimeConfig: domain.RuntimeConfig{SelectedCaseIndices: failedIndices},
		ForceRerun:    req.ForceRerun,
	})
}
