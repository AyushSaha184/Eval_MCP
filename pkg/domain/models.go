package domain

import (
	"time"
)

// Project represents an evaluation project.
type Project struct {
	ID                   string    `json:"id"`
	Slug                 string    `json:"slug"`
	Name                 string    `json:"name"`
	Description          string    `json:"description,omitempty"`
	DefaultBaselineRunID string    `json:"default_baseline_run_id,omitempty"`
	CreatedAt            time.Time `json:"created_at"`
}

// Prompt represents a versioned prompt template.
type Prompt struct {
	ID           string                 `json:"id"`
	ProjectID    string                 `json:"project_id"`
	PromptKey    string                 `json:"prompt_key"`
	Version      int                    `json:"version"`
	Content      string                 `json:"content"`
	SystemPrompt string                 `json:"system_prompt,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	CreatedAt    time.Time              `json:"created_at"`
}

// PromptReference identifies a prompt by ID or key+version.
type PromptReference struct {
	PromptID  string `json:"prompt_id,omitempty"`
	PromptKey string `json:"prompt_key,omitempty"`
	Version   *int   `json:"version,omitempty"`
}

// AdHocPrompt allows inline prompt content without prior registration.
type AdHocPrompt struct {
	PromptKey    string                 `json:"prompt_key,omitempty"`
	Content      string                 `json:"content"`
	SystemPrompt string                 `json:"system_prompt,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// Dataset represents a collection of test cases.
type Dataset struct {
	ID          string                 `json:"id"`
	ProjectID   string                 `json:"project_id"`
	DatasetName string                 `json:"dataset_name"`
	VersionHash string                 `json:"version_hash"`
	Description string                 `json:"description,omitempty"`
	Tags        []string               `json:"tags,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
	CaseCount   int                    `json:"case_count"`
	CreatedAt   time.Time              `json:"created_at"`
}

// DatasetCaseInput defines a single test case for dataset registration.
type DatasetCaseInput struct {
	InputText      string                 `json:"input_text"`
	ExpectedOutput string                 `json:"expected_output,omitempty"`
	Context        []string               `json:"context,omitempty"`
	Labels         []string               `json:"labels,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// DatasetCase represents a stored test case.
type DatasetCase struct {
	ID             string                 `json:"id"`
	DatasetID      string                 `json:"dataset_id"`
	CaseIndex      int                    `json:"case_index"`
	InputText      string                 `json:"input_text"`
	ExpectedOutput string                 `json:"expected_output,omitempty"`
	Context        []string               `json:"context,omitempty"`
	Labels         []string               `json:"labels,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// DatasetReference identifies a dataset by ID or name+hash.
type DatasetReference struct {
	DatasetID   string `json:"dataset_id,omitempty"`
	DatasetName string `json:"dataset_name,omitempty"`
	VersionHash string `json:"version_hash,omitempty"`
}

// DatasetRegistration request.
type DatasetRegistration struct {
	Project     string                 `json:"project"`
	DatasetName string                 `json:"dataset_name"`
	Description string                 `json:"description,omitempty"`
	Tags        []string               `json:"tags,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
	Cases       []DatasetCaseInput     `json:"cases"`
}

// ModelConfig specifies the LLM configuration.
type ModelConfig struct {
	Provider   string                 `json:"provider"`
	ModelName  string                 `json:"model_name"`
	Temperature float64               `json:"temperature"`
	MaxTokens  int                    `json:"max_tokens"`
	Extra      map[string]interface{} `json:"extra,omitempty"`
}

// RetrieverConfig specifies RAG retrieval settings.
type RetrieverConfig struct {
	Provider  string                 `json:"provider"`
	IndexName string                 `json:"index_name,omitempty"`
	TopK      int                    `json:"top_k"`
	Extra     map[string]interface{} `json:"extra,omitempty"`
}

// RuntimeConfig specifies execution parameters.
type RuntimeConfig struct {
	MaxConcurrency       int                    `json:"max_concurrency"`
	TimeoutSeconds       int                    `json:"timeout_seconds"`
	CaseLimit            *int                   `json:"case_limit,omitempty"`
	SelectedCaseIndices  []int                  `json:"selected_case_indices,omitempty"`
	IncludeArtifacts     bool                   `json:"include_artifacts"`
	Labels               []string               `json:"labels,omitempty"`
	Extra                map[string]interface{} `json:"extra,omitempty"`
}

// RunEvalRequest options.
type RunEvalRequest struct {
	Project          string           `json:"project"`
	PromptReference  *PromptReference `json:"prompt_reference,omitempty"`
	AdHocPrompt      *AdHocPrompt     `json:"ad_hoc_prompt,omitempty"`
	DatasetReference DatasetReference `json:"dataset_reference"`
	Metrics          []string         `json:"metrics"`
	ModelConfig      ModelConfig      `json:"model_config"`
	RuntimeConfig    RuntimeConfig    `json:"runtime_config"`
	TriggerSource    TriggerSource    `json:"trigger_source"`
	TriggeredBy      string           `json:"triggered_by,omitempty"`
	BaselineRunID    string           `json:"baseline_run_id,omitempty"`
	ForceRerun       bool             `json:"force_rerun"`
}

// RagCaseInput for inline RAG scoring.
type RagCaseInput struct {
	Query           string                 `json:"query"`
	ExpectedOutput  string                 `json:"expected_output,omitempty"`
	ExpectedContext []string               `json:"expected_context,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// RagScoreRequest options.
type RagScoreRequest struct {
	Project          string            `json:"project"`
	DatasetReference *DatasetReference `json:"dataset_reference,omitempty"`
	DatasetName      string            `json:"dataset_name,omitempty"`
	Cases            []RagCaseInput    `json:"cases,omitempty"`
	PromptReference  *PromptReference  `json:"prompt_reference,omitempty"`
	AdHocPrompt      *AdHocPrompt      `json:"ad_hoc_prompt,omitempty"`
	RetrieverConfig  RetrieverConfig   `json:"retriever_config"`
	Metrics          []string          `json:"metrics"`
	ModelConfig      ModelConfig       `json:"model_config"`
	RuntimeConfig    RuntimeConfig     `json:"runtime_config"`
	TriggerSource    TriggerSource     `json:"trigger_source"`
	TriggeredBy      string            `json:"triggered_by,omitempty"`
	ForceRerun       bool              `json:"force_rerun"`
}

// RunQueued response envelope.
type RunQueued struct {
	RunID       string    `json:"run_id"`
	Status      RunStatus `json:"status"`
	Cached      bool      `json:"cached"`
	CacheKey    string    `json:"cache_key"`
	SourceRunID string    `json:"source_run_id,omitempty"`
}

// NormalizedMetricResult holds a calculated score.
type NormalizedMetricResult struct {
	MetricName   string                 `json:"metric_name"`
	MetricFamily string                 `json:"metric_family"`
	Score        float64                `json:"score"`
	Threshold    *float64               `json:"threshold,omitempty"`
	Direction    MetricDirection        `json:"direction"`
	Passed       *bool                  `json:"passed,omitempty"`
	Details      map[string]interface{} `json:"details,omitempty"`
}

// EvalRun represents an evaluation run record.
type EvalRun struct {
	ID                     string                 `json:"id"`
	RunID                  string                 `json:"run_id"`
	ProjectID              string                 `json:"project_id"`
	RunType                RunType                `json:"run_type"`
	Status                 RunStatus              `json:"status"`
	TriggerSource          TriggerSource          `json:"trigger_source"`
	TriggeredBy            string                 `json:"triggered_by,omitempty"`
	PromptRefID            string                 `json:"prompt_ref_id,omitempty"`
	DatasetRefID           string                 `json:"dataset_ref_id,omitempty"`
	BaselineRunID          string                 `json:"baseline_run_id,omitempty"`
	MetricsRequested       []string               `json:"metrics_requested"`
	PassRate               *float64               `json:"pass_rate,omitempty"`
	CreatedAt              time.Time              `json:"created_at"`
	StartedAt              *time.Time             `json:"started_at,omitempty"`
	CompletedAt            *time.Time             `json:"completed_at,omitempty"`
	ErrorMessage           string                 `json:"error_message,omitempty"`
	CacheKey               string                 `json:"cache_key"`
	IsCachedResult         bool                   `json:"is_cached_result"`
	TotalCases             int                    `json:"total_cases"`
	ProcessedCases         int                    `json:"processed_cases"`
	AttemptCount           int                    `json:"attempt_count"`
	PromptSnapshot         map[string]interface{} `json:"prompt_snapshot,omitempty"`
	DatasetSnapshot        map[string]interface{} `json:"dataset_snapshot,omitempty"`
	ModelConfigSnapshot    map[string]interface{} `json:"model_config_snapshot,omitempty"`
	RetrieverConfigSnapshot map[string]interface{} `json:"retriever_config_snapshot,omitempty"`
	RuntimeConfigSnapshot   map[string]interface{} `json:"runtime_config_snapshot,omitempty"`
}

// EvalCaseResult stores single case results.
type EvalCaseResult struct {
	ID                     string                   `json:"id"`
	RunID                  string                   `json:"run_id"`
	DatasetCaseID          string                   `json:"dataset_case_id,omitempty"`
	CaseIndex              int                      `json:"case_index"`
	InputTextSnapshot      string                   `json:"input_text_snapshot"`
	ActualOutput           string                   `json:"actual_output,omitempty"`
	ExpectedOutputSnapshot string                   `json:"expected_output_snapshot,omitempty"`
	RetrievedContextSnapshot []string               `json:"retrieved_context_snapshot,omitempty"`
	LatencyMS              int                      `json:"latency_ms"`
	TokenUsage             map[string]interface{}   `json:"token_usage,omitempty"`
	Status                 CaseResultStatus         `json:"status"`
	FailureReason          string                   `json:"failure_reason,omitempty"`
	Metrics                []NormalizedMetricResult `json:"metrics,omitempty"`
}

// RunStatusResponse for polling endpoints.
type RunStatusResponse struct {
	RunID             string             `json:"run_id"`
	Status            RunStatus          `json:"status"`
	RunType           RunType            `json:"run_type"`
	ProcessedCases    int                `json:"processed_cases"`
	TotalCases        int                `json:"total_cases"`
	PassRate          *float64           `json:"pass_rate,omitempty"`
	StartedAt         *time.Time         `json:"started_at,omitempty"`
	CompletedAt       *time.Time         `json:"completed_at,omitempty"`
	ErrorMessage      string             `json:"error_message,omitempty"`
	IsCachedResult    bool               `json:"is_cached_result"`
	SuggestionSummary *SuggestionSummary `json:"suggestion_summary,omitempty"`
}

// HistoryFilters parameters.
type HistoryFilters struct {
	Project     string     `json:"project"`
	PromptKey   string     `json:"prompt_key,omitempty"`
	DatasetName string     `json:"dataset_name,omitempty"`
	Status      RunStatus  `json:"status,omitempty"`
	StartDate   *time.Time `json:"start_date,omitempty"`
	EndDate     *time.Time `json:"end_date,omitempty"`
	Label       string     `json:"label,omitempty"`
	Page        int        `json:"page"`
	PageSize    int        `json:"page_size"`
}

// RunSummary overview struct.
type RunSummary struct {
	RunID               string     `json:"run_id"`
	ProjectSlug         string     `json:"project_slug"`
	RunType             RunType    `json:"run_type"`
	Status              RunStatus  `json:"status"`
	PromptKey           string     `json:"prompt_key,omitempty"`
	PromptVersion       *int       `json:"prompt_version,omitempty"`
	DatasetName         string     `json:"dataset_name,omitempty"`
	DatasetVersionHash  string     `json:"dataset_version_hash,omitempty"`
	Metrics             []string   `json:"metrics"`
	PassRate            *float64   `json:"pass_rate,omitempty"`
	ProcessedCases      int        `json:"processed_cases"`
	TotalCases          int        `json:"total_cases"`
	IsCachedResult      bool       `json:"is_cached_result"`
	CreatedAt           time.Time  `json:"created_at"`
	StartedAt           *time.Time `json:"started_at,omitempty"`
	CompletedAt         *time.Time `json:"completed_at,omitempty"`
	ErrorMessage        string     `json:"error_message,omitempty"`
	Labels              []string   `json:"labels,omitempty"`
}

// HistoryResponse paginated output.
type HistoryResponse struct {
	Items    []RunSummary `json:"items"`
	Total    int          `json:"total"`
	Page     int          `json:"page"`
	PageSize int          `json:"page_size"`
}

// CompareRequest compare prompt versions.
type CompareRequest struct {
	Project                  string           `json:"project"`
	BaselinePromptReference PromptReference  `json:"baseline_prompt_reference"`
	CandidatePromptReference PromptReference `json:"candidate_prompt_reference"`
	DatasetReference        DatasetReference `json:"dataset_reference"`
	Metrics                  []string         `json:"metrics"`
	ModelConfig              ModelConfig      `json:"model_config"`
	RuntimeConfig            RuntimeConfig    `json:"runtime_config"`
	TriggerSource            TriggerSource    `json:"trigger_source"`
	TriggeredBy              string           `json:"triggered_by,omitempty"`
	ForceRerun               bool             `json:"force_rerun"`
}

// MetricDelta for comparison.
type MetricDelta struct {
	MetricName     string          `json:"metric_name"`
	Direction      MetricDirection `json:"direction"`
	BaselineScore  *float64        `json:"baseline_score,omitempty"`
	CandidateScore *float64        `json:"candidate_score,omitempty"`
	Delta          *float64        `json:"delta,omitempty"`
	Improved       bool            `json:"improved"`
	Regressed      bool            `json:"regressed"`
}

// CompareResponse output.
type CompareResponse struct {
	Status           string        `json:"status"`
	BaselineRunID    string        `json:"baseline_run_id"`
	CandidateRunID   string        `json:"candidate_run_id"`
	Deltas           []MetricDelta `json:"deltas"`
	ImprovedMetrics  []string      `json:"improved_metrics"`
	RegressedMetrics []string      `json:"regressed_metrics"`
	UnchangedMetrics []string      `json:"unchanged_metrics"`
}

// RegressionThreshold for custom regression rules.
type RegressionThreshold struct {
	MetricName   string  `json:"metric_name"`
	AllowedDelta float64 `json:"allowed_delta"`
}

// RegressionRequest input.
type RegressionRequest struct {
	CandidateRunID string                `json:"candidate_run_id"`
	BaselineRunID  string                `json:"baseline_run_id,omitempty"`
	Project        string                `json:"project,omitempty"`
	Thresholds     []RegressionThreshold `json:"thresholds,omitempty"`
}

// RegressionMetricOutcome detailed metric outcome.
type RegressionMetricOutcome struct {
	MetricName    string          `json:"metric_name"`
	BaselineScore *float64        `json:"baseline_score,omitempty"`
	CandidateScore *float64        `json:"candidate_score,omitempty"`
	Delta         *float64        `json:"delta,omitempty"`
	Direction     MetricDirection `json:"direction"`
	AllowedDelta  float64         `json:"allowed_delta"`
	Regressed     bool            `json:"regressed"`
}

// RegressionResponse output.
type RegressionResponse struct {
	BaselineRunID   string                    `json:"baseline_run_id"`
	CandidateRunID  string                    `json:"candidate_run_id"`
	IsRegression    bool                      `json:"is_regression"`
	AffectedMetrics []RegressionMetricOutcome `json:"affected_metrics"`
}

// FailureCluster group of related failed cases.
type FailureCluster struct {
	ClusterKey    string   `json:"cluster_key"`
	Title         string   `json:"title"`
	MetricName    string   `json:"metric_name,omitempty"`
	CaseResultIDs []string `json:"case_result_ids"`
	Size          int      `json:"size"`
	SampleInputs  []string `json:"sample_inputs"`
}

// SuggestFixRequest input.
type SuggestFixRequest struct {
	RunID        string `json:"run_id"`
	CaseLimit    int    `json:"case_limit"`
	ClusterLimit int    `json:"cluster_limit"`
	ModelName    string `json:"model_name,omitempty"`
}

// SuggestionSummary overview.
type SuggestionSummary struct {
	ID     string `json:"id"`
	RunID  string `json:"run_id"`
	Status string `json:"status"`
}

// SuggestionResponse output.
type SuggestionResponse struct {
	ID              string           `json:"id"`
	RunID           string           `json:"run_id"`
	Summary         string           `json:"summary"`
	SuggestionText  string           `json:"suggestion_text"`
	FailureClusters []FailureCluster `json:"failure_clusters"`
	ModelName       string           `json:"model_name"`
	CreatedAt       time.Time        `json:"created_at"`
}

// BaselineSetRequest input.
type BaselineSetRequest struct {
	Project string `json:"project"`
	RunID   string `json:"run_id"`
}

// AnnotationRequest input.
type AnnotationRequest struct {
	RunID     string `json:"run_id"`
	Label     string `json:"label"`
	Note      string `json:"note,omitempty"`
	CreatedBy string `json:"created_by,omitempty"`
}

// AnnotationRead output.
type AnnotationRead struct {
	ID        string    `json:"id"`
	RunID     string    `json:"run_id"`
	Label     string    `json:"label"`
	Note      string    `json:"note,omitempty"`
	CreatedBy string    `json:"created_by,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// SupportedMetric overview.
type SupportedMetric struct {
	Name             string          `json:"name"`
	Provider         string          `json:"provider"`
	Family           string          `json:"family"`
	Direction        MetricDirection `json:"direction"`
	DefaultThreshold *float64        `json:"default_threshold,omitempty"`
	Levels           []string        `json:"levels"`
	Description      string          `json:"description,omitempty"`
}

// SupportedMetricsResponse output.
type SupportedMetricsResponse struct {
	Metrics         []SupportedMetric `json:"metrics"`
	RunTypes        []RunType         `json:"run_types"`
	StorageProvider string            `json:"storage_provider"`
	QueueBackend    string            `json:"queue_backend"`
}

// RerunFailedRequest input.
type RerunFailedRequest struct {
	RunID       string `json:"run_id"`
	TriggeredBy string `json:"triggered_by,omitempty"`
	ForceRerun  bool   `json:"force_rerun"`
}
