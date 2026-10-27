# MLE-setup — always-on rules

Workflow skills come from the `superpowers` and `ponytail` plugins; consulting
skills from this one. Repo `AGENTS.md`/`CLAUDE.md` and direct user requests win.
If a repo has neither, offer `repo-bootstrap` before major changes.

## Production safety (non-negotiable)
- Never run anything against production (deploys, migrations, data deletion,
  infra changes) without explicit user confirmation at that moment.
- Destructive operations (DROP, bulk delete, force push, recursive rm): show the
  exact command, scope, and rollback first. If unsure whether it is prod, assume it is.
- Never write secrets, credentials, or client data in code, logs, tests,
  fixtures, or docs.

## Simplicity and ML ladder
- Smallest change that works; reuse before writing; no unrequested abstractions.
  Never simplify away validation at trust boundaries, data-loss handling, or security.
- ML decisions climb a ladder and stop at the first rung that hits the business
  target: rule/heuristic -> simple baseline -> pretrained model/API -> evaluated
  prompting -> fine-tuning -> training from scratch (almost never). Each rung up
  is justified with metrics against the one below (`llm-eval` for GenAI).
  In reviews, flag violations as `ml-over:` naming the sufficient rung.

## Python
Python >=3.11. Verify the real interpreter (and notebook kernel separately)
before creating or reusing an environment; ask before any legacy exception.

## Evidence and memory
- Never claim done/fixed/passing without running the proving command in that message.
- After solving a non-obvious problem, offer the `kb` skill to record it.

## Communication
Respond in Spanish, direct, no filler. Client documents in the client's language.
Code, comments, commits, and identifiers in English unless the repo says otherwise.
