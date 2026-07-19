# Failure Mode Report: gemini_latest

## 1. Executive Summary

This experiment ran **1** task(s) in **real** mode using **gemini**.
The average overall score was **0.7669** with mean latency of **76.78s** and **21.00** sources per task.

- Tasks below 80% overall score: **1**
- Weakest average dimension: **source_coverage** (0.6000)
- Distinct failure notes: **6**

## 2. Lowest Scoring Tasks

| Task ID | Overall | Source Cov. | Citation | Latency (s) | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| task-001-clickup-notion | 0.7669 | 0.6000 | 1.0000 | 76.78 | 2 |

## 3. Common Failure Notes

- (1) Major field 'sales_battlecard' is missing or empty
- (1) Expected section 'recent_moves' is missing or empty
- (1) Expected section 'sales_battlecard' is missing or empty
- (1) Expected source type 'company_page' not found in report sources
- (1) Expected source type 'docs' not found in report sources
- (1) One-sided comparison row: 'General Pricing Transparency'

## 4. Source Coverage Weaknesses

- **task-001-clickup-notion** — coverage 0.60, 21 source(s). Expected source type 'company_page' not found in report sources; Expected source type 'docs' not found in report sources

## 5. Citation Integrity Issues

- No citation integrity issues detected.

## 6. Comparison Matrix Issues

- **task-001-clickup-notion** — two-sidedness 0.80, citation validity 1.00. One-sided comparison row: 'General Pricing Transparency'

## 7. Latency / Efficiency Issues

- **task-001-clickup-notion** — 76.78s (slow (61-120s)), efficiency score 0.4

## 8. Recommended Fixes for Next Phase

1. Expand track-specific query templates and source-type detection to capture company, pricing, docs, and news pages more reliably.
2. Improve URL/title heuristics in `detect_source_type` and add track-level source_type overrides for pricing and news queries.
3. Map benchmark expected sections to report fields and add targeted prompt instructions for consistently empty sections.
4. Reduce `max_results_per_query`, parallelize tracks carefully, and cache repeated search queries across benchmark tasks.
