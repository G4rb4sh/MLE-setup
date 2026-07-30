---
name: repo-bootstrap
description: >
  Configures a repository that does not have agent setup. Use when the
  repo has no AGENTS.md or CLAUDE.md of its own, when the user says
  "bootstrap", "configure this repo", or "repo setup", or when starting
  work on a new client project.
---

Objective: leave the repo with a single source of truth (`AGENTS.md`) and the
minimal `.claude/` structure specific to this project. Never
invent commands or workflows: everything you write must be
verified in the repo, or asked of the user.

## 1. Analyze the repository
Determine, by reading real files (manifests, Dockerfiles, CI configs,
Makefiles, scripts, README):
- Languages, frameworks, and main tools.
- Exact commands for build, test (full suite and a single file),
  lint, format, and local run. Verify them by running them if safe.
- Directory structure and each module's responsibility.
- Existing conventions: commit style, naming, test patterns.
- Sensitive areas: migrations, prod configs, secrets, infrastructure.
- Client context (B2B consulting project): client name,
  constraints (compliance, sensitive data, environments,
  deployment target). If it does not appear in the repo, ask the user.

## 2. Create AGENTS.md at the root
Maximum ~80 lines, actionable. Sections:
1. What this project is and which client it is for (2-3 lines).
2. Commands: exact and verified.
3. Architecture: brief directory map.
4. Conventions: positive rules ("prefer X over Y").
5. Forbidden areas: what not to touch without confirmation.
6. Client context: constraints, environments, sensitive data.

## 3. Link tools
- `CLAUDE.md` -> symlink to `AGENTS.md` (if not possible, one-line file:
  "Read and follow AGENTS.md at the root of this repo").
- `.github/copilot-instructions.md` -> same criterion.

## 4. Create repo-specific .claude/
Only what has real evidence in the repo:
- `.claude/skills/deploy/SKILL.md`: real deploy workflow step by step
  with pre-checks. If there is no evidence (CI/CD, scripts), ask.
- `.claude/skills/ml-experiment/SKILL.md`: only if there is an ML component.
  Repo experiment conventions: where scripts and configs live,
  how runs are tracked.
Do not duplicate what already exists at plugin level: workflow skills
(brainstorming, writing-plans, tdd, debug, verify), simplicity skills
(ponytail and variants), consulting skills (pr-review, handoff,
prod-incident, llm-eval, eda, status-update, pre-delivery-audit,
scoping), or the generic agents.

## 5. Close
- Summary of created files and user confirmation before
  committing.
- Separate commits: one for AGENTS.md and links, another for .claude/.
