# Eval_MCP

## About

`Eval_MCP` is an installable MCP server for prompt evaluation and RAG evaluation workflows.

It is designed so end users can use it like Serena:

- install it with `uvx` or `uv tool install`
- connect it to Claude Desktop or Cursor
- run it as an MCP server over stdio with `eval-mcp serve`
- let the heavy evaluation work happen in a backend platform instead of inside the MCP process

This project has two layers:

1. installable MCP package
   - lightweight
   - runs over stdio
   - validates tool input
   - calls the backend HTTP API
   - returns clean MCP tool responses

2. backend platform
   - persistent evaluation system
   - uses PostgreSQL, SQLAlchemy, Alembic, workers, snapshots, caching, comparisons, regressions, suggestions, and dashboard
   - does the heavy work

Live backend integrations now support:

- real OpenAI-backed generation
- real Anthropic-backed generation
- real Anthropic-backed judge suggestions
- optional live `deepeval` and `ragas` integrations when those libraries are installed
- rotating backend API keys
- optional Redis-backed queueing

That means the normal user does not need to manually run `python server.py`, does not need to connect Claude Desktop directly to a database, and does not need heavy local orchestration just to use the MCP tools.

## Table Of Contents

- [About](#1-eval_mcp-about)
- [Table Of Contents](#2-table-of-contents)
- [Install Guide For Normal Users](#3-install-guide-for-normal-users)
- [Claude Desktop / Cursor Config](#4-claude-desktop--cursor-config)
- [Other MCP Client Configs](#5-other-mcp-client-configs)
- [Troubleshooting For Normal Users](#6-troubleshooting-for-normal-users)
- [How The Product Works](#7-how-the-product-works)
- [CLI Commands](#8-cli-commands)
- [Self-Hosted / Operator Guide](#9-self-hosted--operator-guide)
- [Environment Variables](#10-environment-variables)
- [HTTP API Surface](#11-http-api-surface)
- [Docker](#12-docker)
- [Project Layout](#13-project-layout)
- [Testing](#14-testing)
- [Known Simplifications](#15-known-simplifications)
- [Compatibility Notes](#16-compatibility-notes)

## Install Guide For Normal Users

This section is for someone who only wants to use `Eval_MCP` inside Claude Desktop or Cursor.

### What A Normal User Needs

You need:

- Python 3.11+
- `uv`
- a running backend API URL
- an API key if the backend requires one

You do not need:

- to run `python server.py`
- to configure PostgreSQL directly
- to run Alembic migrations
- to start workers yourself if you are using a hosted backend

### Option A: Run With `uvx`

This is the simplest path.

```bash
uvx eval-mcp serve
```

This downloads and runs the package on demand.

### Option B: Install It As A Tool

```bash
uv tool install eval-mcp
eval-mcp serve
```

### Option C: Install From This Repository Locally

Use this if you are testing the repo itself.

```bash
uv tool install .
eval-mcp serve
```

### Required Client Environment Variables

Set these in your MCP client config or shell:

```bash
EVAL_MCP_API_URL=https://your-backend.example.com
EVAL_MCP_API_KEY=your-api-key
```

Optional:

```bash
EVAL_MCP_TIMEOUT_SECONDS=30
EVAL_MCP_DEFAULT_PROJECT=my-project
```

### What `eval-mcp serve` Actually Does

When you run:

```bash
eval-mcp serve
```

it:

- starts the MCP server over stdio
- registers the eval tools
- validates tool arguments
- sends tool requests to the backend API
- returns the backend response to Claude Desktop or Cursor

It does not:

- start a web server
- run eval jobs locally
- connect directly to PostgreSQL
- replace the backend API or worker

## 4. Claude Desktop / Cursor Config

Use config like this:

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

If you installed it already with `uv tool install eval-mcp`, you can also use:

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "eval-mcp",
      "args": ["serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

## 5. Other MCP Client Configs

`Eval_MCP` is a stdio MCP server, so it can also be used from other MCP-capable tools.

### VS Code

VS Code uses `.vscode/mcp.json` with a top-level `"servers"` object.

Example:

```json
{
  "servers": {
    "eval-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

If already installed:

```json
{
  "servers": {
    "eval-mcp": {
      "type": "stdio",
      "command": "eval-mcp",
      "args": ["serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

### Claude Code / Claude CLI

Claude Code uses `.mcp.json` with `"mcpServers"`.

Example:

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

CLI setup form:

```bash
claude mcp add eval-mcp --scope project -- uvx eval-mcp serve
```

Then add the environment values in the generated config.

### Codex CLI And Codex Extension

Codex uses `~/.codex/config.toml`.

Example:

```toml
[mcp_servers.eval-mcp]
command = "uvx"
args = ["eval-mcp", "serve"]

[mcp_servers.eval-mcp.env]
EVAL_MCP_API_URL = "http://localhost:8000"
EVAL_MCP_API_KEY = "dev-key"
```

If already installed:

```toml
[mcp_servers.eval-mcp]
command = "eval-mcp"
args = ["serve"]

[mcp_servers.eval-mcp.env]
EVAL_MCP_API_URL = "http://localhost:8000"
EVAL_MCP_API_KEY = "dev-key"
```

### Antigravity

Antigravity currently appears to use a raw JSON MCP config with `"mcpServers"`.

Example:

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_URL": "http://localhost:8000",
        "EVAL_MCP_API_KEY": "dev-key"
      }
    }
  }
}
```

### Generic Rule

For most MCP clients, the only values that matter are:

- command: `uvx` or `eval-mcp`
- args: `["eval-mcp", "serve"]` or `["serve"]`
- env:
  - `EVAL_MCP_API_URL`
  - `EVAL_MCP_API_KEY`

If your backend is hosted, replace `http://localhost:8000` with your deployed API URL.

## 6. Troubleshooting For Normal Users

### Problem: `uvx eval-mcp serve` fails

Check:

- `uv` is installed
- Python 3.11+ is available
- the package name is `eval-mcp`

Try:

```bash
uv --version
python --version
uvx eval-mcp serve
```

### Problem: Claude Desktop / Cursor says the MCP server failed to start

Check:

- the command is correct
- the args are correct
- `EVAL_MCP_API_URL` is present
- the backend URL is reachable

Good:

```json
{
  "command": "uvx",
  "args": ["eval-mcp", "serve"]
}
```

Or:

```json
{
  "command": "eval-mcp",
  "args": ["serve"]
}
```

### Problem: the MCP server starts but tool calls fail

Usually this means:

- bad `EVAL_MCP_API_URL`
- bad `EVAL_MCP_API_KEY`
- backend API is down
- backend worker is not running

Check the backend health manually:

```bash
curl http://localhost:8000/health
```

If the backend uses an API key, confirm the same key is configured on both sides.

### Problem: run gets created but stays queued

That means:

- the API is running
- the worker is probably not running

In self-hosted mode, make sure this process is running:

```bash
eval-mcp worker
```

### Problem: I set a Render/Postgres database but Claude still cannot use the tools

Claude Desktop or Cursor should not connect to the database directly.

The correct chain is:

```text
Claude Desktop / Cursor
-> eval-mcp serve
-> backend API
-> PostgreSQL + worker
```

So if the DB is configured but the backend API is not running, the MCP tools will still fail.

### Problem: timeout or slow responses

Try:

```bash
EVAL_MCP_TIMEOUT_SECONDS=60
```

But also check whether:

- backend API is reachable
- worker is overloaded
- long-running jobs are expected

For long evals, normal behavior is:

- create run
- get `run_id`
- poll status later

## 7. How The Product Works

High-level flow:

```text
Claude Desktop / Cursor
-> eval-mcp serve
-> MCP tool handler
-> backend HTTP API
-> service layer
-> database + worker queue
-> async worker execution
-> stored results
-> status/history/comparison/suggestion responses
```

The important design rule is:

- MCP layer is thin
- backend layer is heavy

The installable MCP package lives in:

- `src/eval_mcp/`

The backend platform lives in:

- `src/api/`
- `src/services/`
- `src/db/`
- `src/workers/`
- `src/eval_backends/`
- `src/dashboard/`

## 8. CLI Commands

Console entrypoint:

```text
eval-mcp = "eval_mcp.cli:main"
```

Supported commands:

```bash
eval-mcp serve
eval-mcp api
eval-mcp worker
eval-mcp dashboard
eval-mcp migrate
```

Meaning:

- `eval-mcp serve`
  - starts MCP over stdio
  - normal user command
- `eval-mcp api`
  - starts backend FastAPI server
- `eval-mcp worker`
  - starts worker loop
- `eval-mcp dashboard`
  - starts read-only dashboard
- `eval-mcp migrate`
  - runs Alembic migrations

## 9. Self-Hosted / Operator Guide

Use this if you want to run the backend yourself.

### Step 1: Configure backend env

At minimum:

```bash
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME
EVAL_MCP_API_KEY=dev-key
API_HOST=127.0.0.1
API_PORT=8000
```

### Step 2: Install dependencies

```bash
uv sync
```

Or:

```bash
pip install -e .[dev]
```

### Step 3: Run migrations

```bash
eval-mcp migrate
```

### Step 4: Start backend API

```bash
eval-mcp api
```

### Step 5: Start worker

```bash
eval-mcp worker
```

### Step 6: Optional dashboard

```bash
eval-mcp dashboard
```

### Step 7: Connect the installable MCP package to your backend

```bash
EVAL_MCP_API_URL=http://127.0.0.1:8000
EVAL_MCP_API_KEY=dev-key
eval-mcp serve
```

## 10. Environment Variables

### User / MCP Package Variables

```bash
EVAL_MCP_API_URL
EVAL_MCP_API_KEY
EVAL_MCP_TIMEOUT_SECONDS
EVAL_MCP_DEFAULT_PROJECT
```

### Backend Variables

```bash
DATABASE_URL
EVAL_MCP_API_KEY
EVAL_MCP_API_KEYS
LOG_LEVEL
QUEUE_BACKEND
REDIS_URL
REDIS_QUEUE_NAME
WORKER_POLL_INTERVAL_SECONDS
WORKER_MAX_RETRIES
STORAGE_PROVIDER
LOCAL_ARTIFACT_DIRECTORY
DEFAULT_MODEL_PROVIDER
DEFAULT_MODEL_NAME
ANTHROPIC_API_KEY
ANTHROPIC_API_BASE
ANTHROPIC_API_VERSION
OPENAI_API_KEY
OPENAI_API_BASE
OPENAI_ORG_ID
MODEL_REQUEST_TIMEOUT_SECONDS
JUDGE_REQUEST_TIMEOUT_SECONDS
USE_LIVE_DEEPEVAL
USE_LIVE_RAGAS
S3_BUCKET
S3_REGION
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
API_HOST
API_PORT
DASHBOARD_HOST
DASHBOARD_PORT
```

## 11. HTTP API Surface

The installable MCP package calls these backend routes:

```text
GET  /v1/projects
GET  /v1/projects/{project}/datasets
GET  /v1/projects/{project}/prompts
POST /v1/datasets/register
POST /v1/runs/eval
POST /v1/runs/rag
GET  /v1/runs/{run_id}/status
POST /v1/history/query
POST /v1/baselines/set
POST /v1/comparisons/prompt-versions
POST /v1/regressions/detect
POST /v1/runs/rerun-failed
POST /v1/runs/annotate
POST /v1/suggestions
GET  /v1/meta/supported-metrics
```

## 12. Docker

Docker is backend/operator-facing.

Build:

```bash
docker build -t eval-mcp .
```

Run API:

```bash
docker run --env-file .env -p 8000:8000 eval-mcp eval-mcp api --host 0.0.0.0 --port 8000
```

Run worker:

```bash
docker run --env-file .env eval-mcp eval-mcp worker
```

Run dashboard:

```bash
docker run --env-file .env -p 8501:8501 eval-mcp eval-mcp dashboard --host 0.0.0.0 --port 8501
```

### Render

A committed [render.yaml](c:\vscode\Projects\Eval_MCP\render.yaml) is included for deploying:

- `eval-mcp-api` web service
- `eval-mcp-worker` background worker

Use Neon or another PostgreSQL provider for `DATABASE_URL`.

## 13. Project Layout

```text
src/
  eval_mcp/
    __init__.py
    __main__.py
    api_client.py
    cli.py
    config.py
    mcp_server.py
    tool_handlers.py
  eval_mcp_server/
    runtime.py
  api/
  core/
  dashboard/
  db/
  domain/
  eval_backends/
  services/
  storage/
  tools/
  workers/
```

## 14. Testing

Run all tests:

```bash
pytest -q -p no:cacheprovider
```

Covered areas include:

- backend unit and integration flows
- CLI parsing
- MCP config loading
- API client behavior
- tool handler to mocked backend calls
- dry-run entrypoint behavior
- real provider path unit tests for OpenAI and Anthropic adapters
- opt-in live Postgres smoke coverage via `EVAL_MCP_SMOKE_DATABASE_URL`

## 15. Known Simplifications

- `deepeval` and `ragas` still fall back to internal heuristics unless their live libraries are installed and enabled
- Render deployment is committed, but you still need to provide real secrets and database values
- API auth now supports key rotation, but it is still shared-secret auth rather than a full identity system
- packaging validation is dry-run based, not a published PyPI install test

## 16. Compatibility Notes

- `server.py` is kept as a compatibility shim
- backend logic was preserved and moved under `src/`
- end-user UX is now centered on `uvx eval-mcp serve` and `eval-mcp serve`
- VS Code uses `.vscode/mcp.json`
- Claude Code uses `.mcp.json`
- Codex uses `~/.codex/config.toml`
