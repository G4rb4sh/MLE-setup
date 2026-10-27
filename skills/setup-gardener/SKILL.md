---
name: setup-gardener
description: >
  Use when editing MLE-setup, skills, agent instructions or hooks; saving
  preferences outside memory; diagnosing missing skills; moving the setup
  between computers; or digesting lessons. Triggers include "mejorar el setup",
  "dónde editar", "guardar esta preferencia", "modificar tus herramientas",
  "skills no aparecen", "gardener", and "setup maintenance".
---

# Maintain the setup from its source

Edit existing guidance before adding more. Use the smallest change that fixes
observed friction; do not turn one preference into a framework.

## 1. Locate source and active surface
- Resolve symlinks/junctions on this skill's location. In the source checkout,
  this file is `skills/setup-gardener/SKILL.md` beneath the `MLE-setup` git root.
- Verify the root with git, inspect its status and local instructions, and
  preserve unrelated changes. Never edit a plugin cache or VS Code extension
  installation as the source of truth.
- If loaded from a copy, consult the personal `mle-setup` skill, known local
  marketplace configuration, or the user for the source checkout. Search known
  project locations first, not the entire home directory. Do not guess Mac paths
  on Windows or silently clone a new source.
- Identify the surface: VS Code, Copilot CLI, or Claude Code. A CLI marketplace
  entry does not prove VS Code loaded the plugin. Verify discovery separately.

## 2. Choose the edit location
Paths below are relative to the appropriate source checkout.

| Change | Source of truth |
| --- | --- |
| Shared always-on guidance | `MLE-setup/hooks/session-context.md` |
| Reusable workflow or trigger | Existing `MLE-setup/skills/<name>/SKILL.md` |
| Subagent behavior | `MLE-setup/agents/` |
| Executable session behavior | `MLE-setup/hooks/hooks.json` and `session-start.sh` |
| Private preferences, machine map, personal authorization | `MLE-setup-personal/skills/` |
| Cross-project notes | `MLE-setup-personal/memory/` or the configured user-memory location |
| Linking across computers | `MLE-setup-personal/bin/` and its README |
| One client's/project's rule | That project's `AGENTS.md` or `.github/instructions/` |
| Native editor/MCP tool behavior | Supported configuration or an extension update, not installed vendor code |

Keep machine paths and private information out of the shared plugin. If adding
an always-on rule, keep it short and put procedures in a skill. Update descriptions
with actual user phrases when discovery failed. Respect third-party attribution.

## 3. Apply within the user's authorization
- A targeted request or explicit standing authorization can cover small, local,
  reversible edits. State the scope and apply them without asking the same
  permission again. Otherwise propose the change first.
- Do not interpret permission to improve the setup as permission to weaken
  security, bypass tool approvals, change production, install untrusted plugins,
  or perform destructive operations. Follow the user's git policy; no automatic
  commit, push, publication, or blanket staging of existing changes.
- For a targeted request, skip inbox cleanup, upstream refreshes, and unrelated
  preferences. This setup is maintained for the user's task, not for its own sake.

## 4. Verify source, installation, and activation separately
- Inspect the diff; check frontmatter, name/folder agreement, descriptions and
  referenced paths. For hooks/scripts, run syntax checks and focused behavior
  tests (including idempotence and conflict handling for linking scripts).
- Exercise the changed hook and parse its output; do not claim injection worked
  merely because a Markdown file changed. Test representative skill scenarios.
- For VS Code skill discovery, use a supported personal skill directory such as
  `~/.copilot/skills/<name>/SKILL.md`, an explicitly configured skill location,
  or a verified editor plugin installation. Preserve the original public/private
  source; do not move a shared skill into the private repo just to expose it.
  A source link avoids stale copies. Personal linking scripts expose only that
  repo's skills, not the whole shared plugin. A skill link does not activate
  plugin hooks or agents; those require the corresponding plugin/editor configuration.
- Confirm the skill in `/skills` or the Agent Customizations editor in a fresh
  chat if needed. If the editor UI cannot be inspected, report filesystem checks
  and leave actual discovery explicitly unverified; do not fabricate activation.
- For another computer, synchronize source and recreate links or update the
  installed plugin copy. Do not assume Settings Sync transfers external repos.
  Only bump manifest versions when preparing an authorized publication.
- Close with changed locations, checks run, remaining activation steps, and
  commit/push status. Do not claim Windows execution based only on Mac tests.

## Optional periodic maintenance
When requested (or suggested after >10 lessons / ~2 weeks), read
`~/.mle-setup/lessons.md`; a missing inbox is empty, not an error. Route each lesson
using the table above or `kb` for a solved case. New workflow skills need repeated
evidence; merge overlap and propose unused-skill removal. Archive only lessons
actually processed, with their destination, and retain unresolved ones. Review
vendored upstream changes only when useful; never update them silently.
