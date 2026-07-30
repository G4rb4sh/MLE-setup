---
name: scoping
description: >
  Scoping and technical estimation of a project or feature for a
  client. Use when the user says "estimate", "scoping",
  "proposal for the client", "how long would it take", or describes a
  business problem for a new client.
---

Objective: a defensible estimate with explicit assumptions, not a
magic number. Steps:

1. Understand the business problem: what client decision or process
   improves, how success is measured, what happens if it is not done.
   Ask for anything missing before estimating.
2. Inventory unknowns: data access and quality, integrations
   with client systems, constraints (compliance, on-prem vs
   cloud, latency, language), who operates the solution afterward.
3. Propose a minimal reference architecture (Mermaid diagram) and
   mark each component as: known / likely / risk.
4. Break down into deliverable phases, each with demonstrable value
   to the client (discovery -> PoC -> MVP -> production). Estimate by
   phase in ranges, not single points, and only the next phase in
   detail.
5. Explicitly list: assumptions (if they break, the number changes),
   out of scope, and the 3 main risks with mitigation.
6. Output: short document in the client's language, with a separate
   internal technical section for the team.

Rule: never estimate total effort for an ML project before seeing
the data; until then, estimate only discovery.
