# Agent Swarm Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two Agent Factories (`swarm-scan`, `swarm-build`) plus a skill so the agent can fan out tens of subagents from one instruction, instead of the operator pasting prompts by hand.

**Architecture:** One plugin-contributed extension registers both factories via `defineFactory` + `joinSession`. `swarm-scan` is read-only and divergent (fan out across lenses, dedup in JS, adversarially verify, synthesize). `swarm-build` is convergent and writes (partition into units with exclusive file ownership, implement in parallel, verify with a real shell command). Pure functions are extracted into a separate module so they can be unit-tested without a running CLI.

**Tech Stack:** Node.js ESM (`.mjs`), `@github/copilot-sdk/extension` (auto-resolved, not installed), `node:test` + `node:assert` for tests, `node:child_process` for the verify gate.

**Spec:** `docs/superpowers/specs/2026-08-26-agent-swarm-orchestration-design.md`

---

## Context an implementer needs

**This repo is a Copilot CLI plugin, not an application.** It ships Markdown skills, agent definitions, and hooks. There is currently no JavaScript and no test runner. This plan adds both.

**Factories are experimental and have sharp edges.** Three of them break silently and are the source of most bugs:

1. **Identical `ctx.agent()` calls memoize into ONE subagent.** The cache key is the prompt plus all options, including `label`. Ten calls with the same prompt and no distinct label produce one subagent whose result is returned ten times. Every independent subagent needs a unique `label`.
2. **An ordinary subagent failure resolves to `null`, it does not throw.** Every `await ctx.agent(...)` must be null-guarded before use.
3. **Filter with `v => v !== null`, never `Boolean`.** `Boolean` also discards a valid `false`, `0`, and `""`.

**Already verified empirically — do not re-litigate:**

- `ctx.agent(prompt, { agent })` is **silently ignored**, even for an invalid name. Never pass `agent`. Read-only cannot be enforced; it is detected via `git status`.
- Factory subagents **can** write inside the workspace and run with `cwd` at the workspace root.
- Plugin extensions load from `<plugin>/extensions/<name>/extension.mjs`.

**`ctx.phase()` sets one run-global value.** Call it at run-level transitions only, never inside a concurrent stage, where calls would race. Distinguish concurrent work with `label`.

**The `run` body of a factory authored via `factories_manage` must be self-contained** (no closures, no static imports). That constraint does **not** apply here, because these factories live in a real extension file. Normal module-level imports and helpers are fine.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `extensions/swarm/lib/partition.mjs` | Pure: validate a partition, diff declared vs actual ownership. No SDK, no I/O. |
| `extensions/swarm/lib/dedup.mjs` | Pure: normalize and deduplicate findings, tally votes. No SDK, no I/O. |
| `extensions/swarm/lib/shell.mjs` | Run a shell command, capture exit code and output. Wraps `node:child_process`. |
| `extensions/swarm/lib/schemas.mjs` | The `FactoryJsonSchema` objects shared by both factories. |
| `extensions/swarm/scan.mjs` | `swarm-scan` factory definition. |
| `extensions/swarm/build.mjs` | `swarm-build` factory definition. |
| `extensions/swarm/extension.mjs` | Entry point. Imports both, calls `joinSession`. |
| `extensions/swarm/test/*.test.mjs` | `node:test` unit tests for the pure modules and the shell wrapper. |
| `skills/orchestrating-swarms/SKILL.md` | When to use which factory, the scaling ladder, how to author one ad hoc. |
| `skills/dispatching-parallel-agents/SKILL.md` | Rewritten to point at factories. |

The pure modules exist so the logic that must be correct is testable without a running CLI. Factory bodies themselves are integration-tested by running them.

---

## Task 1: Test harness

**Files:**
- Create: `package.json`
- Create: `extensions/swarm/test/smoke.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `extensions/swarm/test/smoke.test.mjs`:

```js
import test from "node:test";
import assert from "node:assert/strict";

test("test runner works", () => {
    assert.equal(1 + 1, 2);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `npm ERR! Missing script: "test"` (there is no `package.json` yet).

- [ ] **Step 3: Write the minimal implementation**

Create `package.json`:

```json
{
    "name": "mle-setup",
    "version": "0.1.0",
    "private": true,
    "type": "module",
    "scripts": {
        "test": "node --test extensions/swarm/test/"
    }
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — `# pass 1`, `# fail 0`.

- [ ] **Step 5: Commit**

```bash
git add package.json extensions/swarm/test/smoke.test.mjs
git commit -m "test: add node:test harness for swarm extension"
```

---

## Task 2: Partition validation

Rejects a partition where two units claim the same file, before any agent runs.

**Files:**
- Create: `extensions/swarm/lib/partition.mjs`
- Create: `extensions/swarm/test/partition.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `extensions/swarm/test/partition.test.mjs`:

```js
import test from "node:test";
import assert from "node:assert/strict";
import { validatePartition } from "../lib/partition.mjs";

test("accepts units with disjoint files", () => {
    const result = validatePartition([
        { task: "a", files: ["src/a.js"] },
        { task: "b", files: ["src/b.js"] },
    ]);
    assert.equal(result.ok, true);
    assert.deepEqual(result.conflicts, []);
});

test("rejects two units claiming the same file", () => {
    const result = validatePartition([
        { task: "a", files: ["src/shared.js", "src/a.js"] },
        { task: "b", files: ["src/shared.js"] },
    ]);
    assert.equal(result.ok, false);
    assert.deepEqual(result.conflicts, [{ file: "src/shared.js", units: ["a", "b"] }]);
});

test("normalizes ./ prefixes before comparing", () => {
    const result = validatePartition([
        { task: "a", files: ["./src/shared.js"] },
        { task: "b", files: ["src/shared.js"] },
    ]);
    assert.equal(result.ok, false);
});

test("rejects a unit with no files", () => {
    const result = validatePartition([{ task: "a", files: [] }]);
    assert.equal(result.ok, false);
    assert.match(result.error, /no files/);
});

test("rejects an empty partition", () => {
    const result = validatePartition([]);
    assert.equal(result.ok, false);
    assert.match(result.error, /at least one unit/);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `Cannot find module '../lib/partition.mjs'`.

- [ ] **Step 3: Write the minimal implementation**

Create `extensions/swarm/lib/partition.mjs`:

```js
/** Strip a leading ./ so "./src/a.js" and "src/a.js" compare equal. */
export function normalizePath(file) {
    return String(file).replace(/^\.\//, "").trim();
}

/**
 * Validate that no two units claim the same file.
 * Returns { ok, conflicts, error }.
 */
export function validatePartition(units) {
    if (!Array.isArray(units) || units.length === 0) {
        return { ok: false, conflicts: [], error: "partition must contain at least one unit" };
    }

    const owners = new Map();
    for (const unit of units) {
        const files = Array.isArray(unit.files) ? unit.files : [];
        if (files.length === 0) {
            return { ok: false, conflicts: [], error: `unit "${unit.task}" declares no files` };
        }
        for (const raw of files) {
            const file = normalizePath(raw);
            if (!owners.has(file)) owners.set(file, []);
            owners.get(file).push(unit.task);
        }
    }

    const conflicts = [...owners.entries()]
        .filter(([, tasks]) => tasks.length > 1)
        .map(([file, units]) => ({ file, units }));

    return { ok: conflicts.length === 0, conflicts, error: "" };
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — 6 passing.

- [ ] **Step 5: Commit**

```bash
git add extensions/swarm/lib/partition.mjs extensions/swarm/test/partition.test.mjs
git commit -m "feat: validate swarm partitions reject overlapping file ownership"
```

---

## Task 3: Ownership violation detection

Compares what agents actually changed against what they were allowed to change.

**Files:**
- Modify: `extensions/swarm/lib/partition.mjs`
- Modify: `extensions/swarm/test/partition.test.mjs`

- [ ] **Step 1: Write the failing test**

Append to `extensions/swarm/test/partition.test.mjs`:

```js
import { findOwnershipViolations } from "../lib/partition.mjs";

test("no violations when changes match ownership", () => {
    const violations = findOwnershipViolations(
        [{ task: "a", files: ["src/a.js"] }],
        ["src/a.js"]
    );
    assert.deepEqual(violations, []);
});

test("flags a file changed but owned by nobody", () => {
    const violations = findOwnershipViolations(
        [{ task: "a", files: ["src/a.js"] }],
        ["src/a.js", "src/rogue.js"]
    );
    assert.deepEqual(violations, [{ file: "src/rogue.js", owner: null }]);
});

test("ignores an owned file that was never changed", () => {
    const violations = findOwnershipViolations(
        [{ task: "a", files: ["src/a.js", "src/untouched.js"] }],
        ["src/a.js"]
    );
    assert.deepEqual(violations, []);
});

test("normalizes paths on both sides", () => {
    const violations = findOwnershipViolations(
        [{ task: "a", files: ["./src/a.js"] }],
        ["src/a.js"]
    );
    assert.deepEqual(violations, []);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `findOwnershipViolations is not a function`.

- [ ] **Step 3: Write the minimal implementation**

Append to `extensions/swarm/lib/partition.mjs`:

```js
/**
 * Compare files actually changed against declared ownership.
 * A changed file owned by nobody is a violation. Returns [{ file, owner }].
 */
export function findOwnershipViolations(units, changedFiles) {
    const owners = new Map();
    for (const unit of units) {
        for (const raw of unit.files ?? []) {
            owners.set(normalizePath(raw), unit.task);
        }
    }

    return changedFiles
        .map(normalizePath)
        .filter((file) => file.length > 0 && !owners.has(file))
        .map((file) => ({ file, owner: null }));
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — 10 passing.

- [ ] **Step 5: Commit**

```bash
git add extensions/swarm/lib/partition.mjs extensions/swarm/test/partition.test.mjs
git commit -m "feat: detect files changed outside declared swarm ownership"
```

---

## Task 4: Finding deduplication and vote tallying

Dedup runs before the verification fan-out, which is the ×k stage. Verifying duplicates is where waste concentrates.

**Files:**
- Create: `extensions/swarm/lib/dedup.mjs`
- Create: `extensions/swarm/test/dedup.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `extensions/swarm/test/dedup.test.mjs`:

```js
import test from "node:test";
import assert from "node:assert/strict";
import { dedupeFindings, tallyVotes } from "../lib/dedup.mjs";

test("collapses findings with the same title ignoring case and spacing", () => {
    const result = dedupeFindings([
        { title: "Race condition in cache" },
        { title: "  race CONDITION in cache  " },
        { title: "Memory leak" },
    ]);
    assert.equal(result.length, 2);
    assert.equal(result[0].title, "Race condition in cache");
});

test("keeps the first occurrence and its full payload", () => {
    const result = dedupeFindings([
        { title: "Bug", detail: "original" },
        { title: "bug", detail: "duplicate" },
    ]);
    assert.deepEqual(result, [{ title: "Bug", detail: "original" }]);
});

test("drops entries without a usable title", () => {
    const result = dedupeFindings([{ title: "" }, { title: "   " }, { detail: "x" }, { title: "Real" }]);
    assert.deepEqual(result, [{ title: "Real" }]);
});

test("returns empty for a non-array input", () => {
    assert.deepEqual(dedupeFindings(null), []);
});

test("confirms a finding when votes meet the threshold", () => {
    assert.equal(tallyVotes([{ isReal: true }, { isReal: true }, { isReal: false }], 2), true);
});

test("rejects a finding below the threshold", () => {
    assert.equal(tallyVotes([{ isReal: true }, { isReal: false }], 2), false);
});

test("treats a null vote as not confirming", () => {
    assert.equal(tallyVotes([{ isReal: true }, null], 2), false);
});

test("confirms with a threshold of zero and no votes", () => {
    assert.equal(tallyVotes([], 0), true);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `Cannot find module '../lib/dedup.mjs'`.

- [ ] **Step 3: Write the minimal implementation**

Create `extensions/swarm/lib/dedup.mjs`:

```js
/** Case- and whitespace-insensitive key used to collapse duplicate findings. */
function keyOf(finding) {
    return String(finding?.title ?? "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ");
}

/** Collapse duplicate findings, keeping the first occurrence of each. */
export function dedupeFindings(findings) {
    if (!Array.isArray(findings)) return [];

    const seen = new Set();
    const out = [];
    for (const finding of findings) {
        const key = keyOf(finding);
        if (key === "" || seen.has(key)) continue;
        seen.add(key);
        out.push(finding);
    }
    return out;
}

/**
 * True when at least `threshold` votes affirm the finding.
 * A null vote (failed subagent) never confirms.
 */
export function tallyVotes(votes, threshold) {
    if (threshold <= 0) return true;
    const affirmed = (votes ?? []).filter((v) => v !== null && v?.isReal === true).length;
    return affirmed >= threshold;
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — 18 passing.

- [ ] **Step 5: Commit**

```bash
git add extensions/swarm/lib/dedup.mjs extensions/swarm/test/dedup.test.mjs
git commit -m "feat: dedupe swarm findings and tally adversarial votes"
```

---

## Task 5: Shell runner for the verify gate

The gate runs the real command. Not an agent claiming it passed.

**Files:**
- Create: `extensions/swarm/lib/shell.mjs`
- Create: `extensions/swarm/test/shell.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `extensions/swarm/test/shell.test.mjs`:

```js
import test from "node:test";
import assert from "node:assert/strict";
import { runCommand, gitChangedFiles } from "../lib/shell.mjs";

test("captures success and stdout", async () => {
    const result = await runCommand("echo hello");
    assert.equal(result.passed, true);
    assert.equal(result.exitCode, 0);
    assert.match(result.output, /hello/);
});

test("captures failure with a non-zero exit code", async () => {
    const result = await runCommand("exit 3");
    assert.equal(result.passed, false);
    assert.equal(result.exitCode, 3);
});

test("merges stderr into the output", async () => {
    const result = await runCommand("echo oops >&2; exit 1");
    assert.equal(result.passed, false);
    assert.match(result.output, /oops/);
});

test("truncates very long output", async () => {
    const result = await runCommand("for i in $(seq 1 20000); do echo line$i; done");
    assert.ok(result.output.length <= 32_768 + 200);
    assert.match(result.output, /truncated/);
});

test("times out a hanging command instead of hanging", async () => {
    const result = await runCommand("sleep 30", { timeoutMs: 500 });
    assert.equal(result.passed, false);
    assert.match(result.output, /timed out/i);
});

test("gitChangedFiles returns an array in a git repo", async () => {
    const files = await gitChangedFiles();
    assert.ok(Array.isArray(files));
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `Cannot find module '../lib/shell.mjs'`.

- [ ] **Step 3: Write the minimal implementation**

Create `extensions/swarm/lib/shell.mjs`:

```js
import { exec } from "node:child_process";

const MAX_OUTPUT = 32_768;
const DEFAULT_TIMEOUT_MS = 600_000;

function truncate(text) {
    if (text.length <= MAX_OUTPUT) return text;
    return `${text.slice(0, MAX_OUTPUT)}\n... [truncated, ${text.length - MAX_OUTPUT} more characters]`;
}

/**
 * Run a shell command and capture its outcome.
 * Never rejects: a failure is reported as { passed: false }.
 */
export function runCommand(command, { cwd = process.cwd(), timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {}) {
    return new Promise((resolve) => {
        exec(
            command,
            { cwd, timeout: timeoutMs, signal, maxBuffer: 10 * 1024 * 1024, killSignal: "SIGKILL" },
            (error, stdout, stderr) => {
                const output = truncate(`${stdout ?? ""}${stderr ?? ""}`);
                if (!error) {
                    resolve({ passed: true, exitCode: 0, output });
                    return;
                }
                const timedOut = error.killed === true || error.signal === "SIGKILL";
                resolve({
                    passed: false,
                    exitCode: typeof error.code === "number" ? error.code : 1,
                    output: timedOut ? `${output}\n[command timed out after ${timeoutMs}ms]` : output,
                });
            }
        );
    });
}

/** Files changed vs HEAD, including untracked ones. Empty array outside a repo. */
export async function gitChangedFiles(options = {}) {
    const result = await runCommand("git status --porcelain", options);
    if (!result.passed) return [];
    return result.output
        .split("\n")
        .map((line) => line.slice(3).trim())
        .filter((line) => line.length > 0);
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — 24 passing.

- [ ] **Step 5: Commit**

```bash
git add extensions/swarm/lib/shell.mjs extensions/swarm/test/shell.test.mjs
git commit -m "feat: add shell runner and git change detection for the verify gate"
```

---

## Task 6: Shared schemas

**Files:**
- Create: `extensions/swarm/lib/schemas.mjs`
- Create: `extensions/swarm/test/schemas.test.mjs`

Only `type`, `required`, `enum`, `const`, `properties`, `items`, `anyOf`/`oneOf`/`allOf` are honored. `additionalProperties`, `pattern`, `minLength`, and numeric ranges are **silently ignored** — never rely on them to constrain a result.

- [ ] **Step 1: Write the failing test**

Create `extensions/swarm/test/schemas.test.mjs`:

```js
import test from "node:test";
import assert from "node:assert/strict";
import { FINDINGS, VERDICT, LENSES, UNITS } from "../lib/schemas.mjs";

test("FINDINGS requires a findings array of titled objects", () => {
    assert.equal(FINDINGS.type, "object");
    assert.deepEqual(FINDINGS.required, ["findings"]);
    assert.equal(FINDINGS.properties.findings.type, "array");
    assert.deepEqual(FINDINGS.properties.findings.items.required, ["title"]);
});

test("VERDICT requires a boolean isReal", () => {
    assert.deepEqual(VERDICT.required, ["isReal"]);
    assert.equal(VERDICT.properties.isReal.type, "boolean");
});

test("LENSES requires an array of strings", () => {
    assert.deepEqual(LENSES.required, ["lenses"]);
    assert.equal(LENSES.properties.lenses.items.type, "string");
});

test("UNITS requires task and files on each unit", () => {
    assert.deepEqual(UNITS.required, ["units"]);
    assert.deepEqual(UNITS.properties.units.items.required, ["task", "files"]);
});

test("schemas use only honored keywords", () => {
    const ignored = ["additionalProperties", "pattern", "minLength", "maxLength", "format", "minimum", "maximum"];
    const walk = (node) => {
        if (node === null || typeof node !== "object") return;
        for (const key of Object.keys(node)) {
            assert.ok(!ignored.includes(key), `schema uses ignored keyword: ${key}`);
            walk(node[key]);
        }
    };
    [FINDINGS, VERDICT, LENSES, UNITS].forEach(walk);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test`

Expected: FAIL — `Cannot find module '../lib/schemas.mjs'`.

- [ ] **Step 3: Write the minimal implementation**

Create `extensions/swarm/lib/schemas.mjs`:

```js
/**
 * Structural schemas for subagent output.
 *
 * Only type, required, enum, const, properties, items, and anyOf/oneOf/allOf
 * are honored by the factory runtime. Constraints such as additionalProperties,
 * pattern, and minLength are silently ignored — do not add them.
 */

export const FINDINGS = {
    type: "object",
    properties: {
        findings: {
            type: "array",
            items: {
                type: "object",
                properties: {
                    title: { type: "string" },
                    detail: { type: "string" },
                    location: { type: "string" },
                    confidence: { type: "string", enum: ["low", "medium", "high"] },
                },
                required: ["title"],
            },
        },
    },
    required: ["findings"],
};

export const VERDICT = {
    type: "object",
    properties: {
        isReal: { type: "boolean" },
        reason: { type: "string" },
    },
    required: ["isReal"],
};

export const LENSES = {
    type: "object",
    properties: {
        lenses: { type: "array", items: { type: "string" } },
    },
    required: ["lenses"],
};

export const UNITS = {
    type: "object",
    properties: {
        units: {
            type: "array",
            items: {
                type: "object",
                properties: {
                    task: { type: "string" },
                    files: { type: "array", items: { type: "string" } },
                },
                required: ["task", "files"],
            },
        },
    },
    required: ["units"],
};

export const SUMMARY = {
    type: "object",
    properties: {
        summary: { type: "string" },
        recommendation: { type: "string" },
    },
    required: ["summary"],
};
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npm test`

Expected: PASS — 29 passing.

- [ ] **Step 5: Commit**

```bash
git add extensions/swarm/lib/schemas.mjs extensions/swarm/test/schemas.test.mjs
git commit -m "feat: add shared output schemas for swarm subagents"
```

---

## Task 7: The swarm-scan factory

**Files:**
- Create: `extensions/swarm/scan.mjs`

No unit test: this is orchestration over a live runtime. It is integration-tested in Task 10.

- [ ] **Step 1: Write the factory**

Create `extensions/swarm/scan.mjs`:

```js
import { defineFactory } from "@github/copilot-sdk/extension";
import { FINDINGS, VERDICT, LENSES, SUMMARY } from "./lib/schemas.mjs";
import { dedupeFindings, tallyVotes } from "./lib/dedup.mjs";
import { gitChangedFiles } from "./lib/shell.mjs";

const DEFAULT_LENSES = ["correctness", "edge cases", "prior art"];

function scopeLine(scope) {
    return Array.isArray(scope) && scope.length > 0
        ? `Restrict your search to these paths: ${scope.join(", ")}.`
        : "Search the whole repository.";
}

function sourceLine(sources) {
    if (sources === "web") return "Search the public web, papers, and public repositories. Do not read this repository.";
    if (sources === "both") return "Search BOTH this repository AND the public web, papers, and public repositories.";
    return "Search this repository only. Do not search the web.";
}

export const swarmScan = defineFactory({
    meta: {
        name: "swarm-scan",
        description:
            "Read-only parallel investigation. Fans out finders across lenses, dedupes, and adversarially verifies. " +
            "Use for debugging, auditing, codebase exploration, and prior-art search. " +
            "args: { question: string, lenses?: string[], scope?: string[], " +
            "sources?: 'repo'|'web'|'both', finders?: integer, verifyVotes?: integer }",
        phases: [
            { title: "Plan", detail: "Derive lenses" },
            { title: "Scan", detail: "Fan out finders" },
            { title: "Verify", detail: "Adversarial verification" },
            { title: "Synthesize", detail: "Merge into a report" },
        ],
        argsSchema: {
            type: "object",
            properties: {
                question: { type: "string" },
                lenses: { type: "array", items: { type: "string" } },
                scope: { type: "array", items: { type: "string" } },
                sources: { type: "string", enum: ["repo", "web", "both"] },
                finders: { type: "integer" },
                verifyVotes: { type: "integer" },
            },
            required: ["question"],
        },
        limits: {
            maxConcurrentSubagents: 12,
            maxTotalSubagents: 200,
            timeoutSeconds: 3600,
        },
    },

    run: async (ctx) => {
        const {
            question,
            scope = [],
            sources = "repo",
            finders = 3,
            verifyVotes = 2,
        } = ctx.args ?? {};

        if (typeof question !== "string" || question.trim() === "") {
            throw new Error("swarm-scan requires a non-empty question");
        }

        const context = `${scopeLine(scope)} ${sourceLine(sources)}`;
        const before = await ctx.step("writes-before", () => gitChangedFiles({ signal: ctx.signal }));

        // Phase 1 — lenses. One cheap agent, only when the caller did not supply them.
        ctx.phase("Plan");
        let lenses = Array.isArray(ctx.args?.lenses) ? ctx.args.lenses.filter((l) => typeof l === "string") : [];
        if (lenses.length === 0) {
            const derived = await ctx.agent(
                `Break this investigation into ${finders} distinct angles of attack, each a short phrase. ` +
                    `Investigation: ${question}\n${context}\n` +
                    `Return JSON {"lenses":["...","..."]}.`,
                { label: "lens-planner", schema: LENSES }
            );
            lenses = derived?.lenses?.length ? derived.lenses : DEFAULT_LENSES;
        }
        lenses = lenses.slice(0, finders);
        ctx.log(`Scanning across ${lenses.length} lenses: ${lenses.join(", ")}`);

        // Phase 2 — fan out. Unique label per finder, or they memoize into one.
        ctx.phase("Scan");
        const perLens = await ctx.parallel(
            lenses.map((lens, i) => async () => {
                ctx.log(`finder:${i} (${lens}) started`);
                const result = await ctx.agent(
                    `You are investigating, READ-ONLY. Do not modify, create, or delete any file.\n` +
                        `Question: ${question}\nYour angle: ${lens}\n${context}\n` +
                        `Report concrete, specific findings. Return JSON {"findings":[{"title","detail","location","confidence"}]}.`,
                    { label: `finder:${i}:${lens}`, schema: FINDINGS }
                );
                const found = result?.findings ?? [];
                ctx.log(`finder:${i} (${lens}) landed with ${found.length} findings`);
                return found;
            })
        );

        // Dedup in JS, before the expensive verification fan-out.
        const raw = perLens.filter((v) => v !== null).flat();
        const findings = dedupeFindings(raw);
        ctx.log(`${raw.length} findings, ${findings.length} after dedup`);

        // Phase 3 — verify. verifyVotes: 0 skips it entirely.
        ctx.phase("Verify");
        let confirmed = findings;
        let rejected = [];

        if (verifyVotes > 0 && findings.length > 0) {
            const lensesForVotes = ["correctness", "reproducibility", "evidence", "security", "scope"];
            const judged = await ctx.parallel(
                findings.map((finding, i) => async () => {
                    const votes = await ctx.parallel(
                        Array.from({ length: verifyVotes }, (_, v) => async () =>
                            ctx.agent(
                                `Adversarially check this claim. Try to REFUTE it. Default to false when uncertain.\n` +
                                    `Judge specifically from this angle: ${lensesForVotes[v % lensesForVotes.length]}.\n` +
                                    `Claim: ${finding.title}\nDetail: ${finding.detail ?? "none"}\n` +
                                    `Location: ${finding.location ?? "unspecified"}\n${context}\n` +
                                    `Return JSON {"isReal":<boolean>,"reason":"..."}.`,
                                { label: `verify:${i}:${v}`, schema: VERDICT }
                            )
                        )
                    );
                    return { finding, isReal: tallyVotes(votes, verifyVotes) };
                })
            );

            const settled = judged.filter((v) => v !== null);
            confirmed = settled.filter((v) => v.isReal).map((v) => v.finding);
            rejected = settled.filter((v) => !v.isReal).map((v) => v.finding);
            ctx.log(`${confirmed.length} confirmed, ${rejected.length} rejected`);
        } else if (verifyVotes === 0) {
            ctx.log("verifyVotes is 0 — findings are unverified");
        }

        // Phase 4 — synthesize.
        ctx.phase("Synthesize");
        let summary = "";
        if (confirmed.length > 0) {
            const synthesis = await ctx.agent(
                `Synthesize these verified findings into a direct answer.\nQuestion: ${question}\n` +
                    `Findings: ${JSON.stringify(confirmed)}\n` +
                    `Return JSON {"summary":"...","recommendation":"..."}.`,
                { label: "synthesizer", schema: SUMMARY }
            );
            summary = synthesis?.summary ?? "";
        }

        // A read-only scan that wrote is a defect. Detect it; we cannot prevent it.
        const after = await ctx.step("writes-after", () => gitChangedFiles({ signal: ctx.signal }), {
            volatile: true,
        });
        const unexpectedWrites = after.filter((f) => !before.includes(f));
        if (unexpectedWrites.length > 0) {
            ctx.log(`WARNING: read-only scan modified ${unexpectedWrites.length} path(s): ${unexpectedWrites.join(", ")}`);
        }

        const dropped = [];
        if (Array.isArray(ctx.args?.lenses) && ctx.args.lenses.length > finders) {
            dropped.push(`${ctx.args.lenses.length - finders} lenses beyond finders=${finders}`);
        }

        return { question, lenses, confirmed, rejected, summary, dropped, unexpectedWrites };
    },
});
```

- [ ] **Step 2: Verify it parses**

Run: `node --check extensions/swarm/scan.mjs`

Expected: no output, exit 0.

- [ ] **Step 3: Verify the existing tests still pass**

Run: `npm test`

Expected: PASS — 29 passing.

- [ ] **Step 4: Commit**

```bash
git add extensions/swarm/scan.mjs
git commit -m "feat: add swarm-scan factory for parallel read-only investigation"
```

---

## Task 8: The swarm-build factory

**Files:**
- Create: `extensions/swarm/build.mjs`

- [ ] **Step 1: Write the factory**

Create `extensions/swarm/build.mjs`:

```js
import { defineFactory } from "@github/copilot-sdk/extension";
import { UNITS } from "./lib/schemas.mjs";
import { validatePartition, findOwnershipViolations } from "./lib/partition.mjs";
import { runCommand, gitChangedFiles } from "./lib/shell.mjs";

export const swarmBuild = defineFactory({
    meta: {
        name: "swarm-build",
        description:
            "Parallel implementation with exclusive file ownership and a real verify gate. " +
            "Partitions work into units, implements them concurrently, then runs the verify command for real and fixes failures. " +
            "args: { plan: string, verify: string, units?: [{task,files}], maxFixRounds?: integer }",
        phases: [
            { title: "Baseline", detail: "Verify before touching anything" },
            { title: "Partition", detail: "Split into units" },
            { title: "Implement", detail: "Parallel implementation" },
            { title: "Gate", detail: "Verify and fix" },
        ],
        argsSchema: {
            type: "object",
            properties: {
                plan: { type: "string" },
                verify: { type: "string" },
                units: {
                    type: "array",
                    items: {
                        type: "object",
                        properties: {
                            task: { type: "string" },
                            files: { type: "array", items: { type: "string" } },
                        },
                        required: ["task", "files"],
                    },
                },
                maxFixRounds: { type: "integer" },
            },
            required: ["plan", "verify"],
        },
        limits: {
            maxConcurrentSubagents: 8,
            maxTotalSubagents: 100,
            timeoutSeconds: 7200,
        },
    },

    run: async (ctx) => {
        const { plan, verify, maxFixRounds = 3 } = ctx.args ?? {};

        if (typeof plan !== "string" || plan.trim() === "") {
            throw new Error("swarm-build requires a non-empty plan");
        }
        if (typeof verify !== "string" || verify.trim() === "") {
            throw new Error("swarm-build requires a verify command");
        }

        const shellOpts = { signal: ctx.signal };

        // Phase 1 — baseline. Without it, "I broke this" and "already broken" are indistinguishable.
        ctx.phase("Baseline");
        const baseline = await ctx.step("baseline", async () => {
            const result = await runCommand(verify, shellOpts);
            return { passed: result.passed, exitCode: result.exitCode, output: result.output };
        });
        ctx.log(baseline.passed ? "Baseline is green" : "Baseline is RED — pre-existing failures will be ignored");

        const filesBefore = await ctx.step("files-before", () => gitChangedFiles(shellOpts));

        // Phase 2 — partition.
        ctx.phase("Partition");
        let units = Array.isArray(ctx.args?.units) ? ctx.args.units : [];
        if (units.length === 0) {
            const derived = await ctx.agent(
                `Split this work into independent units that can be implemented in parallel.\n` +
                    `CRITICAL: no two units may touch the same file. Assign every file to exactly one unit. ` +
                    `Group by coherent task (a module, a feature slice), not one unit per file.\n` +
                    `Work: ${plan}\n` +
                    `Return JSON {"units":[{"task":"...","files":["path",...]}]}.`,
                { label: "partitioner", schema: UNITS }
            );
            units = derived?.units ?? [];
        }

        const validation = validatePartition(units);
        if (!validation.ok) {
            const detail = validation.error || `overlapping ownership: ${JSON.stringify(validation.conflicts)}`;
            ctx.log(`Partition rejected — ${detail}`);
            return { units, gate: null, rounds: 0, ownershipViolations: [], baseline, error: `invalid partition: ${detail}` };
        }
        ctx.log(`Partitioned into ${units.length} units with disjoint ownership`);

        // Phase 3 — implement. One exclusive owner per file.
        ctx.phase("Implement");
        const implemented = await ctx.parallel(
            units.map((unit, i) => async () => {
                ctx.log(`unit:${i} (${unit.task}) started on ${unit.files.length} file(s)`);
                const result = await ctx.agent(
                    `Implement this unit of work.\nOverall goal: ${plan}\nYour task: ${unit.task}\n` +
                        `You EXCLUSIVELY own these files: ${unit.files.join(", ")}\n` +
                        `Other agents are working in parallel on other files RIGHT NOW. ` +
                        `Do NOT create, modify, or delete any file outside your list. ` +
                        `If your task requires a change elsewhere, describe it in your reply instead of making it.\n` +
                        `Verify your own work with: ${verify}\n` +
                        `Reply with a short summary of what you changed and any change you needed elsewhere.`,
                    { label: `unit:${i}:${unit.task}` }
                );
                ctx.log(`unit:${i} (${unit.task}) landed`);
                return { unit: unit.task, summary: result ?? "(no summary — subagent failed)" };
            })
        );

        // Deterministic ownership check. No agents.
        const filesAfter = await ctx.step("files-after", () => gitChangedFiles(shellOpts), { volatile: true });
        const changed = filesAfter.filter((f) => !filesBefore.includes(f));
        const ownershipViolations = findOwnershipViolations(units, changed);
        if (ownershipViolations.length > 0) {
            ctx.log(`WARNING: ${ownershipViolations.length} file(s) changed outside declared ownership`);
        }

        // Phase 4 — gate. The real command, then serial fixes.
        ctx.phase("Gate");
        let gate = await runCommand(verify, shellOpts);
        let rounds = 0;
        ctx.log(gate.passed ? "Gate passed" : `Gate failed (exit ${gate.exitCode})`);

        while (!gate.passed && rounds < maxFixRounds) {
            rounds += 1;
            ctx.log(`Fix round ${rounds}/${maxFixRounds}`);
            await ctx.agent(
                `The verification command is failing after a parallel implementation. Fix it.\n` +
                    `Command: ${verify}\nOutput:\n${gate.output}\n` +
                    `Goal: ${plan}\n` +
                    (baseline.passed
                        ? "The suite was green before this work, so these failures were introduced by it."
                        : `The suite was ALREADY FAILING before this work. Ignore pre-existing failures. Baseline output:\n${baseline.output}`) +
                    `\nYou may edit any file. Make the command pass without weakening or deleting tests.`,
                { label: `fixer:${rounds}` }
            );
            gate = await runCommand(verify, shellOpts);
            ctx.log(gate.passed ? `Gate passed after ${rounds} fix round(s)` : `Still failing after round ${rounds}`);
        }

        return {
            units: implemented.filter((v) => v !== null),
            gate: { passed: gate.passed, exitCode: gate.exitCode, output: gate.output },
            baseline,
            rounds,
            ownershipViolations,
            changedFiles: changed,
        };
    },
});
```

- [ ] **Step 2: Verify it parses**

Run: `node --check extensions/swarm/build.mjs`

Expected: no output, exit 0.

- [ ] **Step 3: Verify the existing tests still pass**

Run: `npm test`

Expected: PASS — 29 passing.

- [ ] **Step 4: Commit**

```bash
git add extensions/swarm/build.mjs
git commit -m "feat: add swarm-build factory for parallel implementation with a verify gate"
```

---

## Task 9: Extension entry point

**Files:**
- Create: `extensions/swarm/extension.mjs`

- [ ] **Step 1: Write the entry point**

Create `extensions/swarm/extension.mjs`:

```js
import { joinSession } from "@github/copilot-sdk/extension";
import { swarmScan } from "./scan.mjs";
import { swarmBuild } from "./build.mjs";

await joinSession({ factories: [swarmScan, swarmBuild] });
```

- [ ] **Step 2: Verify it parses**

Run: `node --check extensions/swarm/extension.mjs`

Expected: no output, exit 0.

Note: running the file directly fails — `@github/copilot-sdk` resolves only inside a CLI-forked extension process. `--check` parses without executing, which is the right check here.

- [ ] **Step 3: Commit**

```bash
git add extensions/swarm/extension.mjs
git commit -m "feat: register swarm factories from the extension entry point"
```

---

## Task 10: Integration test in a live session

The unit tests cover the pure logic. This verifies the factories actually load and run, and probes the one remaining runtime unknown (`model`).

**Files:** none — this is a manual verification gate.

- [ ] **Step 1: Install the plugin build into the running CLI**

The CLI loads plugins from the installed-plugins directory, not this repo. Sync it:

```bash
rsync -a --delete extensions/ ~/.copilot/installed-plugins/mle-setup/mle-setup/extensions/
```

- [ ] **Step 2: Reload and confirm both factories registered**

Use the `extensions_reload` tool, then `factories_manage` with `operation: "list"`.

Expected: `swarm-scan` and `swarm-build` both listed. Also run `extensions_manage` with `operation: "list"` and expect `mle-setup:swarm` as **running**.

If it is `failed`, use `extensions_manage` with `operation: "inspect"` and `name: "swarm"` to read the log tail.

- [ ] **Step 3: Smoke-test swarm-scan cheaply**

Run `run_factory` with:

```json
{
    "name": "swarm-scan",
    "args": {
        "question": "What does the repo-bootstrap skill do and when does it trigger?",
        "scope": ["skills/repo-bootstrap"],
        "finders": 2,
        "verifyVotes": 0
    }
}
```

Expected: status `completed`; `confirmed` non-empty; `unexpectedWrites` **empty**; the progress log shows both finders starting before either lands (that is the proof of real parallelism).

- [ ] **Step 4: Verify the partition guard rejects overlap without spending agents**

Run `run_factory` with a deliberately invalid partition:

```json
{
    "name": "swarm-build",
    "args": {
        "plan": "irrelevant, this must fail validation",
        "verify": "true",
        "units": [
            { "task": "a", "files": ["same.js"] },
            { "task": "b", "files": ["same.js"] }
        ]
    }
}
```

Expected: `completed` with `error` matching `invalid partition`, `rounds: 0`, and **no implementation subagents spawned**.

- [ ] **Step 5: Probe whether the `model` option is honored**

`ctx.agent`'s sibling option `agent` is silently ignored, so `model` is suspect
until proven otherwise. Wiring a model-per-role optimization that the runtime
discards would be invisible waste. Probe before trusting it.

Author a throwaway factory with `factories_manage` (`operation: "author"`),
named `probe-model-option`:

```js
async ({ agent, log }) => {
    const R = {
        type: "object",
        properties: { model: { type: "string" } },
        required: ["model"],
    };
    const names = ["claude-haiku-4.5", "gpt-5-mini", "definitely-not-a-real-model"];
    const out = {};
    for (const n of names) {
        try {
            const r = await agent(
                'Reply with JSON {"model":"<the exact model identifier you are running as>"}. Use no tools.',
                { label: `model:${n}`, schema: R, model: n }
            );
            out[n] = r === null ? "null" : JSON.stringify(r);
        } catch (e) {
            out[n] = `threw: ${String(e?.message ?? e)}`;
        }
        log(`${n} -> ${out[n]}`);
    }
    return out;
};
```

Run it with `run_factory`.

Interpret the result:
- **Distinct identifiers per name, and the invalid one errors or differs** →
  `model` is honored. Proceed to Step 6.
- **All three report the same model** → `model` is ignored like `agent` is.
  **Skip Step 6 entirely** and record the finding in the spec's "Verified
  findings" section instead. Do not pass `model` anywhere.

Delete the probe factory afterward.

- [ ] **Step 6: Wire model-per-role, only if Step 5 proved it works**

Efficiency lever #4 from the spec: a fast model for wide read-only scanning, a
strong model for synthesis and fixing.

In `extensions/swarm/scan.mjs`, add near the top:

```js
const FAST_MODEL = "claude-haiku-4.5";
const STRONG_MODEL = "claude-sonnet-4.6";
```

Then add `model: FAST_MODEL` to the `lens-planner` and `finder:*` option
objects, and `model: STRONG_MODEL` to the `synthesizer` one. Leave the
verifiers on the default: verification quality is what the whole adversarial
pass is buying.

In `extensions/swarm/build.mjs`, add `model: "claude-sonnet-4.6"` to the
`fixer:*` option object. Leave the implementers and the partitioner on the
default — they write code, and a cheap model writing bad code costs more fix
rounds than it saves.

Re-run `npm test` (expected: PASS, 29 passing) and `node --check` on both files.

- [ ] **Step 7: Record the results**

Append a "Verified" note to the spec stating both factories loaded, scan
produced confirmed findings with no unexpected writes, the partition guard
rejected overlap before spawning agents, and whether `model` is honored.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: record swarm factory integration verification"
```

---

## Task 11: The orchestrating-swarms skill

**Files:**
- Create: `skills/orchestrating-swarms/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `skills/orchestrating-swarms/SKILL.md`:

````markdown
---
name: orchestrating-swarms
description: >
  Use when a task splits into many independent pieces and one agent
  would be a bottleneck: auditing a codebase, investigating a bug from
  several angles, checking whether a solution already exists in a repo
  or paper, or implementing several independent units at once. Also use
  when the user says "swarm", "in parallel", "many agents", or "fan out".
---

# Orchestrating Swarms

## Overview

An Agent Factory is a JS orchestration that spawns and coordinates subagents
inside the session. Unlike dispatching subagents by hand, a factory runs tens
concurrently, verifies their output, and merges the results.

Two factories ship with this plugin. Use them before authoring anything.

| Factory | Shape | Use for |
| --- | --- | --- |
| `swarm-scan` | read-only, divergent | debugging, auditing, exploring, prior-art search |
| `swarm-build` | writing, convergent | implementing independent units in parallel |

Run one with `run_factory`. List what is registered with `factories_manage`
(`operation: "list"`).

## swarm-scan

```json
{
    "name": "swarm-scan",
    "args": {
        "question": "Why does the checkout flow drop the session on retry?",
        "scope": ["src/checkout"],
        "sources": "repo",
        "finders": 4,
        "verifyVotes": 2
    }
}
```

- `sources`: `"repo"` (default), `"web"`, or `"both"`. Use `"both"` for
  "does this already exist?" — it searches papers and public repos too.
- `lenses`: supply them to control the angles; omit to have them derived.
- `verifyVotes: 0` skips verification. Use it for a quick look.

Returns `{ confirmed, rejected, summary, dropped, unexpectedWrites }`.

**Always check `unexpectedWrites`.** A read-only scan cannot be enforced —
subagents have the full toolset — so it is detected instead. A non-empty
`unexpectedWrites` means a scan modified the working tree. Report it.

## swarm-build

```json
{
    "name": "swarm-build",
    "args": {
        "plan": "Add retry with backoff to the three API clients",
        "verify": "npm test",
        "maxFixRounds": 3
    }
}
```

`verify` must be a **real command** — `npm test`, `pytest -q`, `cargo test`.
It runs for real, twice at minimum: once as a baseline before anything is
touched, and once as the gate. Without the baseline, a pre-existing failure is
indistinguishable from one this work introduced, and the fixer wastes rounds on
someone else's bug.

Supply `units` to control the partition; omit to have it derived. Two units may
never declare the same file — the run is rejected before spawning any agent if
they do.

Returns `{ units, gate, baseline, rounds, ownershipViolations, changedFiles }`.

**Check `ownershipViolations` even when the gate passes.** It lists files
changed outside declared ownership, which means the partition was wrong even if
the tests happened to survive.

## Scaling ladder

Default small; escalate explicitly.

| Ask | finders | verifyVotes |
| --- | --- | --- |
| "take a quick look" | 2 | 0 |
| normal | 3 | 2 |
| "be thorough", "audit everything" | 8-12 | 3-5 |

Cost is not the constraint; waste is. Verification is the ×k stage, so a wide
finder pool with `verifyVotes: 0` is cheap, while a narrow pool with 5 votes is
not.

## Authoring one ad hoc

When neither factory fits — a tournament, a self-repair loop, staged escalation —
author one with `factories_manage` (`operation: "author"`). Read
`docs/factories.md` and `docs/factory-patterns.md` in the SDK first.

**The `run` body is self-contained.** It closes over nothing: no outer scope, no
static imports. Define every schema, constant, and helper inside the function,
and load modules with `await import()`.

Three rules that fail silently if broken:

1. **Unique `label` per independent subagent.** Identical prompt-and-options
   pairs memoize into ONE subagent. Ten calls, one agent, one result repeated.
2. **Null-guard every `agent()` result.** An ordinary failure resolves to `null`
   rather than throwing.
3. **Filter with `v => v !== null`, not `Boolean`** — which also drops a valid
   `false`, `0`, or `""`.

Also: `schema` honors only `type`, `required`, `enum`, `const`, `properties`,
`items`, and `anyOf`/`oneOf`/`allOf`. `pattern`, `minLength`, and
`additionalProperties` are silently ignored. And `ctx.agent`'s `agent` option is
ignored entirely, including an invalid name — never pass it.

## Efficiency

1. **Never pay an LLM for what JavaScript does.** Get JSON back via `schema` and
   dedupe, filter, rank, and merge in the run body.
2. **Never spawn an agent for deterministic work.** `git diff`, file listings,
   and greps run in the body.
3. **Prefer `pipeline` over `parallel`.** No barrier between stages, so a slow
   item never blocks a fast one. Use a barrier only when a stage needs the whole
   set at once — dedup does, mapping does not.
4. **Dedupe before verifying**, never after. Verification is the ×k stage.
5. **Log what you drop.** A top-N or a sampling step must say what it discarded.

## Resuming

A run that trips a limit or dies keeps its ID and journal. Recover the ID with
`factories_manage` (`operation: "runs"`) and resume with
`run_factory` using `resumeFromRunId`. Completed steps replay for free;
restarting from scratch pays for them twice.

## When NOT to use a swarm

- **One coherent change.** A single agent that holds the whole context does it
  better. Fan-out costs coordination.
- **You do not know what is broken yet.** Explore first, then fan out with a
  real question.
- **Genuinely sequential steps.** B needs A's output. A swarm cannot help.
- **Units that must edit the same file.** Repartition, or do it serially.
````

- [ ] **Step 2: Verify the frontmatter parses**

Run:

```bash
head -12 skills/orchestrating-swarms/SKILL.md
```

Expected: valid YAML frontmatter with `name` and `description`, matching the style of the other skills in `skills/`.

- [ ] **Step 3: Commit**

```bash
git add skills/orchestrating-swarms/SKILL.md
git commit -m "docs: add orchestrating-swarms skill"
```

---

## Task 12: Rewrite dispatching-parallel-agents

It currently teaches manual `Task()` dispatch, which is exactly the workflow being replaced. Left as-is, the agent keeps hand-dispatching and never reaches for a factory.

**Files:**
- Modify: `skills/dispatching-parallel-agents/SKILL.md` (full rewrite)

- [ ] **Step 1: Read the current skill**

```bash
cat skills/dispatching-parallel-agents/SKILL.md
```

Note what it claims, so the rewrite keeps the genuinely useful part — how to scope an agent prompt — and drops the manual dispatch mechanics.

- [ ] **Step 2: Replace it**

Replace the entire contents of `skills/dispatching-parallel-agents/SKILL.md`:

````markdown
---
name: dispatching-parallel-agents
description: >
  Use when facing 2+ independent tasks that can be worked on without
  shared state or sequential dependencies. Covers choosing between a
  swarm factory and hand-dispatched subagents, and how to scope an
  agent's prompt so it succeeds.
---

# Dispatching Parallel Agents

## First: prefer a factory

For anything wider than a handful of tasks, use the `orchestrating-swarms`
skill instead of dispatching by hand. A factory runs tens of subagents
concurrently, verifies their output, dedupes, and survives a restart via its
journal. Hand dispatch does none of that.

| Situation | Use |
| --- | --- |
| Many independent investigations | `swarm-scan` |
| Many independent implementation units | `swarm-build` |
| 2-3 tasks, each needing its own long context | hand-dispatched subagents |
| A shape neither factory fits | author a factory ad hoc |

Hand dispatch still wins in one case: a couple of tasks where you want the
agent's full turn-by-turn reasoning in your own context, and coordination
overhead would exceed the benefit.

## Scoping an agent's prompt

This part matters either way — a factory subagent needs the same care as a
hand-dispatched one.

Each agent gets **isolated context**. It inherits nothing from your session, so
you construct exactly what it needs:

- **Specific scope.** One clear problem domain, not "fix all the tests".
- **Self-contained context.** Paste the error messages, the test names, the file
  paths. It cannot see your conversation.
- **Explicit constraints.** "Do NOT change production code." "You own only these
  files." Without constraints an agent will refactor whatever it dislikes.
- **A defined output.** Say what to return. With a factory, enforce it with a
  `schema`.

### Bad vs good

| Bad | Good |
| --- | --- |
| "Fix the tests" | "Fix the 3 failures in `src/agents/abort.test.ts`" |
| "Fix the race condition" | Paste the failing names and the actual error |
| (no constraints) | "Fix tests only, do not touch production code" |
| "Fix it" | "Return the root cause and the changes you made" |

## Parallel writes

Agents writing concurrently corrupt each other's work unless ownership is
exclusive. **The unit of safety is the file.** Two agents that never touch the
same file need no isolation.

Ownership is exclusive, not one-to-one: one agent may own many files. Partition
by coherent task — a module, a feature slice — and file ownership follows.
Partitioning per file pays a cold start to edit twenty lines.

An agent that needs a change in someone else's file **reports it** rather than
making it. Apply those serially afterward. Agents cannot negotiate with each
other, and building a protocol so they could is a distributed system with LLMs
as nodes.

`swarm-build` enforces all of this: it rejects an overlapping partition before
spawning anything, and reports files changed outside declared ownership.

## After they return

1. **Read every summary.** Agents make systematic errors, not random ones.
2. **Run the real verification command** and read the output. An agent claiming
   success is not evidence — see `verification-before-completion`.
3. **Check for cross-contamination.** `git diff --name-only`, compared against
   what each agent was supposed to own.

## When NOT to dispatch in parallel

- **Related failures.** Fixing one may fix the rest. Investigate together first.
- **You do not know what is broken.** Explore first; dispatch on a real question.
- **Shared state.** Same files, same port, same fixture database.
- **Sequential dependencies.** B needs A's output.
````

- [ ] **Step 3: Verify no stale manual-dispatch guidance remains**

```bash
grep -n "Task(" skills/dispatching-parallel-agents/SKILL.md
```

Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add skills/dispatching-parallel-agents/SKILL.md
git commit -m "docs: point dispatching-parallel-agents at swarm factories"
```

---

## Task 13: Wire it into the plugin

The session-start hook injects the active instruction set. It must mention swarms, or the agent will not know they exist.

**Files:**
- Modify: `hooks/session-context.md`
- Modify: `README.md`
- Modify: `plugin.json`

- [ ] **Step 1: Read the current hook context**

```bash
cat hooks/session-context.md
```

- [ ] **Step 2: Add a swarm line to the skills gateway**

In `hooks/session-context.md`, inside the "Skills gateway" section, add one line
alongside the existing skill triggers:

```markdown
- Work that splits into many independent pieces (wide audit, multi-angle
  investigation, several independent units): `orchestrating-swarms`.
```

Keep it to one line. The hook is injected into every session; length has a cost.

- [ ] **Step 3: Document the extension in the README**

In `README.md`, after the "Subagents" bullet, add:

```markdown
- **Extension**: `swarm-scan` and `swarm-build` Agent Factories for running
  tens of subagents in parallel with verification (see the
  `orchestrating-swarms` skill).
```

- [ ] **Step 4: Bump the version**

In both `plugin.json` and `.claude-plugin/plugin.json`, change `"version": "0.1.0"` to `"version": "0.2.0"`. Do the same in `.claude-plugin/marketplace.json`, which carries the version in two places (top-level `metadata.version` and the entry in `plugins`).

Verify all of them changed:

```bash
grep -rn '"version"' plugin.json .claude-plugin/
```

Expected: every match reads `0.2.0`.

- [ ] **Step 5: Verify the tests still pass**

Run: `npm test`

Expected: PASS — 29 passing.

- [ ] **Step 6: Commit**

```bash
git add hooks/session-context.md README.md plugin.json .claude-plugin/
git commit -m "feat: wire swarm factories into the plugin and bump to 0.2.0"
```

---

## Task 14: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `npm test`

Expected: PASS — 29 passing, 0 failing.

- [ ] **Step 2: Verify every JS file parses**

```bash
for f in $(find extensions -name "*.mjs"); do node --check "$f" || echo "FAILED: $f"; done
```

Expected: no `FAILED` lines.

- [ ] **Step 3: Sync and reload**

```bash
rsync -a --delete extensions/ ~/.copilot/installed-plugins/mle-setup/mle-setup/extensions/
```

Then `extensions_reload`, then `extensions_manage` with `operation: "list"`.

Expected: `mle-setup:swarm` **running**, not failed.

- [ ] **Step 4: Confirm both factories are registered**

`factories_manage` with `operation: "list"`.

Expected: both `swarm-scan` and `swarm-build` listed, each with its declared phases and argument shape.

- [ ] **Step 5: End-to-end swarm-build on a real target**

Point it at a throwaway change in a repo with a real test suite. Confirm:
- `baseline` recorded before anything was touched
- `ownershipViolations` empty
- `gate.passed` true
- the progress log shows units starting concurrently

- [ ] **Step 6: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found in final swarm verification"
```
