# Failure Mode Report: phase4_mock_baseline

## 1. Executive Summary

This experiment ran **5** task(s) in **mock** mode using **groq**.
The average overall score was **0.9200** with mean latency of **0.03s** and **5.00** sources per task.

- Tasks below 80% overall score: **0**
- Weakest average dimension: **source_coverage** (0.6000)
- Distinct failure notes: **2**

## 2. Lowest Scoring Tasks

| Task ID | Overall | Source Cov. | Citation | Latency (s) | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| task-001-clickup-notion | 0.9200 | 0.6000 | 1.0000 | 0.03 | 0 |
| task-002-asana-monday | 0.9200 | 0.6000 | 1.0000 | 0.03 | 0 |
| task-003-linear-jira | 0.9200 | 0.6000 | 1.0000 | 0.02 | 0 |
| task-004-slack-teams | 0.9200 | 0.6000 | 1.0000 | 0.03 | 0 |
| task-005-hubspot-salesforce | 0.9200 | 0.6000 | 1.0000 | 0.02 | 0 |

## 3. Common Failure Notes

- (5) Expected source type 'news' not found in report sources
- (5) Expected source type 'docs' not found in report sources

## 4. Source Coverage Weaknesses

- **task-001-clickup-notion** — coverage 0.60, 5 source(s). Expected source type 'news' not found in report sources; Expected source type 'docs' not found in report sources
- **task-002-asana-monday** — coverage 0.60, 5 source(s). Expected source type 'news' not found in report sources; Expected source type 'docs' not found in report sources
- **task-003-linear-jira** — coverage 0.60, 5 source(s). Expected source type 'news' not found in report sources; Expected source type 'docs' not found in report sources
- **task-004-slack-teams** — coverage 0.60, 5 source(s). Expected source type 'news' not found in report sources; Expected source type 'docs' not found in report sources
- **task-005-hubspot-salesforce** — coverage 0.60, 5 source(s). Expected source type 'news' not found in report sources; Expected source type 'docs' not found in report sources

## 5. Citation Integrity Issues

- No citation integrity issues detected.

## 6. Latency / Efficiency Issues

- All tasks completed within the 30s efficiency target.

## 7. Recommended Fixes for Next Phase

1. Expand track-specific query templates and source-type detection to capture company, pricing, docs, and news pages more reliably.
2. Improve URL/title heuristics in `detect_source_type` and add track-level source_type overrides for pricing and news queries.
