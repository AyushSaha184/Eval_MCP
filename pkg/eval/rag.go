package eval

import (
	"math"
	"strings"

	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/AyushSaha184/Eval_MCP/pkg/metrics"
)

func ScoreRagMetrics(
	metricNames []string,
	question string,
	actualOutput string,
	expectedOutput string,
	retrievedContext []string,
	expectedContext []string,
) ([]domain.NormalizedMetricResult, error) {
	var results []domain.NormalizedMetricResult

	answerTokens := tokenSet(actualOutput)
	retrievedTokens := tokenSet(strings.Join(retrievedContext, " "))
	expectedContextTokens := tokenSet(strings.Join(expectedContext, " "))

	for _, name := range metricNames {
		def, err := metrics.GetMetricDefinition(name)
		if err != nil || def.Provider != "ragas" {
			continue
		}

		var score float64
		switch name {
		case "faithfulness":
			if len(answerTokens) == 0 {
				score = 0.0
			} else {
				overlap := 0
				for tok := range answerTokens {
					if retrievedTokens[tok] {
						overlap++
					}
				}
				score = float64(overlap) / float64(len(answerTokens))
			}
		case "answer_relevancy":
			qAns := question + " " + actualOutput
			qExp := question + " " + expectedOutput
			score = levenshteinRatio(qAns, qExp)
		case "context_precision":
			if len(retrievedTokens) == 0 {
				score = 0.0
			} else {
				overlap := 0
				for tok := range retrievedTokens {
					if expectedContextTokens[tok] {
						overlap++
					}
				}
				score = float64(overlap) / float64(len(retrievedTokens))
			}
		case "context_recall":
			if len(expectedContextTokens) == 0 {
				score = 0.0
			} else {
				overlap := 0
				for tok := range expectedContextTokens {
					if retrievedTokens[tok] {
						overlap++
					}
				}
				score = float64(overlap) / float64(len(expectedContextTokens))
			}
		default:
			continue
		}

		score = math.Round(score*1000000) / 1000000

		var passed *bool
		if def.DefaultThreshold != nil {
			p := false
			if def.Direction == domain.HigherIsBetter {
				p = score >= *def.DefaultThreshold
			} else {
				p = score <= *def.DefaultThreshold
			}
			passed = &p
		}

		results = append(results, domain.NormalizedMetricResult{
			MetricName:   def.Name,
			MetricFamily: def.Family,
			Score:        score,
			Threshold:    def.DefaultThreshold,
			Direction:    def.Direction,
			Passed:       passed,
			Details:      map[string]interface{}{"provider": def.Provider},
		})
	}
	return results, nil
}
