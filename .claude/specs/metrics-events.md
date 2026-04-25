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
  "total_elapsed_min": 43,
  "business_deviations": {
    "count": 2,
    "backend": ["AC-3: bulk delete → async job queue", "SPEC_GAP: soft delete for GDPR"],
    "frontend": []
  }
}
```

**Field semantics:**

- `ts` (required): ISO 8601 UTC timestamp of when the story was marked PASSED
- `story`, `epic`, `event` (required): standard identification
- `outcome` (required): always `"passed"` for this event type
- `bmad_spec_bytes` (int): byte size of the **full story file** at reception (both layers: `## Business Context` written by BMad + technical sections written by the tech-spec-writer). Field name kept for schema backward-compat; the value covers both layers.
- `spec_verdict` (enum): final verdict from `kiat-validate-spec` after any clarification rounds (`CLEAR` | `NEEDS_CLARIFICATION` | `BLOCKED`)
- `spec_clarification_rounds` (int): number of clarification rounds (to the tech-spec-writer and/or BMad, depending on which layer the gap was in) before `CLEAR` was reached
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
- `business_deviations` (object): summary of deviations from spec reported by coders at Phase 5c. Contains:
  - `count` (int): total number of deviations across all coders (0 if all reported `NONE`)
  - `backend` (array of strings): one-line summaries of backend deviations (empty array if `NONE`)
  - `frontend` (array of strings): one-line summaries of frontend deviations (empty array if `NONE`)

**On precision of timestamps:** Team Lead does NOT have a reliable system clock. The `ts`, `fix_budget_used_min`, and `total_elapsed_min` fields are best-effort estimates based on the conversation context. Acceptable precision: ±5 minutes. If Team Lead cannot estimate, set the minute fields to `null` — `report.py` will handle it gracefully.

#### How Team Lead tracks the 45-minute fix budget (single source of truth)

The rule itself (45 minutes per story, immediate escalations bypass the budget) is stated in [`README.md`](../../README.md#layer-2--wall-clock-retry-budget-not-cycle-count) (Layer 2) and in [`kiat-team-lead.md`](../agents/kiat-team-lead.md#retry-budget-time-based-not-cycle-based) (Retry budget section). The **tracking methodology** — how Team Lead turns that rule into a concrete timestamp — lives here because it is the same mechanism that feeds the `fix_budget_used_min` rollup field:

1. **Start:** record `fix_budget_started_at` the first time you send BLOCKED issues back to a coder. This is the only clock. Do NOT start it on test failures inside Phase 3 unless those failures end up BLOCKED by a reviewer.
2. **On each re-review cycle:** compute `elapsed = now - fix_budget_started_at` using your best-effort sense of wall-clock time from the conversation (message spacing, prior step durations). You do not have a real clock — ±5 minutes is acceptable.
3. **Decision on each BLOCKED re-review:**
   - `elapsed < 45 min` → allow another fix cycle, no matter the cycle number (cycle 3, 4, 5 all OK)
   - `elapsed ≥ 45 min` → escalate with `reason: "fix_budget_exhausted"`, do NOT run another cycle
4. **Rollup:** at story completion, `fix_budget_used_min = elapsed` at the final re-review (or `0` if the story never entered a fix cycle, or `null` if you truly cannot estimate).

Immediate-escalation cases (security blocker, `NEEDS_DISCUSSION` that Team Lead cannot arbitrate, spec clarification request) bypass the clock entirely — see the Retry Budget section of `kiat-team-lead.md` for the full list. They produce `story_escalated` events with `fix_budget_used_min: null` when they fire before any fix cycle has started.

---

### `story_escalated` (PRIMARY — escalation path)

Emitted by Team Lead **once per escalated story**, at the moment Team Lead escalates to `kiat-tech-spec-writer`, BMad, user, or designer (depending on which layer the blocker is in).

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
- `escalated_to` (enum): `"tech-spec-writer"` | `"bmad"` | `"user"` | `"designer"`
- `reason` (enum): `"spec_blocked"` | `"spec_clarification_loop"` | `"budget_overflow"` | `"fix_budget_exhausted"` | `"needs_discussion"` | `"security_blocker"` | `"test_flakiness"` | `"other"`
- `reached_phase` (string): which phase the story reached before escalation — `"0a"` | `"0b"` | `"1"` | `"2"` | `"3"` | `"4"` | `"5"`
- `failure_pattern_id` (string, optional): if the escalation matches a documented `FP-NNN` in `failure-patterns.md`
- `note` (string, optional): free-text context for why it was escalated
- `reviews` can be empty `{}` if escalation happened before any reviewer ran
- `fix_budget_used_min` can be `null` if escalation happened before the fix budget started

---

---

### Reconciliation Events (v1.2 additive)

These event types support the per-story reconciliation protocol
introduced in v1.2. Full semantics live in
[`reconciliation-protocol.md`](reconciliation-protocol.md). The events
are written by **`bmad-reconcile`** (per story) and **tech-spec-writer**
(when its Phase -1 queue scan auto-promotes an L2 to L3).

These events are additive — they don't replace any v1.1 event. A
story can have one `story_rollup` AND one `reconcile_complete` AND zero
or more `epic_block` events.

---

### `reconcile_complete` (v1.2)

Emitted by `bmad-reconcile` once per story it processes, AFTER it has
written the `.reconcile.md` companion file and applied L1 changes /
queued L2 entries / written L3 escalations. This event is what
`bmad-retrospective` reads to discover which stories had reconciles.

```json
{
  "ts": "2026-04-25T15:30:00Z",
  "story": "story-05",
  "epic": "epic-2",
  "event": "reconcile_complete",
  "reconcile_path": "delivery/epics/epic-2/story-05-soft-delete.reconcile.md",
  "l1_applied": 2,
  "l2_queued": 1,
  "l3_blocked": 0,
  "next_story_launchable": true,
  "queue_ids_added": ["Q-014"]
}
```

**Field semantics:**

- `reconcile_path` (string): path to the generated `.reconcile.md`
  companion file
- `l1_applied` (int): number of L1 deviations reconcile applied
  directly to `delivery/business/` or `delivery/specs/`
- `l2_queued` (int): number of L2 deviations reconcile appended to
  `delivery/_queue/needs-human-review.md`
- `l3_blocked` (int): number of L3 deviations reconcile escalated via
  `epic_block` events (see below)
- `next_story_launchable` (bool): false if `l3_blocked > 0`, true
  otherwise. Team Lead's pre-launch check uses this to decide whether
  the next story can start.
- `queue_ids_added` (array of string): list of `Q-NNN` IDs
  appended in this run, for traceability

If reconcile failed entirely (could not produce a valid
`.reconcile.md`), it emits `reconcile_failed` instead — see below.

---

### `reconcile_failed` (v1.2)

Emitted by `bmad-reconcile` when it cannot complete (typically because
the `## Post-Delivery Notes` section is malformed and somehow bypassed
the validator hook). A failure here blocks epic closure exactly as a
missing reconcile would — the reconciliation guard at Team Lead Phase 6
greps for `RECONCILE_DONE` markers, and a failed reconcile produces a
`RECONCILE_FAILED` marker instead.

```json
{
  "ts": "2026-04-25T15:32:00Z",
  "story": "story-05",
  "epic": "epic-2",
  "event": "reconcile_failed",
  "reason": "post_delivery_schema_invalid",
  "note": "Block contains bullets but no `**Tag**:` field on bullet 2"
}
```

**Field semantics:**

- `reason` (enum): `"post_delivery_schema_invalid"` |
  `"queue_write_failed"` | `"events_write_failed"` |
  `"contradiction_with_business"` | `"other"`
- `note` (string, optional): free-text context

---

### `epic_block` (v1.2)

Emitted by `bmad-reconcile` (when it classifies a deviation as L3) OR
by tech-spec-writer (when its Phase -1 queue scan auto-promotes an L2
to L3 due to scope overlap with the new story). Team Lead reads
`events.jsonl` for unresolved `epic_block` events at every story
pre-launch — an unresolved event refuses the next story.

```json
{
  "ts": "2026-04-25T15:30:00Z",
  "story": "story-05",
  "epic": "epic-2",
  "event": "epic_block",
  "source": "bmad-reconcile",
  "deviation_tag": "SPEC_GAP",
  "summary": "RLS contract break — 401 returned where AC-4 spec'd 404",
  "blocked_until": "human_signoff",
  "reconcile_path": "delivery/epics/epic-2/story-05-soft-delete.reconcile.md",
  "queue_id": null
}
```

**Field semantics:**

- `source` (enum): `"bmad-reconcile"` (deviation classified as L3 at
  reconcile time) | `"tech-spec-writer"` (L2 auto-promoted via Phase
  -1 scope-overlap)
- `deviation_tag` (enum): `AC-N` | `SPEC_GAP` | `DECISION` |
  `OUT-OF-SCOPE` | `SKILL_GAP`
- `summary` (string): one-line description, copied verbatim from the
  Post-Delivery Notes bullet
- `blocked_until` (enum): `"human_signoff"` (current spec) — future
  values may include `"timeout"`, `"automatic_promotion"`, etc.
- `reconcile_path` (string): pointer to the `.reconcile.md` (when
  `source` is `bmad-reconcile`) — null when `source` is
  `tech-spec-writer` and the block came from a queue overlap
- `queue_id` (string or null): `Q-NNN` ID of the queue entry that was
  promoted (only set when `source` is `tech-spec-writer`)

### How Team Lead checks for unresolved blocks

Before launching any new story, Team Lead greps `events.jsonl` for
`epic_block` events whose epic matches the new story's epic AND whose
`story` field has NOT been followed by an `epic_unblock` event for the
same `(epic, story, deviation_tag)` triple. An unresolved match refuses
the launch.

---

### `epic_unblock` (v1.2)

Emitted by Team Lead (or by a human via a manual append) when an
`epic_block` has been resolved. Cancels the block.

```json
{
  "ts": "2026-04-25T18:00:00Z",
  "story": "story-05",
  "epic": "epic-2",
  "event": "epic_unblock",
  "blocks_cleared": [
    {"deviation_tag": "SPEC_GAP", "ts": "2026-04-25T15:30:00Z"}
  ],
  "resolution": "Updated AC-4 to specify 401 (RLS-driven), added matching frontend handling in story-05a"
}
```

**Field semantics:**

- `blocks_cleared` (array of objects): each object identifies the
  `epic_block` event being canceled by `(deviation_tag, ts)`. Multiple
  blocks may be cleared in one event when a single human signoff
  resolves them together.
- `resolution` (string): one or two sentences explaining what the
  human decided / did

---

### v1.0 Legacy Events (deprecated — still parsed by report.py for backward compat)

The event types below are from v1.0 (intra-story phase transitions). Team Lead should NOT emit these anymore — use `story_rollup` / `story_escalated` instead. `report.py` still reads them for stories written before v1.1, and aggregates them on the fly if no rollup is present.

---

### 1. `received` (legacy)
Emitted when Team Lead picks up a new story (written by `kiat-tech-spec-writer`, with a BMad-authored `## Business Context` on top when applicable).

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
- `clarifications_requested` (int): number of questions sent back to the tech-spec-writer (and/or BMad for Business Context gaps) (0 if CLEAR)

On `NEEDS_CLARIFICATION`, a second `spec_validated` event is emitted after
the rewrite is re-validated — this lets reports count how many
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

On `overflow`, Team Lead escalates to `kiat-tech-spec-writer` with a split
request; a subsequent `preflight` event captures the re-check after the split.

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
Emitted when Team Lead escalates to `kiat-tech-spec-writer`, BMad, user, or designer (any reason).

```json
{
  "ts": "2026-04-10T14:45:00Z",
  "story": "story-27",
  "event": "escalated",
  "to": "tech-spec-writer",
  "reason": "fix_budget_exhausted",
  "elapsed_min": 47,
  "failure_pattern_id": "FP-003"
}
```

**Fields:**
- `to` (enum): `"tech-spec-writer"` | `"bmad"` | `"user"` | `"designer"`
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

2. **Escalation path** — on escalating to `kiat-tech-spec-writer` / BMad / user / designer:
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
