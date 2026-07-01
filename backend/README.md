# RivalScope AI — Backend

FastAPI + LangGraph research agent for **RivalScope AI**.

---

## Phase 3 Overview

Phase 3 replaces Phase 2 mock stubs with a live competitive intelligence pipeline.

| Area | What was added |
| --- | --- |
| **Primary LLM** | Groq (`llama-3.1-8b-instant`) via `langchain-groq` |
| **Fallback LLM** | Gemini (`gemini-2.5-flash`) via `langchain-google-genai` |
| **Web search** | Tavily search and extract across four research tracks |
| **Evidence collection** | Real `Source` and `EvidenceItem` objects built from live search results |
| **Claim verification** | LLM fact-checking with `verified` / `weakly_supported` / `unsupported` status |
| **Report generation** | Source-grounded `CompetitorReport` generated from collected evidence |
| **Mode toggle** | `RESEARCH_MODE=mock` preserves Phase 2 demo behavior with no API keys required |

---

## Environment Variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Full `.env` reference:

```env
GROQ_API_KEY=
GOOGLE_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=

LLM_PROVIDER=groq
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_MODEL=gemini-2.5-flash

RESEARCH_MODE=real

APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

| Variable | Required for real mode | Default |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes (unless `LLM_PROVIDER=gemini`) | — |
| `GOOGLE_API_KEY` | No (Gemini fallback / alternative primary) | — |
| `GEMINI_API_KEY` | No (alias for `GOOGLE_API_KEY`) | — |
| `TAVILY_API_KEY` | Yes | — |
| `LLM_PROVIDER` | No | `groq` |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` |
| `RESEARCH_MODE` | No | `mock` |

---

## Mock Mode

```env
RESEARCH_MODE=mock
```

Mock mode requires no API keys. All research nodes return deterministic demo data. Mock mode is the default and is used for local UI development and CI.

---

## Real Mode

```env
RESEARCH_MODE=real
```

Real mode requires:

- `TAVILY_API_KEY` — for web search and extraction
- At least one LLM key: `GROQ_API_KEY`, `GOOGLE_API_KEY`, or `GEMINI_API_KEY`

If required keys are missing, the API returns HTTP 400 with a descriptive message before running the graph.

---

## Install Dependencies

```bash
cd backend
python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e .
```

---

## Run Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- OpenAPI docs: <http://localhost:8000/docs>

---

## Run Tests

```bash
pytest
```

Tests run in mock mode and make no external API calls. All tests pass without API keys.

---

## Manual Live Test

```bash
python scripts/manual_live_research_test.py
```

Requires `RESEARCH_MODE=real` and valid API keys in `.env`. The script:

1. Validates all required keys before making any network calls — exits with a helpful message if anything is missing
2. Runs a full research cycle: ClickUp vs Notion in project management
3. Prints a console summary (run_id, source count, evidence count, confidence score, all report sections)
4. Saves the full report JSON to `logs/manual_live_report.json`

---

## Security Notes

- **Never commit `.env`** — it is gitignored; committing it exposes your keys permanently in git history.
- **Never expose API keys to the frontend** — keys live in the backend process only and never appear in HTTP responses, logs, or error messages.
- **Keep real keys backend-only** — the frontend receives only report data; no key names or values are serialized into API responses.

---

## Development Cost Control

- Keep `max_results_per_query` small (default is 3) — each query consumes Tavily credits and increases LLM context size.
- Do not run benchmark or load-test loops in real mode — Tavily and Groq both have per-minute rate limits.
- Prefer mock mode for UI development — it is instant, free, and deterministic.

---

## Available Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `POST` | `/api/research` | Run the full workflow; returns `{ "report": { ... } }` |
| `GET` | `/api/research/stream` | SSE stream of progress events, then `final_report` |

### `POST /api/research`

Returns HTTP 400 if `RESEARCH_MODE=real` and required keys are missing.

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

Query parameters:

```text
/api/research/stream?our_company=ClickUp&competitor=Notion&market=Project%20management&report_type=quick_brief
```

SSE event types:

- `progress` — step update with `runId`, `step`, `name`, `message`, `status`
- `final_report` — complete `CompetitorReport` payload
- `error` — workflow failure or missing keys

Real-mode progress sequence:

1. Normalizing research input
2. Creating research plan — 4 research tracks
3. Searching company profile sources
4. Searching product and feature sources
5. Searching pricing sources
6. Searching recent news sources
7. Verifying evidence claims
8. Generating source-grounded report

---

## LangGraph Structure

```text
app/graph/
  state.py      # RivalScopeState — TypedDict with operator.add reducers on list fields
  nodes.py      # Eight node functions; each branches on RESEARCH_MODE
  workflow.py   # StateGraph definition and run_research_graph() entry point
  constants.py  # Step labels and TOTAL_STEPS
```

### Graph flow

```text
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

List fields (`progress_events`, `sources`, `evidence`, `errors`, `verified_claims`) use `operator.add` reducers so parallel track results merge safely without conflicts.

---

## Services

```text
app/services/
  llm.py              # get_primary_llm(), get_fallback_llm(), invoke_with_fallback()
  search.py           # search_web(), extract_urls(), dedupe_urls()
  query_builder.py    # Deterministic query builders per research track
  research_tracks.py  # run_research_track(), run_all_basic_tracks()
  evidence.py         # Converts Tavily results into Source and EvidenceItem objects
  fact_checker.py     # LLM-based claim verification with JSON-parse fallback
  report_generator.py # LLM report generation with multi-level fallback
  json_utils.py       # extract_json_from_text(), safe_get_message_text()
  prompts.py          # System prompt constants for all LLM calls
  mock_data.py        # Phase 2 mock report builder (used in mock mode)
```

---

## Project Layout

```text
backend/
  app/
    api/routes/research.py   # HTTP routes (POST + SSE stream)
    core/                    # Settings (config.py) and logging
    graph/                   # LangGraph state, nodes, workflow
    schemas/                 # Pydantic models (research, report, events)
    services/                # LLM, search, evidence, and report services
    main.py                  # FastAPI entrypoint
  logs/                      # rivalscope.log + manual_live_report.json (gitignored)
  scripts/
    manual_live_research_test.py   # Manual smoke test for real mode only
  tests/
  pyproject.toml
  .env.example
  .env                       # Never commit — gitignored
```
