# Wren

Your personal AI agent platform: a web chat backed by a tool-using agent with durable memory and **real code execution**. Self-hosted, free brains on Cloudflare Workers AI.

## What ships

- **Agent brains** (tried in order, free first):
  1. Cloudflare Workers AI chain: `gpt-oss-120b` then `llama-3.3-70b-instruct-fp8-fast` (your account, free tier; models that reject tool schemas are retried without them)
  2. Any OpenAI-compatible endpoint (OpenAI, OpenRouter, Groq)
  3. Local Ollama
- **Auth**: email + password, JWT sessions, bcrypt
- **Chat**: threads, history, live SSE streaming of agent events
- **Agent loop**: OpenAI-style tool-calling across every brain, with a step cap
- **Real code execution** (per-user workspace directory): `list_files`, `read_file`, `write_file`, `run_python`, `run_javascript`, `run_shell`, with path-escape protection and timeouts. The agent explores a repo, edits files, runs code, and verifies its own work.
- **Memory**: durable per-user facts the agent saves and reuses across threads
- **CLI**: `python cli/wren.py login | chat | run "task"` against the same backend
- **Frontend**: React (Vite) dark shell
- **Ops**: docker-compose (Postgres + backend + frontend), GitHub Actions CI, pytest suite

## Quickstart

```bash
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET=change-me
# free brains (Cloudflare Workers AI):
export CF_ACCOUNT_ID=your-account-id
export CF_API_TOKEN=your-token      # needs Workers AI:Edit permission
# or any OpenAI-compatible key instead:
# export MODEL_API_KEY=sk-...
uvicorn app.main:app --reload

# frontend (second terminal)
cd frontend && npm install && npm run dev

# CLI
python cli/wren.py login
python cli/wren.py run "make a flask todo app in the workspace and run its tests"
```

Open http://localhost:5173, create an account, chat.

### Docker

```bash
CF_ACCOUNT_ID=... CF_API_TOKEN=... docker compose up --build
```

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./wren.db` | any SQLAlchemy URL; use Postgres in prod |
| `JWT_SECRET` | dev value | token signing secret |
| `CF_ACCOUNT_ID` / `CF_API_TOKEN` | none | free Workers AI brains (first in the chain) |
| `MODEL_API_KEY` / `MODEL_BASE_URL` / `MODEL_NAME` | none / openai / gpt-4o-mini | OpenAI-compatible fallback |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | none / llama3.1 | local fallback |
| `AGENT_MAX_STEPS` | `12` | tool-loop safety cap |
| `WORKSPACE_ROOT` | `./workspaces` | where agent file/exec tools operate (one subdir per user) |
| `NODE_BIN` | auto | path to node for run_javascript |

## Tests

```bash
pytest -q
```

## Roadmap

- Phase 3: IDE (file tree, code editor, terminal) + monorepo-aware tooling
- Phase 4: OAuth connections (Gmail, Google Calendar), token streaming
- Phase 5: semantic memory (embeddings + vector search), user preferences page
- Phase 6: outbound channels (email, SMS), plans/limits, admin
