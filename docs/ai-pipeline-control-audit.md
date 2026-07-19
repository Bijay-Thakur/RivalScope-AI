# RivalScope AI — Pipeline Control Audit

**Date:** 2026-07-19  
**Scope:** `backend/app` LangGraph research pipeline (FastAPI + LangGraph).  
**Prompt policy:** System prompts in `prompts.py` treated as given; this audit focuses on application-level enforcement.

## Pipeline (as implemented)

```
normalize_input → create_research_plan → [4 parallel tracks] → fact_checker_stub
  → comparison_agent → report_generator → END
```

Search/extract: Tavily. Evidence/claims: deterministic from search results. LLM stages: fact checker, comparison, report.

---

## Control scorecard

| Control | Status | Existing component | Risk | Required change |
|---|---|---|---|---|
| Research planner LLM call | Missing | `nodes.create_research_plan` (hardcoded 4 tasks); `RESEARCH_PLANNER_SYSTEM_PROMPT` unused | Plan coverage not LLM-driven; prompt dead code | Keep app-owned plan; expand to 7–9 tasks + programmatic `ResearchPlan` validation |
| Planner track/query validation | Missing | None | Duplicate/unknown tracks possible if plan grows | Add `validate_research_plan` |
| Search + retrieval | Implemented | `search.py`, `research_tracks.py`, `query_builder.py` | Rate limits / empty results | Keep; parallel queries already present |
| Content sanitization / injection | Partial | Prompt TRUST BOUNDARY only | Prompt injection via webpage text | Add `content_sanitize.py`; sanitize before LLM context |
| Atomic evidence records | Partial | `EvidenceItem` with claim/raw_text/source_id/company | Claim quality improved; not full typed pricing/feature metadata | Keep EvidenceItem as atomic unit; sanitize raw_text; optional metadata later |
| Source ID app-owned | Implemented | `uuid4()` in `evidence.source_from_search_result` | LLM may invent IDs in FC/compare | Allowlist validation post-LLM |
| Source company ownership | Partial | `company` on Source/Evidence in real tracks; mock often untagged | Cross-company citation leakage | Allowlists `our`/`competitor`; tag mock sources |
| Fact-check count/order/status | Partial | `fact_checker.py` soft parse | Wrong count/status; invented IDs | Normalize 1:1 to input; filter source_ids; map `status` alias |
| Unsupported claim filtering | Missing | Status stored but unused | Unsupported claims enter report narrative | `claim_policy.filter_decisive_claims` |
| Comparison schema/business rules | Partial | `_parse_row` coerces advantage | Invalid rows, leakage, winners without evidence | `validate_comparison_matrix` + repair/fallback |
| Report schema | Partial | Pydantic + safe coercions; sources/evidence overwritten from state | Narrative may invent facts | Grounding strip + deterministic confidence |
| Post-generation grounding | Missing (prod) | Eval judge only | Ungrounded report sentences ship | Deterministic `grounding_verifier` |
| Structured JSON repair | Partial | `json_utils.extract_json_from_text` | Truncated JSON → silent fallback | Bounded repair attempt on schema fail |
| LLM timeout / same-provider retry | Missing | Single attempt then cross-provider fallback | Transient 429/timeout kills stage | Stage temps + timeout + bounded retry |
| Groq primary / Gemini fallback | Implemented | `llm.invoke_with_fallback` + step providers | — | Preserve; add stage temperature map |
| Observability | Partial | `log_run_event`, LangSmith optional | Incomplete validation metrics | Log validation outcomes per stage |
| Tests for failure modes | Partial | Routing/eval/comparison parse tests | Missing allowlist/injection/unsupported | Add `test_pipeline_controls.py` |

---

## Highest-impact gaps (pre-fix)

1. No source-ID allowlists after fact-check / comparison.  
2. Unsupported claims not blocked in code.  
3. No production post-report grounding.  
4. No retrieval sanitization.  
5. No planner programmatic validation.  
6. No LLM timeout / same-provider retry.

Implementation follows in the same change set.

---

## Post-implementation status (2026-07-19)

| Control | Status after change |
|---|---|
| Planner validation (7–9, coverage, duplicates) | Implemented (`pipeline_validation.validate_research_plan`) |
| Content sanitization / injection flagging | Implemented (`content_sanitize`) |
| Source-ID allowlists + company separation | Implemented |
| Fact-check 1:1 normalize | Implemented |
| Unsupported claim filtering | Implemented (`claim_policy`) |
| Comparison business rules + pricing incompatibility | Implemented |
| Structured JSON repair (bounded) | Implemented (`structured_output`) |
| Deterministic confidence | Implemented (`confidence`) |
| Post-report grounding | Implemented (`grounding_verifier`) |
| LLM timeout / retry / stage temps | Implemented (`llm.py` + settings) |
| Failure-mode tests | Implemented (`tests/test_pipeline_controls.py`) |

See also: [ai-pipeline-contract.md](./ai-pipeline-contract.md).
