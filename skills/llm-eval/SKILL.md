---
name: llm-eval
description: >
  Design or improve evaluation for an LLM-based feature (RAG,
  agents, classification, extraction, chat). Use when the user
  mentions evals, prompt or model changes, quality regressions,
  or before delivering a GenAI feature to a client.
---

Objective: no prompt, model, or retrieval change reaches the
client without numbers. Steps:

1. Define what "good" means for this feature with the user:
   observable criteria (factual accuracy, format, coverage,
   correct refusal, latency, cost). Without criteria there is no eval.
2. Build a versioned case dataset in the repo: typical cases,
   edge cases, adversarial cases, and cases that must be rejected.
   Start small (20-50) and grow with each real reported failure.
3. Choose the method by criterion: programmatic asserts where possible
   (format, fields, citations present), LLM-as-judge with written rubric
   where not, and sampled human review to calibrate the judge.
4. A single command runs the eval and returns score by criterion,
   compared against the previous run (detect regressions, not
   only the average).
5. Record every run: prompt version, model, parameters,
   dataset, and results. A change without a recorded run is not merged.

Rule: failures found in production or by the client become dataset cases
before they are fixed.
