package mcp

import (
	"context"
	"strings"
	"testing"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
)

func TestBackendOfflineError(t *testing.T) {
	cfg := config.Load()
	cfg.APIURL = "http://127.0.0.1:59999" // intentionally unreachable port

	ms := NewMCPServer(cfg)
	ctx := context.Background()

	_, err := ms.callAPI(ctx, "GET", "/v1/projects", nil)
	if err == nil {
		t.Fatalf("expected error when backend is offline, got nil")
	}

	errMsg := err.Error()
	if !strings.Contains(errMsg, "Backend API server is NOT running or unreachable") {
		t.Errorf("expected user-friendly offline message, got: %s", errMsg)
	}
	if !strings.Contains(errMsg, "eval-mcp api") {
		t.Errorf("expected instructions to run 'eval-mcp api', got: %s", errMsg)
	}
}
