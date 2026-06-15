# RivalScope AI — Backend

FastAPI research agent API for **RivalScope AI**. Phase 2 delivers a LangGraph-powered competitive research workflow with REST and SSE endpoints, structured schemas, and run logging — all backed by mock data so the frontend can integrate without live API keys.

## Phase 2 — What this backend does

Phase 2 turns the research demo into a real API surface:

- Accepts research requests (your company, competitor, market, report type)
- Runs an eight-node **LangGraph** workflow with parallel research tracks
- Returns a structured **`CompetitorReport`** (snapshot, positioning, pricing, battlecard, evidence, sources)
- Streams **progress events** and the final report over **Server-Sent Events (SSE)**
- Writes **JSONL run logs** to `app/logs/research_runs.jsonl` for each workflow run

No Gemini or Tavily calls are made in Phase 2. Reports are generated from request-aware mock data.

## Install dependencies

```bash
cd backend
python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e .
```

Optional: copy environment defaults for local development.

```bash
cp .env.example .env
```

## Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs

## Available endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/api/research` | Run the full workflow; returns `{ "report": { ... } }` |
| `GET` | `/api/research/stream` | SSE stream of progress events, then `final_report` |

### `POST /api/research`

Request body (camelCase aliases supported):

```json
{
  "ourCompany": "ClickUp",
  "competitor": "Notion",
  "market": "Project management / docs",
  "reportType": "sales_battlecard"
}
```

`reportType` values: `quick_brief`, `deep_research`, `sales_battlecard`.

### `GET /api/research/stream`

Query parameters (snake_case):

```
/api/research/stream?our_company=ClickUp&competitor=Notion&market=Project%20management&report_type=quick_brief
```

SSE event types:

- `progress` — step updates with `runId`, `step`, `name`, `message`, `status`
- `final_report` — complete `CompetitorReport` payload
- `error` — workflow failure

## LangGraph structure

The workflow lives under `app/graph/`:

```
app/graph/
  state.py      # RivalScopeState — shared TypedDict with reducers for parallel updates
  nodes.py      # Eight node functions (normalize, plan, tracks, verify, report)
  workflow.py   # StateGraph definition and run_research_graph() entry point
  constants.py  # Step labels and TOTAL_STEPS
```

### Graph flow

```
START
  → normalize_input
  → create_research_plan
  → ┬ company_profile_track ─┐
    ├ product_track           ─┤  (parallel)
    ├ pricing_track           ─┤
    └ news_track              ─┘
  → fact_checker_stub
  → report_generator
  → END
```

- **`RivalScopeState`** holds `run_id`, the `ResearchRequest`, progress events, evidence, sources, verified claims, and the final report.
- List fields (`progress_events`, `sources`, `evidence`) use **reducers** so parallel track nodes can append safely.
- **`run_research_graph()`** invokes the compiled graph and writes run logs: `run_started`, `graph_completed`, or `run_failed`.

## What is mocked for now

| Area | Current behavior |
|------|------------------|
| **Research tracks** | Each track node returns demo evidence and sources; no web scraping or search |
| **Fact checking** | `fact_checker_stub` marks claims as `mock_verified` |
| **Report generation** | `build_mock_report()` in `app/services/mock_data.py` builds the report from request fields |
| **LLM / search** | `GOOGLE_API_KEY` and `TAVILY_API_KEY` are configured but **not used** |
| **SSE streaming** | The graph runs to completion first; progress events are then replayed with a short delay |

Progress messages are prefixed with `Demo:` to make mock behavior obvious in the UI.

## Phase 3 — Planned additions

Phase 3 will replace stubs with live research:

- **Gemini** for planning, synthesis, and report generation
- **Tavily** (and page fetch/extract) for real source discovery and grounding
- **True streaming** — emit progress events as nodes execute, not after the full run
- **Frontend integration** — wire the Next.js dashboard to `/api/research/stream`
- **Stronger verification** — real fact-checking against fetched sources instead of `mock_verified`

## Tests

```bash
pytest
```

Covers the research API, LangGraph workflow, and run logging.

## Project layout

```
app/
  api/routes/research.py   # HTTP routes (POST + SSE stream)
  core/                    # Settings and logging (including write_run_log)
  graph/                   # LangGraph state, nodes, workflow
  schemas/                 # Pydantic models (research, report, events)
  services/mock_data.py    # Request-aware mock report builder
  logs/                    # rivalscope.log + research_runs.jsonl (gitignored)
  main.py                  # FastAPI entrypoint
tests/
pyproject.toml
.env.example
```
