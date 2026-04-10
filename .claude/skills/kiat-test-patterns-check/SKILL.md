---
name: kiat-test-patterns-check
description: >
  Forced-response test patterns self-check. Invoked by kiat-backend-coder and
  kiat-frontend-coder at Step 0.5 (after context budget check, BEFORE writing
  any code or tests). Converts "did you read testing.md?" from a trust question
  into a forced acknowledgment via scope-detection + selective block loading.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Test Patterns Self-Check (Router)

**Purpose:** `delivery/specs/testing.md` has 26+ anti-flakiness rules. Coders skim them, forget under pressure, or decide "this story doesn't need it". This skill converts the passive checklist into a **forced acknowledgment per applicable pattern**, loaded selectively to keep context budget under control.

**When invoked:** by `kiat-backend-coder` or `kiat-frontend-coder` at Step 0.5 — after the context budget check, BEFORE planning or writing any test.

**Output:** `TEST_PATTERNS: ACKNOWLEDGED` on line 1, followed by scope-detection answers and acknowledgment blocks for every applicable pattern.

---

## How It Works (Selective Loading)

Unlike a monolithic checklist, this skill is a **router**. It works in 3 steps:

1. **Read this SKILL.md** (short — scope detection questions + block registry)
2. **Answer the 9 scope-detection questions** in writing (yes / no per question)
3. **For every `yes`, Read ONLY the corresponding block file** from `blocks/`

This keeps context load small: a story that only involves forms and Playwright E2E loads 2 block files (A + E), not 9. Average story loads 3-5 blocks.

---

## Step 1: Scope Detection (Answer All 9)

Read the story spec. For each question below, answer **yes** or **no** in writing:

1. **A.** Does this story involve a form or input fields? *(yes / no)*
2. **B.** Does this story involve auto-save (`useAutoSave` or "saves as user types")? *(yes / no)*
3. **C.** Does this story involve Clerk auth, protected routes, or `useAppAuth`? *(yes / no)*
4. **D.** Does this story involve user-scoped data / RLS (user can't see other users' data)? *(yes / no)*
5. **E.** Does this story involve Playwright E2E tests? *(yes / no)*
6. **F.** Does this story involve Venom backend tests? *(yes / no)*
7. **G.** Does this story involve async mutations, `useMutation`, PATCH endpoints, or optimistic locking (`updated_at`)? *(yes / no)*
8. **H.** Does this story involve file upload, S3, or MinIO? *(yes / no)*
9. **I.** Does this story involve multi-step wizards or stepper UI with state persistence? *(yes / no)*

---

## Step 2: Load Applicable Blocks

For each question answered `yes` in Step 1, **Read the corresponding block file** from the `blocks/` directory:

| ID | Topic | File |
|---|---|---|
| **A** | Forms / input fields | [`blocks/block-a-forms.md`](blocks/block-a-forms.md) |
| **B** | Auto-save | [`blocks/block-b-autosave.md`](blocks/block-b-autosave.md) |
| **C** | Clerk auth | [`blocks/block-c-clerk.md`](blocks/block-c-clerk.md) |
| **D** | RLS / user-scoped data | [`blocks/block-d-rls.md`](blocks/block-d-rls.md) |
| **E** | Playwright E2E | [`blocks/block-e-playwright.md`](blocks/block-e-playwright.md) |
| **F** | Venom backend tests | [`blocks/block-f-venom.md`](blocks/block-f-venom.md) |
| **G** | Async mutations / locking | [`blocks/block-g-mutations.md`](blocks/block-g-mutations.md) |
| **H** | File upload / S3 / MinIO | [`blocks/block-h-file-upload.md`](blocks/block-h-file-upload.md) |
| **I** | Multi-step wizards | [`blocks/block-i-wizards.md`](blocks/block-i-wizards.md) |

**Rule (per CLAUDE.md meta-rule #4):** only load blocks where your Step 1 answer was `yes`. Do NOT load all 9 to "be safe" — that defeats the selective design. A 3-block load costs ~3x less context than loading all 9.

---

## Step 3: Emit Acknowledgment

Each block file contains a short rule summary and a **Required acknowledgment** paragraph. You MUST paste the acknowledgment paragraph verbatim into your output.

Your final output format:

```
TEST_PATTERNS: ACKNOWLEDGED

Story: story-NN-<slug>

Scope detection:
  A. Forms/input fields:        YES
  B. Auto-save:                 YES
  C. Clerk auth:                NO
  D. RLS:                       YES
  E. Playwright E2E:            YES
  F. Venom backend tests:       YES
  G. Async mutations / locking: YES
  H. File upload:               NO
  I. Multi-step wizards:        NO

Applicable blocks: A, B, D, E, F, G (6 blocks loaded)

=== Block A (Forms) ===
[verbatim acknowledgment from block-a-forms.md]

=== Block B (Auto-save) ===
[verbatim acknowledgment from block-b-autosave.md]

... (one block per YES)

→ Proceeding to Step 1 (read spec).
```

---

## Enforcement Rules

1. **No skipping.** If a scope answer is `yes`, the corresponding block MUST be loaded and its acknowledgment MUST appear verbatim in your output. Paraphrasing is not acceptable — the rule text is load-bearing and the reviewer will grep for it.

2. **All-NO is suspicious.** If every scope answer is `no`, justify why in writing (e.g., "pure config refactor, no tests needed"). A story with no applicable test patterns is rare and Team Lead may flag it.

3. **Audit trail.** Your handoff to the reviewer MUST include the full `TEST_PATTERNS: ACKNOWLEDGED` block. The reviewer greps for this line and cross-checks each loaded block against your actual implementation.

4. **Drift detection.** If your actual code violates an acknowledgment you made (e.g., you acknowledged Block E rules but used `waitForTimeout` in a test), the reviewer flags it as `VERDICT: BLOCKED` with reference to the specific block you violated. This is a protocol violation, not just a bug.

---

## Notes

- The selective loading is designed to keep context budget small. Load only what applies.
- Blocks are short (30-60 lines each) and self-contained. You can load them in parallel if multiple apply.
- If a new pitfall is discovered, add a new block file under `blocks/` and register it in the table above. Also update `delivery/specs/testing.md` with the reference.
- The forced-response format works because it converts "did you read it?" from a trust question into a textual evidence question. The acknowledgment is either in the output or it isn't.
