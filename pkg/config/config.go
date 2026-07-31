package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	Port                 int
	APIURL               string
	RedisURL             string
	DataDir              string
	ArtifactDir          string
	DefaultModelProvider string
	DefaultModelName     string
	OpenAIAPIKey         string
	OpenAIAPIBase        string
	AnthropicAPIKey      string
	AnthropicAPIBase     string
	GeminiAPIKey         string
	GeminiAPIBase        string
	RequestTimeout       time.Duration
	LogLevel             string
}

func getEnv(key, fallback string) string {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		return val
	}
	return fallback
}

func Load() *Config {
	portStr := getEnv("PORT", getEnv("EVAL_MCP_PORT", "8000"))
	port, err := strconv.Atoi(portStr)
	if err != nil {
		port = 8000
	}

	apiURL := getEnv("EVAL_MCP_API_URL", "http://127.0.0.1:"+strconv.Itoa(port))

	return &Config{
		Port:                 port,
		APIURL:               apiURL,
		RedisURL:             getEnv("REDIS_URL", "redis://localhost:6379/0"),
		DataDir:              getEnv("DATA_DIR", "./data"),
		ArtifactDir:          getEnv("ARTIFACT_DIR", "./data/artifacts"),
		DefaultModelProvider: getEnv("DEFAULT_MODEL_PROVIDER", "stub"),
		DefaultModelName:     getEnv("DEFAULT_MODEL_NAME", "stub-evaluator"),
		OpenAIAPIKey:         getEnv("OPENAI_API_KEY", ""),
		OpenAIAPIBase:        getEnv("OPENAI_API_BASE", "https://api.openai.com/v1"),
		AnthropicAPIKey:      getEnv("ANTHROPIC_API_KEY", ""),
		AnthropicAPIBase:     getEnv("ANTHROPIC_API_BASE", "https://api.anthropic.com"),
		GeminiAPIKey:         getEnv("GEMINI_API_KEY", getEnv("GOOGLE_API_KEY", "")),
		GeminiAPIBase:        getEnv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com"),
		RequestTimeout:       60 * time.Second,
		LogLevel:             getEnv("LOG_LEVEL", "info"),
	}
}
