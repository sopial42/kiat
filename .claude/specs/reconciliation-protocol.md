# Reconciliation Protocol (Story-level + Epic-level)

> **Why this file exists.** The existing pipeline already captures coder
> deviations into `## Post-Delivery Notes` (Phase 5c) and prevents an epic
> from closing while any story has unreconciled deviations (Phase 6
> reconciliation guard). This file extends that foundation with **severity
> tiers**, a **queue mechanism**, **companion `.reconcile.md` files**, and
> **auto-promotion rules** so the pipeline self-heals between stories
> without humans bottlenecking each one.

This document is the single source of truth for:

1. The **L1 / L2 / L3 severity model** layered on top of the existing
   `AC-N | SPEC_GAP | DECISION` categories.
2. The **`.reconcile.md` companion-file format** — what BMad writes per
   story and per epic, separate from the story spec itself.
3. The **queue contract** at `delivery/_queue/needs-human-review.md` —
   write-once by reconcile, read-many by humans and the epic retro,
   force-closed at epic completion.
4. The **L2→L3 auto-promotion rule** on scope overlap that prevents
   downstream stories from inheriting silent drift.
5. **When and how** `/bmad-correct-course` (per story) and `bmad-retrospective`
   (per epic) are spawned, what they read, what they write.

If a rule about reconciliation lives somewhere else (a coder agent prompt,
a template, a CLAUDE.md), that other place is wrong — link here instead.

---

## The model in one diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  PER-STORY RECONCILE (after each Team Lead handoff, automatic)       │
│                                                                      │
│  Inputs:                                                             │
│  - story-NN.md  §Post-Delivery Notes  (validated by hook)            │
│  - delivery/business/  (read-only, for context)                      │
│  - delivery/_queue/needs-human-review.md  (write-only, append)       │
│                                                                      │
│  Triage each entry by SEVERITY:                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  L1 → APPLIES IT  (auto, reversible, low-risk)              │     │
│  │  L2 → QUEUES IT   (proposal in needs-human-review.md)       │     │
│  │  L3 → BLOCKS      (writes epic_block to events.jsonl)       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  Output: story-NN.reconcile.md  (companion file, audit trail)        │
└──────────────────────────────────────────────────────────────────────┘

         ↓     story-NN.reconcile.md exists with L1 audit + L2/L3 refs

┌──────────────────────────────────────────────────────────────────────┐
│  TEAM LEAD PRE-FLIGHT for story-(NN+1)                               │
│                                                                      │
│  Before launching the next story:                                    │
│  - Reads delivery/metrics/events.jsonl for open epic_block events    │
│  - If L3 open → REFUSES to launch until human resolves               │
│                                                                      │
│  TECH-SPEC-WRITER PHASE -1 for story-(NN+1)                          │
│                                                                      │
│  Before authoring the next story:                                    │
│  - Reads delivery/_queue/needs-human-review.md                       │
│  - For each open L2: does it overlap the new story's scope?          │
│    - YES → AUTO-PROMOTE to L3 (write epic_block, halt)               │
│    - NO  → reference it as context, proceed                          │
└──────────────────────────────────────────────────────────────────────┘

         ↓     stories accumulate, queue grows, L1s already applied

┌──────────────────────────────────────────────────────────────────────┐
│  EPIC RETROSPECTIVE (after final story merges, semi-automatic)       │
│                                                                      │
│  Inputs:                                                             │
│  - all story-NN.reconcile.md  (per-story audit trails)               │
│  - all story-NN.md §Post-Delivery Notes                              │
│  - delivery/_queue/needs-human-review.md  (full queue)               │
│                                                                      │
│  Activities:                                                         │
│  - Detect cross-story patterns (3+ identical SKILL_GAPs, etc.)       │
│  - Force-close every remaining queue entry                           │
│  - Audit doc-state: did every L1 actually land in the right doc?     │
│  - Extract process lessons                                           │
│                                                                      │
│  Output: _epic.reconcile.md  (epic-level audit + lessons)            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Categories vs severities — they are orthogonal

The existing system has three **categories** (the *what*):

| Category | Meaning |
|---|---|
| `AC-N` | Acceptance criterion N implemented differently than specified |
| `SPEC_GAP` | New concept/behavior not in spec or `delivery/business/` |
| `DECISION` | Judgment call on something the spec was silent about |

This protocol adds three **severities** (the *how to react*). Every
deviation has both: a category (what kind of thing happened) and a
severity (how reconcile should treat it).

| Severity | When | Who decides | Who acts | Blocks next story? |
|---|---|---|---|---|
| **L1 — auto-apply** | Reversible, narrow, the canonical landing spot is obvious | reconcile (mechanically) | reconcile | No |
| **L2 — propose & queue** | Judgment call, multiple candidate landing spots, or affects nothing immediately downstream | reconcile (writes proposal) | human (async) | No, unless promoted |
| **L3 — escalate & block** | Contradicts existing `delivery/business/` rule, breaks an already-shipped story, or is auto-promoted from L2 due to scope overlap | reconcile or tech-spec-writer pre-flight | human (synchronous) | **Yes — Team Lead refuses next story launch** |

The category does not determine the severity by itself. A `DECISION`
entry can be L1 (one-line addition to an existing convention), L2 (new
domain rule, multiple candidate locations), or L3 (the decision
contradicts a rule already in `delivery/business/`).

---

## The `## Post-Delivery Notes` schema (input — written by Team Lead Phase 5c)

Coders emit `Business Deviations:` blocks in their handoff (existing
contract). Team Lead aggregates them into the story's
`## Post-Delivery Notes` section. The validator hook
(`check-post-delivery-schema.sh`) enforces the schema below.

```markdown
## Post-Delivery Notes

> Aggregated by Team Lead at Phase 5c from coder handoffs. Consumed by
> /bmad-correct-course (when human invokes it) to produce story-NN.reconcile.md.

<!-- POST_DELIVERY_BLOCK_BEGIN -->
### Backend deviations

- **Tag**: AC-3 | **Severity**: L1
  **Summary**: bulk delete uses async job queue, not synchronous
  **File**: backend/internal/usecase/items/delete_bulk.go:42
  **SpecRef**: story-NN.md:74 (AC-3 line)
  **Status**: RESOLVED — coder canonicalized AC-3 inline before handoff
  **Why**: timeout above 50 items, user feedback acceptable

- **Tag**: SPEC_GAP | **Severity**: L2
  **Summary**: introduced "soft delete" for GDPR — not in glossary
  **File**: backend/internal/domain/items/item.go:18 (DeletedAt field)
  **SpecRef**: none (gap)
  **Status**: NEEDS_PROMOTION — candidate locations are
              `delivery/business/glossary.md#soft-delete` (new entry) or
              `delivery/business/business-rules.md#data-retention` (existing
              section, just add a sub-bullet)
  **Why**: GDPR Art. 17 right-to-erasure; coder kept rows for audit trail

### Frontend deviations

- _(none)_
<!-- POST_DELIVERY_BLOCK_END -->
```

If no coder reports any deviations, the section keeps its placeholder:

```markdown
## Post-Delivery Notes

_(no deviations)_
```

The placeholder form bypasses the hook — empty stories don't need a
schema check. Anything else MUST follow the bullet schema above.

### Required fields per entry

| Field | Type | Notes |
|---|---|---|
| `Tag` | enum | `AC-N` (N is the AC number) \| `SPEC_GAP` \| `DECISION` \| `OUT-OF-SCOPE` \| `SKILL_GAP` |
| `Severity` | enum | `L1` \| `L2` \| `L3` — coder's initial assessment, may be re-classified by reconcile |
| `Summary` | string | one line, no jargon — readable by a non-coder |
| `File` | string | `path:line` (or `path` if no specific line) — what was changed |
| `SpecRef` | string | `story-NN.md:line` for AC-N tags, `none` if it's a gap |
| `Status` | enum | `RESOLVED` (already applied by coder) \| `NEEDS_PROMOTION` (L2 in waiting) \| `BLOCKING` (L3) |
| `Why` | string | one or two sentences — the reason BMad Review mode needs to grade business impact |

The HTML comment markers `POST_DELIVERY_BLOCK_BEGIN/END` are **contract
markers** the validator hook and reconcile both grep for. Same convention
as `REVIEW_LOG_BLOCK_BEGIN/END`. Do not remove them.

### Severity hints for the coder

The coder is the closest observer of the deviation, so their initial
severity is taken as a hint, not as final. Reconcile may downgrade or
upgrade. Hints:

- **L1** if you fixed the spec yourself (e.g., updated AC text inline) or
  the change is a one-bullet addition to a doc that already exists.
- **L2** if you don't know which file should hold the new rule, or the
  rule could change behavior in a future story.
- **L3** if your change conflicts with something in `delivery/business/`
  or breaks behavior shipped in an earlier story.

---

## The `story-NN.reconcile.md` schema (output — written by `/bmad-correct-course`)

Companion file, one per story, written next to `story-NN.md` in the same
epic directory. Created only if Post-Delivery Notes contained at least
one entry — stories that ship as specified do not get a `.reconcile.md`.

```markdown
# Reconciliation: story-NN-<slug>

> Generated by `/bmad-correct-course` after Team Lead handoff.
> Source: [story-NN-<slug>.md](./story-NN-<slug>.md) §Post-Delivery Notes
> Generated at: <ISO-8601 UTC timestamp>

## Summary

<one paragraph — N L1 applied, N L2 queued, N L3 blocked>

## L1 — Auto-applied

| Tag | Action | Target | Verified |
|---|---|---|---|
| AC-3 | spec text canonicalized | story-NN.md:74 | ✓ |
| ... | ... | ... | ... |

_(or `_(no L1 entries)_` if none)_

## L2 — Queued for human triage

| Queue ID | Tag | Proposal | Affects | Status |
|---|---|---|---|---|
| Q-014 | SPEC_GAP | Add "soft delete" to glossary | `delivery/business/glossary.md` | OPEN |
| ... | ... | ... | ... | ... |

→ Full proposals in [`delivery/_queue/needs-human-review.md`](../../_queue/needs-human-review.md)

_(or `_(no L2 entries)_` if none)_

## L3 — Escalated, blocking

| Tag | Reason | Event | Resolution required |
|---|---|---|---|
| SPEC_GAP | RLS contract break (404 vs 401) — contradicts story-03 cache logic | `epic_block` line N of events.jsonl | human signoff before story-(NN+1) |
| ... | ... | ... | ... |

_(or `_(no L3 entries)_` if none)_

## Reconciliation outcome

- **Applied (L1)**: <count> changes
- **Queued (L2)**: <count> proposals
- **Blocked (L3)**: <count> escalations
- **Story-(NN+1) launchable**: <yes | no — see L3 above>

<!-- RECONCILE_DONE: <ISO-8601 UTC timestamp> -->
```

The trailing `RECONCILE_DONE` marker is what the **reconciliation guard**
in Team Lead Phase 6 greps for to determine "this story has been
reconciled". It replaces the old `_Reconciled by BMad on <date>_` line
that lived inside the story file — see migration notes below.

### Migration from the old marker

Older stories (pre-protocol) carry the inline marker:

```markdown
_Reconciled by BMad on 2026-04-22 — 2 items updated in delivery/business/, ..._
```

The reconciliation guard MUST accept both forms during the migration
window:

- New form: companion `story-NN.reconcile.md` exists AND contains
  `<!-- RECONCILE_DONE: ... -->`
- Legacy form: story file's `## Post-Delivery Notes` contains a line
  matching `_Reconciled by BMad on .* —`

Both count as "reconciled". The legacy form is read-only — never write
new ones — and will be removed in a future protocol revision after all
existing stories have either landed or been re-reconciled.

---

## The `_epic.reconcile.md` schema (output — written by `bmad-retrospective`)

Companion file at the epic root, generated when the epic closes.
Aggregates per-story `.reconcile.md` files into one rollup view, plus
adds the cross-story patterns and process lessons that only become
visible at epic-end.

```markdown
# Epic Retrospective: epic-NN-<slug>

> Generated by `bmad-retrospective` after the final story merge.
> Generated at: <ISO-8601 UTC timestamp>

## Story-level reconciliations

| Story | L1 applied | L2 queued | L3 blocked | Reconcile file |
|---|---|---|---|---|
| story-01 | 2 | 1 | 0 | [.reconcile.md](./story-01-...reconcile.md) |
| story-02 | 0 | 0 | 0 | _(no deviations — shipped as specified)_ |
| ... | ... | ... | ... | ... |

## Patterns detected

<one bullet per cross-story pattern. Examples:>

- **3 SKILL_GAPs for `sharp-edges`** across stories 01 / 02 / 04 →
  registry bug — either install the skill or remove from
  `available-skills.md`.
- **2 SPEC_GAPs both about Makefile evolution** → spec template should
  require an explicit "Makefile changes" section to force the writer to
  think about it upfront.

_(or `_(no cross-story patterns detected)_` if none)_

## Queue closures

| Queue ID | Decision | Outcome |
|---|---|---|
| Q-014 | ACCEPT — promote to glossary | added to `delivery/business/glossary.md#soft-delete` |
| Q-018 | REJECT | proposal too narrow, will reconsider in next epic if pattern repeats |
| ... | ... | ... |

Every L2 entry from this epic that landed in the queue MUST appear in
this table with a non-OPEN decision. Open queue items at epic-close are
a protocol violation — escalate to human, do not flip the epic to
`✅ Done`.

## Process lessons

<one bullet per lesson. Examples:>

- Tech-spec-writer should always cite `Makefile` line numbers when
  referencing build targets — story-03 spec asserted line 42 which had
  drifted to line 47 by story time.
- 45-min fix budget was hit on story-04 because reviewer issues were
  ambiguous — adopt the "concrete file:line" reviewer pattern from the
  Clerk-auth review template.

_(or `_(no new lessons — pipeline ran cleanly)_` if none)_

## Doc-state audit

<verifies that every L1 actually landed in the right place, and that
every queue closure that said "added to X" actually edited X.>

- `delivery/business/glossary.md` — confirmed: 3 entries added
  (soft-delete, audit-trail, withdrawal-window)
- `delivery/business/business-rules.md` — confirmed: rule R-12 updated
  per Q-014
- `delivery/specs/backend-conventions.md` — confirmed: WithAudit() helper
  added per Q-018

_(or `_(no doc state changes — all reconciliations were process or
spec-only)_` if none)_

<!-- EPIC_RECONCILE_DONE: <ISO-8601 UTC timestamp> -->
```

The `EPIC_RECONCILE_DONE` marker is what gates the epic flipping to
`✅ Done` (extends the existing reconciliation guard).

---

## The queue file: `delivery/_queue/needs-human-review.md`

Append-only by `/bmad-correct-course`, force-closed by `bmad-retrospective`,
read by humans and by the tech-spec-writer's Phase -1 scope-overlap
check.

```markdown
# Needs Human Review

> Append-only queue of L2 proposals from `/bmad-correct-course`. Each entry is
> closed either:
>   - by a human triage (status changes from OPEN to RESOLVED / REJECTED), or
>   - by `bmad-retrospective` at epic close (force-closed in batch), or
>   - by tech-spec-writer Phase -1 auto-promotion to L3 (status becomes PROMOTED)
>
> Entries are NEVER deleted — closed entries become the audit trail.

<!-- QUEUE_BLOCK_BEGIN -->

## Q-014 — `[OPEN]` Promote "soft delete" to glossary

- **Source**: story-NN-<slug> (epic-X)
- **Tag**: SPEC_GAP
- **Opened at**: 2026-04-25T14:30:00Z
- **Affects**: `delivery/business/glossary.md` (candidate location)
- **Affects (files)**: `backend/internal/domain/items/item.go`
- **Proposal**: add a glossary entry "soft delete" with definition
  "logical deletion (record kept for audit/RGPD) marked by `deleted_at`
  timestamp; queries filter on `deleted_at IS NULL` by default".
- **Alternative**: add as a sub-bullet under
  `delivery/business/business-rules.md#data-retention` — leaner but
  loses discoverability.
- **Recommended**: glossary entry (the term will be reused).

---

## Q-013 — `[RESOLVED]` Promote `WithAudit()` helper to backend-conventions

- **Source**: story-MM-<slug> (epic-X)
- **Tag**: DECISION
- **Opened at**: 2026-04-22T10:15:00Z
- **Closed at**: 2026-04-23T09:00:00Z (by human, via epic-X retro)
- **Decision**: ACCEPT — added to `delivery/specs/backend-conventions.md`
  §"Repository helpers" as a 5-line subsection.
- **Outcome**: future audit-logging mutations can reference the helper
  by name, no rediscovery required.

<!-- QUEUE_BLOCK_END -->
```

### Queue entry schema

| Field | Type | Notes |
|---|---|---|
| `Q-NNN` heading | string | monotonically increasing across all epics, never reused |
| `[STATUS]` in heading | enum | `OPEN` \| `RESOLVED` \| `REJECTED` \| `PROMOTED` (auto-escalated to L3) |
| `Source` | string | `story-NN-<slug> (epic-X)` |
| `Tag` | enum | same vocabulary as Post-Delivery Notes |
| `Opened at` | timestamp | ISO 8601 UTC, set by reconcile |
| `Closed at` | timestamp | set when status leaves OPEN |
| `Affects` | string | candidate landing location for the proposal (a doc path) |
| `Affects (files)` | string | source-code files mentioning the change — used by Phase -1 scope-overlap check |
| `Proposal` | prose | what the proposed change is, in two or three sentences |
| `Alternative` | prose | other reasonable landing spots reconcile considered |
| `Recommended` | prose | reconcile's pick + why |
| `Decision` (only when not OPEN) | prose | human's verdict + outcome |

`Q-NNN` IDs are monotonically allocated — `/bmad-correct-course` greps the
queue for the highest existing ID and increments. Never reuse an ID,
even after a REJECTED entry.

---

## Auto-promotion L2 → L3 (the scope-overlap rule)

The most failure-prone case in async-queue models is **silent drift**:
story-N reconcile queues an L2, story-(N+1) needs the same artifact, and
the second story's coder reinvents the pattern because the queue item is
"only a proposal".

The protection: at **Phase 0c of every new story**, **Team Lead** scans
the queue and asks one question per OPEN L2 entry:

> "Does this new story's scope overlap any of the L2's `Affects (files)`
> or `Affects` doc?"

This lives in Team Lead, not in tech-spec-writer, because:

- Team Lead runs on **every** story; tech-spec-writer only runs in Phase
  -1 (informal request or partial story). For an existing complete
  story file, tech-spec-writer is skipped — and the queue must still be
  scanned.
- By Phase 0c, the story file is finalized on disk regardless of whether
  Phase -1 ran. Team Lead already loaded it at Phase 0a for diff-check.
- The scan is mechanical (grep + path-prefix comparison), no creative
  judgment required. Spawning a sub-agent for it is unnecessary
  overhead.

| Answer | Action |
|---|---|
| No | Proceed to Phase 0b. |
| Yes (overlap) | **AUTO-PROMOTE** the L2 to L3 — change queue status to `PROMOTED`, write an `epic_block` event to `events.jsonl` citing the queue ID with `source: "kiat-team-lead"`. Flip the story to `🛑 Blocked` and escalate to the user. |

This makes L2 effectively "**async unless it would silently corrupt the
next story, in which case it auto-becomes L3**". Humans aren't blocking
each story, but they are forced to triage before the queue can poison
work.

Team Lead's audit line on every Phase 0c:

```
Queue scope-overlap check: 3 OPEN L2 entries reviewed, 0 overlaps with story-NN scope ✓
```

or

```
Queue scope-overlap check: 3 OPEN L2 entries reviewed, 1 overlap (Q-014 affects backend/internal/domain/items, story-NN touches that package) → AUTO-PROMOTED to L3 ❌ — REFUSED to launch story-NN
```

---

## When does each component run?

| Component | Triggered by | Reads | Writes |
|---|---|---|---|
| **Validator hook** (`check-post-delivery-schema.sh`) | `SubagentStop` for `kiat-team-lead` | Story file's `## Post-Delivery Notes` section | nothing — exit 0 (pass) or 2 (block) |
| **`/bmad-correct-course`** (BMad skill, **human-invoked** after Team Lead emits `RECONCILIATION_NEEDED`) | When human runs `/bmad-correct-course` on a story with deviations (typically right after Team Lead's Phase 5d notification) | Story `## Post-Delivery Notes` + queue (read-only context) + `delivery/business/` (read-only context) | `story-NN.reconcile.md` + queue (append L2) + `events.jsonl` (epic_block for L3) + `delivery/business/` or `delivery/specs/` (apply L1) |
| **Team Lead pre-launch L3 check** | Phase 0 (first thing) for every new story | `events.jsonl` (search for unresolved `epic_block`) | nothing — refuses to launch on hit |
| **Team Lead queue scope-overlap check** | Phase 0c (after spec diff-check, before context budget) for every new story | Queue file + the new story's scope | nothing if no overlap; queue (status → PROMOTED) + `events.jsonl` (epic_block) on overlap |
| **`bmad-retrospective`** | Triggered after final story `✅ Done` (notification-driven, not auto) | All `*.reconcile.md` + queue file + Post-Delivery Notes | `_epic.reconcile.md` + queue (force-close remaining OPEN entries) |

---

## What goes where — quick reference

| Artifact | Lives in | Written by | Read by |
|---|---|---|---|
| Coder's raw deviation report | story file `## Post-Delivery Notes` | Team Lead Phase 5c | reconcile |
| Per-story reconciliation outcome | `story-NN.reconcile.md` | reconcile | retrospective, humans |
| L2 proposal (queued) | `delivery/_queue/needs-human-review.md` | reconcile | tech-spec-writer (Phase -1), retrospective, humans |
| L3 escalation (blocking) | `delivery/metrics/events.jsonl` event `epic_block` | reconcile or tech-spec-writer | Team Lead pre-launch, humans |
| Per-epic reconciliation rollup | `_epic.reconcile.md` | retrospective | humans, future epic planning |
| L1 changes (applied) | `delivery/business/*.md` or `delivery/specs/*.md` | reconcile | everyone |

---

## Failure modes and how this protocol guards against them

| Failure mode | Guard |
|---|---|
| Coder deviation buried in PR description, never reaches business layer | Phase 5c forces aggregation into `## Post-Delivery Notes`; hook validates schema |
| Post-Delivery Notes well-formed but no one acts on it | reconcile spawns automatically per story (not "when the human remembers") |
| Reconcile applies L1 changes silently, human never sees | every `.reconcile.md` is git-tracked and surfaces in PR diff |
| L2 proposal queued and forgotten, next story rebuilds the same thing | Phase -1 queue scan catches scope overlap and auto-promotes to L3 |
| L3 in queue but Team Lead launches anyway | Team Lead pre-launch reads `events.jsonl` for open `epic_block` events and refuses |
| Epic closes with proposals still OPEN | reconciliation guard (extended) requires `EPIC_RECONCILE_DONE` marker, retro must force-close every OPEN entry |
| Reconcile incorrectly applies L1 (wrong content, wrong file) | Doc-state audit at retro re-checks every claimed L1 landing |
| Reconcile output drifts from a stale schema version | Validator hook checks `POST_DELIVERY_BLOCK_BEGIN/END` markers; reconcile schema bump = protocol revision (this file) |

---

## Related files

- [`bmad-reconcile-contract.md`](bmad-reconcile-contract.md) — the
  contract BMad's reconcile mode must honor (inputs, outputs, escalation
  rules). Implementation lives in BMad-land; the contract lives here.
- [`metrics-events.md`](metrics-events.md) — defines `epic_block` and
  `reconcile_complete` event shapes.
- [`available-skills.md`](available-skills.md) — registry the
  tech-spec-writer scans alongside the queue.
- [`../../delivery/epics/README.md`](../../delivery/epics/README.md) —
  the project-side contract for the two-layer story model + Post-Delivery
  Notes section.
- [`../../delivery/business/README.md`](../../delivery/business/README.md) —
  BMad's writing protocol; the Review-mode section pre-dates this
  protocol and describes the inline-marker form (now superseded by
  `.reconcile.md` companion files; both forms accepted during migration).
- [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) — Phase 5c
  (aggregation), Phase 6 (reconciliation guard, extended here).
- [`../agents/kiat-tech-spec-writer.md`](../agents/kiat-tech-spec-writer.md) —
  Phase -1 queue scan rule.
- [`../tools/hooks/check-post-delivery-schema.sh`](../tools/hooks/check-post-delivery-schema.sh) —
  validator hook on Team Lead `SubagentStop`.
