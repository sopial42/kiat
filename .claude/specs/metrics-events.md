# Metrics Events: JSONL Event Log Schema (v2)

> **Why this exists:** Kiat's enforcement layers already emit audit lines in agent outputs. This doc defines the **collection format** so those lines become structured data we can report on.

**Format:** Append-only JSONL (one JSON object per line).
**Location:** `delivery/metrics/events.jsonl` (active, v2 events only)
**Archive:** `delivery/metrics/events.archive-2026-05-16.jsonl` (legacy v1/v1.1 events — read-only by convention)
**Writer:** Team Lead (only).
**Reader:** `.claude/tools/report.py` — generates weekly/epic markdown reports.

---

## Schema version history

| Version | Date | Change |
|---|---|---|
| v1 | 2026-04 | Initial intra-story event types (granular) |
| v1.1 | 2026-04 | Rollup-first: one `story_rollup` per story replaces 8-10 granular events |
| v1.2 | 2026-05 | Reconciliation events (`reconcile_complete`, `reconcile_failed`, `epic_block`, `epic_unblock`, `queue_supersede`) |
| **v2** | **2026-05-16** | **Archive cut + canonical schema. `business_deviations` always object; `mode` enum-restricted; `spec` block required; `deviations_declared_explicitly` added; `prod_validation` retired. Active file restarted empty.** |
| **v2.1** | **2026-05-17** | **v2.1 observability (additive — no breaking change). New event `reconciliation_needed` emitted by Team Lead Stage 6.3 for human-triage latency measurement. New `severity_by_tag` field on `reconcile_complete` for the Severity × Tag cross-table.** |

**Archive cut (2026-05-16):** `delivery/metrics/events.jsonl` was moved to `events.archive-2026-05-16.jsonl`. The archive is read-only and holds all v1/v1.1/v1.2 events. New events (v2) write to the fresh `events.jsonl`. `report.py --scope all-time` reads both files and normalizes legacy events in-memory.

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

### `story_rollup` (PRIMARY — success path, v2 schema)

Emitted by Team Lead **once per successful story**, at the moment Team Lead marks the story as PASSED. Contains everything `report.py` needs.

#### v2 template (copy-paste this, fill in your values)

```json
{"ts":"2026-05-17T10:00:00Z","schema":"v2","event":"story_rollup","story":"<story-NN-slug>","epic":"<epic-X-slug>","outcome":"passed","size":"XS","scope":"infra","layers":["framework"],"mode":"normal","spec":{"verdict":"CLEAR","byte_count":3456,"clarification_rounds":0,"writer_mode":"enrichment"},"preflight":{"backend_coder":{"estimated_tokens":18000,"budget":35000,"result":"pass"}},"review_cycles":[{"domain":"backend","cycles":1,"final_verdict":"APPROVED","clerk_skill_triggered":false,"clerk_verdict":null,"test_patterns_consistent":true,"total_issues_across_cycles":0}],"fix_budget_used_min":0,"test_patterns_drift":false,"business_deviations":{"count":0,"backend":[],"frontend":[]},"deviations_declared_explicitly":true,"failure_pattern_id":null,"code_commit_sha":"<40-hex-sha>"}
```

**Field semantics (v2 canonical):**

- `ts` (required): ISO 8601 UTC timestamp of when the story was marked PASSED
- `schema` (required, v2+): always `"v2"` for new events. Absent on legacy events — `report.py` treats absent as `"v1"`.
- `story`, `epic`, `event` (required): standard identification
- `outcome` (required): always `"passed"` for this event type
- `size` (required): `"XS"` | `"S"` | `"M"` | `"L"` — story T-shirt size
- `scope` (required): e.g. `"infra"`, `"backend"`, `"frontend"`, `"full-stack"` — story scope category
- `layers` (required, array of strings): e.g. `["framework"]`, `["backend","frontend"]` — architectural layers touched
- `code_commit_sha` (required, string, 40-hex): the SHA of the commit Team Lead created at Stage 7.1. **MUST differ from the parent SHA.** Without this field, `report.py` rejects the rollup as malformed. The 2026-05-01 incident — 5 rollups written `passed` while no commit existed — is the canonical reason this field is required.
- `mode` (required, enum): `"normal"` | `"solo"` | `"team_lead_authored"`. **No other values accepted — custom values are a protocol violation.**
  - `"normal"` = full pipeline (tech-spec-writer → coders → reviewers)
  - `"solo"` = Stage 1.1 solo track (requires `solo_track` and `solo_authz`)
  - `"team_lead_authored"` = Team Lead wrote the spec inline (spec bypassed; use `spec.verdict: "BYPASSED"`)
- `solo_track` (enum, REQUIRED when `mode == "solo"`): `"A"` | `"B"`. MUST be absent when `mode != "solo"`.
- `solo_authz` (string, REQUIRED when `mode == "solo"`): the authz token from the user, e.g. `"go 2026-05-16"`.
- `spec` (required, object): spec validation block. Required on every rollup.
  - `verdict` (enum): `"CLEAR"` | `"NEEDS_CLARIFICATION"` | `"BLOCKED"` | `"BYPASSED"` (BYPASSED = Team Lead authored inline, writer not invoked)
  - `byte_count` (int): byte size of the full story file at Stage 3.1 check (`wc -c`)
  - `clarification_rounds` (int): number of `SPEC_CLARIFICATION` rounds before `CLEAR` was reached; sourced from `SPEC_HANDOFF.clarification_rounds`. 0 if CLEAR on first pass or BYPASSED.
  - `writer_mode` (string): `"enrichment"` | `"greenfield"` | `"team_lead_authored"` — matches SPEC_HANDOFF `mode` field
- `preflight` (object): per-agent context budget pre-flight results. Keys are agent names; values are `{estimated_tokens, budget, result}`. Omit keys for agents not launched. Use `"n/a — solo Track B"` string for the value if solo track bypassed pre-flight.
- `review_cycles` (array of objects): one entry per domain that had review activity. Each object:
  - `domain` (enum): `"backend"` | `"frontend"`
  - `cycles` (int): total review cycles (1 = approved first try)
  - `final_verdict` (enum): `"APPROVED"` | `"NEEDS_DISCUSSION"` | `"BLOCKED"`
  - `clerk_skill_triggered` (bool): any cycle invoked `kiat-clerk-auth-review`?
  - `clerk_verdict` (enum or null): final Clerk verdict if triggered, else null
  - `test_patterns_consistent` (bool): all cycles confirmed patterns match? false if any cycle flagged drift
  - `total_issues_across_cycles` (int): sum of issues across all BLOCKED cycles
- `fix_budget_used_min` (int or null): **retrospective metric only** — approximate minutes in fix cycles after first BLOCKED verdict. The 45-min gate was retired by [EV-0003](../EVOLUTION.md#ev-0003--retire-fix_budget45min). 0 if no fix cycle, null if unknown.
- `test_patterns_drift` (bool): true if any `review_cycles` entry has `test_patterns_consistent: false`.
- `business_deviations` (required, object): summary of coder deviations from spec (Stage 6.2). **Always an object — never an integer.**
  - `count` (int): total deviations across all coders. 0 if all reported `NONE`.
  - `backend` (array of strings): one-line summaries of backend deviations. `[]` if none.
  - `frontend` (array of strings): one-line summaries of frontend deviations. `[]` if none.
- `deviations_declared_explicitly` (required when `business_deviations.count == 0`, bool): distinguishes "zero deviations because the coder declared NONE explicitly" (true) from "zero deviations because the coder didn't write a Business Deviations block at all" (false — canary for missing block). Always set this honestly. `false` = protocol gap, not just absence of deviations.
- `failure_pattern_id` (string or null): `FP-NNN` if this story matched a documented failure pattern, else null.

**Fields retired in v2 (do not include in new events):**

- `prod_validation` — retired by [EV-0007](../EVOLUTION.md#ev-0007--retire-phase-7-prod_validation) on 2026-05-16. Legacy archive events keep it untouched — no migration. `report.py` ignores it on read.
- `bmad_spec_bytes`, `spec_verdict`, `spec_clarification_rounds` — replaced by the `spec` object block above. Legacy events keep them; new v2 events use the `spec` block only.
- `reviews` (object keyed by domain) — replaced by `review_cycles` (array). Legacy events keep the old shape; `report.py` normalizes both.

**On precision of timestamps:** Team Lead does NOT have a reliable system clock. The `ts`, `fix_budget_used_min`, and `total_elapsed_min` fields are best-effort estimates based on the conversation context. Acceptable precision: ±5 minutes. If Team Lead cannot estimate, set the minute fields to `null` — `report.py` will handle it gracefully.

#### How Team Lead estimates `fix_budget_used_min` (retrospective metric, v2)

The 45-min escalation gate was retired by [EV-0003](../EVOLUTION.md#ev-0003--retire-fix_budget45min) after 80 stories showed it never fired. The field stays in the rollup for retro analytics, but it is **never a trigger** — Team Lead never branches on it, never escalates because of it, never prepends it to a retry prompt. Re-cycles are bounded by the qualitative signals listed in [`kiat-team-lead.md`](../agents/kiat-team-lead.md#retry-budget-qualitative-signals-only) (spec ambiguity, security issue, ≥ 3 BLOCKED cycles).

Tracking methodology for the retrospective number:

1. **Mental start point:** the first time you send BLOCKED issues back to a coder. Do NOT count test failures inside Stage 4.3 unless those failures end up BLOCKED by a reviewer.
2. **At story completion:** estimate the elapsed minutes between that point and the final re-review using your best-effort sense of wall-clock time from the conversation (message spacing, prior step durations). You do not have a real clock — ±5 minutes is acceptable.
3. **Rollup:** `fix_budget_used_min = <estimate>` (or `0` if the story never entered a fix cycle, or `null` if you truly cannot estimate).

Escalation cases (security blocker, `NEEDS_DISCUSSION` that Team Lead cannot arbitrate, spec clarification request, ≥ 3 BLOCKED cycles without convergence) produce `story_escalated` events with `fix_budget_used_min: null` when they fire before any fix cycle has started, or with the best-effort estimate otherwise.

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
  "reached_stage": "3.3",
  "bmad_spec_bytes": 34000,
  "spec_verdict": "CLEAR",
  "preflight": {
    "backend_coder": {"estimated_tokens": 44000, "budget": 35000, "result": "overflow"}
  },
  "reviews": {},
  "fix_budget_used_min": null,
  "total_elapsed_min": 2,
  "failure_pattern_id": "FP-001",
  "note": "Story spec alone is 15k tokens. Split required."
}
```

**Field semantics:**

Everything in `story_rollup` PLUS:
- `outcome` (required): always `"escalated"` for this event type
- `escalated_to` (enum): `"tech-spec-writer"` | `"bmad"` | `"user"` | `"designer"`
- `reason` (enum): `"spec_blocked"` | `"spec_clarification_loop"` | `"budget_overflow"` | `"fix_budget_exhausted"` | `"needs_discussion"` | `"security_blocker"` | `"test_flakiness"` | `"other"`
- `reached_stage` (string): which stage the story reached before escalation — `"1.1"` | `"1.2"` | `"1.3"` | `"2"` | `"3.1"` | `"3.2"` | `"3.3"` | `"4.1"` | `"4.2"` | `"4.3"` | `"5.1"` | `"5.2"` | `"6.1"` | `"6.2"` | `"6.3"` | `"7.1"` | `"7.2"` | `"7.3"`. **Legacy `reached_phase` field still readable by `report.py` for archived v1/v1.1 events.**
- `failure_pattern_id` (string, optional): if the escalation matches a documented `FP-NNN` in `failure-patterns.md`
- `note` (string, optional): free-text context for why it was escalated
- `reviews` can be empty `{}` if escalation happened before any reviewer ran
- `fix_budget_used_min` can be `null` if escalation happened before any fix cycle started (retrospective metric only — the 45-min gate was retired by EV-0003)

---

---

### Reconciliation Events (v1.2 additive)

These event types support the per-story reconciliation protocol
introduced in v1.2. Full semantics live in
[`reconciliation-protocol.md`](reconciliation-protocol.md). The events
are written by **`/bmad-correct-course`** (per story) and **tech-spec-writer**
(when its Stage 2 queue scan auto-promotes an L2 to L3).

These events are additive — they don't replace any v1.1 event. A
story can have one `story_rollup` AND one `reconcile_complete` AND zero
or more `epic_block` events.

---

### `reconciliation_needed` (v2.1 observability)

Emitted by Team Lead at **Stage 6.3**, immediately after creating the
`.reconcile.md` companion file (Stage 6.2) and emitting the
`RECONCILIATION_NEEDED:` notification block. Marks the moment a story
finished its automated pipeline and is now awaiting human triage via
`/bmad-correct-course`.

The matching `reconcile_complete` event (when it eventually fires)
gives the latency `RECONCILE_DONE - RECONCILIATION_NEEDED` — the
**human triage cost** per story. This is the headline observability
signal added in v2.1.

```json
{
  "ts": "2026-05-17T18:30:00Z",
  "schema": "v2",
  "event": "reconciliation_needed",
  "story": "story-05-soft-delete",
  "epic": "epic-2",
  "reconcile_path": "delivery/epics/epic-2/story-05-soft-delete.reconcile.md",
  "deviations_count": 4,
  "deviations_unresolved": 2,
  "severity_hint": {"L1": 2, "L2": 2, "L3": 0}
}
```

**Field semantics:**

- `reconcile_path` (string): path to the just-created
  `.reconcile.md` companion file
- `deviations_count` (int): total number of deviation entries in
  the `## Deviations` block (regardless of status)
- `deviations_unresolved` (int): number of entries with
  `Status: NEEDS_PROMOTION` or `Status: BLOCKING` (i.e., not
  already RESOLVED at handoff via the producer-pays gate)
- `severity_hint` (object, optional): the coder's initial severity
  classification, taken as a hint only. Keys: `L1` | `L2` | `L3`,
  values: int. `/bmad-correct-course` may reclassify during triage.

**Emit rule:** exactly one `reconciliation_needed` per story that
has a `.reconcile.md` file. If `## Deviations` is empty or all
entries are `RESOLVED`, the event is still emitted (signals that
no triage is needed; latency to `reconcile_complete` should be ~0).

---

### `reconcile_complete` (v1.2 — enriched in v2.1)

Emitted by `/bmad-correct-course` once per story it processes, AFTER it has
written the `.reconcile.md` companion file and applied L1 changes /
queued L2 entries / written L3 escalations. This event is what
`bmad-retrospective` reads to discover which stories had reconciles.

Pairs with `reconciliation_needed` (emitted by Team Lead) to compute
human triage latency.

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
  "queue_ids_added": ["Q-014"],
  "severity_by_tag": {
    "SPEC_GAP": {"L1": 1, "L2": 1, "L3": 0},
    "DECISION": {"L1": 1, "L2": 0, "L3": 0}
  }
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
- `severity_by_tag` (object, **v2.1 additive**): final severity
  breakdown per tag-enum prefix, post-triage by
  `/bmad-correct-course`. Keys are one of the 8 enum prefixes
  (`SPEC_GAP`, `DECISION`, `SCOPE_CUT`, `BOY_SCOUT`, `DOMAIN_NEW`,
  `PROCESS`, `TEST_DRIFT`, `UPSTREAM_MISMATCH`). Values are
  `{"L1": int, "L2": int, "L3": int}` counts. `report.py` uses this
  to render the **Severity × Tag** cross-table. Empty or missing
  when no deviations had a recognized tag-enum prefix.

If reconcile failed entirely (could not produce a valid
`.reconcile.md`), it emits `reconcile_failed` instead — see below.

---

### `reconcile_failed` (v1.2)

Emitted by `/bmad-correct-course` when it cannot complete (typically because
the `## Post-Delivery Notes` section is malformed and somehow bypassed
the validator hook). A failure here blocks epic closure exactly as a
missing reconcile would — the reconciliation guard at Team Lead Stage 7
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

Emitted by `/bmad-correct-course` (when it classifies a deviation as L3) OR
by tech-spec-writer (when its Stage 2 queue scan auto-promotes an L2
to L3 due to scope overlap with the new story). Team Lead reads
`events.jsonl` for unresolved `epic_block` events at every story
pre-launch — an unresolved event refuses the next story.

```json
{
  "ts": "2026-04-25T15:30:00Z",
  "story": "story-05",
  "epic": "epic-2",
  "event": "epic_block",
  "source": "bmad-correct-course",
  "deviation_tag": "SPEC_GAP",
  "summary": "RLS contract break — 401 returned where AC-4 spec'd 404",
  "blocked_until": "human_signoff",
  "reconcile_path": "delivery/epics/epic-2/story-05-soft-delete.reconcile.md",
  "queue_id": null
}
```

**Field semantics:**

- `source` (enum): `"bmad-correct-course"` (deviation classified as L3 at
  reconcile time) | `"tech-spec-writer"` (L2 auto-promoted via Phase
  -1 scope-overlap)
- `deviation_tag` (enum): `AC-N` | `SPEC_GAP` | `DECISION` |
  `OUT-OF-SCOPE` | `SKILL_GAP`
- `summary` (string): one-line description, copied verbatim from the
  Post-Delivery Notes bullet
- `blocked_until` (enum): `"human_signoff"` (current spec) — future
  values may include `"timeout"`, `"automatic_promotion"`, etc.
- `reconcile_path` (string): pointer to the `.reconcile.md` (when
  `source` is `/bmad-correct-course`) — null when `source` is
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

### `queue_supersede` (v1.2 — added by EV-0002)

Emitted by Team Lead at Stage 3.2 **in lieu of `epic_block`** when the
scope-overlap scan finds a Q-ID that the new story explicitly declares
in its `## Supersedes:` section. The story is not blocked — it lands
and the Q-ID is closed as `[SUPERSEDED]` in the queue. **Emitted BEFORE
Stage 3.3 runs** so the queue stays consistent even if the budget check
later fails.

```json
{
  "ts": "2026-05-16T23:30:00Z",
  "story": "story-NN",
  "epic": "epic-X",
  "event": "queue_supersede",
  "queue_id": "Q-058",
  "deviation_tag": "AC_T13_FR27_WIDGET_INTEGRATION_DEFERRED",
  "summary": "this story IS the FR27 widget integration",
  "source": "kiat-team-lead"
}
```

**Field semantics:**

- `queue_id` (string, required): the `Q-NNN` ID being superseded
- `deviation_tag` (string, required): copied verbatim from the queue
  entry's heading tag (post-`Q-NNN — [STATUS]`)
- `summary` (string, required): one-line rationale, copied from the
  story's `## Supersedes:` bullet for this Q-ID
- `source` (enum, required): always `"kiat-team-lead"` (Stage 3.2 is
  the only writer)

`queue_supersede` is mutually exclusive with `epic_block` for the same
`(story, queue_id)` pair — Team Lead emits one or the other, never
both, per Stage 3.2's branching logic
([`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md#phase-0c--reconciliation-queue-scope-overlap-check-mandatory)).
Reverting a supersession (e.g., the human later disagrees) is handled
out-of-band by reopening a new `Q-NNN` entry — the original
`queue_supersede` event stays as audit trail.

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
  "estimated_tokens": 31000,
  "budget": 35000,
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

### 7. `fix_budget_started` (legacy, retired)
Historically emitted when a coder received BLOCKED feedback, to start the 45-min retry clock. The 45-min gate was retired by [EV-0003](../EVOLUTION.md#ev-0003--retire-fix_budget45min); the event is no longer emitted but the shape is preserved here so `report.py` can still parse historical lines without crashing.

```json
{
  "ts": "2026-04-10T14:18:42Z",
  "story": "story-27",
  "event": "fix_budget_started",
  "budget_min": 45
}
```

**Fields:**
- `budget_min` (int): historical budget value (always `45` in the archived lines)

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
  - `"fix_budget_exhausted"` — historical reason from when the 45-min gate existed; retired by [EV-0003](../EVOLUTION.md#ev-0003--retire-fix_budget45min) and no longer emitted by new stories. Kept in the enum so legacy lines parse.
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

## Writing Events (Team Lead Protocol — v2 Rollup-First)

**v2 rule:** Team Lead writes **exactly ONE event per story**, at the very end of the story, using Bash `>> events.jsonl` heredoc. The event is a single JSONL line, no pretty-printing. Use the v2 template above — include `"schema": "v2"` and use the `spec` block, `review_cycles` array, and `business_deviations` object form.

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

- **`bmad_spec_bytes`**: was measured at Stage 3.3 pre-flight check (Team Lead ran `wc -c` on the spec file)
- **`spec_verdict` + `spec_clarification_rounds`**: recorded from Stage 3.1 (how many times `kiat-validate-spec` returned `NEEDS_CLARIFICATION` before reaching `CLEAR`)
- **`preflight`**: recorded at Stage 3.3 (one entry per launched coder)
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

See `.claude/tools/report.py`. The reader:
1. By default: opens `delivery/metrics/events.jsonl` (active v2 events only)
2. With `--scope all-time`: also reads `delivery/metrics/events.archive-2026-05-16.jsonl` and normalizes legacy events in-memory to v2 shape before computing metrics
3. Parses each line as JSON (skips malformed lines with a warning)
4. Groups by story ID
5. Computes per-story and aggregate metrics
6. Outputs markdown to stdout or a file

**Legacy normalization** (applied in-memory by `report.py` when reading the archive):
- `business_deviations` as int → `{count: <int>, backend: [], frontend: []}` object
- `spec_verdict` + `spec_clarification_rounds` flat fields → `spec: {verdict: ..., byte_count: null, clarification_rounds: ..., writer_mode: "unknown"}`
- `reviews` object → `review_cycles` array (one entry per domain key)
- `prod_validation` field → ignored

Metrics derivable from this schema:
- Pre-flight overflow rate (count of `preflight` with `result: "overflow"` ÷ total `preflight` events)
- Verdict distribution (count of `review` events grouped by `verdict`)
- Fix budget distribution (histogram + p90 of `fix_budget_used_min` across rollups — retrospective; the 45-min gate was retired by EV-0003)
- Clerk skill trigger rate (count of `review` with `clerk_skill_triggered: true` ÷ total reviews)
- Test patterns consistency (count of `review` with `test_patterns_consistent: false`)
- Escalation reasons histogram (count of `escalated` events by `reason`)
- Spec clarification rounds (count of `spec_validated` events per story)
- Cycles per story (count of `review` events per story)
- Total elapsed time per story (from `received` to `passed`)
- Story completion rate (count of `passed` ÷ count of `received`)

---

## Schema Versioning

Current version: **v2** (active `events.jsonl`). Legacy v1/v1.1/v1.2 events in `events.archive-2026-05-16.jsonl`.

Any breaking change to existing event shapes must:
1. Bump the schema version (v3, ...)
2. Add `"schema": "v3"` (or equivalent) to new events
3. Archive the current active file, restart empty
4. Keep the reader backward-compatible with all prior archives

**Additive changes** (new optional fields with defaults) do NOT require a version bump or archive cut.

**v2 field `"schema": "v2"`** — present on all events written after 2026-05-16. Absent on legacy archive events (treat absent as `"v1"`).

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
