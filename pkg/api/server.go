package api

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/AyushSaha184/Eval_MCP/pkg/metrics"
	"github.com/AyushSaha184/Eval_MCP/pkg/services"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

type Server struct {
	cfg *config.Config
	svc *services.Services
}

func NewServer(cfg *config.Config, svc *services.Services) *Server {
	return &Server{
		cfg: cfg,
		svc: svc,
	}
}

func (s *Server) Router() http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]interface{}{"status": "healthy", "service": "eval-mcp"})
	})

	r.Route("/v1", func(r chi.Router) {
		r.Get("/projects", s.listProjects)
		r.Get("/projects/{project}/datasets", s.listProjectDatasets)
		r.Get("/projects/{project}/prompts", s.listProjectPrompts)
		r.Post("/datasets/register", s.registerDataset)
		r.Post("/runs/eval", s.runEval)
		r.Post("/runs/rag", s.runRag)
		r.Get("/runs/{run_id}/status", s.getRunStatus)
		r.Post("/history/query", s.queryHistory)
		r.Post("/baselines/set", s.setBaseline)
		r.Post("/comparisons/prompt-versions", s.comparePrompts)
		r.Post("/regressions/detect", s.detectRegression)
		r.Post("/runs/rerun-failed", s.rerunFailed)
		r.Post("/runs/annotate", s.annotateRun)
		r.Post("/suggestions", s.suggestFix)
		r.Get("/runs/{run_id}/suggestions/latest", s.getLatestSuggestion)
		r.Get("/meta/supported-metrics", s.supportedMetrics)
	})

	return r
}

func writeJSON(w http.ResponseWriter, code int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(payload)
}

func (s *Server) listProjects(w http.ResponseWriter, r *http.Request) {
	projs := s.svc.Store().ListProjects()
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "items": projs})
}

func (s *Server) listProjectDatasets(w http.ResponseWriter, r *http.Request) {
	project := chi.URLParam(r, "project")
	proj, found := s.svc.Store().GetProject(project)
	if !found {
		writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "items": []domain.Dataset{}})
		return
	}
	datasets := s.svc.Store().ListDatasets(proj.ID)
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "items": datasets})
}

func (s *Server) listProjectPrompts(w http.ResponseWriter, r *http.Request) {
	project := chi.URLParam(r, "project")
	proj, found := s.svc.Store().GetProject(project)
	if !found {
		writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "items": []domain.Prompt{}})
		return
	}
	prompts := s.svc.Store().ListPrompts(proj.ID)
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "items": prompts})
}

func (s *Server) registerDataset(w http.ResponseWriter, r *http.Request) {
	var req domain.DatasetRegistration
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	proj, _ := s.svc.Store().GetOrCreateProject(req.Project)

	casesBytes, _ := json.Marshal(req.Cases)
	hash := sha256.Sum256(casesBytes)
	versionHash := fmt.Sprintf("v_%s", hex.EncodeToString(hash[:])[:8])

	ds, _ := s.svc.Store().SaveDataset(domain.Dataset{
		ProjectID:   proj.ID,
		DatasetName: req.DatasetName,
		Description: req.Description,
		Tags:        req.Tags,
		Metadata:    req.Metadata,
		VersionHash: versionHash,
	}, req.Cases)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"ok":           true,
		"dataset_name": ds.DatasetName,
		"version_hash": ds.VersionHash,
		"case_count":   ds.CaseCount,
	})
}

func (s *Server) runEval(w http.ResponseWriter, r *http.Request) {
	var req domain.RunEvalRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.RunEvalSuite(r.Context(), req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "run_id": resp.RunID, "status": resp.Status, "cached": resp.Cached, "cache_key": resp.CacheKey})
}

func (s *Server) runRag(w http.ResponseWriter, r *http.Request) {
	var req domain.RagScoreRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.ScoreRagPipeline(r.Context(), req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "run_id": resp.RunID, "status": resp.Status, "cached": resp.Cached, "cache_key": resp.CacheKey})
}

func (s *Server) getRunStatus(w http.ResponseWriter, r *http.Request) {
	runID := chi.URLParam(r, "run_id")
	run, found := s.svc.Store().GetRun(runID)
	if !found {
		writeJSON(w, http.StatusNotFound, map[string]interface{}{"ok": false, "error": "run not found"})
		return
	}

	incSug, _ := strconv.ParseBool(r.URL.Query().Get("include_suggestion"))
	var sugSummary *domain.SuggestionSummary
	if incSug {
		if sug, ok := s.svc.Store().GetLatestSuggestion(runID); ok {
			sugSummary = &domain.SuggestionSummary{
				ID:     sug.ID,
				RunID:  sug.RunID,
				Status: "completed",
			}
		}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"ok":                 true,
		"run_id":             run.RunID,
		"status":             run.Status,
		"run_type":           run.RunType,
		"processed_cases":    run.ProcessedCases,
		"total_cases":        run.TotalCases,
		"pass_rate":          run.PassRate,
		"started_at":         run.StartedAt,
		"completed_at":       run.CompletedAt,
		"error_message":      run.ErrorMessage,
		"is_cached_result":   run.IsCachedResult,
		"suggestion_summary": sugSummary,
	})
}

func (s *Server) queryHistory(w http.ResponseWriter, r *http.Request) {
	var req domain.HistoryFilters
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	items, total := s.svc.Store().QueryHistory(req)
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"ok":        true,
		"items":     items,
		"total":     total,
		"page":      req.Page,
		"page_size": req.PageSize,
	})
}

func (s *Server) setBaseline(w http.ResponseWriter, r *http.Request) {
	var req domain.BaselineSetRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	proj, _ := s.svc.Store().GetOrCreateProject(req.Project)
	if err := s.svc.Store().SetProjectBaseline(proj.ID, req.RunID); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "project": proj.Slug, "baseline_run_id": req.RunID})
}

func (s *Server) comparePrompts(w http.ResponseWriter, r *http.Request) {
	var req domain.CompareRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.ComparePromptVersions(r.Context(), req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "status": resp.Status, "baseline_run_id": resp.BaselineRunID, "candidate_run_id": resp.CandidateRunID})
}

func (s *Server) detectRegression(w http.ResponseWriter, r *http.Request) {
	var req domain.RegressionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.DetectRegression(req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "baseline_run_id": resp.BaselineRunID, "candidate_run_id": resp.CandidateRunID, "is_regression": resp.IsRegression, "affected_metrics": resp.AffectedMetrics})
}

func (s *Server) rerunFailed(w http.ResponseWriter, r *http.Request) {
	var req domain.RerunFailedRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.RerunFailedCases(r.Context(), req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "run_id": resp.RunID, "status": resp.Status})
}

func (s *Server) annotateRun(w http.ResponseWriter, r *http.Request) {
	var req domain.AnnotationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	ann := domain.AnnotationRead{
		RunID:     req.RunID,
		Label:     req.Label,
		Note:      req.Note,
		CreatedBy: req.CreatedBy,
	}
	s.svc.Store().SaveAnnotation(ann)
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "run_id": ann.RunID, "label": ann.Label})
}

func (s *Server) suggestFix(w http.ResponseWriter, r *http.Request) {
	var req domain.SuggestFixRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	resp, err := s.svc.QueueSuggestion(r.Context(), req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "run_id": resp.RunID, "status": resp.Status})
}

func (s *Server) getLatestSuggestion(w http.ResponseWriter, r *http.Request) {
	runID := chi.URLParam(r, "run_id")
	sug, found := s.svc.Store().GetLatestSuggestion(runID)
	if !found {
		writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "status": "pending", "suggestion": nil})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"ok": true, "status": "completed", "id": sug.ID, "summary": sug.Summary, "suggestion_text": sug.SuggestionText, "failure_clusters": sug.FailureClusters})
}

func (s *Server) supportedMetrics(w http.ResponseWriter, r *http.Request) {
	defs := metrics.ListMetricDefinitions()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"ok":               true,
		"metrics":          defs,
		"run_types":        []string{"prompt_eval", "rag_eval", "comparison_backing_run", "suggestion_eval"},
		"storage_provider": "memory_json",
		"queue_backend":    "redis",
	})
}
