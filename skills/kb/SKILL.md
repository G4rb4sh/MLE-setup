---
name: kb
description: >
  Personal knowledge base of problems already solved in other projects.
  CHECK when starting diagnosis of a non-trivial error, an integration
  problem, or a technical decision that smells familiar. SAVE when the
  user says "save this in the kb", "this will happen to us again", or
  when closing a problem that was costly to solve.
---

Lazy retrieval in two steps: never load full cases unless requested.
State lives in `~/.mle-setup/knowledge/`.

## Check
1. Step 1 (cheap): grep `~/.mle-setup/knowledge/INDEX.md` with
   2-3 symptom terms. Each index line is a case:
   `<id> | <tags> | <symptom in one sentence>`.
2. Step 2 (only if there is a match): read ONLY
   `~/.mle-setup/knowledge/cases/<id>.md` for the matching case. Never
   open all of cases/ or cases "just in case".
3. No match (or missing index: create it with its header):
   continue normally; do not announce that the kb had nothing.

## Save
1. Draft a SANITIZED case: no client name, no data,
   no internal URLs, no contractual details. Refer to the
   context generically ("a client's payments API",
   "a vision pipeline in GCP"). This file travels across contexts
   where client-to-client confidentiality is non-negotiable.
2. Create `~/.mle-setup/knowledge/cases/<id>.md` with id
   `YYYYMM-<slug>` and sections: Symptom / Cause / Solution /
   How to detect it quickly next time. Maximum ~25 lines.
3. Add the line to INDEX.md: `<id> | <3-5 tags> | <symptom>`.
4. Show the case to the user before saving (the user checks the
   sanitization).

Tags are retrieval: use the terms someone would shout when
searching (error names, technologies, symptoms), not abstract categories.
