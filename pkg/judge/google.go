package judge

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
)

type JudgeResult struct {
	Summary         string                  `json:"summary"`
	SuggestionText  string                  `json:"suggestion_text"`
	FailureClusters []domain.FailureCluster `json:"failure_clusters"`
	Metadata        map[string]interface{}  `json:"metadata"`
}

type GeminiJudge struct {
	cfg        *config.Config
	httpClient *http.Client
}

func NewGeminiJudge(cfg *config.Config) *GeminiJudge {
	return &GeminiJudge{
		cfg: cfg,
		httpClient: &http.Client{
			Timeout: cfg.RequestTimeout,
		},
	}
}

func (j *GeminiJudge) GenerateSuggestion(
	ctx context.Context,
	runID string,
	clusters []domain.FailureCluster,
	sampleInputs []string,
	modelName string,
) (*JudgeResult, error) {
	if j.cfg.GeminiAPIKey != "" {
		return j.generateLive(ctx, runID, clusters, sampleInputs, modelName)
	}
	return j.generateStub(runID, clusters, sampleInputs, modelName), nil
}

func (j *GeminiJudge) generateStub(
	runID string,
	clusters []domain.FailureCluster,
	sampleInputs []string,
	modelName string,
) *JudgeResult {
	dominant := "mixed quality failures"
	if len(clusters) > 0 {
		dominant = clusters[0].Title
	}

	summary := fmt.Sprintf("Run %s shows repeated issues around %s.", runID, dominant)
	bullets := []string{
		"- Tighten the system prompt to demand grounded, directly comparable outputs.",
		"- Add explicit formatting examples for the highest-volume failure cluster.",
		"- Review failing cases with the strongest regressions before expanding the prompt scope.",
	}
	if len(sampleInputs) > 0 {
		bullets = append(bullets, fmt.Sprintf("- Representative failing input: %s", sampleInputs[0]))
	}

	return &JudgeResult{
		Summary:         summary,
		SuggestionText:  strings.Join(bullets, "\n"),
		FailureClusters: clusters,
		Metadata: map[string]interface{}{
			"model_name":    modelName,
			"cluster_count": len(clusters),
			"provider":      "google-stub",
		},
	}
}

func (j *GeminiJudge) generateLive(
	ctx context.Context,
	runID string,
	clusters []domain.FailureCluster,
	sampleInputs []string,
	modelName string,
) (*JudgeResult, error) {
	if modelName == "" {
		modelName = "gemini-2.5-flash"
	}

	clustersJSON, _ := json.Marshal(clusters)
	samplesJSON, _ := json.Marshal(sampleInputs)

	prompt := fmt.Sprintf(
		"Run ID: %s\nFailure clusters: %s\nSample inputs: %s\n\nReturn JSON with:\n- \"summary\": one sentence\n- \"suggestion_text\": 3-6 bullet points as plain text",
		runID, string(clustersJSON), string(samplesJSON),
	)

	payload := map[string]interface{}{
		"contents": []map[string]interface{}{
			{
				"role": "user",
				"parts": []map[string]string{
					{
						"text": "You are an evaluation engineer. Return concise, actionable prompt-improvement guidance. Respond as JSON with keys: summary, suggestion_text.\n\n" + prompt,
					},
				},
			},
		},
		"generationConfig": map[string]interface{}{
			"temperature":      0.2,
			"maxOutputTokens":  700,
			"responseMimeType": "application/json",
		},
	}

	bodyBytes, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/v1beta/models/%s:generateContent?key=%s", strings.TrimSuffix(j.cfg.GeminiAPIBase, "/"), modelName, j.cfg.GeminiAPIKey)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := j.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Gemini judge request failed (%d): %s", resp.StatusCode, string(b))
	}

	var res struct {
		Candidates []struct {
			Content struct {
				Parts []struct {
					Text string `json:"text"`
				} `json:"parts"`
			} `json:"content"`
		} `json:"candidates"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}

	content := ""
	if len(res.Candidates) > 0 && len(res.Candidates[0].Content.Parts) > 0 {
		content = res.Candidates[0].Content.Parts[0].Text
	}

	var parsed struct {
		Summary        string `json:"summary"`
		SuggestionText string `json:"suggestion_text"`
	}
	if err := json.Unmarshal([]byte(content), &parsed); err != nil {
		return j.generateStub(runID, clusters, sampleInputs, modelName), nil
	}

	return &JudgeResult{
		Summary:         parsed.Summary,
		SuggestionText:  parsed.SuggestionText,
		FailureClusters: clusters,
		Metadata: map[string]interface{}{
			"model_name":    modelName,
			"cluster_count": len(clusters),
			"provider":      "google",
		},
	}, nil
}
