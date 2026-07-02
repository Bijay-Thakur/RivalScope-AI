# Failure Mode Report: report_writer_smoke

## 1. Executive Summary

This experiment ran **1** task(s) in **real** mode using **groq**.
The average overall score was **0.9600** with mean latency of **22.16s** and **31.00** sources per task.

- Tasks below 80% overall score: **0**
- Weakest average dimension: **source_coverage** (0.8000)
- Distinct failure notes: **1**

## 2. Lowest Scoring Tasks

| Task ID | Overall | Source Cov. | Citation | Latency (s) | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| task-001-clickup-notion | 0.9600 | 0.8000 | 1.0000 | 22.16 | 0 |

## 3. Common Failure Notes

- (1) Expected source type 'company_page' not found in report sources

## 4. Source Coverage Weaknesses

- **task-001-clickup-notion** — coverage 0.80, 31 source(s). Expected source type 'company_page' not found in report sources

## 5. Citation Integrity Issues

- No citation integrity issues detected.

## 6. Latency / Efficiency Issues

- All tasks completed within the 30s efficiency target.

## 7. Recommended Fixes for Next Phase

1. Expand track-specific query templates and source-type detection to capture company, pricing, docs, and news pages more reliably.
2. Improve URL/title heuristics in `detect_source_type` and add track-level source_type overrides for pricing and news queries.
