---
name: pr-review
description: >
  Correctness review of a diff, branch, or PR before merging. Use when the user
  says "revisá esto", "revisame el PR", "¿está listo para mergear?", "review",
  or before opening a PR. Not for over-engineering/complexity (ponytail-review)
  or a whole-repo delivery check (pre-delivery-audit).
---

## 1. Pin the scope
- Get the fixed point (base branch, commit, or PR). If not given, ask.
- Run `git diff <base>...HEAD` and `git log <base>..HEAD --oneline`. Stop if the
  ref does not resolve or the diff is empty.
- Find the spec: issue referenced in commits, a path the user gave, or a doc in
  `docs/`/`specs/`. If none exists, say so and skip the Spec axis.

## 2. Review on separate axes (do not merge or rerank them)
**Spec**: requirements missing or partial; behavior not asked for (scope creep);
requirements implemented wrongly. Quote the spec line for each.

**Correctness**: logic, edge cases, error handling, concurrency if relevant.
Are the changes covered by tests that verify behavior, not implementation?

**Standards**: repo `AGENTS.md`/`CONTRIBUTING.md` and existing patterns. A
documented repo rule always wins; skip what linters already enforce.

**Safety and contract**: no secrets or client data in code/logs/fixtures,
external inputs validated, breaking changes to APIs/schemas flagged.

**ML (when applicable)**: data leakage between splits, seeds/config/data
version traceable (see `ml-repro`), metrics compared against a baseline,
`ml-over:` when a lower rung of the ML ladder would suffice.

## 3. Report
One line per finding, `file:line — problem — fix`, ordered by severity, grouped
by axis. Close with a verdict (ready to merge / needs changes), blockers listed
separately from suggestions. For large diffs, suggest running `ponytail-review`.
