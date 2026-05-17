# Team Lead — Stage 3: Validation

> Loaded on demand after Stage 1 (intake) passes. Covers **Phase 0a** (spec diff-check), **Phase 0c** (queue scope-overlap check), and **Phase 0b** (pre-flight context budget), in that order. All three must pass before any coder launches. Status transition `📝 Drafted → 🚧 In Progress` happens at the end of this stage.

---

## Phase 0a — Spec diff-check (MANDATORY, runs first on every story)

The writer already ran `kiat-validate-spec` inside its own workflow before handoff — by contract it cannot return `SPEC_HANDOFF` unless the skill said `CLEAR`. Re-running the full skill here would be duplicate work in the common case where the file hasn't changed.

Instead, do a **diff-check**: trust the writer's verdict if the story file is byte-identical to what the writer handed off, re-validate only if it changed.

**Two sub-cases:**

1. **Input came from Phase -1** (Team Lead just spawned the writer):
   - Read `spec_byte_count` from the `SPEC_HANDOFF`.
   - Run `wc -c delivery/epics/epic-X/story-NN.md` and compare.
   - If equal → trust `SPEC_VERDICT: CLEAR`, **proceed to Phase 0b immediately**.
   - If different → the file was edited between handoff and now (unusual, but possible if the user tweaked it). Run the `kiat-validate-spec` skill and parse its first line exactly as in sub-case 2.

2. **Input was an existing story file (Phase -1 skipped)**:
   - There is no prior handoff to compare against. Run the `kiat-validate-spec` skill on the story and parse the first line **deterministically**:

| First line                                  | Action |
|----------------------------------------------|--------|
| `SPEC_VERDICT: CLEAR`                        | Proceed to Phase 0b |
| `SPEC_VERDICT: NEEDS_CLARIFICATION`          | Respawn `kiat-tech-spec-writer` with the skill's specific questions attached. Wait for an updated `SPEC_HANDOFF`. Re-enter Phase 0a on the new file. Do NOT launch coders. |
| `SPEC_VERDICT: BLOCKED`                      | Escalate to user. Spec has structural gaps. Do NOT patch ambiguities yourself. |

If the skill output doesn't start with `SPEC_VERDICT:`, treat it as malformed and re-run.

**Audit line (always emit in your phase log)** — one of:
```
Spec diff-check: story-NN unchanged since writer handoff (4812 bytes), verdict CLEAR ✓
Spec diff-check: story-NN changed since handoff (was 4812, now 4901), re-validated → CLEAR ✓
Spec validation: story-NN (no prior handoff), skill returned CLEAR ✓
```

**Why a diff-check, not a second full run**: the writer's `kiat-validate-spec` pass is the authoritative validation. Re-running the skill against an identical file just burns tokens and invites spurious drift. A byte-equality check is a strict and cheap proxy for "nothing changed" — if bytes are equal, the skill verdict is still valid by construction.

---

## Phase 0c — Reconciliation queue scope-overlap check (MANDATORY)

After Phase 0a (spec is `CLEAR` and the story file is finalized on disk), but before Phase 0b (context budget), scan `delivery/_queue/needs-human-review.md` for OPEN L2 entries that would overlap this story's scope. Phase 0 already caught any unresolved L3 (`epic_block`) events; Phase 0c catches L2 entries that would silently corrupt this story if launched against them.

**Why this lives in Team Lead, not in tech-spec-writer**: by Phase 0c, the story file is on disk regardless of whether Phase -1 ran (informal request → writer authored it) or was skipped (existing story file). Team Lead already loaded the file at Phase 0a. The scan is a mechanical grep + path comparison — no creative judgment required, no need to spawn a sub-agent.

**Procedure**:

1. **Read** `delivery/_queue/needs-human-review.md`. Find every entry whose heading contains `[OPEN]`.
2. For each OPEN entry, read its `**Affects**:` and `**Affects (files)**:` fields.
3. **Determine this story's scope** from the story file. Sources:
   - Files mentioned under `## Backend` (database migrations, API contract paths suggest handler files, business logic suggests domain/usecase packages)
   - Files mentioned under `## Frontend` (component paths, hook paths)
   - Docs the story will edit (rare — most stories don't edit `delivery/business/` or `delivery/specs/` directly, but flag if any are mentioned)
4. **Detect overlap**:
   - **Doc overlap**: the story explicitly targets the doc named in `Affects` (e.g., entry proposes a glossary addition, story body says it will add a glossary entry).
   - **File overlap**: any of the entry's `Affects (files)` paths fall under a directory the story touches. Path-prefix match — e.g., queue says `backend/internal/domain/items/`, story touches `backend/internal/domain/items/list.go` → overlap.
5. **On overlap, check for a declared supersession FIRST** (per EV-0002):
   - Read the story file's `## Supersedes` section (immediately below the front-matter, above `## Business Context`). If the section is absent, treat as no declaration.
   - **If the overlapping Q-ID is listed there** (verbatim `Q-NNN`), this is a SUPERSESSION, not a conflict. Do:
     - Edit the queue entry: change `[OPEN]` in the heading to `[SUPERSEDED]`, add a `**Closed at**: <ISO-8601 UTC>` line, add `**Decision**: superseded by <story-NN> (Phase 0c — Team Lead honored the story's `## Supersedes:` declaration)`.
     - Append a `queue_supersede` event to `delivery/metrics/events.jsonl` with the story ID, the queue ID, the entry's `deviation_tag`, and a one-line `summary` copied from the story's Supersedes rationale. Schema: [`../../specs/metrics-events.md`](../../specs/metrics-events.md) §`queue_supersede`. **Emit this event BEFORE running Phase 0b** — the queue must be in a consistent state if Phase 0b fails.
     - Emit the audit line (see below) and **proceed to Phase 0b**.
   - **If the Q-ID is NOT declared in `## Supersedes`**, fall through to the AUTO-PROMOTE path in step 6.

6. **On overlap that is NOT declared as superseded, AUTO-PROMOTE** to L3 and refuse to launch:
   - Edit the queue entry: change `[OPEN]` in the heading to `[PROMOTED]`, add a `**Closed at**: <ISO-8601 UTC>` line, add `**Decision**: auto-promoted to L3 by Team Lead Phase 0c — overlaps with story-NN scope (specifics: <evidence>)`.
   - Append an `epic_block` event to `delivery/metrics/events.jsonl` with `source: "kiat-team-lead"`, the queue ID in the `queue_id` field, and `blocked_until: "human_signoff"`. Schema: [`../../specs/metrics-events.md`](../../specs/metrics-events.md) §`epic_block`.
   - Flip the story to `🛑 Blocked` and update the epic aggregate.
   - Escalate to user with the queue ID, the overlap evidence, and what they need to decide.
   - Do NOT proceed to Phase 0b.
7. **On no overlap**, emit the audit line and proceed to Phase 0b.

**Audit line (always emit)** — pick the variant that matches the outcome:
```
Queue scope-overlap check: 3 OPEN L2 entries reviewed, 0 overlaps with story-NN scope ✓
```
or
```
Queue scope-overlap check: 3 OPEN L2 entries reviewed, 1 overlap declared as supersession (Q-058 by story-NN), 0 conflicts → queue updated [SUPERSEDED], queue_supersede event emitted ✓
```
or
```
Queue scope-overlap check: 3 OPEN L2 entries reviewed, 1 overlap (Q-014 affects backend/internal/domain/items, story-NN touches that package) → AUTO-PROMOTED to L3 ❌ — REFUSED to launch story-NN
```

**Why this gate exists**: an L2 proposal in the queue is "async unless acted on now". When the next story's scope overlaps, the L2 stops being async — building on top of it would make it effectively binding without human signoff. Auto-promotion forces the human decision at the cheapest moment (before any coder runs). Full rationale and the complete L1/L2/L3 model: [`../../specs/reconciliation-protocol.md`](../../specs/reconciliation-protocol.md).

---

## Phase 0b — Pre-flight context budget check (MANDATORY)

Before launching ANY coder, verify the story's injected context fits the coder's budget. Full rules live in [`.claude/specs/context-budgets.md`](../../specs/context-budgets.md). Short version:

1. **Identify target agents** and their hard budgets:
   - `kiat-backend-coder` / `kiat-frontend-coder`: **35k tokens**
   - `kiat-backend-reviewer` / `kiat-frontend-reviewer`: **20k tokens**
2. **Compute estimated size** via `wc -c <file> | bytes / 4`, summed over:
   - Ambient docs (CLAUDE.md + the per-layer convention doc + testing.md + the per-layer pitfalls doc if the story involves tests: `testing-pitfalls-backend.md` for backend-coder, `testing-pitfalls-frontend.md` for frontend-coder)
   - Story spec (`delivery/epics/epic-X/story-NN.md`)
   - Per-story specs referenced in the story's `## Skills` section
   - Required skills (counted once)
3. **Decision**:
   - `estimated ≤ budget` → proceed to Phase 1
   - `estimated > budget` → overflow protocol (below)

**Overflow protocol**:

| Culprit | Action |
|---|---|
| Spec > 6k tokens (~24k bytes) | Escalate to `kiat-tech-spec-writer` with a split request. Do NOT launch. |
| Too many code refs | Trim to 2-3 most representative; coder reads more on demand |
| Ambient docs dominate on a small story | Calibration issue — flag to user, adjust `context-budgets.md` |
| Mixed overflow | Trim refs first; if still over, escalate |

**Absolute rule**: you NEVER launch a coder with overflowing context "to see if it works". The budget is a hard gate.

**Audit line**:
```
Pre-flight budget check: Backend-Coder 31k / 35k ✓  Frontend-Coder 29k / 35k ✓
```
or on overflow:
```
Pre-flight budget check: Backend-Coder 44k / 35k ❌ — ESCALATED (story-NN too large)
```

---

## Status transition (mandatory, immediately after the budget check passes)

Before launching any coder in the next stage, edit the story's `**Status**` line near the top of the file (below `**Epic**:`) from `📝 Drafted` to `🚧 In Progress`. In the **same edit pass**, recompute and update the epic's `_epic.md` aggregate status per the rule in [`delivery/epics/README.md#status-lifecycle`](../../../delivery/epics/README.md#status-lifecycle). For a story moving to `🚧 In Progress`, the epic's aggregate becomes `🚧 In Progress` unless another story is already `🛑 Blocked` (in which case the epic stays `🛑 Blocked`).

If the budget check fails and you escalate: set the story to `🛑 Blocked` instead (and update the epic aggregate the same way). Do NOT leave it at `📝 Drafted` — the status line is the shared signal for "is this story moving?".

**Audit line**:
```
Status transition: story-NN 📝 Drafted → 🚧 In Progress ✓  (epic-X aggregate recomputed)
```
