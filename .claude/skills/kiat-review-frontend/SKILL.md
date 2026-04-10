---
name: kiat-review-frontend
description: >
  Structured frontend code review for Kiat stories (Next.js App Router + React
  + TypeScript + Shadcn/UI + Tailwind). Use this skill whenever a
  frontend-coder agent reports code ready for review, or when a human reviewer
  wants a systematic quality gate on a frontend diff. Checks spec compliance,
  design system adherence, accessibility (WCAG AA), responsive behavior, hooks
  and state patterns, error handling, forms, Playwright E2E tests, and
  performance. Emits a machine-parseable 3-way verdict that Team Lead parses
  deterministically.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Frontend Code Review

## Why this skill exists

Frontend reviews on Kiat stories are harder than backend reviews because the failure modes are more subjective: a design that's almost right, an accessibility issue that only a screen-reader user would hit, a hook pattern that works today but will break on re-render next week. Without a structured protocol, reviews drift into personal taste — and review quality becomes reviewer-dependent.

This skill gives a consistent phased protocol and externalizes the detailed checklist so progress through the review is tracked rather than improvised. The 3-way verdict format means Team Lead can route outcomes without parsing prose.

The checklist lives in `references/checklist.md`. Read it once at the start of Phase 3; referring back to it category by category is much faster than trying to remember 100+ items.

## When to invoke

- A frontend coder agent has reported code ready for review.
- A human wants a systematic quality gate on a frontend diff before merging.
- Team Lead is running defense-in-depth on a story that touches critical user-facing paths (auth, payments, accessibility-sensitive forms).

## The review process

### Phase 1 — Read spec and design system

Before looking at code, read:
- the story spec at `delivery/epic-X/story-NN.md` — for acceptance criteria, Figma references, and the intended user flows,
- the project design system at [`delivery/specs/design-system.md`](../../../delivery/specs/design-system.md) — for color tokens, spacing scale, typography rules, and component conventions.

Reading the design system matters because "this uses the wrong color" is only a meaningful comment if you know what the right color is. Without the spec, you'll flag correct code as wrong; without the design system, you'll miss real drift.

### Phase 2 — Verify the coder's test-patterns acknowledgment

The frontend coder runs `kiat-test-patterns-check` at Step 0.5 and emits a `TEST_PATTERNS: ACKNOWLEDGED` block in its handoff. Your job:

1. **Grep the handoff for `TEST_PATTERNS: ACKNOWLEDGED`.** If it's missing, return `VERDICT: BLOCKED` citing the missing block and stop.
2. **Verify each loaded block's acknowledgment is verbatim.** Paraphrased acknowledgments are a signal the coder didn't actually load the block. Flag as `BLOCKED`.
3. **Cross-check the acknowledged rules against the code.** If the coder acknowledged Block E (Playwright) rules but the test file contains `page.waitForTimeout(500)`, that's drift from written commitment — flag with file:line and return `BLOCKED`.

This phase is fast when the coder did it right. It exists because the worst test flakiness bugs slip past reviews that skip it.

### Phase 3 — Apply the checklist

Read [`references/checklist.md`](references/checklist.md) and work through each category in order. Categories are ordered by blast radius: accessibility and spec compliance failures hit real users, while naming nits are cosmetic.

Trust the toolchain on anything the toolchain catches (`tsc --noEmit`, `eslint`, `prettier`, test runners). Your value in a review is in judgment items — architecture, accessibility, design compliance, drift from acknowledged rules — not in restating what the linter already said.

### Phase 4 — Decide the verdict

Apply the decision logic below and emit the output in the format below.

## Decision logic

| Situation | Verdict |
|---|---|
| All applicable checklist items pass, no concerns | `APPROVED` |
| Checklist passes but a judgment call needs human arbitration (Figma vs design-system ambiguity, UX tradeoff, accessibility edge case, performance concern) | `NEEDS_DISCUSSION` |
| Any applicable checklist item fails with a concrete fix required | `BLOCKED` |
| You're unsure whether something is a problem | `NEEDS_DISCUSSION` — don't hide doubt behind `APPROVED` |
| You find one blocker plus some discussion points | `BLOCKED` takes precedence; list the discussion points in the body too |

There are three outcomes. If you want a fourth, you're either unsure (`NEEDS_DISCUSSION`) or you found an issue (`BLOCKED`) — pick one.

## Output format

The first line of your output is parsed by Team Lead. It is one of three exact strings:

- `VERDICT: APPROVED`
- `VERDICT: NEEDS_DISCUSSION`
- `VERDICT: BLOCKED`

### If `APPROVED`

```
VERDICT: APPROVED

Spec compliance: all acceptance criteria met, UI matches Figma ✓
Test patterns: TEST_PATTERNS: ACKNOWLEDGED verified, no drift ✓
Components: Shadcn primitives used, TypeScript fully typed, RSC boundary correct ✓
Styling: design tokens only, no hardcoded values, responsive at mobile/tablet/desktop ✓
Accessibility: labels, ARIA, keyboard navigation, contrast verified ✓
Hooks: useQuery cache keys correct, useMutation invalidates, stable deps ✓
E2E: <N> Playwright tests (happy path + errors + edge cases) ✓
Performance: no unnecessary re-renders, no memory leaks, images optimized ✓
Clerk-auth skill: <NOT_APPLICABLE | PASSED>
```

### If `NEEDS_DISCUSSION`

```
VERDICT: NEEDS_DISCUSSION

Code works, tests pass, checklist clean. Needs Team Lead arbitration on:

1. <Category>: <summary> (file:line)
   - <the specific pattern or concern>
   - <why it might not be right but isn't clearly wrong>
   - Question: <the specific decision needed>

2. ...

Not blocking merge. Awaiting Team Lead / BMAD / designer decision.
```

### If `BLOCKED`

```
VERDICT: BLOCKED

1. <Category>: <summary> (file:line)
   - <the concrete problem>
   - <the specific fix>

2. ...
```

List each blocker with a file:line reference and a specific fix. Vague blockers ("the component feels wrong") aren't actionable — be specific.

## Merging with the Clerk auth skill

If the diff touches any auth-adjacent code, invoke [`kiat-clerk-auth-review`](../kiat-clerk-auth-review/SKILL.md) after Phase 3 and merge its verdict into yours:

| Your verdict | Clerk verdict | Combined verdict |
|---|---|---|
| APPROVED | PASSED | APPROVED |
| APPROVED | DISCUSSION | NEEDS_DISCUSSION |
| APPROVED | BLOCKED | BLOCKED (Clerk wins) |
| NEEDS_DISCUSSION | any | NEEDS_DISCUSSION or BLOCKED (worst case) |
| BLOCKED | any | BLOCKED (list both in the body) |

The stricter verdict wins. Include a `Clerk-auth skill:` line in the body — don't hide the Clerk outcome.

## Calibration notes

- Accessibility isn't a feature to add later. It's a baseline that affects real users from day one — flagging a missing label at review time costs nothing, adding it after launch costs a retrofit PR and may miss edge cases.
- Responsive behavior isn't a "mobile-QA later" item. Test the diff at the project's breakpoints at review time — if the spec says 320/640/1024, check those three.
- "Will refactor next PR" is not a valid review outcome. Either the code is fine to merge (mark `APPROVED`) or it isn't (mark `BLOCKED`).
- When Figma contradicts the design system, that's a `NEEDS_DISCUSSION` — the designer needs to decide which wins, not the reviewer.
- E2E flakiness is the reviewer's problem to help solve. If a test uses `waitForTimeout`, don't just flag it — point the coder at the relevant test-patterns block so they can fix the pattern, not the symptom.
