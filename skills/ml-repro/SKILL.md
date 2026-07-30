---
name: ml-repro
description: >
  Reproducibility checklist for ML code. Use when writing or
  reviewing training, evaluation, or data pipeline code, or when
  the user mentions experiments, models, or datasets.
---

When writing or reviewing ML code, verify:

1. Seeds fixed and logged (framework, numpy, dataloaders).
2. Experiment configuration versioned in files, not
   hardcoded or only in notebooks.
3. Identifiable data version (hash, snapshot, or immutable
   reference). Never paths to data that can change without trace.
4. Metrics and artifacts logged in the project tracker (see
   repo AGENTS.md); if the repo does not define a tracker, ask before
   introducing a new one.
5. Train/val/test separation without data leakage; document the split.
6. The experiment can be rerun with one documented command.

For notebooks: reusable logic extracted into modules; the notebook
only orchestrates and visualizes.
