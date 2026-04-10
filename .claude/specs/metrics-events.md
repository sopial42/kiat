# Metrics Events: JSONL Event Log Schema (v1.1)

> **Why this exists:** Kiat's enforcement layers already emit audit lines in agent outputs. This doc defines the **collection format** so those lines become structured data we can report on.

**Format:** Append-only JSONL (one JSON object per line).
**Location:** `delivery/metrics/events.jsonl`
**Writer:** Team Lead (only).
**Reader:** `kiat/.claude/tools/report.py` — generates weekly/epic markdown reports.

---

## v1.1 Update: Rollup-First Writing Strategy

**Previous assumption (v1.0):** Team Lead emits 8-10 events per story, one per phase transition (`received`, `spec_validated`, `preflight`, `coder_launched`, `coder_finished`, `review` x N, `passed`). This assumed LLMs can reliably write JSONL lines at every phase while orchestrating. **In practice, they can't** — writing 10+ tool calls per story competes with the main orchestration work, leads to missed events, typo-ed timestamps, and schema drift.

**v1.1 approach:** Team Lead writes **ONE event per story**: either `story_rollup` (success) or `story_escalated` (escalation). The rollup contains everything `report.py` needs, computed from the conversation state at story completion.

**Consequences of this change:**
- ✅ Fiability: one write per story is much more reliable than 10
- ✅ Simplicity: Team Lead doesn't need precise intra-story timestamps
- ✅ Same report metrics available (verdicts, cycles, clerk skill usage, escalation reasons)
- ❌ Lost granularity: we no longer know exactly *when* preflight ran vs review cycle 1
- ❌ Can't correlate events across stories if they interleave

For Kiat's purpose (weekly health reports, failure pattern detection), the tradeoff is strongly in favor of rollup. Intra-story granularity was a nice-to-have, not a must-have.

**Backward compatibility:** `report.py` reads both the legacy granular events (from v1.0) and the new rollup events (v1.1). If a story has a rollup, it's used as the source of truth. If a story only has legacy events, they're aggregated on the fly.

---

## Design Principles

1. **One writer, single-threaded**: Only Team Lead writes events.
2. **Append-only**: Events are never updated or deleted. Corrections are new events with `event: "correction"`.
3. **Self-describing**: Every event has `ts`, `story`, `event` as minimum fields.
4. **Git-friendly**: JSONL means each story appends ~1-2 lines to the file, git diffs are readable.
5. **Tool-agnostic**: Any language with JSON parsing can consume it.
6. **Stable schema**: Field names never change. New events add new types; new fields are additive with defaults.
7. **Rollup-first (v1.1)**: prefer one `story_rollup` or `story_escalated` event at story completion over many intra-story events.

---

## Common Fields (every event)

| Field | Type | Required | Description |
|---|---|---|---|
| `ts` | string (ISO 8601 UTC) | yes | Timestamp of the event, e.g. `"2026-04-10T14:02:11Z"` |
| `story` | string | yes | Story ID, e.g. `"story-27"` |
| `event` | string | yes | Event type (see below) |
| `epic` | string | no | Epic ID, e.g. `"epic-3"`. Optional, convenient for grouping. |

---

## Event Types

### v1.1 Primary Events (use these — rollup-first)

These two event types cover every normal story. Team Lead writes exactly one of them at story completion.

---

### `story_rollup` (PRIMARY — success path)

Emitted by Team Lead **once per successful story**, at the moment Team Lead marks the story as PASSED. Contains everything `report.py` needs.

```json
{
  "ts": "2026-04-10T14:45:00Z",
  "story": "story-27",
  "epic": "epic-3",
  "event": "story_rollup",
  "outcome": "passed",
  "bmad_spec_bytes": 18420,
  "spec_verdict": "CLEAR",
  "spec_clarification_rounds": 0,
  "preflight": {
    "backend_coder": {"estimated_tokens": 21000, "budget": 25000, "result": "pass"},
    "frontend_coder": {"estimated_tokens": 19000, "budget": 25000, "result": "pass"}
  },
  "reviews": {
    "backend": {
      "cycles": 2,
      "final_verdict": "APPROVED",
      "clerk_skill_triggered": true,
      "clerk_verdict": "PASSED",
      "test_patterns_consistent": true,
      "total_issues_across_cycles": 3
    },
    "frontend": {
      "cycles": 1,
      "final_verdict": "APPROVED",
      "clerk_skill_triggered": false,
      "clerk_verdict": null,
      "test_patterns_consistent": true,
      "total_issues_across_cycles": 0
    }
  },
  "fix_budget_used_min": 13,
  "total_elapsed_min": 43
}
```

**Field semantics:**

- `ts` (required): ISO 8601 UTC timestamp of when the story was marked PASSED
- `story`, `epic`, `event` (required): standard identification
- `outcome` (required): always `"passed"` for this event type
- `bmad_spec_bytes` (int): byte size of the story spec at reception
- `spec_verdict` (enum): final verdict from `kiat-validate-spec` after any clarification rounds (`CLEAR` | `NEEDS_CLARIFICATION` | `BLOCKED`)
- `spec_clarification_rounds` (int): number of BMAD clarification rounds before `CLEAR` was reached
- `preflight` (object): per-agent context budget pre-flight results. Keys are agent names; values are `{estimated_tokens, budget, result}`. Omit keys for agents that weren't launched (e.g., no backend work).
- `reviews` (object): per-domain review rollup. Keys are `"backend"` and/or `"frontend"`. Each contains:
  - `cycles` (int): total number of review cycles (1 means approved on first try)
  - `final_verdict` (enum): `"APPROVED"` | `"NEEDS_DISCUSSION"` | `"BLOCKED"` (final verdict when the story became PASSED — usually `APPROVED`, but `NEEDS_DISCUSSION` resolved by Team Lead arbitration is also possible)
  - `clerk_skill_triggered` (bool): did any review cycle invoke `kiat-clerk-auth-review`?
  - `clerk_verdict` (enum or null): if triggered, final Clerk verdict. Null otherwise.
  - `test_patterns_consistent` (bool): did ALL cycles confirm the coder's implementation matched their acknowledged patterns? (false if any cycle flagged drift)
  - `total_issues_across_cycles` (int): sum of `issues_count` from all BLOCKED verdicts during the story
- `fix_budget_used_min` (int): approximate minutes between `fix_budget_started` and story completion. **Team Lead's best estimate** — not required to be precise. Set to 0 if the story was APPROVED on first try without entering a fix cycle.
- `total_elapsed_min` (int): approximate minutes from story reception to completion. **Team Lead's best estimate.**

**On precision of timestamps:** Team Lead does NOT have a reliable system clock. The `ts`, `fix_budget_used_min`, and `total_elapsed_min` fields are best-effort estimates based on the conversation context. Acceptable precision: ±5 minutes. If Team Lead cannot estimate, set the minute fields to `null` — `report.py` will handle it gracefully.

---

### `story_escalated` (PRIMARY — escalation path)

Emitted by Team Lead **once per escalated story**, at the moment Team Lead escalates to BMAD, user, or designer.

```json
{
  "ts": "2026-04-10T15:01:30Z",
  "story": "story-28",
  "epic": "epic-3",
  "event": "story_escalated",
  "outcome": "escalated",
  "escalated_to": "bmad",
  "reason": "budget_overflow",
  "reached_phase": "0b",
  "bmad_spec_bytes": 34000,
  "spec_verdict": "CLEAR",
  "preflight": {
    "backend_coder": {"estimated_tokens": 34000, "budget": 25000, "result": "overflow"}
  },
  "reviews": {},
  "fix_budget_used_min": null,
  "total_elapsed_min": 2,
  "failure_pattern_id": "FP-001",
  "note": "Story spec alone is 11k tokens. Split required."
}
```

**Field semantics:**

Everything in `story_rollup` PLUS:
- `outcome` (required): always `"escalated"` for this event type
- `escalated_to` (enum): `"bmad"` | `"user"` | `"designer"`
- `reason` (enum): `"spec_blocked"` | `"spec_clarification_loop"` | `"budget_overflow"` | `"fix_budget_exhausted"` | `"needs_discussion"` | `"security_blocker"` | `"test_flakiness"` | `"other"`
- `reached_phase` (string): which phase the story reached before escalation — `"0a"` | `"0b"` | `"1"` | `"2"` | `"3"` | `"4"` | `"5"`
- `failure_pattern_id` (string, optional): if the escalation matches a documented `FP-NNN` in `failure-patterns.md`
- `note` (string, optional): free-text context for why it was escalated
- `reviews` can be empty `{}` if escalation happened before any reviewer ran
- `fix_budget_used_min` can be `null` if escalation happened before the fix budget started

---

### v1.0 Legacy Events (deprecated — still parsed by report.py for backward compat)

The event types below are from v1.0 (intra-story phase transitions). Team Lead should NOT emit these anymore — use `story_rollup` / `story_escalated` instead. `report.py` still reads them for stories written before v1.1, and aggregates them on the fly if no rollup is present.

---

### 1. `received` (legacy)
Emitted when Team Lead picks up a new story from BMAD.

```json
{
  "ts": "2026-04-10T14:02:11Z",
  "story": "story-27",
  "epic": "epic-3",
  "event": "received",
  "bmad_spec_bytes": 18420
}
```

**Fields:**
- `bmad_spec_bytes` (int): byte size of the story spec file at reception time

---

### 2. `spec_validated` (legacy)
Emitted after the `kiat-validate-spec` skill runs. Captures the SPEC_VERDICT.

```json
{
  "ts": "2026-04-10T14:02:30Z",
  "story": "story-27",
  "event": "spec_validated",
  "verdict": "CLEAR",
  "clarifications_requested": 0
}
```

**Fields:**
- `verdict` (enum): `"CLEAR"` | `"NEEDS_CLARIFICATION"` | `"BLOCKED"`
- `clarifications_requested` (int): number of questions sent to BMAD (0 if CLEAR)

On `NEEDS_CLARIFICATION`, a second `spec_validated` event is emitted after
BMAD's rewrite is re-validated — this lets reports count how many
clarification rounds a story needed.

---

### 3. `preflight` (legacy)
Emitted for each coder after the context budget pre-flight check.

```json
{
  "ts": "2026-04-10T14:02:45Z",
  "story": "story-27",
  "event": "preflight",
  "agent": "kiat-backend-coder",
  "estimated_tokens": 21000,
  "budget": 25000,
  "result": "pass"
}
```

**Fields:**
- `agent` (enum): `"kiat-backend-coder"` | `"kiat-frontend-coder"` | `"kiat-backend-reviewer"` | `"kiat-frontend-reviewer"`
- `estimated_tokens` (int): `wc -c / 4` estimate
- `budget` (int): hard limit for that agent
- `result` (enum): `"pass"` | `"overflow"`

On `overflow`, Team Lead escalates to BMAD; a subsequent `preflight` event
captures the re-check after the split.

---

### 4. `coder_launched` (legacy)
Emitted when a coder is actually started.

```json
{
  "ts": "2026-04-10T14:03:00Z",
  "story": "story-27",
  "event": "coder_launched",
  "agent": "kiat-backend-coder"
}
```

**Fields:**
- `agent` (enum): `"kiat-backend-coder"` | `"kiat-frontend-coder"`

---

### 5. `coder_finished` (legacy)
Emitted when a coder reports code ready for review.

```json
{
  "ts": "2026-04-10T14:18:30Z",
  "story": "story-27",
  "event": "coder_finished",
  "agent": "kiat-backend-coder",
  "test_patterns_acknowledged": true,
  "files_changed": 6,
  "tests_added": 8
}
```

**Fields:**
- `agent` (enum): `"kiat-backend-coder"` | `"kiat-frontend-coder"`
- `test_patterns_acknowledged` (bool): did the coder's output contain `TEST_PATTERNS: ACKNOWLEDGED`?
- `files_changed` (int): count of files in the diff
- `tests_added` (int): count of new tests

---

### 6. `review` (legacy)
Emitted when a reviewer returns a verdict. **Most important event type — drives most metrics.**

```json
{
  "ts": "2026-04-10T14:18:42Z",
  "story": "story-27",
  "event": "review",
  "agent": "kiat-backend-reviewer",
  "cycle": 1,
  "verdict": "BLOCKED",
  "clerk_skill_triggered": false,
  "clerk_verdict": null,
  "test_patterns_consistent": true,
  "issues_count": 3,
  "elapsed_min_since_fix_budget_start": null
}
```

**Fields:**
- `agent` (enum): `"kiat-backend-reviewer"` | `"kiat-frontend-reviewer"`
- `cycle` (int): 1 for first review, 2 for re-review after fix, etc.
- `verdict` (enum): `"APPROVED"` | `"NEEDS_DISCUSSION"` | `"BLOCKED"`
- `clerk_skill_triggered` (bool): did the diff match Clerk trigger patterns?
- `clerk_verdict` (enum or null): `"PASSED"` | `"DISCUSSION"` | `"BLOCKED"` | `null` (not triggered)
- `test_patterns_consistent` (bool): did the coder's code match the acknowledged patterns?
- `issues_count` (int): number of issues listed (0 if APPROVED)
- `elapsed_min_since_fix_budget_start` (int or null): minutes since the fix budget clock started; null on cycle 1

---

### 7. `fix_budget_started` (legacy)
Emitted when a coder receives BLOCKED feedback and starts the 45-min clock.

```json
{
  "ts": "2026-04-10T14:18:42Z",
  "story": "story-27",
  "event": "fix_budget_started",
  "budget_min": 45
}
```

**Fields:**
- `budget_min` (int): total budget in minutes (default 45)

---

### 8. `escalated` (legacy)
Emitted when Team Lead escalates to BMAD or user (any reason).

```json
{
  "ts": "2026-04-10T14:45:00Z",
  "story": "story-27",
  "event": "escalated",
  "to": "bmad",
  "reason": "fix_budget_exhausted",
  "elapsed_min": 47,
  "failure_pattern_id": "FP-003"
}
```

**Fields:**
- `to` (enum): `"bmad"` | `"user"` | `"designer"`
- `reason` (enum):
  - `"spec_blocked"` — kiat-validate-spec returned BLOCKED
  - `"spec_clarification"` — kiat-validate-spec returned NEEDS_CLARIFICATION
  - `"budget_overflow"` — context budget exceeded
  - `"fix_budget_exhausted"` — 45-min clock ran out
  - `"needs_discussion"` — reviewer verdict NEEDS_DISCUSSION, Team Lead can't arbitrate
  - `"security_blocker"` — RLS missing, secret in code, etc.
  - `"test_flakiness"` — environmental issue, not code
  - `"other"` — free-text reason in a `note` field
- `elapsed_min` (int, optional): only for fix_budget_exhausted
- `failure_pattern_id` (string, optional): if this matches a documented FP-NNN, reference it

---

### 9. `passed` (legacy)
Emitted when a story completes successfully.

```json
{
  "ts": "2026-04-10T14:45:00Z",
  "story": "story-27",
  "event": "passed",
  "total_cycles": 2,
  "total_elapsed_min": 43,
  "backend_verdict": "APPROVED",
  "frontend_verdict": "APPROVED"
}
```

**Fields:**
- `total_cycles` (int): sum of review cycles across both agents
- `total_elapsed_min` (int): wall-clock time from `received` to `passed`
- `backend_verdict` (enum or null): final verdict, null if no backend work
- `frontend_verdict` (enum or null): final verdict, null if no frontend work

---

### 10. `correction` (legacy)
Emitted if a past event needs to be corrected (rare, but needed because
JSONL is append-only).

```json
{
  "ts": "2026-04-10T15:00:00Z",
  "story": "story-27",
  "event": "correction",
  "target_event_ts": "2026-04-10T14:18:30Z",
  "field": "files_changed",
  "old_value": 6,
  "new_value": 7,
  "reason": "missed a file in initial count"
}
```

---

## Writing Events (Team Lead Protocol — v1.1 Rollup-First)

**v1.1 rule:** Team Lead writes **exactly ONE event per story**, at the very end of the story, using the Write tool (append mode) or Bash `>> events.jsonl`. The event is a single JSONL line, no pretty-printing.

### The only two writes Team Lead does per story

1. **Success path** — on marking story PASSED:
   ```
   emit {"event": "story_rollup", "outcome": "passed", ...all fields from the rollup schema above}
   ```

2. **Escalation path** — on escalating to BMAD / user / designer:
   ```
   emit {"event": "story_escalated", "outcome": "escalated", "escalated_to": ..., "reason": ..., "reached_phase": ...}
   ```

**That's it. Two possible writes per story, mutually exclusive.** No intra-story events, no per-phase tracking in the JSONL.

### How to fill the rollup fields

Team Lead builds the rollup from its conversation state at story completion:

- **`bmad_spec_bytes`**: was measured at Phase 0b pre-flight check (Team Lead ran `wc -c` on the spec file)
- **`spec_verdict` + `spec_clarification_rounds`**: recorded from Phase 0a (how many times `kiat-validate-spec` returned `NEEDS_CLARIFICATION` before reaching `CLEAR`)
- **`preflight`**: recorded at Phase 0b (one entry per launched coder)
- **`reviews`**: aggregated from all reviewer verdicts received during the story. Count cycles, pick the final verdict, check if any cycle had `clerk_skill_triggered` or `test_patterns_consistent: false`
- **`fix_budget_used_min`** and **`total_elapsed_min`**: best-effort estimates. Team Lead does not have a system clock — use the conversation's natural sense of time, or set to `null` if unsure. `report.py` handles null gracefully.

### Failure mode

If Team Lead forgets to write the rollup at story completion, the story is invisible to `report.py`. **This is the only fiability concern that matters.** Every other intra-story event can be skipped without consequence because the rollup aggregates everything.

**How to minimize the risk of forgetting the rollup write:**
- Team Lead's phase 6 "Story Complete" checklist explicitly includes "emit story_rollup event"
- The rollup write is the LAST thing Team Lead does for a story — it's the exit marker
- If the report shows fewer stories than you know you ran, that's the drift signal — investigate which story is missing

---

## Reading Events (Report Generator)

See `kiat/.claude/tools/report.py`. The reader:
1. Opens `delivery/metrics/events.jsonl`
2. Parses each line as JSON (skips malformed lines with a warning)
3. Groups by story ID
4. Computes per-story and aggregate metrics
5. Outputs markdown to stdout or a file

Metrics derivable from this schema:
- Pre-flight overflow rate (count of `preflight` with `result: "overflow"` ÷ total `preflight` events)
- Verdict distribution (count of `review` events grouped by `verdict`)
- Fix budget utilization (avg `elapsed_min` across `escalated` with `reason: "fix_budget_exhausted"`)
- Clerk skill trigger rate (count of `review` with `clerk_skill_triggered: true` ÷ total reviews)
- Test patterns consistency (count of `review` with `test_patterns_consistent: false`)
- Escalation reasons histogram (count of `escalated` events by `reason`)
- Spec clarification rounds (count of `spec_validated` events per story)
- Cycles per story (count of `review` events per story)
- Total elapsed time per story (from `received` to `passed`)
- Story completion rate (count of `passed` ÷ count of `received`)

---

## Schema Versioning

The initial schema version is **v1**. Any breaking change to existing event
shapes must:
1. Bump the schema version (v2, v3, ...)
2. Add a `schema_version` field to new events
3. Keep the reader backward-compatible with older events

**Additive changes** (new event types, new optional fields with defaults)
do NOT require a version bump.

---

## Gotchas

- **Don't pretty-print JSONL.** Each event must be a single line — pretty-printing breaks `jq` and line-based parsers.
- **UTC timestamps only.** Avoid timezone ambiguity in reports.
- **Don't embed large blobs.** If you're tempted to dump the full reviewer output into an event, don't — reference it by path or store issues summaries only. Events should be small (< 1 KB each).
- **Rotate when needed.** When `events.jsonl` exceeds ~10 MB, rotate to `events-YYYY-MM.jsonl` and start a new file. The report generator takes a glob, not a single file.
- **Never manually edit past events.** Use `correction` events instead. Manual edits break audit trail.

---

## Future (not in v1)

When we have enough real data:
- Per-epic rollup events (`epic_complete` with aggregate metrics)
- Agent performance snapshots (avg cycles per agent over time)
- Cost events (if we start tracking token spend per story)
- External correlation IDs (if we wire Kiat to GitHub Actions runs)

None of these are in v1. Start small, extend when needed.
