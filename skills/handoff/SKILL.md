---
name: handoff
description: >
  Generates delivery documentation for handing a consulting project over
  to the client. Use when the user says "handoff", "delivery documentation",
  "close the project", or "prepare the transfer".
---

Generate `docs/HANDOFF.md` (or update it) by reading the real repo. Everything in
the language the client uses (ask if it is not obvious). Sections:

1. Executive summary: what the system does and what problem it solves
   (for a non-technical reader).
2. Architecture: Mermaid diagram with components, data flow, and
   external dependencies, each connection labeled with its protocol.
3. Runbook: how to start the system, deploy it, and the 3-5 most likely
   operational issues with their solution.
4. Relevant technical decisions and their trade-offs (why X was chosen
   over Y).
5. Status and pending items: out of scope, known technical debt
   (include output from the ponytail-debt skill), recommended next steps.
6. Access and dependencies: what credentials, services, and accounts
   the client needs to operate independently (without including secrets).

Verify every claim against the code; mark anything you cannot verify with
[CONFIRM] and list it at the end for the user.
Suggest running pre-delivery-audit if it was not done.
