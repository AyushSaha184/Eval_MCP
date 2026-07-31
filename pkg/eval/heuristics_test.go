package eval

import (
	"testing"
)

func TestScoreHeuristicMetricsExactMatch(t *testing.T) {
	metrics := []string{"exact_match", "answer_correctness", "toxicity"}
	actual := "Hello world"
	expected := "hello world"

	results, err := ScoreHeuristicMetrics(metrics, actual, expected, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) < 2 {
		t.Fatalf("expected at least 2 metric results, got %d", len(results))
	}

	for _, r := range results {
		if r.MetricName == "exact_match" {
			if r.Score != 1.0 {
				t.Errorf("expected exact_match score 1.0, got %f", r.Score)
			}
		}
		if r.MetricName == "answer_correctness" {
			if r.Score < 0.95 {
				t.Errorf("expected answer_correctness > 0.95, got %f", r.Score)
			}
		}
	}
}

func TestScoreHeuristicMetricsToxicity(t *testing.T) {
	metrics := []string{"toxicity"}
	actual := "This is a stupid output"
	expected := "This is a nice output"

	results, err := ScoreHeuristicMetrics(metrics, actual, expected, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) != 1 {
		t.Fatalf("expected 1 metric result, got %d", len(results))
	}

	if results[0].Score != 1.0 {
		t.Errorf("expected toxicity score 1.0, got %f", results[0].Score)
	}
}
