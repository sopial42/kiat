---
name: kiat-seed-project-memory
description: >
  After BMad produces an architecture document (typically via
  bmad-create-architecture), extract the cross-story technical decisions and
  propose them as structured entries for delivery/specs/project-memory.md.
  Bridges the BMad→Kiat handoff for greenfield projects where coders would
  otherwise have to rediscover decisions already documented upstream. Use this
  once after the architecture phase completes, or retroactively on an existing
  project that has an architecture document but an empty project-memory.md.
  Re-runnable when the architecture is amended: detects existing entries by ID
  and proposes updates or supersession entries rather than duplicating. Always
  runs in propose-then-confirm mode — no autonomous writes.
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Seed Project Memory from BMad Architecture

## Why this skill exists

`delivery/specs/project-memory.md` is the only cross-story coherence mechanism in Kiat — `kiat-tech-spec-writer` reads it at the start of every new story, and the backend/frontend coders read it when their story touches an area that may have established patterns. Its template assumes the file fills **organically**: "Who writes: you (the human), manually, after each PASSED story." That assumption holds when the project's architecture emerges story-by-story.

For **greenfield projects with a pre-decided architecture**, the assumption breaks. BMad's `bmad-create-architecture` produces a comprehensive document (typically at `_bmad-output/planning-artifacts/architecture.md` or equivalent) full of decisions every story must respect — choice of calc engine, data isolation regime, auth posture at M1, sync direction with external systems, canonical endpoint names, project-specific naming. These decisions are cross-story by definition, but they live in BMad's output folder, which Kiat agents do not read. Without a deliberate handoff, the tech-spec-writer rediscovers (badly) what's already decided, the coders implement inconsistently, and `/bmad-correct-course` mops up the drift one story at a time.

This skill is the deliberate handoff. The human runs it once, the skill **proposes** structured seed entries for `project-memory.md`, the human approves each entry (or all in batch), and only then does the skill write. **BMad does not write — the human writes after explicit confirmation** — so the Kiat rule "BMad never writes to `delivery/specs/`" is preserved.

## Design constraints (from adversarial review)

This skill was designed after a 4-agent adversarial review of two competing proposals. The shipped design (this one) emerged from the synthesis. The constraints below are load-bearing — do not relax them without rerunning the review.

1. **One file, structured.** Decisions seed into a single `delivery/specs/project-memory.md`, **not** distributed across framework-owned `delivery/specs/<topic>.md` files. Distributed overrides were rejected because (a) they pollute framework files and create merge friction with upstream Kiat, (b) the "where does this decision belong?" routing is ambiguous at write time (a single decision often has 2+ plausible topical homes), (c) cross-topic decisions silently fragment, (d) the tech-spec-writer routing table doubles.
2. **Entries have stable IDs** (`PM-NNN`) — never renumbered, never reused. The ID is the reference handle for amendments and supersession.
3. **Cross-topic decisions stay here by construction.** Any decision that touches ≥2 topics (e.g., "three-regime RLS data isolation" touches database + security + backend) is forbidden from being promoted to a single topical file — splitting it would create silent fragmentation. The `Touches:` field records the topics.
4. **Hard cap as a forcing function.** When `project-memory.md` exceeds **25 single-topic entries** (cross-topic entries are exempt), the file fails its own audit. The human must then either promote single-topic clusters to project-owned `delivery/specs/<topic>.md` files (new files, not edits to framework files) or justify retention.
5. **Propose-then-confirm.** The skill defaults to dry-run output. Writing requires an explicit `--apply` confirmation from the human in the same session. This closes the "autonomous BMad bypasses the human" loophole.
6. **Re-runnable.** When the architecture is amended, the human re-runs the skill. It diffs proposed entries against existing IDs and emits either an `Amends PM-NNN` entry (in-place update) or a `Supersedes PM-NNN` entry (replacement) — never a silent overwrite.

## Inputs and outputs

- **Input**: a BMad architecture document. Default path: `_bmad-output/planning-artifacts/architecture.md`. Fall back to globbing `**/architecture.md` if the default is missing.
- **Output (dry-run, default)**: a proposed-entries report to stdout, no file writes.
- **Output (`--apply` after human confirmation)**: appended entries in `delivery/specs/project-memory.md` under a single new `## <Project> Architectural Decisions (pre-implementation seed — YYYY-MM-DD)` section.

## Workflow

### 1. Locate the architecture document

Search in order:

1. `_bmad-output/planning-artifacts/architecture.md`
2. `_bmad-output/**/architecture.md` (if BMad's `planning_artifacts` config points elsewhere)
3. Any `**/architecture.md` file outside `.claude/` and `node_modules/`

If multiple candidates exist, list them and ask the user to pick one. If none exists, abort cleanly: tell the user to run `bmad-create-architecture` first.

### 2. Confirm scope with the user

Announce in one paragraph:

- Path of the architecture document you found.
- Current state of `delivery/specs/project-memory.md` (empty template / N existing entries with highest ID PM-NNN / has prior seed section).
- That you will produce a dry-run report first and require `--apply` confirmation before writing.

Wait for green light before reading the architecture document.

### 3. Read the architecture document and extract candidates

Read the architecture document end-to-end. Extract decisions matching **at least one** of these criteria:

- **Cross-story applicability**: the decision will be invoked in at least two distinct future stories. Single-story decisions (e.g., "story 7 uses a one-off cache") do not belong here.
- **Non-obvious from generic Kiat specs**: the decision is not already covered by `delivery/specs/architecture-clean.md`, `backend-conventions.md`, `database-conventions.md`, etc. If the architecture only restates a generic convention, skip it.
- **Surprising default**: the decision overrides what a reasonable coder would assume from a vanilla Kiat scaffold (e.g., "Clerk stays dormant at M1", "no `audit_events` table at M1", "PDFs are never persisted").

For each candidate, identify the topics it touches by matching against this canonical topic vocabulary (extend only if a clearly new topic appears in the architecture):

```
backend · frontend · database · auth · clerk · api · testing · deployment ·
security · design-system · share-tokens · pdf-generation · calc-engine ·
external-integrations · observability · ci-cd
```

### 4. Draft proposed entries with structured metadata

For each candidate, draft an entry using the structured template:

```markdown
### PM-NNN — <Pattern name — short, findable>

**Status**: active
**Established**: pre-implementation seed (YYYY-MM-DD)
**Last verified**: YYYY-MM-DD
**Touches**: <topic-1, topic-2, ...>
**Rule**: <one sentence — what must hold true>
**Canonical ref**: `<path:line or path:section in architecture.md>`
**Rationale**: <why this and not the obvious alternative — one sentence>
**Deviations allowed when**: <if any — otherwise "never at M1" or "never, escalate to <person>">
```

**ID assignment**: read the existing `project-memory.md`, find the highest `PM-NNN` ID, start new entries at the next number. IDs are stable: once assigned, never renumbered, never reused even after deletion.

**Entry rules**:

- **One sentence rule.** If you need two, the entry is too broad — split it.
- **Always cite the source.** `Canonical ref` must point back to the architecture document so the reader can verify and stay coherent if the architecture is later amended.
- **Quote the verb the architecture uses** (`uses`, `must`, `never`) rather than inventing new force-levels.
- **`Touches:` is the topic index.** A grep on this field across `project-memory.md` answers "what decisions affect topic X" without scanning prose.

### 5. Detect amendments vs new entries

If the architecture document contains a decision that semantically matches an existing entry (e.g., share token TTL is 90j in the doc but PM-008 in `project-memory.md` says 30j):

- Emit the new entry with `**Amends**: PM-008` and `**Status**: active` on the new entry.
- Also emit a proposed edit to PM-008: `**Status**: superseded` and `**Superseded by**: PM-NNN`.
- Surface this conflict explicitly in the dry-run report — do not bury it among the new entries.

### 6. Dry-run report

Produce a report with this structure:

```
== kiat-seed-project-memory dry-run ==

Source: <path/to/architecture.md>
Existing entries: <N> (highest ID: PM-NNN)
Proposed new entries: <M>
Proposed amendments: <P>
Cross-topic entries: <Q> (will stay in project-memory.md; not promotable)
Single-topic entries: <R> (eligible for promotion when cap is hit)

Current size: <X> lines / <Y> single-topic entries
Cap: 400 lines / 25 single-topic entries
After this seed: <X'> lines / <Y'> single-topic entries  [WITHIN CAP | EXCEEDS CAP]

--- Proposed new entries ---
<full text of each entry>

--- Proposed amendments ---
<each amendment with the existing entry it touches>

--- Audit line ---
kiat-seed-project-memory: dry-run, <M> new / <P> amendments / <Q> cross-topic / <R> single-topic
```

If the post-seed state EXCEEDS CAP, end the report with a recommendation to promote single-topic clusters (≥3 entries with the same single `Touches:` topic) to a new project-owned `delivery/specs/<topic>.md` file **before applying**. Do not auto-promote — promotion is a separate human decision.

### 7. Wait for `--apply` confirmation

Present the dry-run report and stop. The user must explicitly say `--apply` (or equivalent) to authorize writes. No timeout, no implicit consent.

### 8. Write the approved entries

On `--apply`:

- Open `delivery/specs/project-memory.md`.
- Append a single new section header if this is the first seed:
  ```markdown
  ---

  ## <Project name> Architectural Decisions (pre-implementation seed — YYYY-MM-DD)

  > These entries were seeded from `<path/to/architecture.md>` before the first
  > story. Source of truth is the architecture document — when it is amended,
  > re-run `kiat-seed-project-memory` to refresh affected entries.
  ```
- Append the approved new entries in PM-NNN order.
- Apply the proposed amendments to existing entries (Status: superseded, Superseded by: PM-NNN).
- Emit the final audit line: `kiat-seed-project-memory: applied <M> new / <P> amendments`.

### 9. Commit suggestion

Suggest a commit message but do not commit unless the user asks:

```
feat(specs): seed project-memory.md from BMad architecture

Pre-implementation seed extracted from <path/to/architecture.md>.
<M> new entries, <P> amendments. Highest ID: PM-NNN.
```

## What this skill does NOT do

- **It does not modify the architecture document.** If a decision is unclear, the skill flags it; corrections happen in the architecture document via the normal BMad flow.
- **It does not duplicate generic Kiat conventions.** If a decision is already in `delivery/specs/<topic>.md`, the skill skips it and notes the reference instead.
- **It does not write `delivery/business/` entries.** Those are domain facts (BMad Capture mode's territory), not technical decisions.
- **It does not promote entries to topical files.** That is a separate human decision, triggered when the cap is hit. A follow-up skill (`kiat-promote-project-memory`, planned) will assist with promotion when the cap is reached.
- **It does not edit framework-owned `delivery/specs/<topic>.md` files.** Distributed overrides were rejected by adversarial review — they pollute framework files and create merge friction.
- **It does not run automatically as part of `bmad-create-architecture`.** It is a human-invoked bridge, kept manual because (a) not every project needs it, (b) entry curation benefits from human judgment, and (c) automating it would force `bmad-create-architecture` to know about Kiat — a coupling the framework deliberately avoids.

## Failure modes to avoid

❌ **Copying the entire architecture document into `project-memory.md`.** The file must stay short and findable — extract decisions, do not photocopy.

❌ **Inventing decisions the architecture does not state.** If a category is silent in the architecture, leave it silent here. The file is a memory of decisions made, not a wishlist.

❌ **Restating generic Kiat conventions.** `delivery/specs/architecture-clean.md` already says "use 4-layer Clean Architecture". Do not seed that. Seed only what the architecture said *in addition* to the generic specs.

❌ **Writing entries without `Canonical ref`.** Every entry must point back to the architecture document, otherwise future readers can not verify or trace amendments.

❌ **Splitting cross-topic decisions across multiple entries.** A decision that legitimately touches database + auth + backend is one entry with `Touches: database, auth, backend` — not three half-entries. Splitting fragments the rule and creates drift.

❌ **Writing without `--apply` confirmation.** The dry-run-then-confirm flow is the only safeguard against autonomous BMad sessions seeding the file unilaterally. Honor it.

## Planned follow-up (separate PRs)

- **`kiat-promote-project-memory`** — invoked when the cap is hit. Detects single-topic clusters (≥3 entries with the same `Touches:` topic) and proposes moving them to a new project-owned `delivery/specs/<topic>.md`, leaving a stub redirect in `project-memory.md`.
- **`kiat-validate-project-memory` CI check** — fails when (a) cap exceeded, (b) any entry has a stale `Canonical ref` (file or line no longer exists), (c) any entry's `Last verified` is older than N epics.
- **Instrumentation** — measure on the LGT pilot project: after 10 stories shipped, count (a) total entries, (b) entries actually loaded by tech-spec-writer per story, (c) routing arguments in PR review. If load-rate is <30%, the file is dead weight and the design needs re-evaluation. If ≥50%, the design is validated. Decide based on data, not vibes.
