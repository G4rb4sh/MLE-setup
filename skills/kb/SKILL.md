---
name: kb
description: >
  Record and retrieve solved problems so they are not solved twice. Use RIGHT
  AFTER fixing a non-obvious bug, integration issue, or environment problem
  ("esto nos va a pasar de nuevo", "guardalo en la kb", "anotá la solución"),
  and BEFORE debugging or planning when the symptom smells familiar ("¿esto ya
  nos pasó?", "¿cómo lo resolvimos?"). Not for trivial fixes or anything
  already documented in the repo.
---

Two stores, searched cheaply with grep; never open every file.

| Store | What goes there | Confidentiality |
| --- | --- | --- |
| `docs/solutions/` in the current repo | Problems specific to this project | Stays with the client repo |
| `~/.mle-setup/knowledge/` (`INDEX.md` + `cases/`) | Patterns that transfer across clients | Must be sanitized |

## Retrieve
1. `grep -ril "<2-3 symptom terms>" docs/solutions/` and
   `grep -i "<terms>" ~/.mle-setup/knowledge/INDEX.md`.
2. Open only the matching files. No match: continue silently.

## Record (only after the fix is verified)
1. Is it non-obvious and likely to recur? If not, skip it.
2. Draft 10-20 lines: **Symptom** (error text, how it showed up) / **Cause** /
   **Fix** / **Applies when** / **How to detect it quickly next time**.
   Tags are the words someone would grep for: error names, tools, symptoms.
3. Default: `docs/solutions/YYYY-MM-DD-<slug>.md` in the repo. If the repo's
   `AGENTS.md` does not mention `docs/solutions/`, propose adding one line:
   "Solved problems: `docs/solutions/` (grep before debugging or planning)."
4. Global case only if the lesson is useful for other clients: remove client
   names, data, internal URLs, architecture details, and identifiable metrics.
   Save `cases/YYYYMM-<slug>.md` and add `<id> | <3-5 tags> | <symptom>` to
   `INDEX.md` (create the folder and index if missing).
5. Show the draft to the user before saving; they confirm sanitization.
