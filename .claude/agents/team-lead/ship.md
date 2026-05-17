# Team Lead — Stage 7: Ship

> Loaded on demand after closeout (Stage 6). Covers **Phase 6** (the hard exit gate): commit guard, integration test gate, rollup write-then-verify, final status transition, and the **reconciliation guard** that controls epic closure. The story is NOT done until every audit line in this stage has been emitted.

---

## Phase 6 — Mark story complete and emit the rollup event (HARD EXIT GATE)

Update the story file with a status footer (date, files changed, test counts, reviewer verdicts) and emit **exactly one** event to `delivery/metrics/events.jsonl`. This is your exit marker. See [`.claude/specs/metrics-events.md`](../../specs/metrics-events.md) for the v1.1 Rollup-First schema.

**Two mutually exclusive paths**:
- **Success** — `event: "story_rollup"`, `outcome: "passed"`
- **Escalation** — `event: "story_escalated"`, `outcome: "escalated"`, with `escalated_to`, `reason`, `reached_phase`

**No intra-story events**. Everything you tracked during the story (spec verdict, clarification rounds, pre-flight estimates, per-cycle reviewer verdicts, clerk skill triggers, test-pattern drift, approximate elapsed time) goes into the single rollup JSON object at the end.

---

## Pre-rollup gates (MANDATORY — run in this order BEFORE the rollup write)

Two gates run before the rollup write-then-verify protocol below. Both must pass. Any failure → REFUSE rollup, set story to `🛑 Blocked`, escalate. The rollup write happens only after both gates are green.

### Gate 1 — Commit guard

The 2026-05-01 incident proved that `outcome: "passed"` rollups written without a committed code state are catastrophic — work lives only in the working tree, gets lost in the next session's reset, the rollup becomes a lie in `events.jsonl`. This gate makes that physically impossible.

```bash
sha_before=$(git rev-parse HEAD)

# Stage the files the coders delivered. Stage explicitly (no `git add -A` / `.`)
# so secrets, scratch files, and cross-story leftovers can't sneak in.
git add <files-from-coder-handoffs>

# Commit per project conventions (delivery/specs/git-conventions.md).
# Pre-commit hooks run normally — never use --no-verify.
git commit -m "feat(epic-X-story-NN-slug): <short description>

<longer body>"

sha_after=$(git rev-parse HEAD)

if [ "$sha_after" = "$sha_before" ]; then
  echo "COMMIT_GUARD_FAIL: no commit was created"
  # REFUSE rollup, escalate "code not committed"
fi
```

The `code_commit_sha` field of the rollup JSON MUST be set to `$sha_after` (see metrics-events.md schema). The rollup is the durable receipt: *"this story's deliverables live at this SHA"*. Without that field, the rollup is malformed and must not be written.

If the commit fails (pre-commit hook, sign-off, lint failure) → fix the underlying issue and create a NEW commit. Do NOT use `--no-verify`. A failing pre-commit hook is information, not friction.

**Audit line**:
```
Commit guard: <sha_after> (parent <sha_before>) ✓
```
or
```
Commit guard: sha unchanged (<sha_before>) ❌ — REFUSED rollup, code not committed
```

### Gate 2 — Integration test gate

Tests passed at coder-level (Phase 3) on a working tree that was not yet integrated with the prior story. After the commit at Gate 1, run the full suite ONE more time on the post-commit tree. This is the gate that catches cross-story interference — exactly the failure mode that took down the 4 epic-09 stories on 2026-05-01.

**Pipe to file, exit code only** — never read the full output into Team Lead's context (would burn 20-50k tokens per command):

```bash
# Backend (run if the story has any backend layer)
make test-back > /tmp/test-back-postcommit.log 2>&1
back_exit=$?
echo "BACK_EXIT=$back_exit"

# Frontend (run if the story has any frontend layer)
make test-e2e > /tmp/test-e2e-postcommit.log 2>&1
e2e_exit=$?
echo "E2E_EXIT=$e2e_exit"
```

- **Both relevant suites green** (`*_exit == 0` for the layers in scope) → proceed to the write-then-verify protocol.
- **Any red** → read `tail -100 /tmp/test-XXX-postcommit.log` (~5k tokens) for diagnosis. The commit at Gate 1 is **kept** (so the user can debug from a real SHA), but:
  - REFUSE rollup
  - Set story `**Status**` to `🛑 Blocked`
  - Escalate with the failure tail and the commit SHA
  - Do NOT mark `✅ Done`

If the failure is a known fix, the coder fixes it, an additional commit is created (Gate 1 re-runs), and Gate 2 re-runs. The smart re-run rule from Phase 3 applies: only the failed test by default, full suite if the fix touches a cross-cutting file ([`delivery/specs/cross-cutting-files.md`](../../../delivery/specs/cross-cutting-files.md)).

**Audit lines**:
```
Test gate: backend make test-back exit=0 ✓  frontend make test-e2e exit=0 ✓
```
or
```
Test gate: backend exit=2 ❌ — REFUSED rollup, story blocked at <sha_after>, see /tmp/test-back-postcommit.log
```

---

## The write-then-verify protocol (MANDATORY)

The rollup write is the **single most failure-prone step** in the whole pipeline: if you forget it or write malformed JSON, the story disappears from `report.py` forever (see [`metrics-events.md`](../../specs/metrics-events.md#failure-mode)). Treat it as a hard exit gate, not a final formality.

Follow these three steps **in order**, without skipping the verify:

1. **Build the JSON object** in your working log first, as a single line (no pretty-print). Double-check every required field against the v2 schema in `metrics-events.md`. Use the v2 template from that doc — include `"schema":"v2"`, use the `spec` block, `review_cycles` array, and `business_deviations` as an object. **`mode` is enum-restricted to `"normal" | "solo" | "team_lead_authored"` — any other value is a protocol violation.** `deviations_declared_explicitly: false` is the canary that the coder never wrote a Business Deviations block at all — set it honestly, never default to `true`.
2. **Append via Bash heredoc** to `delivery/metrics/events.jsonl`:
   ```bash
   cat >> delivery/metrics/events.jsonl <<'EOF'
   {"schema":"v2","ts":"...","story":"story-NN","event":"story_rollup","outcome":"passed","size":"S","scope":"backend","layers":["backend"],"mode":"normal","spec":{"verdict":"CLEAR","byte_count":4500,"clarification_rounds":0,"writer_mode":"enrichment"},"preflight":{"backend_coder":{"estimated_tokens":22000,"budget":35000,"result":"pass"}},"review_cycles":[{"domain":"backend","cycles":1,"final_verdict":"APPROVED","clerk_skill_triggered":false,"clerk_verdict":null,"test_patterns_consistent":true,"total_issues_across_cycles":0}],"fix_budget_used_min":0,"test_patterns_drift":false,"business_deviations":{"count":0,"backend":[],"frontend":[]},"deviations_declared_explicitly":true,"failure_pattern_id":null,"code_commit_sha":"<sha_after>"}
   EOF
   ```
   Use single-quoted heredoc (`<<'EOF'`) so shell expansion doesn't mangle `$` or backticks inside the JSON. Replace `<sha_after>` with the actual SHA from Gate 1. **No `prod_validation` field — it was retired by EV-0007.**
3. **Verify the write back**, immediately, same message if possible:
   ```bash
   tail -n 1 delivery/metrics/events.jsonl | python3 -m json.tool
   ```
   If `json.tool` errors or the last line is not your rollup, the write failed — **do NOT declare the story complete**. Diagnose (escaping issue, file not writable, permissions), fix, and re-emit. A failed rollup is a blocker, same severity as a failed test.

**Audit line (always emit in your final message)**:
```
Rollup event: written and verified ✓ (event: story_rollup | story_escalated, line N of events.jsonl)
```

Until this audit line is in your output, the story is NOT done — even if every reviewer returned APPROVED, every test is green, and the story file has a status footer. The rollup is the real exit marker; everything else is context.

---

## Final status transition (MANDATORY, immediately after the rollup audit line)

Once the rollup is written and verified, the **last** edit you make on the story is to update the `**Status**` line near the top:

| Rollup outcome | New story status |
|---|---|
| `story_rollup` with `outcome: "passed"` | `✅ Done` |
| `story_escalated` with `outcome: "escalated"` | `🛑 Blocked` |

In the **same edit pass**, update the epic's `_epic.md` aggregate status per the rule in [`delivery/epics/README.md#status-lifecycle`](../../../delivery/epics/README.md#status-lifecycle). Key transitions after a story moves:

- Story → `✅ Done`: if this was the last `🚧 In Progress` story in the epic and all others are `✅ Done`, the epic **may** become `✅ Done` — but only after the **reconciliation guard** passes (see below). Otherwise it keeps whatever it was (typically `🚧 In Progress` if other stories are still running, or `📝 Drafted` / `📥 Backlog` if none are).
- Story → `🛑 Blocked`: the epic becomes `🛑 Blocked` immediately (blocked dominates every other state).

---

## Reconciliation guard (epic closure gate)

**When all stories in an epic are `✅ Done` and the epic is about to become `✅ Done`**, scan every story's directory for `.reconcile.md` companion files before flipping the epic status. The protocol details are in [`.claude/specs/reconciliation-protocol.md`](../../specs/reconciliation-protocol.md); short version:

1. For each story in the epic directory, check if `story-NN-<slug>.reconcile.md` exists.
2. **No companion file** → story shipped as specified, no reconciliation needed (Phase 5c didn't create one).
3. **Companion file exists with `<!-- RECONCILE_DONE: ... -->` marker** → reconciled by `/bmad-correct-course`, done.
4. **Companion file exists WITHOUT `RECONCILE_DONE` marker** → **unreconciled** — `/bmad-correct-course` was not run yet (or did not complete).
5. **Legacy form** (pre-protocol stories): the story file's `## Post-Delivery Notes` section contains a line matching `_Reconciled by BMad on .* —` → reconciled by BMad Review mode in legacy form, done. (No new stories should land in legacy form — but they're accepted during migration.)

Additionally, the epic-level retrospective MUST have run: an `_epic.reconcile.md` file exists at the epic root AND it contains an `<!-- EPIC_RECONCILE_DONE: ... -->` marker. Without this file, the epic CANNOT close even if all stories individually pass.

**Decision matrix:**

| Story-level scan | Epic-level retro | Action |
|---|---|---|
| All stories: no companion file or `RECONCILE_DONE` present | `_epic.reconcile.md` present with `EPIC_RECONCILE_DONE` | Epic → `✅ Done` |
| All stories reconciled | `_epic.reconcile.md` missing or no marker | Epic stays `🚧 In Progress`. Emit warning: "Run `/bmad-retrospective` to close the epic." |
| Any story has `.reconcile.md` without `RECONCILE_DONE` | (irrelevant) | Epic stays `🚧 In Progress`. Emit warning listing unreconciled stories. |
| Any L3 `epic_block` event unresolved (check via Phase 0 protocol) | (irrelevant) | Epic stays `🛑 Blocked`. |

**Audit line:**
```
Reconciliation guard: epic-X — 5 stories scanned, 0 unreconciled ✓ → epic eligible for ✅ Done
```
or
```
Reconciliation guard: epic-X — 5 stories scanned, 2 unreconciled (story-03, story-05) ⚠️ → epic stays 🚧 In Progress. BMad reconciliation needed before epic closure.
```

**Why this guard exists**: without it, an epic can close with business deviations that the PO/PM never saw. The guard ensures the feedback loop is actually closed — not just that the data was created (Phase 5c), but that it was consumed (BMad Review mode). It's the difference between "we told the PO" and "the PO acknowledged it".

**Status audit line (always emit)**:
```
Status transition: story-NN 🚧 In Progress → ✅ Done ✓  (epic-X aggregate recomputed)
```
or
```
Status transition: story-NN 🚧 In Progress → 🛑 Blocked ✓  (epic-X aggregate recomputed)
```

This status transition is NOT optional and NOT a cosmetic update — it is the single source of truth the user reads to know "where is dev at". A rollup written without the matching status transition is a half-closed story and the next human who reads the file has no way to know it shipped.

---

## Before escalating

Consult [`.claude/specs/failure-patterns.md`](../../specs/failure-patterns.md):
1. Search the registry for a pattern matching the escalation reason + symptoms
2. If match: apply the documented prevention (if any), increment the recurrence count, append a row to the pattern's recurrence log, include `failure_pattern_id` in the rollup
3. If no match: create a new `FP-NNN-<slug>.md` file, add a registry row, include the new ID
4. Recurrence count ≥ 3 with no prevention → flag explicitly to the user: *"FP-NNN has recurred 3+ times with no prevention — needs structural fix"*
