# Eval_MCP

`Eval_MCP` is a high-performance, single-binary Model Context Protocol (MCP) server for prompt evaluation and RAG pipeline scoring, built natively in **Go**.

---

## Key Features

- **Single Standalone Binary**: Compiles to a single executable (`eval-mcp`) with zero runtime dependencies.
- **16 Native MCP Tools**: Full suite for dataset registration, prompt evaluations, RAG scoring, version comparisons, regression detection, and prompt-fix suggestions.
- **Redis & In-Memory Queue**: Fast background job processing for concurrent evaluations.
- **Modern Dark-Mode Dashboard**: Embedded web UI (`./eval-mcp dashboard`) with glassmorphism aesthetics, Inter/Outfit typography, live stats, and run history.
- **Pure Go Heuristic Metrics**: Built-in scoring for Exact Match, Levenshtein Answer Correctness, Token-Overlap Hallucination & Faithfulness, Lexical Toxicity, and Context Precision/Recall.
- **Zero Auth Overhead**: Clean local execution without user accounts, passwords, or API keys.

---

## Installation Guide

### Prerequisites
- [Go 1.22+](https://go.dev/dl/) installed on your machine.

### Step 1: Clone & Build
```bash
# 1. Clone the repository
git clone https://github.com/AyushSaha184/Eval_MCP.git
cd Eval_MCP

# 2. Build the binary
go build -o eval-mcp ./cmd/eval-mcp

# 3. Create your .env file
cp .env.example .env
```
*(Add your `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` to `.env` if using live LLM providers).*

---

## How to Run & Use `Eval_MCP`

You can run `Eval_MCP` either **100% locally** or connected to a **Render cloud backend**.

### Method 1: Local Mode (Full Local Setup)

To run the complete evaluation stack on your local machine:

1. **Seed Demo Data** *(Optional)*:
   ```bash
   ./eval-mcp seed
   ```

2. **Start the API Server** (Terminal 1):
   ```bash
   ./eval-mcp api
   ```
   *(Runs the REST API at `http://127.0.0.1:8000`)*

3. **Start the Evaluation Worker** (Terminal 2):
   ```bash
   ./eval-mcp worker
   ```
   *(Executes background job evaluations)*

4. **Start the Web Dashboard UI** *(Optional)* (Terminal 3):
   ```bash
   ./eval-mcp dashboard
   ```
   *(Open `http://localhost:8501` to view real-time pass rates & stats)*

5. **Connect your AI Client** (Claude Desktop / Cursor / Antigravity):
   Add `eval-mcp` to your MCP settings file (e.g., `~/.cursor/mcp.json` or `claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "eval-mcp": {
         "command": "/absolute/path/to/Eval_MCP/eval-mcp",
         "args": ["serve"],
         "env": {
           "EVAL_MCP_API_URL": "http://127.0.0.1:8000"
         }
       }
     }
   }
   ```
   *Your AI assistant will automatically launch `./eval-mcp serve` and have access to all 16 evaluation tools!*

---

### Method 2: Render Mode (Cloud Backend + Local MCP Client)

If your backend API and worker are hosted on **Render**:

1. **Build the binary locally**:
   ```bash
   go build -o eval-mcp ./cmd/eval-mcp
   ```

2. **Configure your AI Client to point to Render**:
   In your client JSON settings (`~/.cursor/mcp.json` or `claude_desktop_config.json`), set `EVAL_MCP_API_URL` to your Render service URL:
   ```json
   {
     "mcpServers": {
       "eval-mcp": {
         "command": "/absolute/path/to/Eval_MCP/eval-mcp",
         "args": ["serve"],
         "env": {
           "EVAL_MCP_API_URL": "https://your-app-name.onrender.com"
         }
       }
     }
   }
   ```
   *You don't need to run `./eval-mcp api` or `./eval-mcp worker` locally. The local `./eval-mcp serve` process proxies tool calls straight to Render!*

---

## Deploying Your Own Backend to Render

To deploy your own instance of the backend on Render:

1. Fork or push the repo to your GitHub account.
2. In the [Render Dashboard](https://dashboard.render.com), click **New** → **Blueprint**.
3. Connect your repository. Render automatically reads [`render.yaml`](file:///home/ayush/vscode/Projects/Eval_MCP/render.yaml) and provisions:
   - **`eval-mcp-api`** (Web Service running `./eval-mcp api`)
   - **`eval-mcp-worker`** (Worker Service running `./eval-mcp worker`)
   - **`eval-mcp-redis`** (Managed Redis queue)
4. Add your API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) under Render Environment settings.

---

## Supported MCP Tools (16 Tools)

1. `register_golden_dataset` — Register a dataset of test cases
2. `run_eval_suite` — Queue a prompt evaluation run over a dataset
3. `score_rag_pipeline` — Score RAG retrieval & generation with RAG metrics
4. `compare_prompt_versions` — Compare metric deltas between baseline and candidate prompts
5. `detect_regression` — Detect metric regressions against project baselines
6. `suggest_fix` — Queue LLM-as-a-judge to analyze failure clusters and suggest prompt fixes
7. `get_latest_suggestion` — Fetch latest prompt fix suggestions for a run
8. `get_eval_history` — Query paginated evaluation history
9. `get_run_status` — Get status and pass rate of a run
10. `list_projects` — List all evaluation projects
11. `list_datasets` — List datasets in a project
12. `list_prompts` — List prompt versions in a project
13. `set_baseline_run` — Set default baseline run for a project
14. `rerun_failed_cases` — Rerun failing test cases from a previous run
15. `annotate_run` — Attach labels/notes to a run
16. `get_supported_metrics` — List all supported evaluation metrics

---

## CLI Command Reference

| Command | Action |
|---|---|
| `./eval-mcp serve` | Starts the **MCP stdio server** (called by Cursor/Claude Desktop) |
| `./eval-mcp api` | Starts the **REST HTTP API server** (`:8000`) |
| `./eval-mcp worker` | Starts the **background evaluation worker** |
| `./eval-mcp dashboard` | Starts the **web dashboard UI** (`:8501`) |
| `./eval-mcp seed` | Seeds demo projects and datasets into `./data/db.json` |
| `./eval-mcp version` | Prints engine version (`v1.0.0`) |

---

## Environment Variables (.env)

```bash
PORT=8000
EVAL_MCP_API_URL=http://127.0.0.1:8000
REDIS_URL=redis://localhost:6379/0
DATA_DIR=./data

# Optional LLM Provider Keys
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```
