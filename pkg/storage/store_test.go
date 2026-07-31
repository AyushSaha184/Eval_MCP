package storage

import (
	"os"
	"testing"

	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
)

func TestMemoryStore(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "eval_mcp_test_*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	store, err := NewMemoryStore(tempDir)
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}

	proj, err := store.GetOrCreateProject("test-project")
	if err != nil {
		t.Fatalf("failed project create: %v", err)
	}
	if proj.Slug != "test-project" {
		t.Errorf("expected slug 'test-project', got '%s'", proj.Slug)
	}

	ds, _ := store.SaveDataset(domain.Dataset{
		ProjectID:   proj.ID,
		DatasetName: "my-dataset",
	}, []domain.DatasetCaseInput{
		{InputText: "Input 1", ExpectedOutput: "Output 1"},
	})

	gotDS, cases, found := store.GetDataset(proj.ID, "my-dataset")
	if !found {
		t.Fatalf("expected dataset to be found")
	}
	if gotDS.ID != ds.ID {
		t.Errorf("expected dataset ID %s, got %s", ds.ID, gotDS.ID)
	}
	if len(cases) != 1 {
		t.Errorf("expected 1 case, got %d", len(cases))
	}
}
