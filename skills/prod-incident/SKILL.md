---
name: prod-incident
description: >
  Handling a production incident: something is down, degraded, or
  returning incorrect results in a real environment. Use when the
  user says "it went down", "it is failing in prod", "the client reports
  errors", or similar. DO NOT use for development bugs (that is the
  systematic-debugging skill).
---

Strict order: stabilize first, diagnose later. Do not
propose refactors or root cause while the system is degraded.

## Phase 1: Assess (minutes)
- Scope: what is broken, since when, how many users are affected,
  is data loss or corruption ongoing?
- What changed recently: deploys, migrations, configs, external API
  quotas, credential expiration.

## Phase 2: Mitigate
- Propose the fastest and most reversible mitigation first: rollback
  of the last deploy, feature flag, restart, scale resources,
  disable the non-critical component.
- Production safety: exact command + scope + rollback,
  and user confirmation before running anything in prod.
- Draft (if the user wants) a short client notice:
  what is affected, what is being done, when there will be updates.

## Phase 3: Diagnose
- Only once the system is stable: move to the systematic-debugging skill
  for root cause, using logs/evidence captured during the
  incident.

## Phase 4: Close
- Brief postmortem in docs/incidents/YYYY-MM-DD-<slug>.md: timeline,
  impact, root cause, what would have prevented it, actions with
  owner. Blameless: system causes, not people.
