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

Run the `setup-gardener` skill every ~2 weeks or when the lesson inbox
exceeds 10. Bump `version` in `plugin.json` and `.claude-plugin/marketplace.json`
when publishing changes.

## License

Original code under MIT (see `LICENSE`). Vendored third-party components
and their attribution are listed in `NOTICE`.
