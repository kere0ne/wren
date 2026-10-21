# Wren

Your personal AI assistant platform: a web chat backed by a tool-using agent with durable per-user memory. Self-hosted, OpenAI-compatible on the model layer.

## What ships in Phase 1

- **Auth**: email + password registration and login, JWT sessions, bcrypt hashes
- **Chat**: threads, message history, live SSE streaming of agent events
- **Agent loop**: OpenAI-compatible tool-calling loop (works with OpenAI, OpenRouter, Groq, Ollama, anything speaking `/chat/completions`)
- **Built-in tools**: save/search memory, fetch a web page, calculator, current time
- **Memory**: durable per-user facts the agent saves and reuses across threads
- **Frontend**: React (Vite) dark shell, auth screen, thread sidebar, streaming chat
- **Ops**: docker-compose (Postgres + backend + frontend), GitHub Actions CI, pytest suite

## Quickstart

```bash
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET=change-me
export MODEL_API_KEY=sk-...        # or OpenRouter / Groq key
export MODEL_BASE_URL=https://openrouter.ai/api/v1   # optional
export MODEL_NAME=anthropic/claude-3.5-sonnet        # optional
uvicorn app.main:app --reload

# frontend (second terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173, create an account, chat.

### Docker

```bash
MODEL_API_KEY=sk-... docker compose up --build
```

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./wren.db` | any SQLAlchemy URL; use Postgres in prod |
| `JWT_SECRET` | dev value | token signing secret |
| `MODEL_API_KEY` | none | key for the model provider (server-side only) |
| `MODEL_BASE_URL` | `https://api.openai.com/v1` | any OpenAI-compatible endpoint |
| `MODEL_NAME` | `gpt-4o-mini` | model id |
| `AGENT_MAX_STEPS` | `8` | tool-loop safety cap |

## Tests

```bash
pytest -q
```

## Roadmap

- Phase 2: OAuth connections (Gmail, Google Calendar, Contacts), richer tools
- Phase 3: semantic memory (embeddings + vector search), user preferences page
- Phase 4: outbound channels (email, SMS), plans/limits, admin
