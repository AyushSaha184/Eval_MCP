package domain

type RunStatus string

const (
	StatusQueued    RunStatus = "queued"
	StatusRunning   RunStatus = "running"
	StatusCompleted RunStatus = "completed"
	StatusFailed    RunStatus = "failed"
	StatusCancelled RunStatus = "cancelled"
)

type RunType string

const (
	RunTypePromptEval            RunType = "prompt_eval"
	RunTypeRagEval               RunType = "rag_eval"
	RunTypeComparisonBackingRun RunType = "comparison_backing_run"
	RunTypeSuggestionEval        RunType = "suggestion_eval"
)

type TriggerSource string

const (
	TriggerSourceMCP      TriggerSource = "mcp"
	TriggerSourceAPI      TriggerSource = "api"
	TriggerSourceCLI      TriggerSource = "cli"
	TriggerSourceSchedule TriggerSource = "schedule"
	TriggerSourceCI       TriggerSource = "ci"
)

type MetricDirection string

const (
	HigherIsBetter MetricDirection = "higher_is_better"
	LowerIsBetter  MetricDirection = "lower_is_better"
)

type ArtifactType string

const (
	ArtifactTranscript       ArtifactType = "transcript"
	ArtifactRetrievedContext ArtifactType = "retrieved_context"
	ArtifactPromptfooReport  ArtifactType = "promptfoo_report"
	ArtifactComparisonReport ArtifactType = "comparison_report"
	ArtifactDebugBundle      ArtifactType = "debug_bundle"
)

type CaseResultStatus string

const (
	CasePassed  CaseResultStatus = "passed"
	CaseFailed  CaseResultStatus = "failed"
	CaseError   CaseResultStatus = "error"
	CaseSkipped CaseResultStatus = "skipped"
)
