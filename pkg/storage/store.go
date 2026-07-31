package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/google/uuid"
)

type StoreData struct {
	Projects    []domain.Project           `json:"projects"`
	Prompts     []domain.Prompt            `json:"prompts"`
	Datasets    []domain.Dataset           `json:"datasets"`
	Cases       []domain.DatasetCase       `json:"cases"`
	Runs        []domain.EvalRun           `json:"runs"`
	CaseResults []domain.EvalCaseResult   `json:"case_results"`
	Suggestions []domain.SuggestionResponse `json:"suggestions"`
	Annotations []domain.AnnotationRead     `json:"annotations"`
}

type MemoryStore struct {
	mu          sync.RWMutex
	filePath    string
	projects    map[string]domain.Project           // key: ID or slug
	prompts     map[string]domain.Prompt            // key: ID
	datasets    map[string]domain.Dataset           // key: ID
	cases       map[string]domain.DatasetCase       // key: ID
	runs        map[string]*domain.EvalRun          // key: Public RunID
	caseResults map[string][]domain.EvalCaseResult  // key: Public RunID
	suggestions map[string][]domain.SuggestionResponse // key: Public RunID
	annotations map[string][]domain.AnnotationRead  // key: Public RunID
}

func NewMemoryStore(dataDir string) (*MemoryStore, error) {
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, err
	}
	fp := filepath.Join(dataDir, "db.json")

	store := &MemoryStore{
		filePath:    fp,
		projects:    make(map[string]domain.Project),
		prompts:     make(map[string]domain.Prompt),
		datasets:    make(map[string]domain.Dataset),
		cases:       make(map[string]domain.DatasetCase),
		runs:        make(map[string]*domain.EvalRun),
		caseResults: make(map[string][]domain.EvalCaseResult),
		suggestions: make(map[string][]domain.SuggestionResponse),
		annotations: make(map[string][]domain.AnnotationRead),
	}

	_ = store.load()
	return store, nil
}

func (s *MemoryStore) load() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.loadUnlocked()
}

func (s *MemoryStore) loadUnlocked() error {
	data, err := os.ReadFile(s.filePath)
	if err != nil {
		return err
	}

	var d StoreData
	if err := json.Unmarshal(data, &d); err != nil {
		return err
	}

	for _, p := range d.Projects {
		s.projects[p.ID] = p
		s.projects[p.Slug] = p
	}
	for _, pr := range d.Prompts {
		s.prompts[pr.ID] = pr
	}
	for _, ds := range d.Datasets {
		s.datasets[ds.ID] = ds
	}
	for _, c := range d.Cases {
		s.cases[c.ID] = c
	}
	for i := range d.Runs {
		r := d.Runs[i]
		s.runs[r.RunID] = &r
	}
	for _, cr := range d.CaseResults {
		s.caseResults[cr.RunID] = append(s.caseResults[cr.RunID], cr)
	}
	for _, sg := range d.Suggestions {
		s.suggestions[sg.RunID] = append(s.suggestions[sg.RunID], sg)
	}
	for _, an := range d.Annotations {
		s.annotations[an.RunID] = append(s.annotations[an.RunID], an)
	}
	return nil
}

func (s *MemoryStore) saveUnlocked() error {
	var d StoreData
	seenProj := make(map[string]bool)
	for _, p := range s.projects {
		if !seenProj[p.ID] {
			seenProj[p.ID] = true
			d.Projects = append(d.Projects, p)
		}
	}
	for _, pr := range s.prompts {
		d.Prompts = append(d.Prompts, pr)
	}
	for _, ds := range s.datasets {
		d.Datasets = append(d.Datasets, ds)
	}
	for _, c := range s.cases {
		d.Cases = append(d.Cases, c)
	}
	for _, r := range s.runs {
		d.Runs = append(d.Runs, *r)
	}
	for _, crs := range s.caseResults {
		d.CaseResults = append(d.CaseResults, crs...)
	}
	for _, sgs := range s.suggestions {
		d.Suggestions = append(d.Suggestions, sgs...)
	}
	for _, ans := range s.annotations {
		d.Annotations = append(d.Annotations, ans...)
	}

	bytes, err := json.MarshalIndent(d, "", "  ")
	if err != nil {
		return err
	}
	tmpFile := s.filePath + ".tmp"
	if err := os.WriteFile(tmpFile, bytes, 0644); err != nil {
		return err
	}
	return os.Rename(tmpFile, s.filePath)
}

// Project methods
func (s *MemoryStore) GetProject(identifier string) (domain.Project, bool) {
	s.mu.RLock()
	p, found := s.projects[identifier]
	s.mu.RUnlock()
	if found {
		return p, true
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	p, found = s.projects[identifier]
	return p, found
}

func (s *MemoryStore) GetOrCreateProject(identifier string) (domain.Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if p, found := s.projects[identifier]; found {
		return p, nil
	}

	id := uuid.New().String()
	p := domain.Project{
		ID:        id,
		Slug:      identifier,
		Name:      identifier,
		CreatedAt: time.Now(),
	}
	s.projects[id] = p
	s.projects[identifier] = p
	_ = s.saveUnlocked()
	return p, nil
}

func (s *MemoryStore) ListProjects() []domain.Project {
	s.mu.RLock()
	defer s.mu.RUnlock()

	seen := make(map[string]bool)
	var list []domain.Project
	for _, p := range s.projects {
		if !seen[p.ID] {
			seen[p.ID] = true
			list = append(list, p)
		}
	}
	sort.Slice(list, func(i, j int) bool {
		return list[i].CreatedAt.After(list[j].CreatedAt)
	})
	return list
}

func (s *MemoryStore) SetProjectBaseline(projectID, runID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if p, found := s.projects[projectID]; found {
		p.DefaultBaselineRunID = runID
		s.projects[p.ID] = p
		s.projects[p.Slug] = p
		_ = s.saveUnlocked()
		return nil
	}
	return fmt.Errorf("project not found")
}

// Prompt methods
func (s *MemoryStore) SavePrompt(prompt domain.Prompt) domain.Prompt {
	s.mu.Lock()
	defer s.mu.Unlock()

	if prompt.ID == "" {
		prompt.ID = uuid.New().String()
	}
	if prompt.CreatedAt.IsZero() {
		prompt.CreatedAt = time.Now()
	}
	s.prompts[prompt.ID] = prompt
	_ = s.saveUnlocked()
	return prompt
}

func (s *MemoryStore) GetPrompt(id string) (domain.Prompt, bool) {
	s.mu.RLock()
	p, ok := s.prompts[id]
	s.mu.RUnlock()
	if ok {
		return p, true
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	p, ok = s.prompts[id]
	return p, ok
}

func (s *MemoryStore) GetPromptByKeyAndVersion(projectID, promptKey string, version int) (domain.Prompt, bool) {
	s.mu.RLock()
	for _, p := range s.prompts {
		if (p.ProjectID == projectID || projectID == "") && p.PromptKey == promptKey && (version <= 0 || p.Version == version) {
			s.mu.RUnlock()
			return p, true
		}
	}
	s.mu.RUnlock()

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	for _, p := range s.prompts {
		if (p.ProjectID == projectID || projectID == "") && p.PromptKey == promptKey && (version <= 0 || p.Version == version) {
			return p, true
		}
	}
	return domain.Prompt{}, false
}

func (s *MemoryStore) ListPrompts(projectID string) []domain.Prompt {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var list []domain.Prompt
	for _, p := range s.prompts {
		if p.ProjectID == projectID {
			list = append(list, p)
		}
	}
	return list
}

// Dataset methods
func (s *MemoryStore) SaveDataset(ds domain.Dataset, cases []domain.DatasetCaseInput) (domain.Dataset, []domain.DatasetCase) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if ds.ID == "" {
		ds.ID = uuid.New().String()
	}
	ds.CreatedAt = time.Now()
	ds.CaseCount = len(cases)
	s.datasets[ds.ID] = ds

	var storedCases []domain.DatasetCase
	for i, c := range cases {
		dc := domain.DatasetCase{
			ID:             uuid.New().String(),
			DatasetID:      ds.ID,
			CaseIndex:      i,
			InputText:      c.InputText,
			ExpectedOutput: c.ExpectedOutput,
			Context:        c.Context,
			Labels:         c.Labels,
			Metadata:       c.Metadata,
		}
		s.cases[dc.ID] = dc
		storedCases = append(storedCases, dc)
	}
	_ = s.saveUnlocked()
	return ds, storedCases
}

func (s *MemoryStore) GetDataset(projectID, identifier string) (domain.Dataset, []domain.DatasetCase, bool) {
	s.mu.RLock()
	ds, cases, found := s.getDatasetUnlocked(projectID, identifier)
	s.mu.RUnlock()
	if found {
		return ds, cases, true
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	return s.getDatasetUnlocked(projectID, identifier)
}

func (s *MemoryStore) getDatasetUnlocked(projectID, identifier string) (domain.Dataset, []domain.DatasetCase, bool) {
	var targetDS *domain.Dataset
	for _, ds := range s.datasets {
		if (ds.ProjectID == projectID || projectID == "") && (ds.ID == identifier || ds.DatasetName == identifier) {
			dsCopy := ds
			targetDS = &dsCopy
			break
		}
	}
	if targetDS == nil {
		return domain.Dataset{}, nil, false
	}

	var cases []domain.DatasetCase
	for _, c := range s.cases {
		if c.DatasetID == targetDS.ID {
			cases = append(cases, c)
		}
	}
	sort.Slice(cases, func(i, j int) bool {
		return cases[i].CaseIndex < cases[j].CaseIndex
	})
	return *targetDS, cases, true
}

func (s *MemoryStore) ListDatasets(projectID string) []domain.Dataset {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var list []domain.Dataset
	for _, ds := range s.datasets {
		if ds.ProjectID == projectID {
			list = append(list, ds)
		}
	}
	return list
}

// Run methods
func (s *MemoryStore) SaveRun(run domain.EvalRun) *domain.EvalRun {
	s.mu.Lock()
	defer s.mu.Unlock()

	if run.ID == "" {
		run.ID = uuid.New().String()
	}
	if run.CreatedAt.IsZero() {
		run.CreatedAt = time.Now()
	}
	s.runs[run.RunID] = &run
	_ = s.saveUnlocked()
	return &run
}

func (s *MemoryStore) GetRun(runID string) (*domain.EvalRun, bool) {
	s.mu.RLock()
	r, ok := s.runs[runID]
	s.mu.RUnlock()
	if ok {
		return r, true
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	r, ok = s.runs[runID]
	return r, ok
}

func (s *MemoryStore) FindCachedRun(projectID, cacheKey string, runType domain.RunType) *domain.EvalRun {
	s.mu.RLock()
	defer s.mu.RUnlock()

	for _, r := range s.runs {
		if r.ProjectID == projectID && r.CacheKey == cacheKey && r.RunType == runType && r.Status == domain.StatusCompleted {
			return r
		}
	}
	return nil
}

func (s *MemoryStore) FindInflightRun(projectID, cacheKey string, runType domain.RunType) *domain.EvalRun {
	s.mu.RLock()
	defer s.mu.RUnlock()

	for _, r := range s.runs {
		if r.ProjectID == projectID && r.CacheKey == cacheKey && r.RunType == runType && (r.Status == domain.StatusQueued || r.Status == domain.StatusRunning) {
			return r
		}
	}
	return nil
}

func (s *MemoryStore) UpdateRunStatus(runID string, status domain.RunStatus, errStr string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if r, ok := s.runs[runID]; ok {
		r.Status = status
		now := time.Now()
		if status == domain.StatusRunning && r.StartedAt == nil {
			r.StartedAt = &now
		} else if status == domain.StatusCompleted || status == domain.StatusFailed {
			r.CompletedAt = &now
		}
		if errStr != "" {
			r.ErrorMessage = errStr
		}
		_ = s.saveUnlocked()
	}
}

func (s *MemoryStore) UpdateRunProgress(runID string, processed, total int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if r, ok := s.runs[runID]; ok {
		r.ProcessedCases = processed
		r.TotalCases = total
		if processed == total || (total > 0 && processed%(maxInt(1, total/10)) == 0) {
			_ = s.saveUnlocked()
		}
	}
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func (s *MemoryStore) SaveCaseResults(runID string, results []domain.EvalCaseResult) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.caseResults[runID] = append(s.caseResults[runID], results...)
	_ = s.saveUnlocked()
}

func (s *MemoryStore) GetCaseResults(runID string) []domain.EvalCaseResult {
	s.mu.RLock()
	res, found := s.caseResults[runID]
	s.mu.RUnlock()
	if found && len(res) > 0 {
		return res
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	return s.caseResults[runID]
}

func (s *MemoryStore) SaveSuggestion(runID string, resp domain.SuggestionResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.suggestions[runID] = append(s.suggestions[runID], resp)
	_ = s.saveUnlocked()
}

func (s *MemoryStore) GetLatestSuggestion(runID string) (domain.SuggestionResponse, bool) {
	s.mu.RLock()
	list := s.suggestions[runID]
	s.mu.RUnlock()
	if len(list) > 0 {
		return list[len(list)-1], true
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.loadUnlocked()
	list = s.suggestions[runID]
	if len(list) == 0 {
		return domain.SuggestionResponse{}, false
	}
	return list[len(list)-1], true
}

func (s *MemoryStore) SaveAnnotation(ann domain.AnnotationRead) {
	s.mu.Lock()
	defer s.mu.Unlock()

	ann.ID = uuid.New().String()
	ann.CreatedAt = time.Now()
	s.annotations[ann.RunID] = append(s.annotations[ann.RunID], ann)
	_ = s.saveUnlocked()
}

func (s *MemoryStore) QueryHistory(filters domain.HistoryFilters) ([]domain.RunSummary, int) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var matched []domain.RunSummary
	for _, r := range s.runs {
		if filters.Project != "" && r.ProjectID != filters.Project {
			proj, found := s.projects[filters.Project]
			if !found || r.ProjectID != proj.ID {
				continue
			}
		}
		if filters.Status != "" && r.Status != filters.Status {
			continue
		}

		projSlug := r.ProjectID
		if p, ok := s.projects[r.ProjectID]; ok {
			projSlug = p.Slug
		}

		summary := domain.RunSummary{
			RunID:          r.RunID,
			ProjectSlug:    projSlug,
			RunType:        r.RunType,
			Status:         r.Status,
			Metrics:        r.MetricsRequested,
			PassRate:       r.PassRate,
			ProcessedCases: r.ProcessedCases,
			TotalCases:     r.TotalCases,
			IsCachedResult: r.IsCachedResult,
			CreatedAt:      r.CreatedAt,
			StartedAt:      r.StartedAt,
			CompletedAt:    r.CompletedAt,
			ErrorMessage:   r.ErrorMessage,
		}
		matched = append(matched, summary)
	}

	sort.Slice(matched, func(i, j int) bool {
		return matched[i].CreatedAt.After(matched[j].CreatedAt)
	})

	total := len(matched)
	page := filters.Page
	if page < 1 {
		page = 1
	}
	pageSize := filters.PageSize
	if pageSize < 1 {
		pageSize = 20
	}

	start := (page - 1) * pageSize
	if start >= total {
		return []domain.RunSummary{}, total
	}
	end := start + pageSize
	if end > total {
		end = total
	}

	return matched[start:end], total
}
