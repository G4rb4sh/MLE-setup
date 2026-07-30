---
name: pr-review
description: >
  Review of a diff, branch, or PR before merging. Use when the
  user asks "review this", "PR review", "is this ready to merge?",
  or before opening a PR.
---

Review the change against this checklist. Report concrete findings with
file and line; one line per finding, ordered by severity.

1. Correctness: logic, edge cases, error handling, race conditions
   if applicable.
2. Tests: is the change covered? Do the tests verify behavior,
   not implementation?
3. Consistency: does it follow the repo AGENTS.md conventions and the
   patterns already present in the codebase?
4. Basic security: no hardcoded secrets, external inputs validated,
   no client data in logs.
5. Contract: are changes to APIs, schemas, or public interfaces
   flagged as breaking when appropriate?

Out of scope: complexity and over-engineering (run the ponytail-review skill
in parallel; always suggest it for large diffs).

Close: clear verdict (ready to merge / needs changes) with blockers
listed separately from optional suggestions.
