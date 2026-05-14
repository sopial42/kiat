# Reconciliation Protocol (Story-level + Epic-level)

> **Why this file exists.** The existing pipeline already captures coder
> deviations after Phase 5c and prevents an epic from closing while any
> story has unreconciled deviations (Phase 6 reconciliation guard). This
> file extends that foundation with **severity tiers**, a **queue
> mechanism**, **companion `.reconcile.md` files** (holding both
> deviations and reconciliation in one place), and **auto-promotion
> rules** so the pipeline self-heals between stories without humans
> bottlenecking each one.

This document is the single source of truth for:

1. The **L1 / L2 / L3 severity model** layered on top of the existing
   `AC-N | SPEC_GAP | DECISION` deviation tags.
2. The **`.reconcile.md` companion-file format** — contains BOTH
   deviations (Team Lead Phase 5c) AND reconciliation outcome
   (`/bmad-correct-course`). The story spec file stays untouched.
3. The **queue contract** at `delivery/_queue/needs-human-review.md` —
   write-once by reconcile, read-many by humans and the epic retro,
   force-closed at epic completion.
4. The **L2→L3 auto-promotion rule** on scope overlap that prevents
   downstream stories from inheriting silent drift.
5. **When and how** `/bmad-correct-course` (per story) and
   `/bmad-retrospective` (per epic) are invoked, what they read, what
   they write.

If a rule about reconciliation lives somewhere else (a coder agent
prompt, a template, a CLAUDE.md), that other place is wrong — link
here instead.

---

## File model: spec stays separate from deviations + reconciliation

```
delivery/epics/epic-X/
├── _epic.md                              ← spec (Business Context + tech)
├── _epic.reconcile.md                    ← epic-level retro outcome
│                                            (created by /bmad-retrospective)
├── story-NN-<slug>.md                    ← spec (read-only after Phase 0)
└── story-NN-<slug>.reconcile.md          ← deviations + reconciliation
                                            (created by Team Lead Phase 5c
                                             only when deviations exist;
                                             updated by /bmad-correct-course)
```

**Two files per story when deviations occur**: spec stays focused, and
the companion file holds the entire "what happened beyond the spec"
narrative — the coder's deviations AND BMad's triage outcome — in one
place. Symmetric to `_epic.md` ↔ `_epic.reconcile.md` at epic level.

**No companion file when the story shipped as specified.** Its absence
is the signal "no deviations, nothing to reconcile". The story file
itself never carries a Post-Delivery Notes section in the new model.

---

## The model in one diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  TEAM LEAD PHASE 5c (after coders + reviewers all APPROVED)          │
│                                                                      │
│  Read each coder's `Business Deviations:` block                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  IF all NONE  → no .reconcile.md, audit "shipped as spec"   │     │
│  │  IF any       → CREATE story-NN-<slug>.reconcile.md with    │     │
│  │                 ## Deviations section (validator hook fires)│     │
│  └─────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘

         ↓     story-NN.reconcile.md exists with ## Deviations populated

┌──────────────────────────────────────────────────────────────────────┐
│  TEAM LEAD PHASE 5d                                                  │
│                                                                      │
│  IF .reconcile.md exists → emit RECONCILIATION_NEEDED notification   │
│  ELSE                    → skip                                      │
└──────────────────────────────────────────────────────────────────────┘

         ↓     human invokes /bmad-correct-course on the story

┌──────────────────────────────────────────────────────────────────────┐
│  /bmad-correct-course (BMad existing skill, Kiat-context contract)   │
│                                                                      │
│  Reads story-NN.reconcile.md §Deviations                             │
│  Triages each entry by SEVERITY:                                     │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  L1 → APPLIES IT  (auto, reversible, low-risk)              │     │
│  │  L2 → QUEUES IT   (proposal in needs-human-review.md)       │     │
│  │  L3 → BLOCKS      (writes epic_block to events.jsonl)       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  APPENDS ## Reconciliation section to the SAME .reconcile.md          │
│  Ends with <!-- RECONCILE_DONE: <ts> --> marker                       │
└──────────────────────────────────────────────────────────────────────┘

         ↓     story-NN.reconcile.md now has BOTH ## Deviations AND
               ## Reconciliation, with RECONCILE_DONE marker

┌──────────────────────────────────────────────────────────────────────┐
│  TEAM LEAD PRE-FLIGHT for story-(NN+1)                               │
│                                                                      │
│  Phase 0:  reads events.jsonl for unresolved epic_block (L3)         │
│            → REFUSES to launch on hit                                 │
│  Phase 0c: reads queue for OPEN L2, checks scope overlap             │
│            → AUTO-PROMOTES to L3 on hit, then refuses                │
└──────────────────────────────────────────────────────────────────────┘

         ↓     stories accumulate, queue grows, L1s already applied

┌──────────────────────────────────────────────────────────────────────┐
│  EPIC RETROSPECTIVE (after final story merges, human-invoked)        │
│                                                                      │
│  /bmad-retrospective reads:                                          │
│  - all story-NN.reconcile.md files                                   │
│  - delivery/_queue/needs-human-review.md (full queue)                │
│                                                                      │
│  Force-closes every remaining OPEN queue entry                       │
│  Detects cross-story patterns                                        │
│  Audits doc state (every L1 actually landed?)                        │
│                                                                      │
│  Output: _epic.reconcile.md with EPIC_RECONCILE_DONE marker          │
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
| **L3 — escalate & block** | Contradicts existing `delivery/business/` rule, breaks an already-shipped story, or is auto-promoted from L2 due to scope overlap | reconcile or Team Lead Phase 0c | human (synchronous) | **Yes — Team Lead refuses next story launch** |

The category does not determine the severity by itself. A `DECISION`
entry can be L1 (one-line addition to an existing convention), L2 (new
domain rule, multiple candidate locations), or L3 (the decision
contradicts a rule already in `delivery/business/`).

---

## The producer-pays severity gate (apply BEFORE writing any L2 entry)

The biggest failure mode of any async-queue model is **frictionless
production / expensive consumption**: producers (coders during
reconciliation) emit entries at zero cost; consumers (humans triaging,
future Team Lead pipelines drafting cleanup stories) pay the full
cost. Left unchecked, this turns the queue into a parallel feature
backlog, where each closing epic spawns a significant fraction of the
next epic's stories from its own reconciliation residue — and no
actual user-facing feature is delivered between cycles.

**Pattern signature**: at epic close-out, you observe N small L2
entries (a missing test case, residual naming after a rename, a stale
README listing, comment cleanup). The "obvious" next move is to bundle
them into a "tech-debt cleanup" story for the next epic. That story is
itself a full pipeline cycle (coder + reviewer + rollup) that produces
zero user-observable change. Compounded across N epics, this is the
infinite-loop pattern Kiat must prevent at the source.

The gate inverts the burden: **a deviation becomes L2 only if it
survives three questions in order**. Otherwise it is L1 (applied
inline, in the originating PR) or DROPPED (no entry, no trace). The
coder runs the gate at handoff, the reviewer cross-checks it at review,
`/bmad-correct-course` re-applies it during triage. Three layers of
defense, no new framework machinery — the existing review cycle is
the enforcement layer.

### Q1 — Observable

> Would a user (the project's primary persona), an operator reading
> prod logs / dashboards / metrics, or an automated system (CI test,
> security scanner, monitoring alert) **observe a different state** if
> this deviation were never addressed?

"Observable" means appears in: a UI / API response, a log line, a
dashboard panel, a metric, a test failure, a security scanner output, a
public contract. **It explicitly does NOT mean** "a future maintainer
reading the code might be confused" — admitting that route re-opens the
floodgates and is out of scope for this gate.

- **Yes** → continue to Q2.
- **No** → **DROPPED**. No entry written. If the deviation later
  acquires observability (someone hits the bug, a log appears, a
  contract changes), it can be raised at that moment; it is not lost
  forever, just not actively tracked.

### Q2 — Cost to apply now

> Is the fix more than ~10 minutes of combined coder + reviewer work?

The 10-minute threshold is a Schelling point, not a precise budget. A
new test of <20 LOC, a sub-30-line rename, a one-bullet doc addition
all sit comfortably below. A new domain rule with multiple candidate
locations, a cross-cutting refactor, anything requiring spec rewrites
sits comfortably above.

- **No** (≤ 10 min) → **L1 inline**. The originating PR includes the
  fix. No queue entry, no separate story, no follow-up cycle. Producer
  absorbs the cost in the same context where it was discovered, while
  the file is still warm.
- **Yes** (> 10 min) → continue to Q3.

### Q3 — Boy Scout opportunity

> Does any in-flight or near-term planned story (within ~30 days, i.e.
> visible in the current epic's `## Stories` list or the next epic's)
> naturally edit one of the same files?

The Boy Scout rule: **if you touch a file, you clean what's broken in
it**. This is what prevents "DROPPED today" from compounding into
"rename-hell tomorrow". A cosmetic incoherence in a file that someone
will open next sprint, for unrelated reasons, gets fixed naturally as
part of that sprint's work — without ever entering the queue. The
original incoherence is not lost: it is delegated to the next coder
who has independent reason to be in that file.

- **Yes** → **piggyback**. Append a one-line note to that future
  story's `## Notes` section pointing to the deviation (file + what to
  fix while-here). No queue entry. The coder of that story applies it
  in their PR as part of normal work.
- **No** → **L2 (queue)**. The deviation is observable, expensive, and
  has no natural cleanup vector. This is exactly what the queue is
  for, and it should be a small fraction of all deviations — not the
  default landing zone.

### What survives the gate (worked examples)

After the gate, only deviations that are **(a) observable AND (b) > 10
min AND (c) no piggyback** become L2 queue entries. This is much
narrower than the historical default. Worked examples on the kind of
deviations the gate routes:

| Deviation example | Q1 (observable?) | Q2 (>10 min?) | Q3 (piggyback?) | Outcome |
|---|---|---|---|---|
| Missing test for a code path | Yes (silent regression risk in CI) | Usually No (~10-20 LOC) | — | **L1 inline** by the originating coder |
| Log event names misaligned with package after a rename | Yes (dashboards filter on event name) | Usually No (~few lines per file) | — | **L1 inline** in the rename PR |
| README dir listing stale after a rename | Yes (any reader of the README) | No (~1 line) | — | **L1 inline** in the rename PR |
| Stale identifier strings in callsites across other packages | Mixed (slog yes, comments no) | Mixed | Often Yes (next story may edit some files) | **Slog: L1 inline. Comments: piggyback note** in next story |
| Internal test fixture identifiers (no external surface) | No (zero observability — test data names) | — | — | **DROPPED** |
| New domain concept introduced in code, not in glossary | Yes (next coder won't know the rule) | Usually Yes (multiple candidate landing spots in `delivery/business/`) | Probably No | **L2 queued** for human triage |
| Architectural choice that contradicts an existing `delivery/business/` rule | Yes | (irrelevant) | (irrelevant) | **L3 — block** regardless of gate |

**The rule of thumb**: most deviations should NOT become L2 queue
entries. If your queue is filling with cosmetic-naming, missing-test,
or doc-staleness items, the gate is being misapplied at the producer
side and should be re-tightened.

### Coder severity hint (now subordinate to the gate)

The coder is the closest observer of a deviation, so their initial
severity is taken as a hint, not as final classification.
`/bmad-correct-course` may downgrade or upgrade. Hints to use **after**
the gate has classified the deviation:

- **L2** is the default for what survives the gate (observable + >10
  min + no piggyback).
- **L3** if your change conflicts with something in `delivery/business/`
  or breaks behavior already shipped in an earlier story — **regardless
  of the gate's other answers**. L3 dominates: a contradiction with the
  business layer is always blocking, even if it's "only" 5 lines.
- **L1** is reserved for the gate's Q2-No path (≤10 min, applied
  inline by the originating coder). After the gate, an L1 deviation
  has already been resolved by the time the deviation block is
  written; the entry exists for audit, not for action.

### Gate failure modes and how the review cycle catches them

Two ways the gate can be misused, both controllable by reviewer
discipline (no new framework machinery needed — the existing review
cycle is the enforcement layer):

1. **Permissive Q1** — coder rationalizes "a future reader might be
   confused" as observable. Reviewer pushes back: observable means a
   concrete surface (log, UI, metric, test). Maintainer cognitive load
   is not in scope. The reviewer's `kiat-review-*` skill should flag
   any L2 entry whose Q1 justification reads as "for clarity" or
   "for future maintenance" without naming a concrete observable.
2. **Inflated Q2** — coder declares "this is 11 minutes" to push work
   to L2 instead of doing it inline. Reviewer override: if the diff is
   mechanical and bounded, it goes inline regardless of the estimate.

Neither failure mode is unique to this gate — they are general
code-review discipline. The gate adds no new attack surface; it just
narrows the default landing zone for deviations.

### What the gate explicitly does NOT do (anti-overreach)

This gate is the minimal change that closes the producer/consumer
asymmetry. It does NOT introduce:

- A separate "polish backlog" file (would split attention without
  closing the leak at the source).
- A cap on queue size (treats the symptom, not the cause).
- A ban on cleanup-only stories (the gate already prevents most of
  them by routing items to L1/piggyback/DROPPED before they can
  aggregate into a story).
- Auto-expiration of OPEN queue entries (the existing
  `/bmad-retrospective` force-close at epic end already handles
  abandoned items).

Any of these may become useful later if observed gate misapplication
persists across multiple epics — but adding them preemptively is
YAGNI on framework machinery. Re-evaluate after one quarter of usage.

---

## The `story-NN-<slug>.reconcile.md` schema (one file, two sections)

Created by **Team Lead at Phase 5c** (Deviations section) and updated by
**`/bmad-correct-course`** (Reconciliation section). Lives next to the
story spec file in the same epic directory. Created **only when at
least one coder reported a deviation** — stories that ship as
specified do NOT get a `.reconcile.md`.

Canonical template:
[`../../delivery/epics/epic-template/story-NN-slug.reconcile.md`](../../delivery/epics/epic-template/story-NN-slug.reconcile.md).

```markdown
# Deviations & Reconciliation: story-NN-<slug>

> Companion to [story-NN-<slug>.md](./story-NN-<slug>.md). Created by
> Team Lead Phase 5c (Deviations section), updated by
> `/bmad-correct-course` (Reconciliation section). The story spec file
> itself stays untouched.
>
> Schema and protocol authoritative source:
> [`../../../.claude/specs/reconciliation-protocol.md`](../../../.claude/specs/reconciliation-protocol.md).
>
> Created at: <ISO-8601 UTC timestamp>

---

## Deviations

> Aggregated by Team Lead at Phase 5c from each coder's `Business
> Deviations:` handoff block. Validated by
> `.claude/tools/hooks/check-post-delivery-schema.sh` on Team Lead
> SubagentStop. Consumed by `/bmad-correct-course` (per story) and
> `/bmad-retrospective` (per epic).

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

---

## Reconciliation

> Filled by `/bmad-correct-course` when the human invokes it. Until
> filled, this section contains the placeholder `_(awaiting
> reconciliation — run /bmad-correct-course)_`.

### L1 — Auto-applied

| Tag | Action | Target | Verified |
|---|---|---|---|
| AC-3 | spec text canonicalized | story-NN.md:74 | ✓ |
| ... | ... | ... | ... |

_(or `_(no L1 entries)_` if reconcile applied nothing automatically)_

### L2 — Queued for human triage

| Queue ID | Tag | Proposal (one-liner) | Affects | Status |
|---|---|---|---|---|
| Q-014 | SPEC_GAP | Add "soft delete" to glossary | `delivery/business/glossary.md` | OPEN |
| ... | ... | ... | ... | ... |

→ Full proposals in [`../../_queue/needs-human-review.md`](../../_queue/needs-human-review.md)

_(or `_(no L2 entries)_` if no proposals queued)_

### L3 — Escalated, blocking

| Tag | Reason | Event reference | Resolution required |
|---|---|---|---|
| <tag> | <why this blocks the next story> | `epic_block` line N of `delivery/metrics/events.jsonl` | <what the human must do> |
| ... | ... | ... | ... |

_(or `_(no L3 entries)_` if reconcile produced no blockers)_

### Outcome

- **Applied (L1)**: <count> changes
- **Queued (L2)**: <count> proposals
- **Blocked (L3)**: <count> escalations
- **Story-(NN+1) launchable**: <yes | no — see L3 above>

<!-- RECONCILE_DONE: <ISO-8601 UTC timestamp> -->
```

### Required fields per Deviation entry

| Field | Type | Notes |
|---|---|---|
| `Tag` | enum | `AC-N` (N is the AC number) \| `SPEC_GAP` \| `DECISION` \| `OUT-OF-SCOPE` \| `SKILL_GAP` |
| `Severity` | enum | `L1` \| `L2` \| `L3` — coder's initial assessment, may be re-classified by reconcile |
| `Summary` | string | one line, no jargon — readable by a non-coder |
| `File` | string | `path:line` (or `path` if no specific line) — what was changed |
| `SpecRef` | string | `story-NN.md:line` for AC-N tags, `none` if it's a gap |
| `Status` | enum | `RESOLVED` (already applied by coder) \| `NEEDS_PROMOTION` (L2 in waiting) \| `BLOCKING` (L3) |
| `Why` | string | one or two sentences — the reason BMad needs to grade business impact |

The HTML comment markers `POST_DELIVERY_BLOCK_BEGIN/END` are **contract
markers** the validator hook and `/bmad-correct-course` both grep for.
The `RECONCILE_DONE` marker is what Team Lead's reconciliation guard at
Phase 6 greps for to determine "this story has been fully reconciled".

### Severity hints for the coder

Severity is decided by the **producer-pays gate** (see section above).
Run Q1/Q2/Q3 first; that gate determines whether the deviation is
DROPPED, L1 inline, piggybacked on a future story, or L2 queued. Use
the "Coder severity hint" sub-block of the gate section for the L1/L2/L3
naming convention once the gate has classified the deviation.

### Migration from the old inline marker

Older stories (pre-protocol) carry an inline marker INSIDE the story
file's `## Post-Delivery Notes` section:

```markdown
_Reconciled by BMad on 2026-04-22 — 2 items updated in delivery/business/, ..._
```

The reconciliation guard MUST accept both forms during the migration
window:

- **New form**: companion `story-NN.reconcile.md` exists AND contains
  `<!-- RECONCILE_DONE: ... -->`
- **Legacy form**: story file has `## Post-Delivery Notes` containing a
  line matching `_Reconciled by BMad on .* —`

Both count as "reconciled". The legacy form is read-only — never write
new ones — and will be removed in a future protocol revision after all
existing stories have either landed or been re-reconciled.

---

## The `_epic.reconcile.md` schema (output — written by `/bmad-retrospective`)

Companion file at the epic root, generated when the epic closes.
Aggregates per-story `.reconcile.md` files into one rollup view, plus
adds the cross-story patterns and process lessons that only become
visible at epic-end. Canonical template:
[`../../delivery/epics/epic-template/_epic.reconcile.md`](../../delivery/epics/epic-template/_epic.reconcile.md).

The epic-level companion ends with `<!-- EPIC_RECONCILE_DONE: ... -->`,
which gates the epic flipping to `✅ Done` (extends the existing
reconciliation guard).

---

## The queue file: `delivery/_queue/needs-human-review.md`

Append-only by `/bmad-correct-course`, force-closed by
`/bmad-retrospective`, read by Team Lead at Phase 0c (scope-overlap
check) and humans (anytime). Schema and operational rules:
[`../../delivery/_queue/README.md`](../../delivery/_queue/README.md).

### Queue entry schema

```markdown
## Q-NNN — `[OPEN]` <one-line title>

- **Source**: story-NN-<slug> (epic-X)
- **Tag**: SPEC_GAP
- **Opened at**: <ISO-8601 UTC>
- **Affects**: `delivery/business/glossary.md` (candidate doc)
- **Affects (files)**: `backend/internal/domain/items/item.go`
- **Proposal**: <2-3 sentences>
- **Alternative**: <other reasonable landing spots>
- **Recommended**: <reconcile's pick + why>
```

`Q-NNN` IDs are monotonically allocated — `/bmad-correct-course` greps
the queue for the highest existing ID and increments. Never reuse an
ID, even after a REJECTED entry.

| Status | Meaning |
|---|---|
| `[OPEN]` | Awaiting human triage |
| `[RESOLVED]` | Human accepted, action taken |
| `[REJECTED]` | Human declined |
| `[PROMOTED]` | Auto-escalated to L3 by Team Lead Phase 0c (scope overlap) |

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
| Yes (overlap) | **AUTO-PROMOTE** the L2 to L3 — change queue status to `[PROMOTED]`, write an `epic_block` event to `events.jsonl` citing the queue ID with `source: "kiat-team-lead"`. Flip the story to `🛑 Blocked` and escalate to the user. |

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
| **Team Lead Phase 5c** (Deviations aggregator) | After Phase 5b (pitfall capture), before Phase 5d (notification) | Each coder's `Business Deviations:` handoff block | If any deviations: creates `story-NN-<slug>.reconcile.md` with `## Deviations` section. If all NONE: nothing. |
| **Validator hook** (`check-post-delivery-schema.sh`) | `SubagentStop` for `kiat-team-lead` | Any `.reconcile.md` modified during the run | nothing — exit 0 (pass) or 2 (block) |
| **Team Lead Phase 5d** (notification) | After Phase 5c (only if .reconcile.md was created) | nothing | `RECONCILIATION_NEEDED:` notification block in Team Lead's output |
| **`/bmad-correct-course`** (BMad skill, **human-invoked**) | When human runs `/bmad-correct-course` on a story with a `.reconcile.md` | Companion `.reconcile.md` §Deviations + queue + `delivery/business/` (read-only) | Same `.reconcile.md` (appends `## Reconciliation` section + `RECONCILE_DONE`) + queue (append L2) + `events.jsonl` (epic_block for L3) + `delivery/business/` or `delivery/specs/` (apply L1) |
| **Team Lead Phase 0** (pre-launch L3 check) | First thing for every new story | `events.jsonl` (search for unresolved `epic_block`) | nothing — refuses to launch on hit |
| **Team Lead Phase 0c** (queue scope-overlap check) | After spec diff-check, before context budget | Queue file + new story's scope | nothing if no overlap; queue (status → `PROMOTED`) + `events.jsonl` (epic_block) on overlap |
| **Team Lead Phase 6** (reconciliation guard) | Before flipping epic to `✅ Done` | Every story's `.reconcile.md` (or legacy inline marker) + `_epic.reconcile.md` | nothing — refuses epic close on missing markers |
| **`/bmad-retrospective`** (BMad skill, **human-invoked**) | After final story `✅ Done` (notification-driven) | All `*.reconcile.md` + queue file | `_epic.reconcile.md` + queue (force-close remaining OPEN entries) |

---

## What goes where — quick reference

| Artifact | Lives in | Written by | Read by |
|---|---|---|---|
| Coder's raw deviation report | coder handoff (transient) | coder | Team Lead Phase 5c |
| Per-story Deviations | `story-NN-<slug>.reconcile.md` §`## Deviations` | Team Lead Phase 5c | reconcile, retrospective |
| Per-story Reconciliation outcome | `story-NN-<slug>.reconcile.md` §`## Reconciliation` | `/bmad-correct-course` | retrospective, humans, Team Lead Phase 6 guard |
| L2 proposal (queued) | `delivery/_queue/needs-human-review.md` | `/bmad-correct-course` | Team Lead Phase 0c, retrospective, humans |
| L3 escalation (blocking) | `delivery/metrics/events.jsonl` event `epic_block` | `/bmad-correct-course` or Team Lead Phase 0c | Team Lead pre-launch, humans |
| Per-epic reconciliation rollup | `_epic.reconcile.md` | `/bmad-retrospective` | humans, future epic planning, Team Lead Phase 6 guard |
| L1 changes (applied) | `delivery/business/*.md` or `delivery/specs/*.md` | `/bmad-correct-course` | everyone |

The story spec file (`story-NN-<slug>.md`) is **never modified** by
Phase 5c, `/bmad-correct-course`, or `/bmad-retrospective`. It carries
its own append-only `## Review Log` section (Team Lead per-cycle) and
`## Prod Validation` section (Team Lead Phase 7) — those stay inline.
The Deviations + Reconciliation pair lives entirely in the companion
file.

---

## Failure modes and how this protocol guards against them

| Failure mode | Guard |
|---|---|
| Coder deviation buried in PR description, never reaches business layer | Phase 5c forces aggregation into `.reconcile.md` `## Deviations`; hook validates schema |
| `.reconcile.md` exists but no one acts on it | Team Lead Phase 5d emits `RECONCILIATION_NEEDED:` notification; reconciliation guard at Phase 6 refuses epic close |
| Reconcile applies L1 changes silently, human never sees | every `.reconcile.md` is git-tracked and surfaces in PR diff |
| L2 proposal queued and forgotten, next story rebuilds the same thing | Team Lead Phase 0c queue scan catches scope overlap and auto-promotes to L3 |
| L3 in queue but Team Lead launches anyway | Team Lead pre-launch Phase 0 reads `events.jsonl` for open `epic_block` events and refuses |
| Epic closes with proposals still OPEN | reconciliation guard requires `EPIC_RECONCILE_DONE` marker, retro must force-close every OPEN entry |
| Reconcile incorrectly applies L1 (wrong content, wrong file) | Doc-state audit at retro re-checks every claimed L1 landing |
| Reconcile output drifts from a stale schema version | Validator hook checks `POST_DELIVERY_BLOCK_BEGIN/END` markers; schema bump = protocol revision (this file) |
| Queue grows into a parallel feature backlog (each closing epic spawns a significant fraction of next epic's stories from its own residue) | Producer-pays severity gate (Q1/Q2/Q3) — only observable + >10min + no-piggyback deviations become L2. Cosmetic / clarity-only / cheap-to-inline items are DROPPED, applied L1, or piggybacked on the next story to touch the file. |

---

## Related files

- [`bmad-reconcile-contract.md`](bmad-reconcile-contract.md) — the
  contract `/bmad-correct-course` must honor when used in Kiat context
  (inputs, outputs, escalation rules).
- [`metrics-events.md`](metrics-events.md) — defines `epic_block`,
  `epic_unblock`, `reconcile_complete`, `reconcile_failed` event
  shapes.
- [`available-skills.md`](available-skills.md) — registry the
  tech-spec-writer scans during Phase -1 spec authoring.
- [`../../delivery/epics/README.md`](../../delivery/epics/README.md) —
  the project-side contract for the two-layer story model + the
  companion `.reconcile.md` file.
- [`../../delivery/business/README.md`](../../delivery/business/README.md) —
  BMad's writing protocol; Review-mode section references this protocol
  as the authoritative spec.
- [`../agents/kiat-team-lead.md`](../agents/kiat-team-lead.md) — Phase
  5c (creates `.reconcile.md` Deviations section), Phase 5d
  (notification), Phase 6 (reconciliation guard).
- [`../tools/hooks/check-post-delivery-schema.sh`](../tools/hooks/check-post-delivery-schema.sh) —
  validator hook on Team Lead `SubagentStop`, targets `.reconcile.md`
  files.
