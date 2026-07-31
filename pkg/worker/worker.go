package worker

import (
	"context"
	"fmt"
	"log"
	"math"
	"time"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/AyushSaha184/Eval_MCP/pkg/eval"
	"github.com/AyushSaha184/Eval_MCP/pkg/judge"
	"github.com/AyushSaha184/Eval_MCP/pkg/queue"
	"github.com/AyushSaha184/Eval_MCP/pkg/storage"
)

type Worker struct {
	cfg   *config.Config
	store *storage.MemoryStore
	queue queue.Queue
	llm   *eval.LLMRunner
	judge *judge.GeminiJudge
}

func NewWorker(cfg *config.Config, store *storage.MemoryStore, q queue.Queue) *Worker {
	return &Worker{
		cfg:   cfg,
		store: store,
		queue: q,
		llm:   eval.NewLLMRunner(cfg),
		judge: judge.NewGeminiJudge(cfg),
	}
}

func (w *Worker) Start(ctx context.Context, maxRuns *int) {
	processed := 0
	log.Println("Worker loop started, waiting for jobs...")

	for {
		if ctx.Err() != nil {
			log.Println("Worker loop context cancelled")
			return
		}
		if maxRuns != nil && processed >= *maxRuns {
			log.Println("Max runs reached, stopping worker")
			return
		}

		runID, err := w.queue.Dequeue(ctx)
		if err != nil {
			if ctx.Err() != nil {
				log.Println("Worker loop context cancelled")
				return
			}
			time.Sleep(500 * time.Millisecond)
			continue
		}
		if runID == "" {
			time.Sleep(500 * time.Millisecond)
			continue
		}

		log.Printf("Worker executing run %s", runID)
		if err := w.processRun(ctx, runID); err != nil {
			log.Printf("Run %s failed: %v", runID, err)
			w.store.UpdateRunStatus(runID, domain.StatusFailed, err.Error())
		} else {
			log.Printf("Run %s completed successfully", runID)
		}

		processed++
	}
}

func (w *Worker) processRun(ctx context.Context, runID string) error {
	run, found := w.store.GetRun(runID)
	if !found {
		return fmt.Errorf("run %s not found in store", runID)
	}

	w.store.UpdateRunStatus(runID, domain.StatusRunning, "")

	switch run.RunType {
	case domain.RunTypePromptEval, domain.RunTypeComparisonBackingRun:
		return w.executePromptEval(ctx, run)
	case domain.RunTypeRagEval:
		return w.executeRagEval(ctx, run)
	case domain.RunTypeSuggestionEval:
		return w.executeSuggestionEval(ctx, run)
	default:
		return fmt.Errorf("unsupported run type: %s", run.RunType)
	}
}

func (w *Worker) executePromptEval(ctx context.Context, run *domain.EvalRun) error {
	dsID, _ := run.DatasetSnapshot["dataset_id"].(string)
	_, cases, found := w.store.GetDataset(run.ProjectID, dsID)
	if !found {
		return fmt.Errorf("dataset not found for run")
	}

	var targetCaseIndices map[int]bool
	if rawIndices, ok := run.RuntimeConfigSnapshot["selected_case_indices"]; ok && rawIndices != nil {
		targetCaseIndices = make(map[int]bool)
		if idxList, ok := rawIndices.([]interface{}); ok {
			for _, item := range idxList {
				if n, ok := item.(float64); ok {
					targetCaseIndices[int(n)] = true
				} else if n, ok := item.(int); ok {
					targetCaseIndices[n] = true
				}
			}
		} else if idxList, ok := rawIndices.([]int); ok {
			for _, n := range idxList {
				targetCaseIndices[n] = true
			}
		}
	}

	total := len(cases)
	if len(targetCaseIndices) > 0 {
		total = len(targetCaseIndices)
	}
	w.store.UpdateRunProgress(run.RunID, 0, total)

	modelCfg := domain.ModelConfig{
		Provider:  getString(run.ModelConfigSnapshot, "provider"),
		ModelName: getString(run.ModelConfigSnapshot, "model_name"),
	}
	runtimeCfg := domain.RuntimeConfig{}

	var caseResults []domain.EvalCaseResult
	passedCount := 0
	processedCount := 0

	for _, c := range cases {
		if len(targetCaseIndices) > 0 && !targetCaseIndices[c.CaseIndex] {
			continue
		}

		gen, err := w.llm.Generate(ctx, run.PromptSnapshot, c.InputText, c.ExpectedOutput, modelCfg, runtimeCfg, c.Context)
		if err != nil {
			gen = &eval.GenerationResult{
				OutputText:     "Error: " + err.Error(),
				RenderedPrompt: c.InputText,
				LatencyMS:      0,
			}
		}

		heurMetrics, _ := eval.ScoreHeuristicMetrics(run.MetricsRequested, gen.OutputText, c.ExpectedOutput, c.Context)
		ragMetrics, _ := eval.ScoreRagMetrics(run.MetricsRequested, c.InputText, gen.OutputText, c.ExpectedOutput, gen.RetrievedContext, c.Context)

		allMetrics := append(heurMetrics, ragMetrics...)
		casePassed := true
		for _, m := range allMetrics {
			if m.Passed != nil && !*m.Passed {
				casePassed = false
				break
			}
		}

		status := domain.CasePassed
		if !casePassed {
			status = domain.CaseFailed
		} else {
			passedCount++
		}

		caseResults = append(caseResults, domain.EvalCaseResult{
			ID:                     fmt.Sprintf("%s_case_%d", run.RunID, c.CaseIndex),
			RunID:                  run.RunID,
			DatasetCaseID:          c.ID,
			CaseIndex:              c.CaseIndex,
			InputTextSnapshot:      c.InputText,
			ActualOutput:           gen.OutputText,
			ExpectedOutputSnapshot: c.ExpectedOutput,
			LatencyMS:              gen.LatencyMS,
			TokenUsage:             gen.TokenUsage,
			Status:                 status,
			Metrics:                allMetrics,
		})

		processedCount++
		w.store.UpdateRunProgress(run.RunID, processedCount, total)
	}

	w.store.SaveCaseResults(run.RunID, caseResults)

	passRate := 0.0
	if total > 0 {
		passRate = math.Round((float64(passedCount)/float64(total))*1000000) / 1000000
	}
	run.PassRate = &passRate
	w.store.UpdateRunStatus(run.RunID, domain.StatusCompleted, "")
	return nil
}

func (w *Worker) executeRagEval(ctx context.Context, run *domain.EvalRun) error {
	return w.executePromptEval(ctx, run)
}

func (w *Worker) executeSuggestionEval(ctx context.Context, run *domain.EvalRun) error {
	refRunID, _ := run.RuntimeConfigSnapshot["referenced_run_id"].(string)
	modelName, _ := run.RuntimeConfigSnapshot["model_name"].(string)

	cases := w.store.GetCaseResults(refRunID)
	var sampleInputs []string
	var clusters []domain.FailureCluster

	for _, c := range cases {
		if c.Status == domain.CaseFailed || c.Status == domain.CaseError {
			sampleInputs = append(sampleInputs, c.InputTextSnapshot)
		}
	}

	if len(sampleInputs) > 0 {
		clusters = append(clusters, domain.FailureCluster{
			ClusterKey:   "quality_failures",
			Title:        "Failures in evaluation metrics",
			Size:         len(sampleInputs),
			SampleInputs: sampleInputs,
		})
	}

	judgeRes, err := w.judge.GenerateSuggestion(ctx, refRunID, clusters, sampleInputs, modelName)
	if err != nil {
		return err
	}

	w.store.SaveSuggestion(refRunID, domain.SuggestionResponse{
		ID:              "sug_" + run.RunID,
		RunID:           refRunID,
		Summary:         judgeRes.Summary,
		SuggestionText:  judgeRes.SuggestionText,
		FailureClusters: judgeRes.FailureClusters,
		ModelName:       modelName,
		CreatedAt:       time.Now(),
	})

	w.store.UpdateRunStatus(run.RunID, domain.StatusCompleted, "")
	return nil
}

func getString(m map[string]interface{}, key string) string {
	if m == nil {
		return ""
	}
	v, _ := m[key].(string)
	return v
}
