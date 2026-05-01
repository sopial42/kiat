# `/bmad-correct-course` Contract (Kiat per-story reconciliation)

> **Why this file exists.** BMad is **external to Kiat** (per CLAUDE.md
> §"How to Work in a Kiat Project"). Kiat owns the *contract* for what
> per-story reconciliation must produce; BMad owns the *implementation*
> via its existing `/bmad-correct-course` skill ("Manage significant
> changes during sprint execution"). A populated `## Post-Delivery
> Notes` section IS a significant change during sprint execution — it
> records every place the implementation diverged from the spec. So
> `/bmad-correct-course` is the right BMad tool; this file pins the
> Kiat-side expectations on its output.
>
> When a human runs `/bmad-correct-course` on a Kiat story whose
> companion file `story-NN-<slug>.reconcile.md` has a populated
> `## Deviations` section, the BMad session MUST satisfy what's
> specified below to integrate cleanly with the Kiat pipeline.
> Kiat agents (Team Lead at Phase 6, tech-spec-writer at Phase -1,
> coders at scope reading) are entitled to assume the contract holds.

---

## Scope: per-story reconciliation, not per-epic retrospective

`/bmad-correct-course` handles **one story at a time**, invoked by the
human after Team Lead emits a `RECONCILIATION_NEEDED:` notification at
Phase 5d. The epic-level rollup is `/bmad-retrospective` — a sibling
BMad skill with its own contract (per-epic, not per-story).

Why split: per-story reconcile is reactive (close out the deviations
this story produced, before the next story builds on top); per-epic
retro is reflective (look at patterns across stories, audit doc state,
extract process lessons). Different cadences, different inputs,
different outputs.

---

## Trigger and invocation flow

1. **Coder** ships story, emits `Business Deviations:` block in handoff.
2. **Team Lead Phase 5c** aggregates the deviations into the companion
   file `story-NN-<slug>.reconcile.md` (creating it) under the
   `## Deviations` section using the strict bullet schema. The
   validator hook (`check-post-delivery-schema.sh`) enforces.
3. **Team Lead Phase 5c** creates the companion file
   `story-NN-<slug>.reconcile.md` with a `## Deviations` section
   populated from coder handoffs. The story spec file itself is NOT
   modified — it never carries a deviations section.
4. **Team Lead Phase 5d** detects the companion file's existence and
   emits a `RECONCILIATION_NEEDED:` notification block telling the
   human which story needs `/bmad-correct-course`.
5. **Team Lead Phase 6** writes the rollup and ships the story. The
   reconciliation guard at Phase 6 refuses to flip the epic to `✅
   Done` until every story with a `.reconcile.md` companion file
   carries the `RECONCILE_DONE` marker.
6. **Human** invokes `/bmad-correct-course <story-path>` when
   convenient (immediately if the next story's scope might overlap;
   can defer otherwise — but Team Lead's Phase 0c will auto-promote on
   overlap if too long).
7. **BMad session** running `/bmad-correct-course` reads the
   `.reconcile.md` companion file's `## Deviations` section, triages
   each entry by L1/L2/L3 severity, and produces the artifacts below.

`/bmad-correct-course` MUST NOT be invoked by Team Lead or any Kiat
sub-agent — it is a human-driven skill. Team Lead notifies; the human
decides when.

---

## Solo-mode recovery (no Phase 5c upstream)

When Team Lead ships a story via Phase -2 solo-mode (see [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) §"Phase -2 — Solo-mode fast path"), there is **no Phase 5c upstream** — the `.reconcile.md` companion file does NOT exist when `/bmad-correct-course` is invoked. The skill detects this and switches to **recover-mode**.

### Detection

`/bmad-correct-course` is in recover-mode when ALL of:

- The companion file `delivery/epics/epic-X/story-NN-<slug>.reconcile.md` does NOT exist
- The story file's `## Implementation discipline` section (or equivalent solo-mode marker) is populated
- The most recent `story_rollup` event for this story in `events.jsonl` carries `"mode": "solo"`

If the companion file is missing for any other reason (e.g., human deleted it, file system issue), do NOT enter recover-mode — surface the inconsistency and halt. Recover-mode is reserved for the documented solo-mode case.

### Sources of truth (in priority order) for the reconstructed `## Deviations`

1. **The story file's `## What was deferred` section** — explicit deferrals listed by Team Lead at solo-ship time. Each deferral becomes one deviation bullet (typically tagged `SCOPE_*_DEFERRED`).
2. **The story file's `## Implementation discipline` section** — process choices (solo-mode authorization, Phase 5c skip, reviewer proxy used). At minimum produces one `PROCESS_SOLO_MODE` deviation and one `PROCESS_RECONCILE_RECOVERY` deviation, both L1 audit-only.
3. **The commit body** (`git show <story_commit_sha> --no-patch`) — Team Lead's solo authorization quote, additional rationale, and any "shipped solo" markers required by Phase -2 step 4.
4. **The story spec text itself** (read-only) — for `SpecRef` pointers to acceptance criteria the solo ship absorbed or deferred.

### Procedure

1. Create the `.reconcile.md` companion file from scratch using the canonical template at [`../../delivery/epics/epic-template/story-NN-slug.reconcile.md`](../../delivery/epics/epic-template/story-NN-slug.reconcile.md).
2. Add a header note in the file's intro explaining it was created by recover-mode (not Team Lead Phase 5c). Cite the Phase 5c skip authorization (verbatim user quote + date from the commit body) so the audit trail names the human who authorized the bypass.
3. Populate `## Deviations` from the priority-ordered sources above, following the strict bullet schema (Tag, Severity, Summary, File, SpecRef, Status, Why) — same as the normal Phase 5c output.
4. Continue with the standard reconcile flow (L1/L2/L3 triage, queue closures, `RECONCILE_DONE` marker, `reconcile_complete` event). The output is indistinguishable from a normal reconcile — only the `## Deviations` provenance differs, and that's documented in the header.

### When NOT to enter recover-mode

- The companion file already exists — even if `## Deviations` is empty (`<!-- POST_DELIVERY_BLOCK_BEGIN -->\n_(no deviations)_\n<!-- POST_DELIVERY_BLOCK_END -->`). Empty deviations is a legitimate Phase 5c outcome ("story shipped exactly as specified"); do not overwrite.
- The story rollup event does NOT carry `"mode": "solo"`. Without that flag, the missing companion is a Phase 5c bug, not a solo-mode bypass — surface to the human and halt.
- The story file lacks an `## Implementation discipline` section AND the commit body lacks a solo-mode marker. Recover-mode without provenance is unsafe.

### Why recover-mode exists (for the framework port reviewer)

Two recurrences validated the pattern: epic-12 story-01 (INSEE V3.11 portal migration 2026-05-01) and epic-03 story-02 (Levé palette propagation 2026-05-02). Both shipped solo, both were recovered cleanly post-hoc by `/bmad-correct-course` reading the story file + commit body. Codifying recover-mode pairs with [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) §"Phase -2 — Solo-mode fast path" — without recover-mode, solo-mode stories would orphan their reconciliation and break the epic close guard.

---

## Inputs `/bmad-correct-course` MUST read

| Input | Path | Why |
|---|---|---|
| Coder deviations, aggregated | `delivery/epics/epic-X/story-NN-<slug>.reconcile.md` §`## Deviations` between `POST_DELIVERY_BLOCK_BEGIN/END` markers | The work item — every entry in this section requires triage |
| The story spec (read-only context) | `delivery/epics/epic-X/story-NN-<slug>.md` | To resolve `SpecRef` pointers (`story-NN.md:line`) and understand original AC text |
| Existing business knowledge | `delivery/business/*.md` (read-only) | To grade severity (an entry that contradicts an existing rule is L3) and to identify candidate landing locations for L1/L2 promotions |
| Existing technical conventions | `delivery/specs/*.md` (read-only) | Same — for technical DECISION entries that should land in conventions, not business |
| Open queue entries | `delivery/_queue/needs-human-review.md` | To check whether a similar proposal already exists (avoid duplicates) and to allocate the next `Q-NNN` ID |
| Recent metrics events | `delivery/metrics/events.jsonl` (read-only, last ~50 lines) | To understand what happened in the immediately preceding stories — context for severity grading |

`/bmad-correct-course` MUST NOT read:
- Other stories' `.reconcile.md` files (that's the retrospective's job)
- Source code files beyond what's referenced in the deviation entries
- The story's `## Review Log` (closed cycle, not relevant to deviations)

---

## Outputs `/bmad-correct-course` MUST produce

For every story it processes, the BMad session MUST produce ALL of the
following:

### 1. Append the `## Reconciliation` section to the SAME `.reconcile.md` file

The companion file `story-NN-<slug>.reconcile.md` already exists when
`/bmad-correct-course` runs (it was created by Team Lead at Phase 5c
with the `## Deviations` section). `/bmad-correct-course` updates the
SAME file in place — it does NOT create a new file. Specifically:

- **Replace the `## Reconciliation` placeholder** (`_(awaiting
  reconciliation — run /bmad-correct-course on this story)_`) with the
  L1/L2/L3 sub-sections + Outcome (schema in
  [`reconciliation-protocol.md`](reconciliation-protocol.md) §"The
  `story-NN-<slug>.reconcile.md` schema").
- **Do NOT modify the `## Deviations` section** — that's Team Lead's
  output, immutable from this point forward.
- **End with the marker**:
  ```html
  <!-- RECONCILE_DONE: <ISO-8601 UTC timestamp> -->
  ```
  Without this marker, Team Lead's reconciliation guard treats the
  story as unreconciled and refuses to flip the epic to `✅ Done`.

Canonical template:
`delivery/epics/epic-template/story-NN-slug.reconcile.md`.

### 2. L1 changes — applied directly

For every L1-classified deviation, `/bmad-correct-course` MUST apply
the change to its target file (typically under `delivery/business/` or
`delivery/specs/`). Each application MUST:

- Be reversible by a single git revert
- Touch exactly one file unless the change is mechanically symmetric
  across two files
- Be summarized in the `.reconcile.md` L1 table with the target
  `path:line`

### 3. L2 entries — appended to the queue

For every L2-classified deviation, `/bmad-correct-course` MUST append
a new entry to `delivery/_queue/needs-human-review.md`. The entry MUST
follow the schema in
[`reconciliation-protocol.md`](reconciliation-protocol.md) §"Queue
entry schema". Specifically:

- Allocate the next `Q-NNN` ID by scanning existing entries for the
  highest existing ID
- Set status `[OPEN]` in the heading
- Fill `Source`, `Tag`, `Opened at`, `Affects`, `Affects (files)`,
  `Proposal`, `Alternative`, `Recommended` fields
- Reference the queue ID in the `.reconcile.md` L2 table

### 4. L3 escalations — written to events.jsonl

For every L3-classified deviation, `/bmad-correct-course` MUST append
an `epic_block` event to `delivery/metrics/events.jsonl` (event schema
in [`metrics-events.md`](metrics-events.md)). The event MUST include:

- The story ID and epic
- The deviation tag and a one-line description
- The `blocked_until` field set to `"human_signoff"`
- A pointer to the story's `.reconcile.md` for full context
- `source: "bmad-correct-course"`

The event blocks Team Lead's pre-launch check for the next story.
Misclassifying L1/L2 as L3 has a real cost — it stops the pipeline.
Err on the side of L1 or L2 for ambiguous cases.

### 5. The `reconcile_complete` event

After all of the above, `/bmad-correct-course` MUST emit a single
`reconcile_complete` event to `delivery/metrics/events.jsonl` (schema
in [`metrics-events.md`](metrics-events.md)). The event aggregates the
counts (L1 applied, L2 queued, L3 blocked) and is what
`/bmad-retrospective` reads to discover which stories had reconciles.

---

## Severity classification rules

The coder hints at L1/L2/L3 in the `## Deviations` bullet.
`/bmad-correct-course` MAY override the hint based on broader context.

**Re-apply the producer-pays gate at triage time.** Before honoring any
L2 hint from the coder, re-run the **Q1/Q2/Q3 gate** from
[`reconciliation-protocol.md` §"The producer-pays severity gate"](reconciliation-protocol.md):

- **Q1 — Observable?** Does the `Why` field name a concrete observable
  (log line, metric, UI surface, API contract, CI test, security
  scanner)? If no, **demote to "DROPPED"** — do NOT append to the
  queue. Note in the `.reconcile.md` summary why the entry was dropped.
- **Q2 — > 10 min?** If the fix is ≤10 min and the canonical landing
  spot is obvious, **demote to L1** and apply inline (preserves the
  existing demotion path below).
- **Q3 — Boy Scout opportunity?** If a near-term planned story (visible
  in the current or next epic's `## Stories` list) edits one of the
  same files, **append a one-line note to that story's `## Notes`
  section instead of queuing**. Do NOT append to the queue. Log the
  piggyback in the `.reconcile.md` summary.

Only deviations that survive Q1+Q2+Q3 (observable + >10min + no
piggyback) become L2 queue entries. The historical bias "prefer L2
over L1 in doubt" is **superseded** — that bias was the root cause of
the queue-as-feature-backlog drift the gate was designed to prevent.

The authoritative classification rules below still apply on top of
the gate:

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

When in doubt on **L1 vs L2**: re-run Q1 of the gate. If the deviation
has no concrete observable, prefer DROP. If it does, prefer L1 inline
when the landing spot is unambiguous and ≤10 min; only escalate to L2
when there is real judgment to make (multiple landing spots, new
domain rule, behavior change in future story). The historical
"humans reading the queue are cheap" framing is wrong — humans
triaging cheap items at scale is exactly how the queue becomes a
parallel feature backlog.

When in doubt on **L2 vs L3**: prefer L2 (don't block the pipeline
unless you're sure the deviation contradicts an already-shipped
behavior or a `delivery/business/` rule).

---

## Idempotency and re-runs

`/bmad-correct-course` MUST be idempotent. If invoked twice on the
same story (e.g., the human re-runs it after editing Post-Delivery
Notes):

- The companion `.reconcile.md` is OVERWRITTEN, not appended
- Already-applied L1 changes are NOT re-applied (detect via git diff)
- Already-queued L2 entries are NOT re-queued (detect via Q-NNN
  matching on `Source` field)
- Already-emitted L3 events are NOT re-emitted (detect via story ID
  matching in last N lines of `events.jsonl`)

A re-run is rare but legitimate — typically the result of a coder
catching a Phase 5c aggregation bug. Don't double-act.

---

## Failure handling

If `/bmad-correct-course` cannot produce a valid `## Reconciliation`
section (e.g., the `## Deviations` section is malformed and somehow
bypassed the validator hook), it MUST:

1. Write a single-line `.reconcile.md` with `<!-- RECONCILE_FAILED:
   <reason> -->` instead of the success marker
2. Emit a `reconcile_failed` event to `events.jsonl`
3. Halt — do NOT apply any L1, do NOT queue any L2, do NOT emit L3
4. Surface the failure to the human

A failed reconcile blocks epic closure exactly as a missing
`.reconcile.md` would.

---

## Things `/bmad-correct-course` MUST NOT do

- ❌ Edit code (`backend/`, `frontend/`, `infra/`) — code changes
  belong to the next coder, not to reconcile
- ❌ Edit `.claude/` (framework machinery)
- ❌ Modify the story spec file (`story-NN-<slug>.md`) at all — it is
  read-only from `/bmad-correct-course`'s perspective. All output goes
  into the companion `.reconcile.md`.
- ❌ Modify the `## Deviations` section of the companion file — that's
  Team Lead's output, immutable.
- ❌ Delete entries from the queue
- ❌ Re-classify a previously-applied L1 (the change is already in the
  doc; re-classifying breaks the audit trail)

---

## Per-epic reconciliation: `/bmad-retrospective`

When the final story in an epic moves to `✅ Done`, the human invokes
`/bmad-retrospective` on the epic. It is a separate BMad skill (not
covered by this contract — but its Kiat-context output requirements
mirror this one):

- Reads every story's `.reconcile.md`
- Reads `delivery/_queue/needs-human-review.md` for any remaining OPEN
  entries
- Force-closes every remaining OPEN entry (with human input)
- Detects cross-story patterns
- Audits doc state (verifies every L1 actually landed where claimed)
- Produces `_epic.reconcile.md` at the epic root with `<!-- EPIC_RECONCILE_DONE: ... -->`

Without `_epic.reconcile.md`, the epic CANNOT close. See
[`reconciliation-protocol.md`](reconciliation-protocol.md) §"The
`_epic.reconcile.md` schema" for the canonical structure.

---

## Related

- [`reconciliation-protocol.md`](reconciliation-protocol.md) — the
  authoritative protocol this contract implements a slice of
- [`metrics-events.md`](metrics-events.md) — `epic_block`,
  `reconcile_complete`, `reconcile_failed` event schemas
- [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) — Phase
  5c (aggregation), Phase 5d (`RECONCILIATION_NEEDED` notification),
  Phase 6 (reconciliation guard)
- [`../../delivery/business/README.md`](../../delivery/business/README.md) §"Review mode" —
  BMad's writing protocol; references this contract as the
  authoritative spec for what `/bmad-correct-course` must produce in
  Kiat context.
