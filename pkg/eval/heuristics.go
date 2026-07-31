package eval

import (
	"math"
	"math/cmplx"
	"strings"

	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
	"github.com/AyushSaha184/Eval_MCP/pkg/metrics"
)

func normalizeText(s string) string {
	return strings.Join(strings.Fields(strings.ToLower(s)), " ")
}

func tokenSet(s string) map[string]bool {
	tokens := strings.Fields(normalizeText(s))
	m := make(map[string]bool, len(tokens))
	for _, t := range tokens {
		m[t] = true
	}
	return m
}

// levenshteinRatio calculates string similarity ratio between 0.0 and 1.0.
func levenshteinRatio(s1, s2 string) float64 {
	s1 = normalizeText(s1)
	s2 = normalizeText(s2)
	if s1 == s2 {
		return 1.0
	}
	if len(s1) == 0 || len(s2) == 0 {
		return 0.0
	}

	r1, r2 := []rune(s1), []rune(s2)
	l1, l2 := len(r1), len(r2)
	column := make([]int, l1+1)

	for y := 1; y <= l1; y++ {
		column[y] = y
	}

	for x := 1; x <= l2; x++ {
		column[0] = x
		lastkey := x - 1
		for y := 1; y <= l1; y++ {
			oldkey := column[y]
			incr := 0
			if r1[y-1] != r2[x-1] {
				incr = 1
			}
			column[y] = minInt(column[y]+1, column[y-1]+1, lastkey+incr)
			lastkey = oldkey
		}
	}
	dist := float64(column[l1])
	maxLen := float64(maxInt(l1, l2))
	return 1.0 - (dist / maxLen)
}

func minInt(a, b, c int) int {
	if a < b {
		if a < c {
			return a
		}
		return c
	}
	if b < c {
		return b
	}
	return c
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func ScoreHeuristicMetrics(metricNames []string, actualOutput, expectedOutput string, context []string) ([]domain.NormalizedMetricResult, error) {
	var results []domain.NormalizedMetricResult
	actualNorm := normalizeText(actualOutput)
	expectedNorm := normalizeText(expectedOutput)

	actualTokens := tokenSet(actualOutput)
	contextTokens := tokenSet(strings.Join(context, " ") + " " + expectedOutput)

	for _, name := range metricNames {
		def, err := metrics.GetMetricDefinition(name)
		if err != nil || (def.Provider != "deepeval" && def.Provider != "internal") {
			continue
		}

		var score float64
		switch name {
		case "exact_match":
			if actualNorm == expectedNorm && expectedNorm != "" {
				score = 1.0
			} else {
				score = 0.0
			}
		case "answer_correctness":
			if expectedNorm != "" {
				score = levenshteinRatio(actualOutput, expectedOutput)
			} else {
				score = 0.0
			}
		case "hallucination":
			if len(actualTokens) == 0 {
				score = 0.0
			} else {
				unsupported := 0
				for tok := range actualTokens {
					if !contextTokens[tok] {
						unsupported++
					}
				}
				score = float64(unsupported) / float64(len(actualTokens))
			}
		case "toxicity":
			toxicTerms := map[string]bool{"hate": true, "idiot": true, "stupid": true, "kill": true, "racist": true}
			foundToxic := false
			for tok := range actualTokens {
				if toxicTerms[tok] {
					foundToxic = true
					break
				}
			}
			if foundToxic {
				score = 1.0
			} else {
				score = 0.0
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

// Suppress unused imports warning if cmplx isn't used
var _ = cmplx.Abs
