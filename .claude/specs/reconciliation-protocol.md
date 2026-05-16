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
│  ARCHIVES the closing epic's queue entries to                        │
│    delivery/_queue/archive/epic-{N}.md (move, not copy)              │
│                                                                      │
│  Output: _epic.reconcile.md with EPIC_RECONCILE_DONE marker          │
│          + cleaned needs-human-review.md (epic-{N} entries gone)     │
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
backlog, where each closing epic spawns 30-50% of the next epic's
stories from its own reconciliation residue — and no actual user-facing
feature is delivered between cycles.

**Concrete instance from epic-08** (the trigger for this gate): at
close-out, two L2 entries (Q-051 PEP test coverage, Q-052 `sirene` →
`inpi_rne` rename residue) were proposed for human triage, with the
next planned action being a story-04a "tech-debt cleanup" — itself a
~30-min coder + reviewer pipeline cycle, producing zero user-observable
change. Compounded across N epics, this is the infinite-loop pattern.

The gate inverts the burden: **a deviation becomes L2 only if it
survives three questions in order**. Otherwise it is L1 (applied
inline, in the originating PR) or DROPPED (no entry, no trace). The
coder runs the gate at handoff, the reviewer cross-checks it at review,
`/bmad-correct-course` re-applies it during triage.

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
  for, and it should be a small fraction of all deviations.

### What survives the gate

After the gate, only deviations that are **(a) observable AND (b) > 10
min AND (c) no piggyback** become L2 queue entries. This is much
narrower than the historical default. Empirically, on the epic-08
close-out at protocol introduction, the gate routes the deviations as:

| Item | Q1 (observable?) | Q2 (>10 min?) | Q3 (piggyback?) | Outcome |
|---|---|---|---|---|
| PEP combined match test (Q-051 candidate) | Yes — silent regression in CI | No (~10 LOC) | — | **L1 inline by story-02 coder** |
| slog event names `sirene_*` → `inpi_rne_*` (Q-052 sub-1) | Yes — log dashboards filter on event name | No (~15 lines) | — | **L1 inline by story-03a coder** |
| README dir listing stale (Q-052 sub-2a) | Yes — anyone reading the README | No (~1 line) | — | **L1 inline by story-03a coder** |
| Cross-package callsite stale strings (Q-052 sub-2b) | Mixed (slog yes, comments no) | Mixed | Yes — story-03b edits some of these files | **Slog: L1 inline. Comments: piggyback note in story-03b.** |
| Venom test fixture user IDs (Q-052 sub-3) | No — internal test data, no external surface | — | — | **DROPPED** |

Net effect on this concrete queue: **zero L2 entries**, zero follow-up
cleanup story, identical or better final code state vs. the bundled
story-04a plan.

### Coder severity hint (now subordinate to the gate)

The coder is the closest observer of a deviation, so their initial
severity is taken as a hint, not as final classification.
`/bmad-correct-course` may downgrade or upgrade. Hints to use **after**
the gate has classified the deviation as L2:

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

---

## Resolution-at-handoff (the "producer-pays gate")

The severity gate above (Q1/Q2/Q3) classifies a deviation. This section
governs **who applies the L1 fix and when**. A coder, at handoff time,
may set `**Status**: RESOLVED` on a deviation when **both** conditions
hold: (a) the deviation classifies as L1 by the severity gate, and (b)
the coder has already corrected the code / test / doc inline, in the
same commit as the production code. The originating PR ships the fix;
`/bmad-correct-course` sees the entry for audit only — no further
action. The reviewer cross-checks at review-time; Team Lead Phase 5c
re-checks at aggregation. This is the **producer-pays** convention:
the agent who discovered the deviation absorbs the cost while the file
is still warm, instead of routing it through human triage.

The convention exists because routing every minor inline fix through
`/bmad-correct-course` over-burdens humans, and silently auto-resolving
high-risk items lets real drift sneak past review. The matrix below
draws the line.

### Allowed L1 categories (coder may mark RESOLVED at handoff)

- [ ] **DECISION** on a design tradeoff with no observable business impact (naming, struct layout, narrow port widening, internal helper signature)
- [ ] **BOY_SCOUT** cleanup of a stale incoherence in a file already in the diff
- [ ] **DOCS** clarification (comment, README line, spec template one-liner) that does not change observable behavior
- [ ] **AC-T## interpretation** that landed differently than literal spec text but matches the project's prior canonical convention AND did not change observable behavior (e.g., singular vs plural error envelope on a 404 path that every existing handler already returns singular)

### FORBIDDEN categories (always route through `/bmad-correct-course` — never RESOLVED at handoff)

The coder MUST set `Status: NEEDS_PROMOTION` (or `BLOCKING` for L3) and
let reconciliation triage these, even if the inline fix looks
mechanical:

- Any **RLS / Row-Level-Security** change — new policy, widened transaction scope, GUC handling, table-level RLS toggle.
- Any **security policy** change — auth path, JWT handling, CORS, secrets handling, rate-limit, audit-log gating.
- Any **business rule** change — domain invariant, pricing/scoring rule, eligibility check, anything that would update `delivery/business/business-rules.md`.
- Any **schema migration** — new column, dropped column, changed type, new index that affects query plans, new table.
- Any **cross-cutting file** change per [`cross-cutting-files.md`](cross-cutting-files.md) — registries, catalogs, dispatchers. (Cross-cutting files drive the sequential-stories rule; a silent L1 here breaks downstream stories.)
- Any **upstream API contract** change — request/response shape on a public REST endpoint, event-name change in slog (dashboards filter on these), webhook payload, exported package signature consumed by another service.

Veto is conservative on purpose. A false positive (a legitimate L1
routed through humans) costs 5 minutes of triage. A false negative (a
silent RLS auto-resolve that ships) costs an incident.

### Three verbatim examples (copied from real `.reconcile.md` files)

**Example 1 — allowed L1 (DECISION, project convention).** From
`story-01-historique-snapshots.reconcile.md`:

> **Tag**: DECISION_ENVELOPE_SINGULAR_ERROR | **Severity**: L1
> **Summary**: Story AC-T06 prescribed plural `errors: [{...}]` 404 envelope, but project-wide canonical at `internal/api/response.go` and every existing handler is singular `error: {code, message}`. Coder followed project convention.
> **File**: `backend/internal/interface/handler/search.go` (ListByCase 404 path)
> **SpecRef**: AC-T06
> **Status**: RESOLVED
> **Why**: Project consistency wins. Future story templates should reference the singular envelope. L1 candidate: update spec template (one-line).

Clean producer-pays: no observable change (same wire shape as every
other endpoint), reversible, doc-only follow-up queued separately.

**Example 2 — allowed L1 (DECISION, narrow interface widening).** From
the same file:

> **Tag**: DECISION_COUNT_AT_TIMESTAMP_ON_EXISTING_PARTYREPO | **Severity**: L1
> **Summary**: `CountAtTimestamp` added as a method on the existing `partiesdomain.PartyRepository` interface (vs. a new sibling interface). Same Bun impl, narrow surface increase.
> **File**: `backend/internal/parties/domain/repository.go`
> **SpecRef**: AC-T03
> **Status**: RESOLVED
> **Why**: Smaller blast radius than a new iface; mirrors the existing `CountByCase` shape.

Clean producer-pays: design tradeoff, no observable behavior change,
reversible.

**Example 3 — BORDERLINE: RLS-adjacent, still RESOLVED — discuss.** From
`story-02b-postgres-rls-parties-and-search-results.reconcile.md`:

> **Tag**: BC_CASCADE_AUDIT_RLS_FIX | **Severity**: L1
> **Summary**: `audit/application/list_events_by_case.go` cascade query subqueries `parties` (now RLS-protected by 017). Without GUC the `target_type='party'` branch silently drops every party.* audit event from the cascade. Fix landed in this diff: `ListEventsByCase` widened to `bun.IDB`; usecase runs both the cases pre-flight AND the cascade query inside a single WithRLSTx so the parties subquery sees the office GUC
> **File**: backend/internal/audit/application/list_events_by_case.go:177-191; ...
> **SpecRef**: AC-T07 (no regression on existing tests) — strictly out of explicit AC-T03 BC list but in-scope by the regression gate
> **Status**: RESOLVED
> **Why**: Single-tx wrap (cases pre-flight + cascade subquery in same tx) is optimal — GUC set once, applies to both. Reviewer verified cycle-1.

This one touches the RLS forbidden category on its face — the diff
adjusts a transaction scope so a subquery sees the right GUC. But it
is **not a new RLS policy and not a widening of an existing policy**:
it is a callsite-level fix that makes a regression-gated handler honor
the RLS policy that story-02a already shipped. The reviewer
differential-checked it cycle-1; Phase 5c kept it L1 because the
producer-pays condition holds (fix landed inline, reversible by
reverting the tx widening). The line: **if the diff changes a policy
or widens what data crosses a tenant boundary, route through
`/bmad-correct-course`. If the diff makes an already-shipped policy
correctly cover a previously-uncovered callsite, RESOLVED at handoff
is acceptable provided the reviewer signed off.** When in doubt,
NEEDS_PROMOTION — see veto reasoning above.

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

> **Transition note (epic-16 onwards):** The `**Tag**:` prefix is now restricted to
> the 8-value enum below. Historical `.reconcile.md` files created before epic-16 are
> NOT retroactively re-validated — the hook only runs on files touched during the
> current session (`SubagentStop`), so old free-form tags are grandfathered in place.
> New deviations from epic-16 onwards must use one of the 8 enum prefixes.

### Required fields per Deviation entry

| Field | Type | Notes |
|---|---|---|
| `Tag` | enum | `ENUM_PREFIX[_SUFFIX]` — see the prefix enum below |
**Prefix enum (8 values, exhaustive):**
- `SPEC_GAP` — the spec was unclear/wrong, coder interpreted
- `DECISION` — design tradeoff with no business impact
- `SCOPE_CUT` — scope reduced (deferred to follow-up story, AC out-of-scope)
- `BOY_SCOUT` — cleanup outside scope
- `DOMAIN_NEW` — new domain concept surfaced
- `PROCESS` — framework/protocol deviation
- `TEST_DRIFT` — test fixture/helper/pattern didn't match the spec
- `UPSTREAM_MISMATCH` — external API contract differed from spec

**Suffix**: free-form UPPER_SNAKE_CASE after the first `_` of the tag (e.g., `SPEC_GAP_DEPT_COUNT_MISMATCH`).

A tag that does not start with one of the 8 prefixes is invalid — the post-delivery hook will REJECT the `.reconcile.md` file.

Source of truth for the enum: this file. If the enum changes, update both this table and `.claude/tools/hooks/check-post-delivery-schema.sh`.

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

Append-only by `/bmad-correct-course`, force-closed and archived by
`/bmad-retrospective`, read by Team Lead at Phase 0c (scope-overlap
check) and humans (anytime). Schema and operational rules:
[`../../delivery/_queue/README.md`](../../delivery/_queue/README.md).

### Archive layout (epic-scoped)

```
delivery/_queue/
├── needs-human-review.md      ← live queue (entries from open epics only)
└── archive/
    ├── epic-00.md             ← all Q-NNN entries whose Source = "(epic-00)"
    ├── epic-01.md             ← ... epic-01 ... etc.
    └── ...
```

The live `needs-human-review.md` only ever holds entries whose owning
epic is still open. When `/bmad-retrospective` runs on epic `N`, it
**moves** every entry whose `Source` field matches `(epic-N)` —
regardless of status (`RESOLVED`, `REJECTED`, `PROMOTED`, or
force-closed `OPEN` → `RESOLVED`/`REJECTED`) — into
`delivery/_queue/archive/epic-N.md`, then deletes the same block from
the live file. The move is verbatim: heading, body, status,
`Decision`, everything. `Q-NNN` IDs continue monotonically across the
project — archived IDs are **never reused**.

This keeps the live queue scannable for humans and short for Team
Lead's Phase 0c scope-overlap scan, while preserving the full audit
trail under git-tracked archive files. Auditors read both:

- `needs-human-review.md` for "what's currently in flight"
- `archive/epic-*.md` for "what was decided in past epics"

Grep across `delivery/_queue/**/*.md` to find a Q-NNN regardless of
where it lives.

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
| **`/bmad-retrospective`** (BMad skill, **human-invoked**) | After final story `✅ Done` (notification-driven) | All `*.reconcile.md` + queue file | `_epic.reconcile.md` + queue (force-close remaining OPEN entries, then move epic-N entries to `delivery/_queue/archive/epic-N.md`) |

---

## What goes where — quick reference

| Artifact | Lives in | Written by | Read by |
|---|---|---|---|
| Coder's raw deviation report | coder handoff (transient) | coder | Team Lead Phase 5c |
| Per-story Deviations | `story-NN-<slug>.reconcile.md` §`## Deviations` | Team Lead Phase 5c | reconcile, retrospective |
| Per-story Reconciliation outcome | `story-NN-<slug>.reconcile.md` §`## Reconciliation` | `/bmad-correct-course` | retrospective, humans, Team Lead Phase 6 guard |
| L2 proposal (queued, live) | `delivery/_queue/needs-human-review.md` | `/bmad-correct-course` | Team Lead Phase 0c, retrospective, humans |
| L2 proposal (archived, closed epic) | `delivery/_queue/archive/epic-N.md` | `/bmad-retrospective` (move) | humans (audit), `git grep` |
| L3 escalation (blocking) | `delivery/metrics/events.jsonl` event `epic_block` | `/bmad-correct-course` or Team Lead Phase 0c | Team Lead pre-launch, humans |
| Per-epic reconciliation rollup | `_epic.reconcile.md` | `/bmad-retrospective` | humans, future epic planning, Team Lead Phase 6 guard |
| L1 changes (applied) | `delivery/business/*.md` or `delivery/specs/*.md` | `/bmad-correct-course` | everyone |

The story spec file (`story-NN-<slug>.md`) is **never modified** by
Phase 5c, `/bmad-correct-course`, or `/bmad-retrospective`. It carries
its own append-only `## Review Log` section (Team Lead per-cycle) — that
stays inline. The Deviations + Reconciliation pair lives entirely in the
companion file. (Historical stories may carry a `## Prod Validation`
block from before EV-0007 retired Phase 7; new stories do not.)

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
| Live queue grows unbounded across epics, becomes unscannable | retro archives the closing epic's entries to `delivery/_queue/archive/epic-N.md` after force-close — IDs preserved, never reused |
| Reconcile incorrectly applies L1 (wrong content, wrong file) | Doc-state audit at retro re-checks every claimed L1 landing |
| Reconcile output drifts from a stale schema version | Validator hook checks `POST_DELIVERY_BLOCK_BEGIN/END` markers; schema bump = protocol revision (this file) |
| Queue grows into a parallel feature backlog (each closing epic spawns 30-50% of next epic's stories from its own residue) | Producer-pays severity gate (Q1/Q2/Q3) — only observable + >10min + no-piggyback deviations become L2. Cosmetic / clarity-only / cheap-to-inline items are DROPPED, applied L1, or piggybacked on the next story to touch the file. |

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
