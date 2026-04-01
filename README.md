# Multi-Agent Research Assistant

An AI-powered research system that takes a question and produces a structured, evidence-backed report using a pipeline of four specialized agents.

## How it works

Each research job passes through four sequential agents:

1. **Search** — generates queries, fetches web sources, extracts evidence
2. **Synthesis** — groups evidence into themes, flags contradictions
3. **Report** — writes a structured, cited report in Markdown
4. **Evaluator** — scores the report on coverage, faithfulness, hallucination rate, and usefulness

Jobs run in the background. The frontend polls for updates via Server-Sent Events. All intermediate state is persisted in SQLite.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| LLM | Groq API or HuggingFace Inference API |
| Search | DuckDuckGo (default) + Tavily (optional) |
| PDF export | WeasyPrint |
| Database | SQLite |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |

## Prerequisites

- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com) and/or a [HuggingFace token](https://huggingface.co/settings/tokens)

## Setup

### Backend

```bash
cd api
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example .env       # then edit .env with your keys
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your-api-key   # same value as API_KEY in .env
```

## Running

**API server** (port 8000):
```bash
cd api
source venv/bin/activate
python main.py serve
# dev mode with auto-reload:
python main.py serve --reload
```

**Frontend** (port 3000):
```bash
cd frontend
npm run dev
```

**CLI** (single question, no server needed):
```bash
cd api
python main.py research "What are the trade-offs between CNNs and Vision Transformers?"
```

## Environment variables

Copy `.env.example` to `api/.env` and fill in the values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | | `auto` | `groq`, `huggingface`, or `auto` (tries Groq first) |
| `GROQ_API_KEY` | if using Groq | — | Groq API key |
| `GROQ_MODEL` | | `llama-3.3-70b-versatile` | Groq model ID |
| `HF_TOKEN` | if using HF | — | HuggingFace API token |
| `HF_MODEL` | | `meta-llama/Llama-3.3-70B-Instruct` | HuggingFace model ID |
| `TEMPERATURE` | | `0.3` | LLM sampling temperature |
| `TAVILY_API_KEY` | | — | Tavily search API key (optional, falls back to DuckDuckGo) |
| `MAX_SEARCH_QUERIES` | | `3` | Search queries generated per job |
| `MAX_RESULTS_PER_QUERY` | | `5` | Web results fetched per query |
| `MAX_CONTENT_LENGTH` | | `3000` | Max characters scraped per page |
| `API_KEY` | | — | Static key for `X-API-Key` auth (leave empty to disable) |
| `API_HOST` | | `0.0.0.0` | Bind address |
| `API_PORT` | | `8000` | Bind port |
| `DB_PATH` | | `data/jobs.db` | SQLite file path (relative to `api/`) |
| `CORS_ORIGINS` | | `http://localhost:3000` | Comma-separated allowed origins |

WhatsApp integration variables (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`, `WEBHOOK_SECRET`) are optional.

Generate a strong `API_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## API reference

All `/api/research/*` endpoints require `X-API-Key: <your-key>` if `API_KEY` is set.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/research` | Submit a question — returns `job_id` immediately |
| `GET` | `/api/research` | List all jobs |
| `GET` | `/api/research/{id}` | Job status, report, and evaluation scores |
| `GET` | `/api/research/{id}/reasoning` | Detailed reasoning steps (queries, sources, themes…) |
| `GET` | `/api/research/{id}/events` | SSE stream of live progress |
| `GET` | `/api/research/{id}/pdf` | Download report as PDF |
| `DELETE` | `/api/research/{id}` | Delete a job |
| `DELETE` | `/api/research` | Clear all jobs |
| `GET` | `/api/health` | Health check (no auth) |

**Submit a job:**
```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"question": "What are the opportunities and risks of adopting AI in healthcare?"}'
```

## Job lifecycle

```
pending → searching → synthesising → reporting → evaluating → completed
                                                             ↘ failed
```

## Tests

```bash
cd api
pytest tests/
```
