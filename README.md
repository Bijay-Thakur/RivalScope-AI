# RivalScope AI

Monorepo for **RivalScope AI** — source-grounded competitive intelligence for GTM teams.

## Structure

```
rivalscope-ai/
├── frontend/     Next.js dashboard (TypeScript, Tailwind)
└── backend/      FastAPI + LangGraph research agent API (Python)
```

## Quick start

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Backend

```bash
cd backend
python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e .
python scripts/dev_server.py
```

`dev_server.py` runs uvicorn with reload excludes for `logs/`, `data/`, and `eval_results/` so long research streams are not killed mid-run. If you use bare `uvicorn --reload`, add `--reload-exclude '**/logs/**' --reload-exclude '**/data/**'`.

- Health check: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs

No API keys required for mock mode or frontend demo.

## Status

- **Frontend:** Live agent pipeline UI with real-time SSE progress (`agent_status` + token streaming) and report view
- **Backend:** Symmetric two-company research, full-page extraction, comparison agent, source-grounded report generation (mock + real modes)
- **Evaluation:** Unified eval system — 22 benchmark tasks, structural + full (LLM-judge) modes
- **Tests:** 90 backend tests green; mock mode needs no keys

---

## Backend

FastAPI + LangGraph research agent.

### Phase 3 pipeline

| Area | What it does |
| --- | --- |
| **Primary LLM** | Groq (`llama-3.1-8b-instant`) via `langchain-groq` |
| **Fallback LLM** | Gemini (`gemini-2.5-flash`) via `langchain-google-genai` |
| **Web search** | Tavily search + extract across four research tracks (both companies) |
| **Evidence** | `Source` + `EvidenceItem` from full-page text, company-tagged |
| **Fact-checking** | LLM claim verification |
| **Comparison** | Dedicated comparison agent → structured `ComparisonMatrix` |
| **Report** | Source-grounded `CompetitorReport` from evidence + matrix |
| **Mode toggle** | `RESEARCH_MODE=mock` — deterministic demo, no API keys |

### Environment variables

Copy and fill in keys:

```bash
cd backend
cp .env.example .env
```

```env
GROQ_API_KEY=
GOOGLE_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=

LLM_PROVIDER=groq
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_MODEL=gemini-2.5-flash
JUDGE_MODEL=gemini-2.5-pro

RESEARCH_MODE=mock

# EXTRACT_TOP_N=3
# EXTRACT_MAX_CHARS=6000
# GROQ_MAX_PAYLOAD_CHARS=16000
# MAX_CONTEXT_CHARS=50000

APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

| Variable | Required for real mode | Default |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes (unless `LLM_PROVIDER=gemini`) | — |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | No (fallback / judge) | — |
| `TAVILY_API_KEY` | Yes | — |
| `LLM_PROVIDER` | No | `groq` |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` |
| `JUDGE_MODEL` | No (eval `--mode full` only) | `gemini-2.5-pro` |
| `RESEARCH_MODE` | No | `mock` |
| `EXTRACT_TOP_N` | No | `3` |
| `EXTRACT_MAX_CHARS` | No | `6000` |
| `GROQ_MAX_PAYLOAD_CHARS` | No | `16000` |
| `MAX_CONTEXT_CHARS` | No | `50000` |

**Mock mode** (`RESEARCH_MODE=mock`) — no keys, deterministic demo data. Default for UI dev and CI.

**Real mode** (`RESEARCH_MODE=real`) — needs `TAVILY_API_KEY` + at least one LLM key. Returns HTTP 400 with a clear message if keys are missing.

### Run tests

```bash
cd backend
pytest
```

All tests run in mock mode; no external API calls.

### Manual live test

```bash
cd backend
python scripts/manual_live_research_test.py
```

Requires `RESEARCH_MODE=real` and valid keys. Runs ClickUp vs Notion, prints summary, saves `logs/manual_live_report.json`.

### Security

- Never commit `backend/.env` (gitignored)
- API keys stay in the backend process only — never in frontend responses or logs

---

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `POST` | `/api/research` | Full workflow; returns `{ "report": { ... } }` |
| `GET` | `/api/research/stream` | Live SSE: `agent_status` + `token` as nodes run, then `final_report` |

### `POST /api/research`

```json
{
  "ourCompany": "ClickUp",
  "competitor": "Notion",
  "market": "Project management / docs",
  "reportType": "sales_battlecard"
}
```

`reportType`: `quick_brief`, `deep_research`, `sales_battlecard`.

### `GET /api/research/stream`

```text
/api/research/stream?our_company=ClickUp&competitor=Notion&market=Project%20management&report_type=quick_brief
```

SSE event types:

- `agent_status` — `{ runId, step, name, status: "working" | "done", message? }`
- `token` — best-effort LLM delta: `{ step, node, delta }`
- `final_report` — complete `CompetitorReport`
- `error` — failure or missing keys

Node order (9 steps):

1. Normalize input
2. Create research plan
3–6. Company profile / product / pricing / news tracks (parallel)
7. Fact-check evidence
8. Comparison agent
9. Report generator

### Real-time streaming

Live via LangGraph `astream_events(version="v2")` — events emit **as nodes execute**, not replayed after completion.

| LangGraph event | SSE |
| --- | --- |
| `on_chain_start` (node) | `agent_status` `working` |
| `on_chain_end` (node) | `agent_status` `done` |
| `on_chat_model_stream` | `token` |
| graph complete | `final_report` |

Token streaming is best-effort (Gemini `streaming=True`). If tokens don't arrive, per-agent status and progress still work. Frontend `AgentTrackerModal`: idle → working (glow) → done; respects `prefers-reduced-motion`.

---

## LangGraph

```text
START
  → normalize_input
  → create_research_plan
  → ┬ company_profile_track ─┐
    ├ product_track           ─┤  (parallel)
    ├ pricing_track           ─┤
    └ news_track              ─┘
  → fact_checker_stub
  → comparison_agent
  → report_generator
  → END
```

```text
backend/app/
  graph/           state, nodes, workflow, constants
  services/        llm, search, evidence, fact_checker, comparison_agent, report_generator
  api/routes/      research.py (POST + SSE)
  evaluation/      benchmark harness + judge
  observability/   metrics, tracing
  schemas/         Pydantic models
```

List fields (`sources`, `evidence`, `errors`, etc.) use `operator.add` reducers so parallel tracks merge safely.

---

## Evaluation & observability

One eval system (`backend/app/evaluation/`). Measures structural quality, comparison two-sidedness, and (in full mode) claim grounding.

### Why it matters

Scores whether the pipeline delivers complete, source-backed reports — not whether every claim is factually correct. Structural scorers catch missing sections, weak source mix, broken citations, and one-sided comparisons. Full mode adds LLM-as-judge grounding.

### Benchmark

| Item | Value |
| --- | --- |
| Tasks | **22** in `backend/app/evaluation/benchmark_tasks.json` |
| Report types | `quick_brief`, `deep_research`, `sales_battlecard` |
| Expected sections | 9 per task |
| Expected source types | `company_page`, `pricing_page`, `news`, `docs`, `other` |

### Eval modes

```bash
cd backend

# structural — deterministic only, no LLM, no keys (default)
python scripts/run_evaluation.py --mode structural --limit 5

# full — structural + LLM-judge grounding
python scripts/run_evaluation.py --mode full --limit 3 --experiment full_smoke

# full live (real research + judge)
python scripts/run_evaluation.py --mode full --limit 5 --experiment rivalscope_live_v1 --out eval_results
```

Full live run needs `GOOGLE_API_KEY` + `TAVILY_API_KEY` + `RESEARCH_MODE=real`. `JUDGE_MODEL` should be a stronger Gemini tier than synthesis (`gemini-2.5-pro` vs `gemini-2.5-flash`).

Flags: `--mode`, `--limit` (alias `--max-tasks`), `--experiment`, `--dataset`, `--out`.

Outputs → `backend/eval_results/`: JSON, CSV, `<experiment>_summary.md` (headline metrics), failure-mode report.

### Metrics

**Structural (weighted overall score):**

| Metric | Weight |
| --- | ---: |
| Task completion | 30% |
| Section coverage | 25% |
| Source coverage | 20% |
| Citation integrity | 15% |
| Efficiency (latency) | 10% |

**Comparison (deterministic, all modes):**

- `comparison_two_sidedness` — % matrix rows with both sides filled
- `comparison_citation_validity` — cited source ids resolve
- `advantage_distribution` — sanity flag if 100% one side

**Grounding (`--mode full` only):**

- `grounding_rate` — supported / total claims
- `hallucination_rate` — contradicted / total
- `comparison_grounding` — judged matrix cell support

Judge self-eval bias: judge uses stronger tier than synthesis; treat absolute numbers as directional.

### Observability (LangSmith)

Optional in `backend/.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=rivalscope-ai
```

Restart the backend after changing `.env`. Confirm at `/settings` (badge **LangSmith: ON**) or `GET /api/config`.

**Eval artifacts** record tracing state in each experiment JSON/CSV/summary (`langsmith_tracing`, `langsmith_project`).

#### Where to see traces

| Surface | What you get |
| --- | --- |
| **LangSmith** ([smith.langchain.com](https://smith.langchain.com)) | Hosted nested trace tree — latency, tokens, I/O per span |
| **`/workflow`** (Live Agent Workflow) | In-app SSE `trace` events during a run |
| **`/runs` → Traces** | Persisted tool/LLM spans from SQLite |
| **`/settings`** | Tracing on/off + project name |

#### Trace hierarchy (research + eval)

Each research run exports a `research_graph` trace. LangGraph adds a child span per node:

1. `normalize_input`
2. `create_research_plan`
3. `company_profile_track` · `product_track` · `pricing_track` · `news_track` (parallel)
4. `fact_checker_stub`
5. `comparison_agent`
6. `report_generator`

Under the research tracks (real mode): `search_web` and `extract_urls` (`@traceable` Tavily tools).

Under synthesis nodes: LangChain auto-traces `fact_checker_llm`, `comparison_agent_llm`, `report_generator_llm`.

Eval runs add:

- `evaluation_experiment` — full benchmark
- `benchmark_task` — one competitor pair (inputs include `task_id`)
- `judge_claim` — per-claim judge calls (`--mode full` only)

Run metrics also log to `backend/app/logs/research_runs.jsonl`.

### Cost control

- Keep `--limit` small in real mode
- Prefer mock mode for UI dev and CI
- Do not run all 22 tasks in real mode without budgeting Tavily/Groq credits

---

## Project layout

```text
frontend/
  app/                 Next.js pages
  components/          AgentTrackerModal, ResearchForm, report views
  lib/api.ts           SSE parsing, report deserialization

backend/
  app/
    api/routes/        HTTP routes
    core/              config, logging
    evaluation/        benchmark + judge
    graph/             LangGraph workflow
    observability/     metrics, tracing
    schemas/           Pydantic models
    services/          LLM, search, evidence, reports
    main.py
  eval_results/        experiment outputs (gitignored)
  logs/                rivalscope.log, research_runs.jsonl (gitignored)
  scripts/
    run_evaluation.py
    manual_live_research_test.py
  tests/
  pyproject.toml
  .env.example
```
