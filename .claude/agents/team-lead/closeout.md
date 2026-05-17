# Team Lead — Stage 6: Closeout

> Loaded on demand after review (Stage 5) ends with merged verdict APPROVED. Covers **Stage 6.1** (pitfall capture), **Stage 6.2** (deviations companion file), and **Stage 6.3** (reconciliation notification + event emission). At the end of this stage, the story is ready for the ship stage.

---

## Stage 6.1 — Pitfall capture (after tests pass, before rollup)

If the story consumed **> 15 minutes of coder wall-clock on test-related issues** (flaky assertions, wrong wait patterns, auth quirks, DB seeding problems, Venom key casing, Clerk session corruption, etc.), you MUST capture the lesson before closing the story. The goal: the next coder who hits a similar problem finds the answer in the pitfalls file instead of burning another 15+ minutes.

**Procedure:**

1. Ask the coder: *"What was the root cause of the test fix, and what should future coders do differently?"* — one sentence each.
2. Determine which pitfalls file to append to:
   - Backend test issue → `delivery/specs/testing-pitfalls-backend.md`
   - Frontend/Playwright test issue → `delivery/specs/testing-pitfalls-frontend.md`
   - Both → append to both, with cross-reference
3. Read the target file, check the last pitfall number (e.g., `VP07`, `PP11`), increment it.
4. Append a new entry using the template at the bottom of the file:
   ```markdown
   ### VPNN: <short title>

   **Symptom:** <what went wrong — observable behavior>
   **Rule:** <what to do instead — one sentence>
   **Prevention:** <how to catch this before it happens>
   ```
5. Emit an audit line:
   ```
   Pitfall captured: VP08 in testing-pitfalls-backend.md — "<short title>"
   ```

**When to skip:** If retry time was spent on non-test issues (wrong API contract, missing migration, design mismatch), this step does not apply — those are spec issues, not test pitfalls.

**When the pitfall already exists:** If the coder's fix matches an existing pitfall entry, do NOT create a duplicate. Instead, note in your audit line: `Pitfall already documented: VP04 — no new entry needed`. If the existing entry is incomplete or wrong, update it in place.

---

## Stage 6.2 — Create deviations companion file (after review, before rollup)

After both reviewers return `APPROVED` and Stage 6.1 is done, **aggregate the Business Deviations from both coders into a companion `.reconcile.md` file** next to the story spec. The story spec file itself is NEVER modified — all deviation data lives in the companion.

**Procedure:**

1. **Collect** the `Business Deviations:` section from each coder's handoff (backend and/or frontend).
2. **If ALL coders reported `NONE`**: no action needed — the story shipped as specified, no companion file is created. Emit the audit line and proceed to Stage 7.
3. **If ANY coder reported deviations**: create the companion file at `delivery/epics/epic-X/story-NN-<slug>.reconcile.md`, following the canonical template at [`delivery/epics/epic-template/story-NN-slug.reconcile.md`](../../../delivery/epics/epic-template/story-NN-slug.reconcile.md). The file MUST have:
   - A `## Deviations` section between `<!-- POST_DELIVERY_BLOCK_BEGIN -->` and `<!-- POST_DELIVERY_BLOCK_END -->` markers, with one bullet per deviation following the strict schema (Tag, Severity, Summary, File, SpecRef, Status, Why) — see [`reconciliation-protocol.md`](../../specs/reconciliation-protocol.md) §"The `story-NN-<slug>.reconcile.md` schema".
   - A `## Reconciliation` section containing the placeholder `_(awaiting reconciliation — run /bmad-correct-course on this story)_` — `/bmad-correct-course` will replace this with the L1/L2/L3 outcome when the human invokes it.
4. **The validator hook `check-post-delivery-schema.sh`** runs on your `SubagentStop` and validates the `## Deviations` schema in the new companion file. If it fails, fix the schema and re-edit. When aggregating deviations into the `.reconcile.md` companion, ensure each tag prefix is one of the 8 enum values (`SPEC_GAP|DECISION|SCOPE_CUT|BOY_SCOUT|DOMAIN_NEW|PROCESS|TEST_DRIFT|UPSTREAM_MISMATCH`). The `check-post-delivery-schema.sh` hook will reject the file otherwise.
5. **Include a `business_deviations` count in the rollup event** (Stage 7) — see [`metrics-events.md`](../../specs/metrics-events.md) for the field.

**Audit line (always emit)**:
```
Business reconciliation: 0 deviations — story shipped as specified, no companion file created ✓
```
or
```
Business reconciliation: 3 deviations aggregated into story-NN-<slug>.reconcile.md §Deviations (2 backend, 1 frontend) — awaiting /bmad-correct-course ✓
```

**Why this phase exists**: without it, business-impacting decisions made during coding die in the Git diff. The PO/PM never learns that AC-3 was implemented differently, or that a new domain concept was introduced. `/bmad-correct-course` consumes the `## Deviations` section to update `delivery/business/` and the queue — but the data must exist first. This phase creates the data, in a file separate from the story spec so the spec stays focused.

**Producer-pays gate cross-check (mandatory).** When a coder's handoff contains a deviation marked `Status: RESOLVED`, validate it satisfies the producer-pays gate documented in [`reconciliation-protocol.md` §Resolution-at-handoff](../../specs/reconciliation-protocol.md#resolution-at-handoff-the-producer-pays-gate): L1 severity AND fix landed inline in the same commit AND the category is in the allowed list (DECISION with no business impact, BOY_SCOUT, DOCS, AC-T## interpretation without observable change). If a `RESOLVED` entry hits the FORBIDDEN list (RLS, security, business rule, schema migration, cross-cutting file, upstream API contract) — or the inline fix is missing — re-classify it to `NEEDS_PROMOTION` (L2) before writing the companion file. Bad RESOLVED ships silent drift; the gate is the only place to catch it at Team-Lead level.

---

## Stage 6.3 — Notify human that reconciliation is needed (if deviations exist)

Once the `.reconcile.md` companion file exists AND the `check-post-delivery-schema.sh` hook has passed, you do NOT spawn a reconciliation sub-agent. Per-story reconciliation is **human-invoked** via `/bmad-correct-course` — that's BMad's existing mode for "significant changes during sprint execution", which is exactly what a populated `## Deviations` section in the companion file represents.

Your job at Stage 6.3: **emit a clear notification** so the human knows reconciliation is needed before the next story can safely launch (or before the epic can close). The reconciliation guard at Stage 7 will enforce this — without a `story-NN-<slug>.reconcile.md` companion file carrying `RECONCILE_DONE`, the epic stays open.

**Skip Stage 6.3** if Post-Delivery Notes is the placeholder `_(no deviations)_`. Audit line:
```
Reconciliation: skipped — no deviations to reconcile
```

**Run Stage 6.3** otherwise. The notification format (emit verbatim in your final output, before the rollup):

```
RECONCILIATION_NEEDED: story-NN-<slug>
  Source: delivery/epics/epic-X/story-NN-<slug>.reconcile.md §Deviations
  Deviations: N backend, M frontend
  Action: run `/bmad-correct-course` on this story to triage L1/L2/L3
          and update the SAME .reconcile.md with the Reconciliation
          section + RECONCILE_DONE marker
  Reference: .claude/specs/reconciliation-protocol.md
             .claude/specs/bmad-reconcile-contract.md (the contract
             /bmad-correct-course must honor when used in Kiat context)
```

**Audit line (always emit on Stage 6.3 when deviations exist)**:
```
Reconciliation: human invocation needed (/bmad-correct-course) — 3 deviations queued for triage
```

### Emit `reconciliation_needed` event (v2.1 observability — schema v2.1)

After emitting the notification block AND the audit line, append one JSONL event to `delivery/metrics/events.jsonl`. This event marks the moment human triage becomes needed; pairs with the later `reconcile_complete` event to measure **human triage latency** (`reconcile_complete.ts - reconciliation_needed.ts`).

Skip the event emission when Stage 6.3 itself is skipped (no deviations).

Field derivation:
- `deviations_count` — total entries in `## Deviations`, counted across the backend and frontend sub-sections of the `.reconcile.md` you just created.
- `deviations_unresolved` — count of entries whose `**Status**:` line is `NEEDS_PROMOTION` or `BLOCKING` (i.e., not `RESOLVED` at handoff).
- `severity_hint` — count entries by their `**Severity**:` value (L1/L2/L3). This is the **coder's hint**, not final; `/bmad-correct-course` may reclassify.

Canonical shape (single line, minified JSON):
```json
{"ts":"<ISO-8601 UTC>","schema":"v2","event":"reconciliation_needed","story":"<id>","epic":"<id>","reconcile_path":"<path>","deviations_count":<N>,"deviations_unresolved":<M>,"severity_hint":{"L1":<a>,"L2":<b>,"L3":<c>}}
```

Audit line for the emission:
```
reconciliation_needed event emitted — 4 deviations (2 unresolved), hint L1=2 L2=2 L3=0
```

Full schema: [`../../specs/metrics-events.md#reconciliation_needed`](../../specs/metrics-events.md).

### What `/bmad-correct-course` does in Kiat context (the contract)

When invoked on a story with a populated `.reconcile.md` companion, `/bmad-correct-course` MUST produce the artifacts described in [`.claude/specs/bmad-reconcile-contract.md`](../../specs/bmad-reconcile-contract.md):

- Replaces the `## Reconciliation` placeholder in the SAME `.reconcile.md` file with the L1/L2/L3 triage and a `RECONCILE_DONE` marker (does NOT modify the `## Deviations` section)
- Applied L1 changes (landed directly in `delivery/business/` or `delivery/specs/`)
- Appended L2 entries to `delivery/_queue/needs-human-review.md`
- L3 escalations as `epic_block` events in `delivery/metrics/events.jsonl`
- One `reconcile_complete` event in `events.jsonl`

**Per-epic reconciliation** uses `/bmad-retrospective` — invoked once per epic when all stories are `✅ Done`. It reads every story's `.reconcile.md`, force-closes any remaining OPEN queue entries, and produces `_epic.reconcile.md` with `EPIC_RECONCILE_DONE`.

**Schema** for the input/output files: [`.claude/specs/reconciliation-protocol.md`](../../specs/reconciliation-protocol.md).
