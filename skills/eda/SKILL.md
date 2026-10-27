---
name: eda
description: >
  Standardized first exploration of an unfamiliar dataset. Use when the user
  says "explorá este dataset", "EDA", "¿qué hay en estos datos?", "mirá este
  CSV/tabla", or at the start of an ML project with new data. Not for
  monitoring production data or debugging a pipeline.
---

Generate a reproducible exploratory analysis (script or notebook according to
the repo convention) and a summary. Cover:

1. Shape: rows, columns, types, memory. Sample of 5 rows.
2. Quality: nulls by column, duplicates, constants, cardinality
   of categoricals, impossible or suspicious ranges.
3. Distributions: statistics for numerics, top values for
   categoricals, target balance if it exists.
4. Relationships: strong correlations with the target and between features;
   data leakage signals (features that "know" the future).
5. Temporality: if dates exist, covered range, gaps, visible drift.
6. Modeling risks: short, prioritized list of issues that
   would affect a model, with proposed treatment.

Rules: never upload or copy client data outside the project environment;
the summary uses aggregates, never individual records with sensitive
information.
