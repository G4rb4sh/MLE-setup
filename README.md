# MLE-setup

Agent plugin for B2B ML consulting, for GitHub Copilot CLI (compatible with
Claude Code). It complements two upstream plugins instead of copying them:

| Plugin | Provides | Install |
| --- | --- | --- |
| [superpowers](https://github.com/obra/superpowers) | brainstorming, plans, TDD, debugging, verification, subagents | marketplace `obra/superpowers-marketplace`, plugin `superpowers@superpowers-marketplace` |
| [ponytail](https://github.com/DietrichGebert/ponytail) | simplicity / YAGNI, review and audit for over-engineering | marketplace `DietrichGebert/ponytail`, plugin `ponytail@ponytail` |
| **mle-setup** (this repo) | consulting and ML skills, agents, always-on safety rules | marketplace `G4rb4sh/MLE-setup` (or a local path), plugin `mle-setup@mle-setup` |

## Contents
- **Skills**: repo-bootstrap, pr-review, ml-repro, eda, llm-eval,
  prod-incident, scoping, status-update, pre-delivery-audit, handoff, kb,
  office-docs, setup-gardener.
- **Agents**: code-reviewer, researcher, test-runner.
- **SessionStart hook**: injects [session-context.md](hooks/session-context.md)
  (production safety, ML ladder, Python >=3.11, evidence, language).

## Install

Copilot CLI (shell):

    copilot plugin marketplace add obra/superpowers-marketplace
    copilot plugin marketplace add DietrichGebert/ponytail
    copilot plugin marketplace add G4rb4sh/MLE-setup   # or /path/to/MLE-setup (read live)
    copilot plugin install superpowers@superpowers-marketplace
    copilot plugin install ponytail@ponytail
    copilot plugin install mle-setup@mle-setup

Update with `copilot plugin update <name>`.

Claude Code (inside a session, one command per prompt):

    /plugin marketplace add obra/superpowers-marketplace
    /plugin marketplace add DietrichGebert/ponytail
    /plugin marketplace add G4rb4sh/MLE-setup          # or /path/to/MLE-setup
    /plugin install superpowers@superpowers-marketplace
    /plugin install ponytail@ponytail
    /plugin install mle-setup@mle-setup

Update from `/plugin` (Marketplaces -> update). To try local edits without
installing: `claude --plugin-dir /path/to/MLE-setup`.

Each tool reads its own manifest and hook file: Copilot uses `plugin.json` +
`hooks/copilot-hooks.json`; Claude Code uses `.claude-plugin/plugin.json` +
`hooks/claude-hooks.json`. Both run the same `hooks/session-start.sh`. Do not
add a `hooks/hooks.json` (Claude Code loads it by default and it would run
twice).

## Knowledge base
The `kb` skill stores solved problems per repo in `docs/solutions/` and
sanitized cross-client patterns in `~/.mle-setup/knowledge/`.

Optional: [Engram](https://github.com/Gentleman-Programming/engram) adds automatic
per-project memory over MCP (local SQLite in `~/.engram`, outside any repo).
When its `mem_*` tools are present, the always-on rules tell the agent to use
them; `kb` remains the curated record. Keep `.engram/` in your global gitignore.

## Maintenance
Use [setup-gardener](skills/setup-gardener/SKILL.md): where to edit, how to
verify, and authorization limits. `bash skills/setup-gardener/scripts/doctor.sh`
is a read-only health check (plugins, skill links, brands, Engram). Bump
`version` in the manifests only when publishing. Local maintenance does not
commit or push automatically.

## License
MIT (see `LICENSE` and `NOTICE`).
