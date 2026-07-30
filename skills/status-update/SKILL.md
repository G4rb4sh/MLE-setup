---
name: status-update
description: >
  Generates the periodic progress update for a client from the
  repo's real state. Use when the user says "status update",
  "summary for the client", "what did we advance this week", or similar.
---

1. Gather evidence: git log for the period (ask for the range if
   it is not obvious), merged PRs, task state if there is a tracker
   referenced in AGENTS.md.
2. Translate into business language: what the system can do now
   that it could not do before, in terms of the client's problem. Zero technical
   jargon unless the audience is technical (ask).
3. Structure (in the client's language, half a page maximum):
   - Progress during the period (3-5 value bullets, not commit bullets).
   - In progress and next milestone with estimated date.
   - Blockers or decisions we need from the client (actionable:
     what, who, by when).
   - New risks, only if they are real.
4. Show the draft for editing before sending. Never invent
   progress or dates: everything comes from the repo or the user.
