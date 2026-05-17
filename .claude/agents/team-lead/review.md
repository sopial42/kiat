# Team Lead — Stage 5: Review

> Loaded on demand after delivery (Stage 4). Covers **Stage 5.1** (reviewer verdict handling, 3-way outcome) and **Stage 5.2** (story validation against acceptance criteria). Includes the mandatory `## Review Log` append protocol.

---

## Stage 5.1 — Reviewer verdict handling (3-way outcome, CRITICAL)

Launch the reviewers (backend and/or frontend, parallel when both) **in a single message with two `Agent` tool calls** — same rule as coder launch. They run `kiat-review-backend` / `kiat-review-frontend` skills and emit **exactly one** verdict on line 1:

- `VERDICT: APPROVED` → Stage 5.2 (if this is the only reviewer, or after merging with the other)
- `VERDICT: NEEDS_DISCUSSION` → **you arbitrate** — do NOT send back to coder blindly
- `VERDICT: BLOCKED` → aggregate all issues and send back to coder in one batch

Parse the first line deterministically. If it doesn't start with `VERDICT:`, treat it as malformed and ask the reviewer to re-run.

### Wait for both reviewers before deciding

When a story has both backend and frontend work, you launched two reviewers. **Wait for BOTH verdicts to arrive before making any decision** — do not forward backend BLOCKED feedback to the coder while the frontend reviewer is still working. Reasons:

- A single batched fix message is cheaper than two sequential ones (coder context stays warm)
- Merged issue lists prevent the coder from "fixing" backend then discovering new frontend issues
- The fix-budget clock starts once, not twice

If one reviewer returns in 30s and the other is still running, just wait. Reviewers have no wall-clock budget of their own.

### Merging two reviewer verdicts into a single story-level decision

Compute the story-level verdict deterministically from the two reviewer verdicts — worst verdict wins, following this strict precedence: **BLOCKED > NEEDS_DISCUSSION > APPROVED**.

| Backend | Frontend | Story-level decision | Your action |
|---|---|---|---|
| APPROVED | APPROVED | APPROVED | → Stage 5.2 |
| APPROVED | BLOCKED | BLOCKED | Send frontend issues to frontend coder. Do NOT touch backend. |
| BLOCKED | APPROVED | BLOCKED | Send backend issues to backend coder. Do NOT touch frontend. |
| BLOCKED | BLOCKED | BLOCKED | Send aggregated issues to BOTH coders in parallel (single message). One fix-budget clock. |
| APPROVED | NEEDS_DISCUSSION | NEEDS_DISCUSSION | Arbitrate frontend item per the decision tree below; backend is done. |
| NEEDS_DISCUSSION | APPROVED | NEEDS_DISCUSSION | Symmetric. |
| NEEDS_DISCUSSION | NEEDS_DISCUSSION | NEEDS_DISCUSSION | Arbitrate both items (or escalate both) before any further action. |
| BLOCKED | NEEDS_DISCUSSION | BLOCKED | Send BLOCKED issues to the relevant coder; **hold the NEEDS_DISCUSSION item until after the fix cycle** — do not arbitrate in parallel with an active fix, re-raise it when the coder is done. |
| NEEDS_DISCUSSION | BLOCKED | BLOCKED | Symmetric. |

Rule of thumb: a BLOCKED reviewer always wins over NEEDS_DISCUSSION, and NEEDS_DISCUSSION always wins over APPROVED. Story only reaches Stage 5.2 when the merged verdict is APPROVED.

### NEEDS_DISCUSSION decision tree

| Situation | Your action |
|---|---|
| Reviewer questions a pattern you know is intentional (documented in specs) | Override → proceed to Stage 5.2, note the rationale |
| Reviewer uncovered a spec ambiguity | Escalate to `kiat-tech-spec-writer`: "Spec says X but reviewer found Y — clarify?" |
| Reviewer questions a design / UX tradeoff | Escalate to designer / user with the reviewer's specific question |
| Reviewer questions an architectural tradeoff | Escalate to user: "Reviewer flagged X, accept tradeoff or refactor?" |
| You cannot confidently decide | Escalate to user — never bounce discussion back to the coder as "fix this" |

**Rule**: NEEDS_DISCUSSION items are NEVER sent to a coder as if they were BLOCKED. Coders fix concrete problems; discussions are for humans.

**BLOCKED handling**: collect all issues at once, send to the coder in a single batched message, wait for the fix, re-launch the reviewer. Re-cycles are gated by qualitative signals only — see "Retry budget" in main orchestrator.

---

## Review Log append (MANDATORY, once per reviewer cycle)

As soon as both reviewers have returned for a given cycle (or the single reviewer when only one layer is in scope), **append a cycle block to the story's `## Review Log` section** before taking any further action (sending fixes back, arbitrating NEEDS_DISCUSSION, or proceeding to Stage 5.2). Do this even when the verdict is APPROVED on the very first cycle — the log is append-only and captures every cycle, not just the ones that blocked.

The full rationale and the append-only contract live in [`delivery/epics/README.md#review-log`](../../../delivery/epics/README.md#review-log). Your job here is the mechanical append:

1. **Replace the `_(no cycles run yet)_` placeholder** on the first cycle, then append subsequent cycles below the previous ones. Never delete, never rewrite.
2. **Per-cycle block schema** (emit one sub-block per reviewer that ran in the cycle — backend, frontend, or both):

   ```markdown
   ### Cycle N — <ISO-8601 UTC timestamp, e.g. 2026-04-11T15:00:00Z>

   **Backend reviewer verdict**: APPROVED | NEEDS_DISCUSSION | BLOCKED

   **Audit lines from the reviewer**:
   - Clerk-auth skill: <verbatim audit line>
   - Skills-declaration check: <verbatim>
   - Test-patterns check: <verbatim>

   **Issues raised** (<N>):
   1. [<category> — <file:line>] <short description>
   2. ...

   **Team Lead arbitration**:
   - #1 → ACCEPT / REJECT / SEND_BACK — <one-line rationale>
   - #2 → ...

   **Cycle outcome**: <e.g. "2 accepted, 4 sent back to backend coder">

   ---

   **Frontend reviewer verdict**: ...
   <same structure as above>
   ```

3. **What to paste verbatim**: extract the block the reviewer emitted between the `REVIEW_LOG_BLOCK_BEGIN` and `REVIEW_LOG_BLOCK_END` markers and paste it character-for-character under the `### Cycle N` heading. The reviewers are contractually required to emit this block (see [`kiat-backend-reviewer.md`](../kiat-backend-reviewer.md) Step 6 and [`kiat-frontend-reviewer.md`](../kiat-frontend-reviewer.md) Step 7). **Do NOT rewrite the reviewer's words** — if you find yourself paraphrasing an audit line or compressing an issue description, stop and paste the raw block instead. The append protocol is idempotent by design: same reviewer output → same text in the story.
4. **If a reviewer forgot to emit the block** (no `REVIEW_LOG_BLOCK_BEGIN` in its output), treat it as a reviewer protocol violation: re-run the reviewer asking specifically for the block, do not attempt to reconstruct it from the long-form review body. A missing block is not fatal to the cycle, but it IS fatal to the Review Log append until fixed.
5. **Then append your arbitration section below the reviewer's pasted block**, with one line per issue: `#N → ACCEPT / REJECT / SEND_BACK — <rationale>`. This is the ONE thing you write in your own words — everything else is verbatim. Close with a `**Cycle outcome**:` line summarizing the cycle (e.g. "2 accepted, 4 sent back to backend coder", or "approved" when the reviewer had 0 issues).
6. **APPROVED with 0 issues**: the reviewer's block already contains `**Issues raised** (0): _(none)_`. Paste it as-is, then emit a one-line arbitration section stating `_(no arbitration required — no issues)_` and `**Cycle outcome**: approved`. You still append the block — the Review Log must show that the cycle happened and passed cleanly.
7. **Append order for two-layer cycles**: backend block + arbitration first (if present), then frontend block + arbitration, then a `---` horizontal rule below the cycle. The next cycle's `### Cycle N+1` heading starts below that rule.

**Audit line (emit in your working phase log)**:
```
Review Log: cycle N appended to story-NN (backend APPROVED, frontend BLOCKED with 4 issues) ✓
```

**Failure mode**: if you cannot write to the story file (disk full, permissions, merge conflict with a concurrent BMad edit), do NOT silently proceed. Surface the failure, retry once, and if the second attempt fails, escalate — the Review Log is the project-side audit trail, and a silent miss means a post-mortem has no record of what the reviewer caught.

---

## Stage 5.2 — Story validation

Before marking PASSED, verify:
- Every acceptance criterion from the spec is implemented and tested
- Backend tests comprehensive (happy + validation + RLS if user-scoped)
- Frontend tests comprehensive (happy + error + edge cases, no `waitForTimeout`, no `serial`)
- Both reviewers returned `VERDICT: APPROVED`
- Security checklist items from the coder's pre-handoff checklist are satisfied

When all five hold, proceed to Stage 6 (closeout).
