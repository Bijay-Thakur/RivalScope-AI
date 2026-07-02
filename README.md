# RivalScope AI

Monorepo for **RivalScope AI** — source-grounded competitive intelligence for GTM teams.

## Structure

```
rivalscope-ai/
├── frontend/     Next.js dashboard (TypeScript, Tailwind)
└── backend/      FastAPI research agent API (Python, mock demo)
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs

## Status

- **Frontend:** Portfolio demo with simulated agent progress and mock report
- **Backend:** Phase 3 live research pipeline (mock + real modes) with Phase 4 evaluation harness
- **Evaluation:** 20-task benchmark suite; mock and small real smoke tests completed (see Phase 4 below)

No API keys required for mock mode or frontend demo.

---

## Phase 4 — Evaluation & Observability

Phase 4 adds a repeatable benchmark harness to measure report quality, source coverage, and pipeline reliability — without changing API routes or the frontend.

### Why evaluation matters

RivalScope is meant to produce **source-grounded** competitive intelligence for GTM teams. Without evaluation, it is hard to know whether the agent:

- Returns complete reports across categories (pricing, positioning, battlecard, etc.)
- Collects the right **types** of sources (company pages, pricing, news, docs)
- Maintains citation integrity between evidence and sources
- Runs fast enough for interactive use

Phase 4 scores are **structural and deterministic** (not LLM-as-judge). They catch missing sections, weak source mix, and broken citations — but they do **not** yet verify factual accuracy of claims.

### Benchmark size

- **20 B2B SaaS benchmark tasks** in `backend/app/evaluation/benchmark_tasks.json`
- Covers pairs such as ClickUp vs Notion, Asana vs Monday.com, Stripe vs Adyen, etc.
- Each task defines expected sections, source types, and high-level facts

Initial runs used subsets to control cost: **5 tasks in mock mode**, **2 tasks in real mode**.

### Metrics

Overall score is a weighted blend:

| Metric | Weight | What it measures |
| --- | ---: | --- |
| Task completion | 30% | Major report fields populated |
| Section coverage | 25% | Expected benchmark sections present |
| Source coverage | 20% | Expected source types found |
| Citation integrity | 15% | Evidence linked to valid sources with URLs |
| Efficiency | 10% | Latency (≤30s = 1.0, ≤60s = 0.7, ≤120s = 0.4) |

### How to run

**Mock evaluation** (no API keys, fast, used in CI):

```bash
cd backend
# Windows
set RESEARCH_MODE=mock
python scripts/run_evaluation.py --experiment-name phase4_mock_baseline --max-tasks 5

# Mac/Linux
RESEARCH_MODE=mock python scripts/run_evaluation.py --experiment-name phase4_mock_baseline --max-tasks 5
```

**Real evaluation** (consumes Groq + Tavily credits — keep `--max-tasks` small):

```bash
cd backend
# Ensure backend/.env has GROQ_API_KEY, TAVILY_API_KEY, RESEARCH_MODE=real
python scripts/run_evaluation.py --experiment-name phase4_real_smoke_test --max-tasks 2
```

Outputs are written to `backend/eval_results/`:

- `{experiment}.json` — full results
- `{experiment}.csv` — per-task scores
- `{experiment}_summary.md` — overview table
- `{experiment}_failure_modes.md` — failure analysis and recommended fixes

### Example results (initial runs)

| Experiment | Mode | Tasks | Avg Score | Avg Latency | Avg Sources | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `phase4_mock_baseline` | mock | 5 | 0.92 | 0.03s | 5.0 | Structural baseline; mock data lacks `news` and `docs` source types |
| `phase4_real_smoke_test` | real | 2 | 0.95 | 47.29s | 30.5 | Live search works; source-type labeling still imperfect on 1/2 tasks |

Scores are decent on structure (completion, sections, citations) but **source coverage is the weakest dimension** in both runs. Real-mode latency for one task exceeded 60s.

### Known failure modes

| Failure mode | Seen in | Cause | Planned fix |
| --- | --- | --- | --- |
| Missing `news` / `docs` source types | Mock baseline (5/5 tasks) | Phase 2 mock report only includes `company_page` and `pricing_page` | Align mock data with benchmark expectations or exclude unmockable types from mock scoring |
| Missing `company_page` source type | Real smoke (1/2 tasks) | `detect_source_type` heuristics mislabel some Tavily results | Improve URL/title heuristics; enforce track-level source type overrides |
| Slow runs (>60s) | Real smoke (1/2 tasks) | Four parallel search tracks + LLM calls per task | Tune `max_results_per_query`, add caching, profile slow nodes |
| No factual accuracy scoring | All runs | Phase 4 uses deterministic scorers only | Add LLM-as-judge or human review in a later phase |

See `backend/README.md` for full evaluation and observability documentation.
