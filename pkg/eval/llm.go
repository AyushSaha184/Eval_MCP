package eval

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"strings"
	"time"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/domain"
)

type GenerationResult struct {
	OutputText       string                 `json:"output_text"`
	RenderedPrompt   string                 `json:"rendered_prompt"`
	LatencyMS        int                    `json:"latency_ms"`
	TokenUsage       map[string]interface{} `json:"token_usage"`
	RetrievedContext []string               `json:"retrieved_context"`
	Metadata         map[string]interface{} `json:"metadata"`
}

type LLMRunner struct {
	cfg        *config.Config
	httpClient *http.Client
}

func NewLLMRunner(cfg *config.Config) *LLMRunner {
	return &LLMRunner{
		cfg: cfg,
		httpClient: &http.Client{
			Timeout: cfg.RequestTimeout,
		},
	}
}

func RenderPrompt(promptSnapshot map[string]interface{}, inputText string) string {
	content, _ := promptSnapshot["content"].(string)
	rendered := strings.ReplaceAll(content, "{input}", inputText)
	rendered = strings.ReplaceAll(rendered, "{query}", inputText)
	if rendered == content && content != "" {
		rendered = fmt.Sprintf("%s\n\nInput:\n%s", content, inputText)
	}
	return strings.TrimSpace(rendered)
}

func (r *LLMRunner) Generate(
	ctx context.Context,
	promptSnapshot map[string]interface{},
	inputText string,
	expectedOutput string,
	modelConfig domain.ModelConfig,
	runtimeConfig domain.RuntimeConfig,
	retrievedContext []string,
) (*GenerationResult, error) {
	provider := strings.ToLower(modelConfig.Provider)
	if provider == "" {
		provider = r.cfg.DefaultModelProvider
	}

	switch provider {
	case "stub":
		return r.generateStub(promptSnapshot, inputText, expectedOutput, modelConfig, runtimeConfig, retrievedContext), nil
	case "openai":
		return r.generateOpenAI(ctx, promptSnapshot, inputText, modelConfig, runtimeConfig, retrievedContext)
	case "anthropic":
		return r.generateAnthropic(ctx, promptSnapshot, inputText, modelConfig, runtimeConfig, retrievedContext)
	case "google", "gemini":
		return r.generateGemini(ctx, promptSnapshot, inputText, modelConfig, runtimeConfig, retrievedContext)
	default:
		return r.generateStub(promptSnapshot, inputText, expectedOutput, modelConfig, runtimeConfig, retrievedContext), nil
	}
}

func (r *LLMRunner) generateStub(
	promptSnapshot map[string]interface{},
	inputText, expectedOutput string,
	modelConfig domain.ModelConfig,
	runtimeConfig domain.RuntimeConfig,
	retrievedContext []string,
) *GenerationResult {
	renderedPrompt := RenderPrompt(promptSnapshot, inputText)
	sysPrompt, _ := promptSnapshot["system_prompt"].(string)
	combined := strings.ToLower(sysPrompt + " " + renderedPrompt)

	quality := 0.75
	if strings.Contains(combined, "bad") || strings.Contains(combined, "degrade") || strings.Contains(combined, "weak") {
		quality = 0.25
	} else if strings.Contains(combined, "good") || strings.Contains(combined, "improve") || strings.Contains(combined, "strong") {
		quality = 0.95
	}

	if mode, ok := modelConfig.Extra["mode"].(string); ok {
		switch mode {
		case "perfect":
			quality = 1.0
		case "noisy":
			quality = 0.35
		}
	}

	hash := sha256.Sum256([]byte(renderedPrompt))
	hashHex := hex.EncodeToString(hash[:])
	n := new(big.Int)
	n.SetString(hashHex, 16)
	mod := n.Mod(n, big.NewInt(5)).Int64()

	var outputText string
	if expectedOutput != "" && quality >= 0.9 {
		outputText = expectedOutput
	} else if expectedOutput != "" && quality >= 0.6 {
		if mod != 0 {
			outputText = expectedOutput
		} else {
			outputText = expectedOutput + " (draft)"
		}
	} else if expectedOutput != "" {
		outputText = "uncertain: " + inputText
	} else if len(retrievedContext) > 0 {
		outputText = retrievedContext[0]
	} else {
		outputText = "stub-response: " + inputText
	}

	promptTokens := len(strings.Fields(renderedPrompt))
	if promptTokens < 1 {
		promptTokens = 1
	}
	compTokens := len(strings.Fields(outputText))
	if compTokens < 1 {
		compTokens = 1
	}

	return &GenerationResult{
		OutputText:       outputText,
		RenderedPrompt:   renderedPrompt,
		LatencyMS:        5,
		TokenUsage:       map[string]interface{}{"prompt_tokens": promptTokens, "completion_tokens": compTokens},
		RetrievedContext: retrievedContext,
		Metadata:         map[string]interface{}{"provider": "stub", "runtime": runtimeConfig},
	}
}

func (r *LLMRunner) generateOpenAI(
	ctx context.Context,
	promptSnapshot map[string]interface{},
	inputText string,
	modelConfig domain.ModelConfig,
	runtimeConfig domain.RuntimeConfig,
	retrievedContext []string,
) (*GenerationResult, error) {
	if r.cfg.OpenAIAPIKey == "" {
		return nil, fmt.Errorf("OPENAI_API_KEY is required for OpenAI provider")
	}

	sysPrompt, _ := promptSnapshot["system_prompt"].(string)
	renderedPrompt := RenderPrompt(promptSnapshot, inputText)
	if len(retrievedContext) > 0 {
		renderedPrompt += "\n\nRetrieved context:\n- " + strings.Join(retrievedContext, "\n- ")
	}

	modelName := modelConfig.ModelName
	if modelName == "" {
		modelName = "gpt-4o-mini"
	}

	messages := []map[string]string{}
	if sysPrompt != "" {
		messages = append(messages, map[string]string{"role": "system", "content": sysPrompt})
	}
	messages = append(messages, map[string]string{"role": "user", "content": renderedPrompt})

	payload := map[string]interface{}{
		"model":       modelName,
		"messages":    messages,
		"temperature": modelConfig.Temperature,
		"max_tokens":  modelConfig.MaxTokens,
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", strings.TrimSuffix(r.cfg.OpenAIAPIBase, "/")+"/chat/completions", bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+r.cfg.OpenAIAPIKey)

	start := time.Now()
	resp, err := r.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("OpenAI request failed (%d): %s", resp.StatusCode, string(b))
	}

	var res struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Usage map[string]interface{} `json:"usage"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}

	outputText := ""
	if len(res.Choices) > 0 {
		outputText = strings.TrimSpace(res.Choices[0].Message.Content)
	}

	return &GenerationResult{
		OutputText:       outputText,
		RenderedPrompt:   renderedPrompt,
		LatencyMS:        int(time.Since(start).Milliseconds()),
		TokenUsage:       res.Usage,
		RetrievedContext: retrievedContext,
		Metadata:         map[string]interface{}{"provider": "openai", "model": modelName, "runtime": runtimeConfig},
	}, nil
}

func (r *LLMRunner) generateAnthropic(
	ctx context.Context,
	promptSnapshot map[string]interface{},
	inputText string,
	modelConfig domain.ModelConfig,
	runtimeConfig domain.RuntimeConfig,
	retrievedContext []string,
) (*GenerationResult, error) {
	if r.cfg.AnthropicAPIKey == "" {
		return nil, fmt.Errorf("ANTHROPIC_API_KEY is required for Anthropic provider")
	}

	sysPrompt, _ := promptSnapshot["system_prompt"].(string)
	renderedPrompt := RenderPrompt(promptSnapshot, inputText)
	if len(retrievedContext) > 0 {
		renderedPrompt += "\n\nRetrieved context:\n- " + strings.Join(retrievedContext, "\n- ")
	}

	modelName := modelConfig.ModelName
	if modelName == "" {
		modelName = "claude-3-5-haiku-latest"
	}

	payload := map[string]interface{}{
		"model":       modelName,
		"max_tokens":  modelConfig.MaxTokens,
		"temperature": modelConfig.Temperature,
		"messages":    []map[string]string{{"role": "user", "content": renderedPrompt}},
	}
	if sysPrompt != "" {
		payload["system"] = sysPrompt
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", strings.TrimSuffix(r.cfg.AnthropicAPIBase, "/")+"/v1/messages", bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", r.cfg.AnthropicAPIKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	start := time.Now()
	resp, err := r.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Anthropic request failed (%d): %s", resp.StatusCode, string(b))
	}

	var res struct {
		Content []struct {
			Text string `json:"text"`
		} `json:"content"`
		Usage map[string]interface{} `json:"usage"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}

	outputText := ""
	if len(res.Content) > 0 {
		outputText = strings.TrimSpace(res.Content[0].Text)
	}

	return &GenerationResult{
		OutputText:       outputText,
		RenderedPrompt:   renderedPrompt,
		LatencyMS:        int(time.Since(start).Milliseconds()),
		TokenUsage:       res.Usage,
		RetrievedContext: retrievedContext,
		Metadata:         map[string]interface{}{"provider": "anthropic", "model": modelName, "runtime": runtimeConfig},
	}, nil
}

func (r *LLMRunner) generateGemini(
	ctx context.Context,
	promptSnapshot map[string]interface{},
	inputText string,
	modelConfig domain.ModelConfig,
	runtimeConfig domain.RuntimeConfig,
	retrievedContext []string,
) (*GenerationResult, error) {
	if r.cfg.GeminiAPIKey == "" {
		return nil, fmt.Errorf("GEMINI_API_KEY is required for Gemini provider")
	}

	sysPrompt, _ := promptSnapshot["system_prompt"].(string)
	renderedPrompt := RenderPrompt(promptSnapshot, inputText)
	if len(retrievedContext) > 0 {
		renderedPrompt += "\n\nRetrieved context:\n- " + strings.Join(retrievedContext, "\n- ")
	}

	modelName := modelConfig.ModelName
	if modelName == "" {
		modelName = "gemini-2.5-flash"
	}

	userParts := []map[string]string{}
	if sysPrompt != "" {
		userParts = append(userParts, map[string]string{"text": "System instructions:\n" + sysPrompt})
	}
	userParts = append(userParts, map[string]string{"text": renderedPrompt})

	payload := map[string]interface{}{
		"contents": []map[string]interface{}{
			{
				"role":  "user",
				"parts": userParts,
			},
		},
		"generationConfig": map[string]interface{}{
			"temperature":     modelConfig.Temperature,
			"maxOutputTokens": modelConfig.MaxTokens,
		},
	}

	bodyBytes, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/v1beta/models/%s:generateContent?key=%s", strings.TrimSuffix(r.cfg.GeminiAPIBase, "/"), modelName, r.cfg.GeminiAPIKey)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	start := time.Now()
	resp, err := r.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Gemini request failed (%d): %s", resp.StatusCode, string(b))
	}

	var res struct {
		Candidates []struct {
			Content struct {
				Parts []struct {
					Text string `json:"text"`
				} `json:"parts"`
			} `json:"content"`
		} `json:"candidates"`
		UsageMetadata map[string]interface{} `json:"usageMetadata"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}

	outputText := ""
	if len(res.Candidates) > 0 && len(res.Candidates[0].Content.Parts) > 0 {
		outputText = strings.TrimSpace(res.Candidates[0].Content.Parts[0].Text)
	}

	return &GenerationResult{
		OutputText:       outputText,
		RenderedPrompt:   renderedPrompt,
		LatencyMS:        int(time.Since(start).Milliseconds()),
		TokenUsage:       res.UsageMetadata,
		RetrievedContext: retrievedContext,
		Metadata:         map[string]interface{}{"provider": "gemini", "model": modelName, "runtime": runtimeConfig},
	}, nil
}
