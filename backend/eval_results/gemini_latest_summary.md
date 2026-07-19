# Experiment Summary: gemini_latest

**Status:** Latest full-mode Gemini eval (canonical readings for this directory).

## Overview

- **Experiment name:** gemini_latest
- **Model provider:** gemini (research + judge)
- **Research mode:** real
- **Eval mode:** full
- **Judge model:** gemini-2.5-flash
- **LangSmith tracing:** on
- **LangSmith project:** rivalscope-ai
- **Total tasks:** 1 (`task-001-clickup-notion`)
- **Average score:** 0.7669
- **Average latency (s):** 76.78
- **Average source count:** 21.00

## Headline Metrics

| Metric | Value | Formula |
|---|---:|---|
| **Claim grounding rate** | **100.0%** | (`supported` + `partial`) ÷ `n_judged_ok` |
| **Hallucination rate** | **0.0%** | (`unsupported` + `contradicted`) ÷ `n_judged_ok` |
| Comparison grounding | 88.9% | matrix cell values judged grounded vs citations |
| Comparison two-sidedness | 80.0% | rows with both sides filled |
| Comparison citation validity | 100.0% | matrix source IDs resolve |

## Judge Observability

- **n_claims_total:** 21
- **n_judged_ok:** 21
- **n_judge_errors:** 0
- **n_citation_invalid:** 0

Implied verdict mix for this run:

| Bucket | Count | Share |
|---|---:|---:|
| Grounded (`supported` / `partial`) | 21 | 100% |
| Hallucinated (`unsupported` / `contradicted`) | 0 | 0% |

Because every successfully judged claim lands in exactly one of those two buckets:

**grounding_rate + hallucination_rate = 1.0** → 100% + 0% = 100%.

---

## Why grounding is 100% and hallucination is 0%

### 1. What is actually scored

These rates are **not** “is the whole report factually perfect vs the real world.”

For each item in `report.evidence`:

1. Take the **claim text** (`evidence.claim`).
2. Take the **cited source text** (`evidence.raw_text`, else source snippet).
3. Ask the Gemini judge: does *that citation* support *that claim*?

Verdicts:

| Judge label | Counts toward |
|---|---|
| `supported` | grounding |
| `partial` | grounding |
| `unsupported` | hallucination |
| `contradicted` | hallucination |

So hallucination here means **unfaithful to the cited page**, not “wrong vs Wikipedia / sales reality.”

### 2. Why this run hit 100% / 0%

On this run the pipeline produced **21 evidence claims**, and the judge marked **all 21** as `supported` or `partial`.

That is common when claims are largely **extractive** (sentences pulled from the same page text that is later used as the citation). If claim ≈ sentence from page X, the judge rarely says the page is silent (`unsupported`) or opposite (`contradicted`).

Hallucination is 0% **because** there were zero `unsupported`/`contradicted` verdicts — not because the product cannot invent narrative elsewhere.

### 3. Why an earlier run showed ~87% grounding

| Run | Grounding | Hallucination (current formula) | Claims |
|---|---:|---:|---:|
| Earlier `gemini_post_harden` | ~87% | would be ~13% | 23 |
| This `gemini_latest` | 100% | 0% | 21 |

Same benchmark task, **different live retrieval + generation**. Tavily pages, extracts, and Gemini wording change between runs, so the claim set changes. That earlier ~13% gap was almost certainly `unsupported` claims (source silent), which the **old** metric did not count as hallucination; under the **current** formula those would raise hallucination_rate.

100% here is **run variance on one task**, not a permanent quality guarantee.

### 4. What these rates do *not* cover

Still **not** included in grounding / hallucination:

- Free-form report prose (`companySnapshot`, strengths, weaknesses, battlecard talk tracks, etc.)
- Comparison matrix cells (tracked separately as `comparison_grounding` = **88.9%** this run)
- Gold `expected_facts` from the benchmark file (unused by scorers)

So a report can still overclaim in narrative sections while evidence-claim grounding stays high.

---

## Task Scores

| Task ID | Overall | Completion | Sections | Sources | Citations | Evidence | Sources | Latency (s) | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| task-001-clickup-notion | 0.7669 | 0.8750 | 0.7778 | 0.6000 | 1.0000 | 21 | 21 | 76.78 | 2 |

## Top Failure Notes

Structural / coverage issues (separate from claim grounding):

- (1) Major field 'sales_battlecard' is missing or empty
- (1) Expected section 'recent_moves' is missing or empty
- (1) Expected section 'sales_battlecard' is missing or empty
- (1) Expected source type 'company_page' not found in report sources
- (1) Expected source type 'docs' not found in report sources
- (1) One-sided comparison row: 'General Pricing Transparency'

## Observability

When LangSmith tracing is enabled, open [smith.langchain.com](https://smith.langchain.com) → project `rivalscope-ai` for per-claim judge traces.
