---
name: kiat-test-patterns-check
description: >
  Forced-response test patterns self-check for Kiat coders. Use before writing
  any test or production code to confirm which anti-flakiness patterns apply to
  the current story, then load only the relevant rule blocks. Triggers at
  Step 0.5 of the Kiat coder workflow, right after the context budget check.
  Catches the "I skimmed testing.md last week" failure mode by requiring a
  per-pattern verbatim acknowledgment that the reviewer can grep for later.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Test Patterns Self-Check (Router)

## Why this skill exists

`delivery/specs/testing.md` carries the project's accumulated anti-flakiness rules — most of them learned from real production incidents. Every rule has a cost in time lost when it was discovered and a cost in reliability when it was violated. Yet the file is long, and coders under time pressure tend to skim it or assume "this story doesn't need it". By the time a reviewer catches the drift, the fix is a 45-minute cycle instead of a 30-second self-correction.

This skill turns "did you read testing.md?" from a trust question into a textual-evidence question. You answer 9 short scope questions, load only the rule blocks that apply, and paste each block's acknowledgment paragraph verbatim into your handoff. The reviewer greps for those paragraphs later and cross-checks them against your actual code. If the acknowledgment is absent or the code contradicts it, the drift is mechanical to detect.

The selective loading matters because Kiat coders operate under a 25k-token context budget. Reading all 26+ rules for every story would blow the budget on most features. Loading only the applicable blocks keeps a typical story at 3-5 blocks (~3-5k tokens) instead of the full 26.

## How to use

The workflow is 3 steps. Do them in order — the scope detection comes before loading anything, because loading blocks you don't need wastes budget you may need later.

### Step 1 — Scope detection

Read the story spec. For each of the 9 questions below, answer `yes` or `no` **in writing** in your output. Hedging ("maybe", "partially") is fine if you explain the edge case; the point is to force a conscious decision, not to pass a quiz.

1. **A.** Does this story involve a form or input fields?
2. **B.** Does this story involve auto-save (any `useAutoSave` usage, or "saves as user types")?
3. **C.** Does this story involve Clerk auth, protected routes, or the project's auth wrapper hook?
4. **D.** Does this story involve user-scoped data (RLS — "User B cannot see User A's rows")?
5. **E.** Does this story involve Playwright E2E tests?
6. **F.** Does this story involve Venom backend tests?
7. **G.** Does this story involve async mutations, `useMutation`, PATCH endpoints, or optimistic locking via `updated_at`?
8. **H.** Does this story involve file upload (S3, MinIO, or any multipart path)?
9. **I.** Does this story involve multi-step wizards or stepper UI with state persistence?

### Step 2 — Load applicable blocks

For each `yes` in Step 1, read the corresponding file from `references/`:

| ID | Topic | File |
|---|---|---|
| **A** | Forms / input fields | [`references/block-a-forms.md`](references/block-a-forms.md) |
| **B** | Auto-save | [`references/block-b-autosave.md`](references/block-b-autosave.md) |
| **C** | Clerk auth | [`references/block-c-clerk.md`](references/block-c-clerk.md) |
| **D** | RLS / user-scoped data | [`references/block-d-rls.md`](references/block-d-rls.md) |
| **E** | Playwright E2E | [`references/block-e-playwright.md`](references/block-e-playwright.md) |
| **F** | Venom backend tests | [`references/block-f-venom.md`](references/block-f-venom.md) |
| **G** | Async mutations / optimistic locking | [`references/block-g-mutations.md`](references/block-g-mutations.md) |
| **H** | File upload / S3 / MinIO | [`references/block-h-file-upload.md`](references/block-h-file-upload.md) |
| **I** | Multi-step wizards | [`references/block-i-wizards.md`](references/block-i-wizards.md) |

Load only the blocks you answered `yes` to. Loading all 9 "to be safe" defeats the design — it costs roughly 3× the context of a targeted load and gives the reviewer no signal about what you actually thought was relevant.

### Step 3 — Emit the acknowledgment

Each block file ends with a short **Required acknowledgment** paragraph. Copy it verbatim into your output. Verbatim matters here because the reviewer runs a literal grep against your handoff — paraphrased text looks like drift and triggers a follow-up. The acknowledgment text is short by design; pasting it costs almost nothing.

Your output format:

```
TEST_PATTERNS: ACKNOWLEDGED

Story: story-NN-<slug>

Scope detection:
  A. Forms/input fields:         YES
  B. Auto-save:                  YES
  C. Clerk auth:                 NO
  D. RLS:                        YES
  E. Playwright E2E:             YES
  F. Venom backend tests:        YES
  G. Async mutations / locking:  YES
  H. File upload:                NO
  I. Multi-step wizards:         NO

Applicable blocks: A, B, D, E, F, G (6 blocks loaded)

=== Block A (Forms) ===
[verbatim acknowledgment from block-a-forms.md]

=== Block B (Auto-save) ===
[verbatim acknowledgment from block-b-autosave.md]

... (one block per YES)

→ Proceeding to spec reading (Step 1 of coder workflow).
```

## What happens next — drift detection (behavioral, not textual)

When the reviewer receives your handoff, they do three things with this block — and only the first is a textual check:

1. **Grep for `TEST_PATTERNS: ACKNOWLEDGED`** — if it's missing, the handoff is incomplete and the reviewer returns a `BLOCKED` verdict without reading further.
2. **Grep each block's verbatim acknowledgment paragraph** — paraphrase is `BLOCKED` (it suggests you didn't actually open the block file).
3. **Behavioral cross-check: for each acknowledged block, `rg` the diff for the block's forbidden patterns.** This is the real gate. The reviewer does NOT take your acknowledgment at face value — they grep the code for the specific anti-patterns the block lists, and any hit is a `BLOCKED` verdict with a `file:line` reference.

**Examples of the behavioral cross-check:**

| Block acknowledged | Reviewer's grep on the diff | Drift signal |
|---|---|---|
| Block E (Playwright) | `rg -n "waitForTimeout\|describe\\.serial" frontend/e2e/` | Any match → BLOCKED |
| Block F (Venom) | `rg -n "real-db\|db\\.Connect\|sqlx\\.Connect" backend/` | Any match → BLOCKED |
| Block D (RLS) | `rg -n "SELECT .* FROM <table>" backend/` without a `user_id` scope clause | Any match → BLOCKED |
| Block G (mutations) | PATCH handlers without `WHERE updated_at = ?` | Match → BLOCKED |

**Consequence for you (the coder):** pasting the acknowledgment paragraph is necessary but not sufficient. If you acknowledge Block E and then write `page.waitForTimeout(500)`, the reviewer catches it mechanically — the ceremony protects the rule system, not your throughput. **The acknowledgment is a commitment, not a token.** If you cannot honestly commit to the rule, don't load the block, and scope detection honestly.

Reviewers follow the full protocol in [`kiat-backend-reviewer.md`](../../agents/kiat-backend-reviewer.md) Step 5 and [`kiat-frontend-reviewer.md`](../../agents/kiat-frontend-reviewer.md) Step 6 — they contain the concrete grep recipes per block.

## Edge cases

**Every answer is `no`.** Rare but possible — e.g., a pure config refactor, a README update, a log message tweak. If every scope answer is `no`, write one sentence explaining why (so the reviewer knows you looked and decided nothing applied, versus skipped the skill entirely). The reviewer will usually accept it; if the story has any test implications, they'll push back.

**A question is ambiguous.** If you can't decide yes or no — for example, "the spec mentions a form but I'm only wiring up the submit handler, not the inputs" — answer `yes` and load the block. The cost of an unnecessary block is ~500 tokens; the cost of missing a rule is a 45-minute retry cycle.

**The story needs a pattern not in the registry.** If you find a failure mode that isn't covered by any block, add a new block file under `references/`, register it in the table above, and document the underlying rule in `delivery/specs/testing.md`. The registry and the spec should stay in sync — if a new block exists here but not there, future coders won't know the rule is mandatory.

## Maintenance

- Block files are short by design (roughly 30-60 lines each). If a block grows past ~80 lines, split it or move detail into the spec file it references.
- Acknowledgment paragraphs are the load-bearing text. Changing their wording means reviewers must update their grep; update both in the same commit.
- When a new production incident surfaces a new rule, add the block before the story that would have been saved by it lands — otherwise the skill runs behind reality instead of ahead of it.
