package metrics

import (
	"fmt"
	"strings"

	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
)

type MetricDefinition struct {
	Name             string                 `json:"name"`
	Provider         string                 `json:"provider"`
	Family           string                 `json:"family"`
	Direction        domain.MetricDirection `json:"direction"`
	DefaultThreshold *float64               `json:"default_threshold,omitempty"`
	Levels           []string               `json:"levels"`
	Description      string                 `json:"description,omitempty"`
}

func ptrFloat(v float64) *float64 { return &v }

var registry = map[string]MetricDefinition{
	"exact_match": {
		Name:             "exact_match",
		Provider:         "internal",
		Family:           "correctness",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(1.0),
		Levels:           []string{"case", "aggregate"},
		Description:      "Exact normalized string equality between actual and expected outputs.",
	},
	"answer_correctness": {
		Name:             "answer_correctness",
		Provider:         "deepeval",
		Family:           "correctness",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(0.8),
		Levels:           []string{"case", "aggregate"},
		Description:      "Heuristic semantic similarity between actual and expected outputs.",
	},
	"hallucination": {
		Name:             "hallucination",
		Provider:         "deepeval",
		Family:           "safety",
		Direction:        domain.LowerIsBetter,
		DefaultThreshold: ptrFloat(0.2),
		Levels:           []string{"case", "aggregate"},
		Description:      "Estimated unsupported content ratio in an answer.",
	},
	"toxicity": {
		Name:             "toxicity",
		Provider:         "deepeval",
		Family:           "safety",
		Direction:        domain.LowerIsBetter,
		DefaultThreshold: ptrFloat(0.1),
		Levels:           []string{"case", "aggregate"},
		Description:      "Estimated toxicity score from a simple lexical heuristic.",
	},
	"faithfulness": {
		Name:             "faithfulness",
		Provider:         "ragas",
		Family:           "rag",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(0.75),
		Levels:           []string{"case", "aggregate"},
		Description:      "How well the answer is grounded in retrieved context.",
	},
	"answer_relevancy": {
		Name:             "answer_relevancy",
		Provider:         "ragas",
		Family:           "rag",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(0.7),
		Levels:           []string{"case", "aggregate"},
		Description:      "How relevant the answer is to the question and expected answer.",
	},
	"context_precision": {
		Name:             "context_precision",
		Provider:         "ragas",
		Family:           "rag",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(0.7),
		Levels:           []string{"case", "aggregate"},
		Description:      "Fraction of retrieved context that is useful to answer the query.",
	},
	"context_recall": {
		Name:             "context_recall",
		Provider:         "ragas",
		Family:           "rag",
		Direction:        domain.HigherIsBetter,
		DefaultThreshold: ptrFloat(0.7),
		Levels:           []string{"case", "aggregate"},
		Description:      "Fraction of expected supporting evidence recovered by retrieval.",
	},
}

func GetMetricDefinition(name string) (MetricDefinition, error) {
	norm := strings.ToLower(strings.TrimSpace(name))
	def, found := registry[norm]
	if !found {
		return MetricDefinition{}, fmt.Errorf("unsupported metric: %s", name)
	}
	return def, nil
}

func ListMetricDefinitions() []MetricDefinition {
	list := make([]MetricDefinition, 0, len(registry))
	for _, def := range registry {
		list = append(list, def)
	}
	return list
}
