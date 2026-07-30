---
name: pre-delivery-audit
description: >
  Final audit before delivering code or a system to a client.
  Use when the user says "let's deliver", "delivery audit",
  "is this ready for the client?", or before a handoff.
---

Review the full repo and report by section, with file:line
for each finding and severity (blocking / recommended):

1. Secrets and sensitive information: hardcoded credentials, committed .env
   files, real client data in fixtures, tests, seeds, or
   documentation, internal URLs that should not be exposed.
2. Git history: secrets or sensitive data in old commits
   (search history, not only HEAD).
3. Licenses: dependencies with licenses incompatible with the client's
   commercial use (GPL and similar); list the license for each
   direct dependency.
4. Declared debt: run the ponytail-debt skill (debt:,
   ponytail:, and FIXME markers); classify each row as "resolve before
   delivery" vs "document in the handoff".
5. Complexity: run ponytail-audit in repo mode and attach its
   result.
6. Operability: README with verified setup from scratch, documented
   environment variables, and up-to-date docs/HANDOFF.md (handoff skill).
7. Hygiene: dead code, temporary files, relevant unmerged branches,
   green CI configuration.

Close: verdict (ready / not ready) with blocker list. Do not
apply fixes automatically: report first and get confirmation.
