package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

type MCPServer struct {
	cfg        *config.Config
	server     *server.MCPServer
	httpClient *http.Client
}

func NewMCPServer(cfg *config.Config) *MCPServer {
	s := server.NewMCPServer("eval-mcp", "1.0.0")
	ms := &MCPServer{
		cfg:    cfg,
		server: s,
		httpClient: &http.Client{
			Timeout: cfg.RequestTimeout,
		},
	}
	ms.registerTools()
	return ms
}

func (ms *MCPServer) ServeStdio() error {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	healthURL := strings.TrimSuffix(ms.cfg.APIURL, "/") + "/health"
	req, err := http.NewRequestWithContext(ctx, "GET", healthURL, nil)
	if err == nil {
		if resp, err := ms.httpClient.Do(req); err != nil {
			fmt.Fprintf(os.Stderr, "[WARNING] Backend API server is NOT running at %s.\n[WARNING] Please start the backend server in another terminal by running: eval-mcp api\n", ms.cfg.APIURL)
		} else {
			resp.Body.Close()
		}
	}

	return server.ServeStdio(ms.server)
}

func (ms *MCPServer) callAPI(ctx context.Context, method, path string, payload interface{}) (string, error) {
	apiURL := strings.TrimSuffix(ms.cfg.APIURL, "/") + path
	var body io.Reader
	if payload != nil {
		b, err := json.Marshal(payload)
		if err != nil {
			return "", err
		}
		body = bytes.NewReader(b)
	}

	req, err := http.NewRequestWithContext(ctx, method, apiURL, body)
	if err != nil {
		return "", err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := ms.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("Backend API server is NOT running or unreachable at %s.\n\nPlease start the backend API server by running:\n  eval-mcp api\n\n(Error details: %v)", ms.cfg.APIURL, err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("Backend API error (%d): %s", resp.StatusCode, string(respBytes))
	}

	return string(respBytes), nil
}

func getArgMap(req mcp.CallToolRequest) map[string]interface{} {
	if m, ok := req.Params.Arguments.(map[string]interface{}); ok {
		return m
	}
	return make(map[string]interface{})
}

func getArgString(req mcp.CallToolRequest, key string) string {
	if m, ok := req.Params.Arguments.(map[string]interface{}); ok {
		if v, ok := m[key].(string); ok {
			return v
		}
	}
	return ""
}

func adaptRunEvalPayload(args map[string]interface{}) map[string]interface{} {
	payload := make(map[string]interface{})
	for k, v := range args {
		payload[k] = v
	}

	if dsName, ok := args["dataset_name"].(string); ok && dsName != "" {
		if _, hasRef := payload["dataset_reference"]; !hasRef {
			payload["dataset_reference"] = map[string]interface{}{"dataset_name": dsName}
		}
	}

	if pKey, ok := args["prompt_key"].(string); ok && pKey != "" {
		if _, hasRef := payload["prompt_reference"]; !hasRef {
			payload["prompt_reference"] = map[string]interface{}{"prompt_key": pKey}
		}
	} else if pID, ok := args["prompt_id"].(string); ok && pID != "" {
		if _, hasRef := payload["prompt_reference"]; !hasRef {
			payload["prompt_reference"] = map[string]interface{}{"prompt_id": pID}
		}
	}

	if pContent, ok := args["prompt_content"].(string); ok && pContent != "" {
		if _, hasAdHoc := payload["ad_hoc_prompt"]; !hasAdHoc {
			payload["ad_hoc_prompt"] = map[string]interface{}{
				"content": pContent,
			}
		}
	}
	return payload
}

func (ms *MCPServer) registerTools() {
	// 1. register_golden_dataset
	t1 := mcp.NewTool("register_golden_dataset",
		mcp.WithDescription("Register a golden dataset of test cases for prompt/RAG evaluations"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project slug or name")),
		mcp.WithString("dataset_name", mcp.Required(), mcp.Description("Dataset display name")),
		mcp.WithString("description", mcp.Description("Optional dataset description")),
	)
	ms.server.AddTool(t1, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/datasets/register", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 2. run_eval_suite
	t2 := mcp.NewTool("run_eval_suite",
		mcp.WithDescription("Run an evaluation suite over a dataset with specified metrics"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name/slug")),
		mcp.WithString("dataset_name", mcp.Description("Target dataset name")),
		mcp.WithString("prompt_key", mcp.Description("Registered prompt key")),
		mcp.WithString("prompt_content", mcp.Description("Ad-hoc prompt content")),
	)
	ms.server.AddTool(t2, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		payload := adaptRunEvalPayload(getArgMap(req))
		res, err := ms.callAPI(ctx, "POST", "/v1/runs/eval", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 3. compare_prompt_versions
	t3 := mcp.NewTool("compare_prompt_versions",
		mcp.WithDescription("Compare metric deltas between a baseline and candidate prompt"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
		mcp.WithString("dataset_name", mcp.Description("Dataset name")),
		mcp.WithString("baseline_prompt_key", mcp.Description("Baseline prompt key")),
		mcp.WithString("candidate_prompt_key", mcp.Description("Candidate prompt key")),
	)
	ms.server.AddTool(t3, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := getArgMap(req)
		payload := make(map[string]interface{})
		for k, v := range args {
			payload[k] = v
		}

		if dsName, ok := args["dataset_name"].(string); ok && dsName != "" {
			payload["dataset_reference"] = map[string]interface{}{"dataset_name": dsName}
		}
		if bKey, ok := args["baseline_prompt_key"].(string); ok && bKey != "" {
			payload["baseline_prompt_reference"] = map[string]interface{}{"prompt_key": bKey}
		}
		if cKey, ok := args["candidate_prompt_key"].(string); ok && cKey != "" {
			payload["candidate_prompt_reference"] = map[string]interface{}{"prompt_key": cKey}
		}

		res, err := ms.callAPI(ctx, "POST", "/v1/comparisons/prompt-versions", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 4. detect_regression
	t4 := mcp.NewTool("detect_regression",
		mcp.WithDescription("Detect metric regressions between candidate run and baseline run"),
		mcp.WithString("candidate_run_id", mcp.Required(), mcp.Description("Candidate evaluation run ID")),
		mcp.WithString("baseline_run_id", mcp.Description("Optional baseline run ID")),
	)
	ms.server.AddTool(t4, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/regressions/detect", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 5. score_rag_pipeline
	t5 := mcp.NewTool("score_rag_pipeline",
		mcp.WithDescription("Score RAG retrieval & generation pipeline with RAG metrics"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
		mcp.WithString("dataset_name", mcp.Description("Dataset name")),
	)
	ms.server.AddTool(t5, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		payload := adaptRunEvalPayload(getArgMap(req))
		res, err := ms.callAPI(ctx, "POST", "/v1/runs/rag", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 6. suggest_fix
	t6 := mcp.NewTool("suggest_fix",
		mcp.WithDescription("Queue LLM-as-a-judge to analyze failure clusters and suggest prompt improvements"),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Target run ID to analyze")),
	)
	ms.server.AddTool(t6, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/suggestions", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 7. get_latest_suggestion
	t7 := mcp.NewTool("get_latest_suggestion",
		mcp.WithDescription("Get the latest generated prompt fix suggestion for a run"),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Run ID")),
	)
	ms.server.AddTool(t7, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		runID := url.PathEscape(getArgString(req, "run_id"))
		res, err := ms.callAPI(ctx, "GET", "/v1/runs/"+runID+"/suggestions/latest", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 8. get_eval_history
	t8 := mcp.NewTool("get_eval_history",
		mcp.WithDescription("Query paginated evaluation run history for a project"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
	)
	ms.server.AddTool(t8, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/history/query", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 9. get_run_status
	t9 := mcp.NewTool("get_run_status",
		mcp.WithDescription("Get current status and pass rate of an evaluation run"),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Run ID")),
	)
	ms.server.AddTool(t9, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		runID := url.PathEscape(getArgString(req, "run_id"))
		res, err := ms.callAPI(ctx, "GET", "/v1/runs/"+runID+"/status", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 10. list_projects
	t10 := mcp.NewTool("list_projects",
		mcp.WithDescription("List all evaluation projects"),
	)
	ms.server.AddTool(t10, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "GET", "/v1/projects", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 11. list_datasets
	t11 := mcp.NewTool("list_datasets",
		mcp.WithDescription("List datasets registered under a project"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
	)
	ms.server.AddTool(t11, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		proj := url.PathEscape(getArgString(req, "project"))
		res, err := ms.callAPI(ctx, "GET", "/v1/projects/"+proj+"/datasets", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 12. list_prompts
	t12 := mcp.NewTool("list_prompts",
		mcp.WithDescription("List prompts registered under a project"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
	)
	ms.server.AddTool(t12, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		proj := url.PathEscape(getArgString(req, "project"))
		res, err := ms.callAPI(ctx, "GET", "/v1/projects/"+proj+"/prompts", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 13. set_baseline_run
	t13 := mcp.NewTool("set_baseline_run",
		mcp.WithDescription("Set the default baseline evaluation run for a project"),
		mcp.WithString("project", mcp.Required(), mcp.Description("Project name")),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Run ID to set as baseline")),
	)
	ms.server.AddTool(t13, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/baselines/set", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 14. rerun_failed_cases
	t14 := mcp.NewTool("rerun_failed_cases",
		mcp.WithDescription("Rerun only failing test cases from a previous evaluation run"),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Previous run ID")),
	)
	ms.server.AddTool(t14, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/runs/rerun-failed", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 15. annotate_run
	t15 := mcp.NewTool("annotate_run",
		mcp.WithDescription("Attach a label or note annotation to an evaluation run"),
		mcp.WithString("run_id", mcp.Required(), mcp.Description("Run ID")),
		mcp.WithString("label", mcp.Required(), mcp.Description("Annotation label")),
	)
	ms.server.AddTool(t15, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "POST", "/v1/runs/annotate", req.Params.Arguments)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})

	// 16. get_supported_metrics
	t16 := mcp.NewTool("get_supported_metrics",
		mcp.WithDescription("Get list of all supported evaluation metrics and features"),
	)
	ms.server.AddTool(t16, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		res, err := ms.callAPI(ctx, "GET", "/v1/meta/supported-metrics", nil)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return mcp.NewToolResultText(res), nil
	})
}

// Suppress unused imports
var _ = time.Second
