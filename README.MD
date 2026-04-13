# Eval_MCP

## About

`Eval_MCP` is an installable MCP server for prompt evaluation and RAG evaluation workflows.

It is designed so end users can use it like Serena:

- install it with `uvx` or `uv tool install`
- connect it to Claude Desktop or Cursor
- run it as an MCP server over stdio with `eval-mcp serve`
- let the heavy evaluation work happen in a backend platform instead of inside the MCP process

## Table Of Contents

- [Install Guide](#install-guide)
- [MCP Client Configs](#mcp-client-configs)
- [Troubleshooting For Normal Users](#troubleshooting-for-normal-users)
- [CLI Commands](#cli-commands)
- [Docker](#docker)
- [Known Simplifications](#known-simplifications)

## Install Guide

This section is for someone who only wants to use `Eval_MCP` inside Claude Desktop or Cursor.

### What you need

- Python 3.11+
- `uv`
- an API key if the backend requires one

You only need `EVAL_MCP_API_URL` if you are overriding the default hosted backend with your own deployment.

### Use By Installing Through Package 

#### Option 1: Run With `uvx`

This is the simplest path.

```bash
uvx eval-mcp serve
```
This downloads and runs the package on demand.

#### Option 2: Install It As A Tool

```bash
uv tool install eval-mcp
eval-mcp serve
```

### Use From A Local Clone

Use this if you cloned the repository and want to run the local code instead of the published package.

```bash
uv tool install .
eval-mcp serve
```

### Self-hosting

To run your own backend:

1. Set `EVAL_MCP_API_URL=http://your-server:8000`
2. Set `EVAL_MCP_API_KEY=your-key`

The default hosted backend is `https://eval-mcp.onrender.com`.

### Required Client Environment Variables

Set this in your MCP client config or shell:

```bash
EVAL_MCP_API_KEY=your-api-key
```

Only set `EVAL_MCP_API_URL` if you are overriding the default hosted backend with your own deployment.

Optional:

```bash
EVAL_MCP_TIMEOUT_SECONDS=30
EVAL_MCP_DEFAULT_PROJECT=my-project

```
### How To Use

For hosted usage, onboarding is CLI first and API-key based.

#### 1. Register once

```bash
eval-mcp register --email you@example.com --password "your password" --display-name "Your Name"
```

#### 2. Create a project-scoped API key

```bash
eval-mcp create-api-key --label "name for this key"
```

If you lose your local config or raw key later, log in again to mint a fresh API key:

```bash
eval-mcp login --email you@example.com --password "your password"
```

If you want another hosted project later:

```bash
eval-mcp create-project --name "Team Project"
eval-mcp create-api-key --project team-project --label "team-project-key"
```

#### 3. Paste the returned key into your MCP client config

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "generated key"
      }
    }
  }
}
```

#### 4. Verify identity and scope

```bash
eval-mcp whoami
```

## MCP Client Configs

All MCP clients use the same `command`, `args`, and `env` values. The differences are:
1. The config file location
2. The top-level key (`mcpServers` vs `servers`)
3. VS Code requires `"type": "stdio"`

### Claude Desktop

Config file: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

### Claude Code / Claude CLI

Config file: `.mcp.json` (project-level) or `~/.claude/mcp.json` (global)

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

Or via CLI:
```bash
claude mcp add eval-mcp --scope project -- uvx eval-mcp serve
```
Then add the environment values in the generated config.

### Cursor

Config file: `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global)

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

### VS Code

Config file: `.vscode/mcp.json` (project-level) or user settings

```json
{
  "servers": {
    "eval-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

### Antigravity

Config file: Its JSON MCP config (similar to Claude Desktop)

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "uvx",
      "args": ["eval-mcp", "serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

### Codex CLI

Config file: `~/.codex/config.toml`

```toml
[mcp_servers.eval-mcp]
command = "uvx"
args = ["eval-mcp", "serve"]

[mcp_servers.eval-mcp.env]
EVAL_MCP_API_KEY = "key generated"
```

If already installed locally:

```toml
[mcp_servers.eval-mcp]
command = "eval-mcp"
args = ["serve"]

[mcp_servers.eval-mcp.env]
EVAL_MCP_API_KEY = "key generated"
```

### Local Installation

If you've installed with `uv tool install eval-mcp`, replace `uvx eval-mcp` with just `eval-mcp` in any of the above configs:

```json
{
  "mcpServers": {
    "eval-mcp": {
      "command": "eval-mcp",
      "args": ["serve"],
      "env": {
        "EVAL_MCP_API_KEY": "key generated"
      }
    }
  }
}
```

## Troubleshooting For Normal Users

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
- `EVAL_MCP_API_URL` is correct if you are overriding the default hosted backend
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

## CLI Commands

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
eval-mcp register
eval-mcp login
eval-mcp create-api-key
eval-mcp create-project
eval-mcp logout
eval-mcp whoami
eval-mcp list-api-keys
eval-mcp revoke-api-key <key_id>
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
- `eval-mcp register`
  - hosted registration with password
  - creates the client account and ensures one default project
- `eval-mcp login`
  - verifies hosted account password
  - creates a fresh DB-backed project-scoped API key for the default or requested project
- `eval-mcp create-api-key`
  - creates a DB-backed project-scoped API key
  - prints raw key once and a ready MCP config snippet
- `eval-mcp create-project`
  - creates an additional hosted project for the current account
  - intended for users who want more than the default project created at registration
- `eval-mcp logout`
  - clears the locally stored hosted account state
- `eval-mcp whoami`
  - validates configured API key and prints current scope
- `eval-mcp list-api-keys`
  - optional key inventory for the current account
- `eval-mcp revoke-api-key`
  - optional key revocation by id

## Docker

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

## Known Simplifications

- `deepeval` and `ragas` still fall back to internal heuristics unless their live libraries are installed and enabled
- Render deployment is committed, but you still need to provide real secrets and database values
- API auth now supports key rotation, but it is still shared-secret auth rather than a full identity system
- packaging validation is dry-run based, not a published PyPI install test
