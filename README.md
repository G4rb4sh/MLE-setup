# MLE-setup

A self-contained agent plugin for B2B ML consulting, for GitHub Copilot CLI
(and compatible with Claude Code):

- **Workflow** (vendored from [superpowers](https://github.com/obra/superpowers), MIT):
  brainstorming, writing-plans, test-driven-development, systematic-debugging,
  verification-before-completion, and the collaboration and meta skills.
- **Simplicity** (vendored from [ponytail](https://github.com/DietrichGebert/ponytail), MIT):
  ponytail (code ladder + ML ladder), ponytail-review,
  ponytail-audit, ponytail-debt.
- **ML consulting** (original work): repo-bootstrap, pr-review, ml-repro,
  eda, llm-eval, prod-incident, scoping, status-update, pre-delivery-audit,
  handoff, kb, setup-gardener.
- **Subagents**: code-reviewer, researcher, test-runner.
- **SessionStart hook**: injects the skills gateway + simplicity core +
  preferences + lesson reminder.

## Python policy

Projects and notebooks use **Python >=3.11**. Verify the interpreter before
creating/reusing an environment and select notebook kernels separately; never
fall back to an older system Python without an explicit legacy exception.
This rule lives in [session instructions](hooks/session-context.md),
[repo-bootstrap](skills/repo-bootstrap/SKILL.md), and
[ml-repro](skills/ml-repro/SKILL.md), not only in agent memory.
To carry it to another computer, synchronize this repository and load the updated
plugin there using one of the installation methods below. A separately installed
plugin copy must also be updated; pulling the source alone does not update it.

## Install

### Test locally (without publishing)

    copilot --plugin-dir /path/to/MLE-setup

### From GitHub

    copilot plugin marketplace add G4rb4sh/MLE-setup
    copilot plugin install mle-setup@mle-setup

## User state

Lessons and the knowledge base are stored outside the plugin, in
`~/.mle-setup/` (`lessons.md`, `knowledge/INDEX.md`, `knowledge/cases/`), so
they do not mix with the installed plugin (which is read-only).

## Maintenance

Use [setup-gardener](skills/setup-gardener/SKILL.md) for targeted setup edits,
missing skills, portable preferences, or periodic maintenance (~2 weeks / >10
lessons). It maps what to edit, how to locate source vs installed copies, the
user's authorization boundaries, and checks for source/installation/activation.

VS Code and CLI discovery are separate: a marketplace configured in the CLI is
not proof that the editor loaded it. Personal skill links expose workflows, not
plugin hooks or agents. Use the active editor's skill list to verify discovery.
Bump `version` in `plugin.json` and `.claude-plugin/marketplace.json` only when
preparing publication. Local maintenance does not automatically commit or push.

## License

Original code under MIT (see `LICENSE`). Vendored third-party components
and their attribution are listed in `NOTICE`.
