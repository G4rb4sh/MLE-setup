# Agent swarm orchestration — design

Date: 2026-08-26
Status: approved, pending implementation

## Problem

Parallel agent work is done by hand today: open one agent, plan, ask it to emit
prompts for other agents, then paste those prompts into agents one by one. The
orchestration lives in the operator's head and in a clipboard.

Copilot CLI already ships the missing primitive — **Agent Factories**, JS
orchestrations that spawn and coordinate subagents inside the session. Nothing
in this plugin mentions them. The existing `dispatching-parallel-agents` skill
still teaches manual `Task()` dispatch, so the agent never reaches for
factories and the operator keeps orchestrating by hand.

This design closes that gap.

## Goals

- Fan out tens of subagents from a single instruction, with live visibility.
- Cover the four kinds of work actually being delegated: implementing features,
  debugging, auditing, and exploring (including "does this already exist in a
  repo or a paper?").
- Make parallel writes safe without adding a distributed system.
- Optimize for efficiency, not for a cost ceiling. Limits exist only to stop
  runaway loops.

## Non-goals

- Per-agent git worktrees and N-way merges. Deferred; see Rejected alternatives.
- Inter-agent negotiation over shared files. Deferred; see Rejected alternatives.
- A budget-enforcement mechanism. Cost is not a constraint for this user.

## Architecture

Four use cases reduce to **two shapes**, so there are two factories.

```
swarm-scan   read-only, divergent
  collect context (JS, no agents)
    -> fan out N finders across lenses
    -> dedup in JS
    -> adversarial verification, k votes per finding
    -> synthesis

swarm-build  writing, convergent
  baseline verify
    -> partition into units (1 agent, or supplied)
    -> validate partition in JS (reject overlapping file ownership)
    -> implement in parallel, one exclusive owner per file
    -> check actual diff against declared ownership
    -> serial gate: run the real verify command
    -> on failure, fixer, loop up to maxFixRounds
```

`swarm-scan` covers debugging, auditing, codebase exploration, and prior-art
search. Only the lenses and the sources change, and those are parameters. A
separate "audit" factory would be configuration for a value that does not vary.

`swarm-build` covers implementation. Its "two investigate, one fixes" role is
played by the verify command: a deterministic, free verifier beats two agents
offering opinions.

Anything these two do not fit is authored ad hoc by the orchestrating agent via
`factories_manage` with `operation: "author"`. The skill teaches this.

## Interfaces

### swarm-scan

| arg | type | default | meaning |
| --- | --- | --- | --- |
| `question` | string | required | what to find or diagnose |
| `lenses` | string[] | derived | angles to search from; when omitted, one agent derives them from the question |
| `scope` | string[] | whole repo | paths to restrict to |
| `sources` | `"repo"` \| `"web"` \| `"both"` | `"repo"` | `"both"` covers prior-art search |
| `finders` | integer | 3 | width of the finder pool |
| `verifyVotes` | integer | 2 | adversarial votes per finding; `0` skips verification |

Returns `{ confirmed: [...], rejected: [...], dropped: [...], unexpectedWrites: [...] }`.

`dropped` is explicit: when the factory bounds its own coverage, it says so
rather than silently truncating.

### swarm-build

| arg | type | default | meaning |
| --- | --- | --- | --- |
| `plan` | string | required | what to implement |
| `verify` | string | required | the real command, e.g. `npm test`, `pytest -q` |
| `units` | `[{task, files[]}]` | derived | when omitted, one agent partitions |
| `maxFixRounds` | integer | 3 | serial fix attempts after a failing gate |

Returns `{ units: [...], gate: {passed, output}, rounds, ownershipViolations: [...] }`.

## Write safety

The unit of safety is **the file, not the worktree**. Two agents that never
touch the same file need no git isolation.

Ownership is exclusive, not one-to-one: one agent may own fifteen files. The
partition unit is a coherent task — a module, a feature slice, a failing test
file — and file ownership is the consequence of that partition, not its
criterion. Partitioning per file would pay a cold start to edit twenty lines
and would lose coherence for changes that span files.

Three enforcement layers, cheapest first:

1. **Static check.** Before any agent runs, JS rejects a partition where two
   units declare the same file. Costs nothing, catches the common case.
2. **Actual-diff check.** Between implementation and the gate, `git diff
   --name-only` is compared against declared ownership. A violation is reported
   with the offending unit named. Deterministic, no agents.
3. **The gate.** The verify command runs for real via `child_process` from the
   run body. Not an agent claiming it passed.

The gate runs a **baseline first**, before anything is touched. Without it,
"I broke this" is indistinguishable from "this was already broken", and the
fixer burns rounds repairing pre-existing failures.

This is `verification-before-completion` made mechanical: evidence precedes the
claim, and it does not depend on an agent being honest.

### swarm-scan is read-only by detection, not by construction

Since `agent` is ignored, a scan subagent has the full toolset and could write.
The prompts instruct read-only, but prompts are not a guarantee.

`swarm-scan` therefore captures `git status --porcelain` before and after the
fan-out and returns any path that changed under `unexpectedWrites`. A
read-only scan that reports a non-empty `unexpectedWrites` has misbehaved and
the orchestrator says so instead of silently absorbing it. Cost: two shell
calls, no agents.

Same philosophy as the ownership check — cheap deterministic detection beats
prevention that cannot actually be enforced.

## Efficiency

Cost is not a constraint, but waste is. The levers, in order of impact:

1. **No LLM for what JavaScript does.** Subagents return JSON via `schema`;
   dedup, filtering, ranking and merging happen in the run body.
2. **No agents for deterministic work.** `git diff`, file listings, and symbol
   greps run in the body.
3. **`pipeline` over `parallel`.** No barrier between stages, so a slow item
   never holds up a fast one. Use a barrier only when a stage genuinely needs
   the whole set at once — dedup does, mapping does not.
4. **Model per role.** Fast model for wide read-only scanning; strong model for
   the fixer and the synthesizer.
5. **Dedup before the verification fan-out.** Verification is the ×k stage;
   verifying duplicates is where the waste concentrates.
6. **`ctx.step` journaling.** A killed run resumes and replays completed work
   for free.

## Observability

Every finder logs on start and on landing, and each run-level transition calls
`ctx.phase()`. The swarm must be visible while it works. A black box that runs
for four minutes and emits a report is worse than manual dispatch even when it
is faster, because the operator cannot tell a stuck run from a slow one.

`ctx.phase()` sets a single run-global value, so it is called at run-level
transitions only. Concurrent work is distinguished by `label`.

## Limits

Declared generously, as runaway protection rather than budget:

- `maxConcurrentSubagents` bounds the pool so a wide fan-out queues instead of
  stampeding.
- `maxTotalSubagents` and `timeoutSeconds` stop a loop that will not terminate.

A run that trips a limit keeps its ID and journal, so resuming it replays
completed work for free.

## Deliverables

| Path | Purpose |
| --- | --- |
| `extensions/swarm/extension.mjs` | registers `swarm-scan` and `swarm-build` |
| `skills/orchestrating-swarms/SKILL.md` | when to use which, the scaling ladder, how to author one ad hoc |
| `skills/dispatching-parallel-agents/SKILL.md` | rewritten to point at factories instead of manual `Task()` |

## Scaling ladder

The skill teaches a default that is small, and makes escalation explicit:

- Quick check: 2 finders, `verifyVotes: 0`.
- Normal: 3 finders, 2 votes.
- "Be thorough": large finder pool, 3-5 vote adversarial verification, and a
  completeness critic seeding another round.

## Verified findings

Both open questions were resolved empirically with throwaway probe factories
before implementation started.

**The `agent` option is silently ignored.** `ctx.agent(prompt, { agent })` was
probed with `research`, `explore`, `mle-setup:researcher`, and the deliberately
invalid `definitely-not-a-real-agent`. All four ran, none errored, and all four
self-reported as the default agent. An invalid agent name does not fail — it
degrades silently, which is the worst available failure mode.

Consequence: **a factory subagent cannot be made read-only by construction.**
An earlier draft of this design claimed the wide fan-out would be physically
incapable of writing because it ran as `researcher`. That claim was false and
has been removed. Do not pass `agent` in either factory; it buys nothing and
implies a guarantee that does not exist.

The replacement follows the same principle as the ownership check: **detect
deterministically instead of preventing by prompt.** `swarm-scan` captures
`git status --porcelain` before and after the fan-out and reports any path a
supposedly read-only scan touched. Zero agents, no reliance on prompt
compliance.

Session-level `onPermissionRequest` was considered as a real enforcement
mechanism and rejected: it applies to the whole session, so it would also
constrain the orchestrating agent, and whether it intercepts factory subagent
tool calls at all is unverified.

**Plugin-contributed extensions load from `<plugin>/extensions/<name>/extension.mjs`.**
Confirmed by scaffolding one inside the installed plugin and observing it load
as `plugin:mle-setup:probe-layout`. The factories can therefore ship with
MLE-setup and be available in every repo.

**Factory subagents can write inside the workspace, and run with `cwd` set to
the session's workspace root.** All three probed variants created a file with
the `bash` tool and the write was confirmed on disk. `swarm-build` is viable as
designed: subagents edit files directly, and no patch-application indirection is
needed.

A first probe appeared to show subagents could not write at all, but it was
confounded: it targeted `os.tmpdir()`, and the refusals cited the *path* being
outside the workspace, not a missing tool. Re-probing inside the repo reversed
the result. The relevant boundary is the workspace, not the toolset.

That same probe re-confirmed the `agent` finding from the other direction: the
run with `agent: "definitely-not-a-real-agent"` wrote successfully.

## Rejected alternatives

**Per-agent git worktrees.** Creating them locally is trivial. The cost is
elsewhere: N dependency installs, N times the disk, and an N-way merge that an
LLM must resolve without global context. Worth it at the scale of a
million-line rewrite; not at this scale. Upgrade trigger: if the gate fails on
ownership violations twice in a row, revisit.

**Agents negotiating changes to each other's files.** Factory subagents are
isolated and cannot message one another, so the negotiation protocol would have
to be built in the orchestrator — a distributed system with LLMs as nodes,
expensive and non-deterministic, failing silently. Same outcome without a
protocol: an agent that needs a change in another's file reports it, and the
orchestrator applies it serially afterward.

**A third `audit` factory.** Structurally identical to `swarm-scan`; only the
prompts differ.

**Configurable retries, a `dryRun` flag, writing reports to disk, custom
metrics, a `swarm-plan` factory.** Respectively: `agent()` with a schema
already retries once; a flag whose value never changes; the result already
returns to the orchestrator, which decides; `getRunProgress` is native; and
`writing-plans` already exists.
