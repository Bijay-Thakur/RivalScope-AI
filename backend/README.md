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

## Phase 4 — Evaluation & Observability

Phase 4 adds a benchmark harness and structured run logging on top of the Phase 3 pipeline. API routes and the frontend are unchanged.

### Why evaluation matters

Competitive intelligence is only useful if reports are **complete**, **source-backed**, and **trustworthy enough to act on**. This project makes claims tied to URLs and evidence objects — evaluation verifies that the pipeline actually delivers that structure before we invest in fancier generation.

Phase 4 does **not** claim the agent is factually correct. It measures whether the system:

1. Produces populated report sections for diverse B2B matchups
2. Collects a reasonable mix of source types per category
3. Keeps evidence citations aligned with source records
4. Completes within acceptable latency

That baseline makes later improvements (better search, better prompts, LLM-as-judge) measurable instead of anecdotal.

### Evaluation methodology

```text
benchmark_tasks.json  →  load_benchmark_tasks()
                      →  run_evaluation()        # runs run_research_graph() per task
                      →  score_report()          # deterministic scorers
                      →  write_experiment_results()
                      →  eval_results/{experiment}.*
```

1. Load tasks from `app/evaluation/benchmark_tasks.json`
2. For each task, build a `ResearchRequest` and run the full LangGraph workflow
3. Score the returned `CompetitorReport` with deterministic functions in `app/evaluation/scorers.py`
4. Write JSON, CSV, summary Markdown, and failure-mode analysis to `eval_results/`

The runner respects the current environment: `RESEARCH_MODE=mock` exercises mock nodes; `RESEARCH_MODE=real` calls Tavily and Groq.

**Observability:** `app/observability/metrics.py` logs `run_metrics` events to `app/logs/research_runs.jsonl` after each graph run. Service-level events (search started/completed, evidence built, fact checker, report generator) are logged via `log_run_event()` without API keys or full page content.

### Benchmark size

| Item | Value |
| --- | --- |
| Total benchmark tasks | **20** |
| Categories | Project management, CRM, dev tools, payments, data, AI, commerce, etc. |
| Report types | `quick_brief`, `deep_research`, `sales_battlecard` |
| Expected sections per task | 9 (snapshot, positioning, features, pricing, recent moves, strengths, weaknesses, battlecard, sources) |
| Expected source types per task | 5 (`company_page`, `pricing_page`, `news`, `docs`, `other`) |

Tasks are defined in `app/evaluation/benchmark_tasks.json`. Expected facts are high-level and stable — scorers do not require exact live pricing.

### Metrics

| Metric | Weight | Description |
| --- | ---: | --- |
| `task_completion` | 30% | All major report fields non-empty |
| `section_coverage` | 25% | Fraction of expected benchmark sections present |
| `source_coverage` | 20% | Fraction of expected source types present (partial credit) |
| `citation_integrity` | 15% | Evidence `source_id` references valid sources; sources have URLs |
| Efficiency | 10% | Latency tiers: ≤30s → 1.0, ≤60s → 0.7, ≤120s → 0.4, else 0.1 |

`TaskScore` also records `evidence_count`, `source_count`, `warnings_count`, and `failure_notes`.

### Run mock evaluation

No API keys required. Used for CI (`tests/test_evaluation_runner.py`) and fast regression checks.

```bash
cd backend

# Windows
set RESEARCH_MODE=mock
python scripts/run_evaluation.py --experiment-name phase4_mock_baseline --max-tasks 5

# Mac/Linux
RESEARCH_MODE=mock python scripts/run_evaluation.py --experiment-name phase4_mock_baseline --max-tasks 5
```

### Run real evaluation

Requires `GROQ_API_KEY` and `TAVILY_API_KEY` in `backend/.env`. **Keep `--max-tasks` small** — each task runs four search tracks plus LLM fact-checking and report generation.

```bash
cd backend
# RESEARCH_MODE=real in .env
python scripts/run_evaluation.py --experiment-name phase4_real_smoke_test --max-tasks 2
```

Do not run all 20 tasks in real mode during development unless you intend to spend significant Tavily/Groq credits.

### Example result table

| Experiment | Mode | Tasks | Avg Score | Avg Latency | Avg Sources | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `phase4_mock_baseline` | mock | 5 | 0.92 | 0.03s | 5.0 | All tasks scored 0.92; source coverage capped at 0.60 |
| `phase4_real_smoke_test` | real | 2 | 0.95 | 47.29s | 30.5 | Reports generated with 30–31 sources each; 1 task missed `company_page` labeling |

These are **initial smoke results**, not a full 20-task benchmark. Scores reflect structural quality, not claim-level truth.

### Known failure modes

**Mock mode (`phase4_mock_baseline`, 5 tasks)**

- **Source coverage 0.60 on every task** — mock `build_mock_report()` provides `company_page` and `pricing_page` sources only; benchmark tasks also expect `news` and `docs`.
- **Overall score 0.92** — completion, sections, and citations are perfect; source coverage drags the average down.
- **Not a pipeline bug** — mock data predates the benchmark's source-type expectations.

**Real mode (`phase4_real_smoke_test`, 2 tasks)**

- **Source type mislabeling** — 1 of 2 tasks failed to classify any source as `company_page` despite collecting 31 sources.
- **Latency** — task-002 took 65.85s (efficiency score 0.4); task-001 completed in 28.73s.
- **Citation integrity** — 1.0 on both tasks (evidence linked to sources with URLs).
- **No factual verification** — high scores do not mean claims are correct.

### Planned fixes (next phase)

1. **Align mock data** with benchmark source-type expectations (add `news` and `docs` demo sources, or adjust mock benchmark scoring).
2. **Improve `detect_source_type`** heuristics and track-level overrides in `app/services/evidence.py`.
3. **Expand query templates** per track so Tavily returns more on-target URLs.
4. **Reduce real-mode latency** — profile slow nodes, consider lowering `max_results_per_query`, add query caching across benchmark runs.
5. **Add LLM-as-judge or human eval** for claim-level accuracy (not in Phase 4 scope).

### Evaluation project layout

```text
app/evaluation/
  benchmark_tasks.json   # 20 benchmark cases
  schemas.py             # BenchmarkTask, TaskScore, ExperimentResult
  loader.py              # load_benchmark_tasks()
  scorers.py             # deterministic scoring functions
  runner.py              # run_evaluation()
  report_writer.py       # JSON, CSV, summary outputs
  failure_analysis.py    # failure mode Markdown reports

app/observability/
  metrics.py             # compute_run_metrics() → JSONL

eval_results/            # experiment outputs (JSON, CSV, Markdown)

scripts/
  run_evaluation.py      # CLI entry point
```

---

## Development Cost Control

- Keep `max_results_per_query` small (default is 3) — each query consumes Tavily credits and increases LLM context size.
- Use `--max-tasks` with `scripts/run_evaluation.py` — do not run all 20 benchmark tasks in real mode during development.
- Do not run benchmark or load-test loops in real mode without budgeting for Tavily and Groq usage.
- Prefer mock mode for UI development and CI — it is instant, free, and deterministic.

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
    evaluation/              # Phase 4 benchmark harness
    graph/                   # LangGraph state, nodes, workflow
    observability/           # Phase 4 run metrics
    schemas/                 # Pydantic models (research, report, events)
    services/                # LLM, search, evidence, and report services
    main.py                  # FastAPI entrypoint
  eval_results/              # Phase 4 experiment outputs
  logs/                      # rivalscope.log + research_runs.jsonl (gitignored)
  scripts/
    manual_live_research_test.py   # Manual smoke test for real mode only
    run_evaluation.py              # Phase 4 benchmark CLI
  tests/
  pyproject.toml
  .env.example
  .env                       # Never commit — gitignored
```
