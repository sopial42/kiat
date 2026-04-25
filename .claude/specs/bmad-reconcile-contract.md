# `bmad-reconcile` Contract

> **Why this file exists.** BMad is **external to Kiat** (per CLAUDE.md
> §"How to Work in a Kiat Project"). Kiat owns the *contract* that BMad
> must honor when reconciling story-level deviations; BMad owns the
> *implementation* (the actual `bmad-reconcile` skill or mode lives in
> BMad-land, alongside `bmad-retrospective`, `bmad-create-story`, etc.).
>
> This file is the contract. Any BMad-side implementation of reconcile
> MUST satisfy what's specified below to integrate cleanly with the
> Kiat pipeline. Conversely, Kiat agents (Team Lead, tech-spec-writer,
> coders) are entitled to assume reconcile honors this contract.

---

## Scope: per-story reconciliation, not per-epic retrospective

`bmad-reconcile` handles **one story at a time**, immediately after
Team Lead's Phase 5c. The epic-level rollup is the job of
`bmad-retrospective` — a sibling mode with its own contract.

Why split: per-story reconcile is reactive (close out the deviations
this story produced, before the next story builds on top); per-epic
retro is reflective (look at patterns across stories, audit doc state,
extract process lessons). Different cadences, different inputs,
different outputs.

---

## Inputs reconcile MUST read

| Input | Path | Why |
|---|---|---|
| Coder deviations, aggregated | `delivery/epics/epic-X/story-NN-<slug>.md` §`## Post-Delivery Notes` between `POST_DELIVERY_BLOCK_BEGIN/END` markers | The work item — every entry in this section requires triage |
| Existing business knowledge | `delivery/business/*.md` (read-only) | To grade severity (an entry that contradicts an existing rule is L3) and to identify candidate landing locations for L1/L2 promotions |
| Existing technical conventions | `delivery/specs/*.md` (read-only) | Same — for technical DECISION entries that should land in conventions, not business |
| Open queue entries | `delivery/_queue/needs-human-review.md` | To check whether a similar proposal already exists (avoid duplicates) and to allocate the next `Q-NNN` ID |
| Recent metrics events | `delivery/metrics/events.jsonl` (read-only, last ~50 lines) | To understand what happened in the immediately preceding stories — context for severity grading |

Reconcile MUST NOT read:
- Other stories' Post-Delivery Notes (that's the retrospective's job)
- Source code files beyond what's referenced in the deviation entries
- The story's `## Review Log` (closed cycle, not relevant to deviations)

---

## Outputs reconcile MUST produce

For every story it processes, reconcile produces ALL of the following:

### 1. The companion file `story-NN-<slug>.reconcile.md`

Mandatory whenever the story's `## Post-Delivery Notes` contains at
least one deviation (i.e., not the placeholder). Schema and template:
[`reconciliation-protocol.md`](reconciliation-protocol.md) §"The
`story-NN.reconcile.md` schema" + the canonical template at
`delivery/epics/epic-template/story-NN-slug.reconcile.md`.

The file MUST end with the marker:

```html
<!-- RECONCILE_DONE: <ISO-8601 UTC timestamp> -->
```

Without this marker, the reconciliation guard treats the story as
unreconciled and refuses to flip the epic to `✅ Done`.

### 2. L1 changes — applied directly

For every L1-classified deviation, reconcile MUST apply the change to
its target file (typically under `delivery/business/` or
`delivery/specs/`). Each application MUST:

- Be reversible by a single git revert
- Touch exactly one file unless the change is mechanically symmetric
  across two files
- Be summarized in the `.reconcile.md` L1 table with the target
  `path:line`

### 3. L2 entries — appended to the queue

For every L2-classified deviation, reconcile MUST append a new entry to
`delivery/_queue/needs-human-review.md`. The entry MUST follow the
schema in [`reconciliation-protocol.md`](reconciliation-protocol.md)
§"Queue entry schema". Specifically:

- Allocate the next `Q-NNN` ID by scanning existing entries for the
  highest existing ID
- Set status `[OPEN]` in the heading
- Fill `Source`, `Tag`, `Opened at`, `Affects`, `Affects (files)`,
  `Proposal`, `Alternative`, `Recommended` fields
- Reference the queue ID in the `.reconcile.md` L2 table

### 4. L3 escalations — written to events.jsonl

For every L3-classified deviation, reconcile MUST append an
`epic_block` event to `delivery/metrics/events.jsonl` (event schema in
[`metrics-events.md`](metrics-events.md)). The event MUST include:

- The story ID and epic
- The deviation tag and a one-line description
- The `blocked_until` field set to `"human_signoff"`
- A pointer to the story's `.reconcile.md` for full context

Reconcile MUST also reference the event line number in the
`.reconcile.md` L3 table.

Important: L3 events block Team Lead's pre-launch check for the next
story. Misclassifying an L1/L2 as L3 has a real cost — it stops the
pipeline. Reconcile should err on the side of L1 or L2 for ambiguous
cases.

### 5. The `reconcile_complete` event

After all of the above, reconcile MUST emit a single
`reconcile_complete` event to `delivery/metrics/events.jsonl` (schema
in [`metrics-events.md`](metrics-events.md)). The event aggregates the
counts (L1 applied, L2 queued, L3 blocked) and is what
`bmad-retrospective` reads to discover which stories had reconciles.

---

## Severity classification rules

The coder hints at L1/L2/L3 in the `## Post-Delivery Notes` bullet.
Reconcile MAY override the hint based on broader context. The
authoritative rules:

| Promote to L3 if… | Even if coder said L1 or L2 |
|---|---|
| The deviation contradicts an existing rule in `delivery/business/` | yes |
| The deviation breaks behavior in an already-shipped story (search the last 5 `_epic.md` files for affected functionality) | yes |
| The deviation requires a code change in another file that hasn't been done yet | yes |

| Promote to L2 if… | Even if coder said L1 |
|---|---|
| There are two or more reasonable landing locations for the change | yes |
| The change introduces a new domain term that isn't in the glossary | yes |
| The change is purely technical but its naming conflicts with existing patterns | yes |

| Demote to L1 if… | Even if coder said L2 or L3 |
|---|---|
| The change is a one-bullet addition to a doc whose section is unambiguous | yes (but log the reasoning in the `.reconcile.md` summary) |
| The change is purely cosmetic (typo, formatting, spec text canonicalization that the coder already started) | yes |

When in doubt, prefer L2 over L1 (humans reading the queue are cheap;
applying a wrong change is expensive) and L2 over L3 (don't block the
pipeline unless you're sure).

---

## Idempotency and re-runs

Reconcile MUST be idempotent. If invoked twice on the same story
(e.g., Team Lead re-launches it after a fix to Post-Delivery Notes):

- The companion `.reconcile.md` is OVERWRITTEN, not appended
- Already-applied L1 changes are NOT re-applied (detect via git diff)
- Already-queued L2 entries are NOT re-queued (detect via Q-NNN
  matching on `Source` field)
- Already-emitted L3 events are NOT re-emitted (detect via story ID
  matching in last N lines of `events.jsonl`)

A re-run is rare but legitimate — typically the result of Team Lead
catching a Phase 5c aggregation bug. Don't double-act.

---

## Failure handling

If reconcile cannot produce a valid `.reconcile.md` (e.g., the
`## Post-Delivery Notes` section is malformed and the validator hook
somehow let it through), reconcile MUST:

1. Write a single-line `.reconcile.md` with `<!-- RECONCILE_FAILED:
   <reason> -->` instead of the success marker
2. Emit a `reconcile_failed` event to `events.jsonl`
3. Halt — do NOT apply any L1, do NOT queue any L2, do NOT emit L3
4. Surface the failure to the human

A failed reconcile blocks epic closure exactly as a missing
`.reconcile.md` would.

---

## Things reconcile MUST NOT do

- ❌ Edit code (`backend/`, `frontend/`, `infra/`) — code changes
  belong to the next coder, not to reconcile
- ❌ Edit `.claude/` (framework machinery)
- ❌ Modify the story file's `## Business Context`, `## Acceptance
  Criteria`, or any section other than `## Post-Delivery Notes` itself
  (and even there, only to add the `_Reconciled by BMad on <date>_`
  legacy line if running in legacy-marker mode for backward compat)
- ❌ Delete entries from the queue
- ❌ Re-classify a previously-applied L1 (the change is already in the
  doc; re-classifying breaks the audit trail)
- ❌ Talk to the user directly — reconcile runs as a sub-agent of Team
  Lead, communicates via the structured outputs above

---

## Trigger and invocation

Reconcile is triggered by **Team Lead at Phase 5c**, after deviation
aggregation but before Phase 6 rollup. Team Lead spawns it via the
`Agent` tool. Reconcile returns a structured handoff:

```
RECONCILE_HANDOFF
story_path: delivery/epics/epic-X/story-NN-<slug>.md
reconcile_path: delivery/epics/epic-X/story-NN-<slug>.reconcile.md
l1_applied: <count>
l2_queued: <count>
l3_blocked: <count>
next_story_launchable: yes | no
```

If `next_story_launchable: no`, Team Lead's Phase 6 still proceeds
(the current story is shipped), but Team Lead notes the L3 block in
its rollup event and the next story's pre-launch check will refuse.

If reconcile failed entirely (returns `RECONCILE_HANDOFF_FAILED`),
Team Lead falls back to the legacy mode — emits the rollup with a
`reconcile_failed: true` flag and surfaces to the human.

---

## Implementation notes for BMad-side authors

This contract does not specify HOW reconcile achieves the above — only
WHAT it must produce. Implementation choices belong to the BMad mode
author. Suggested implementation patterns:

- Use a deterministic prompt template that walks each Post-Delivery
  Notes bullet and asks: "tag, severity, target, action?"
- Maintain an in-memory mapping of `Q-NNN` IDs to avoid race conditions
  on parallel reconciles (unlikely but possible if two stories merge
  near-simultaneously)
- Snapshot `delivery/_queue/needs-human-review.md` before append so a
  failed write can be rolled back
- Cite the protocol file and this contract in the BMad mode's prompt so
  the LLM never re-derives the rules

---

## Related

- [`reconciliation-protocol.md`](reconciliation-protocol.md) — the
  authoritative protocol this contract implements a slice of
- [`metrics-events.md`](metrics-events.md) — `epic_block`,
  `reconcile_complete`, `reconcile_failed` event schemas
- [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) — Phase
  5c (where reconcile gets spawned), Phase 6 (reconciliation guard)
- [`../../delivery/business/README.md`](../../delivery/business/README.md) §"Review mode" —
  the pre-protocol BMad reconciliation flow (still accepted in
  legacy-marker mode for backward compat)
