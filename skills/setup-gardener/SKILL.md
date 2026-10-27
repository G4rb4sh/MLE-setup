---
name: setup-gardener
description: >
  Use when editing MLE-setup, its skills, always-on instructions, hooks or
  agents; saving a preference outside memory; diagnosing skills that do not
  appear or do not trigger; updating superpowers/ponytail; or moving the setup
  to another computer. Triggers: "mejorar el setup", "dónde edito esto",
  "guardá esta preferencia", "la skill no aparece", "no se activó la skill",
  "actualizá los plugins", "gardener".
---

# Maintain the setup from its source

Edit existing guidance before adding more. Smallest change that fixes observed
friction; one preference is not a framework.

## 1. Locate source and surface
- Resolve symlinks on this skill's path: the source is `skills/setup-gardener/`
  under the `MLE-setup` git root. Check `git status` and keep unrelated changes.
- Never edit installed plugin copies (`~/.copilot/installed-plugins/`,
  `~/.claude/plugins/`, VS Code extensions). If loaded from a copy, use the
  personal `mle-setup` skill or ask.
- Identify the surface (Copilot CLI/app, VS Code, Claude Code): each discovers
  plugins separately; one working does not prove another does.

## 2. Where each change goes
| Change | Source of truth |
| --- | --- |
| Always-on rule (keep it under ~40 lines) | `MLE-setup/hooks/session-context.md` |
| Hook wiring | `hooks/copilot-hooks.json` (Copilot) and `hooks/claude-hooks.json` (Claude Code); never `hooks/hooks.json` |
| Consulting/ML workflow or trigger | `MLE-setup/skills/<name>/SKILL.md` |
| Subagent behavior | `MLE-setup/agents/` |
| Workflow/simplicity skills | Upstream `superpowers` / `ponytail` plugins: update with `copilot plugin update <name>` or Claude Code `/plugin`; override behavior from this plugin, never by editing their install |
| Private preferences, machine map, authorization | `MLE-setup-personal/skills/` |
| Cross-project notes | `MLE-setup-personal/memory/` |
| Linking across computers | `MLE-setup-personal/bin/` and its README |
| One client's/project's rule | That repo's `AGENTS.md` or `.github/instructions/` |

Keep machine paths and private data out of the shared plugin. Put procedures in
skills, not in always-on text. When a skill did not trigger, add the user's
actual phrase to its `description` (which must say when to use it and when not).

## 3. Authorization
Small, local, reversible edits covered by the request or the personal standing
authorization: apply and explain. Never weaken security, bypass approvals,
touch production, install untrusted plugins, commit, push, or publish without
an explicit request.

## 4. Verify
- Check the diff, frontmatter (`name` equals folder), descriptions, and paths.
- Hooks: `bash -n` the script, run it, and parse its JSON output.
- Hooks: test both formats (`COPILOT_CLI=1` vs only `CLAUDE_PLUGIN_ROOT` set).
- In Copilot CLI, `userPromptSubmitted` plugin hooks cannot inject context; only
  `sessionStart` (and tool/subagent events) can. Claude Code's
  `UserPromptSubmit` can, so per-prompt routing would be Claude-only.
- Discovery: `copilot skill list` / `copilot plugin list`; in Claude Code
  `claude plugin validate <path>` and `/plugin`, in a fresh session. If the
  editor UI cannot be inspected, say discovery is unverified.
- Close with changed files, checks run, pending activation steps, and git status.

## Periodic review (on request)
Query skill usage in the session store over the last ~60 days. Skills never
triggered: fix their `description` or propose removal. Overlapping skills: merge.
