---
name: kiat-review-backend
description: >
  Structured backend code review for Kiat stories (Go + Gin + Clean
  Architecture + Bun ORM + Venom tests). Use this skill whenever a
  backend-coder agent reports code ready for review, or when a human reviewer
  wants a systematic quality gate on a backend diff. Checks spec compliance,
  Clean Architecture layering, API contract correctness, database migrations,
  row-level security, error handling, logging, and Venom test coverage, and
  emits a machine-parseable 3-way verdict that Team Lead parses deterministically.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Backend Code Review

## Why this skill exists

Backend reviews on Kiat stories have two failure modes: superficial ("looks good, merging") and exhaustive-but-unfocused (the reviewer gets lost in nits and misses the one real bug). This skill is tuned against both. It gives a consistent phased protocol so every review covers the same ground, and it emits a 3-way verdict in a fixed format so Team Lead can route the outcome deterministically — no ambiguous "mostly good?" outcomes.

The checklist is deliberately external to this file. When you're running the review you read it from `references/checklist.md`; it lives there because it's 100+ items long and would bury the protocol if it were inline. Progressive disclosure: SKILL.md is the workflow, `references/checklist.md` is the rules.

## When to invoke

- A backend coder agent has reported code ready for review.
- A human wants a systematic quality gate on a backend diff before merging.
- Team Lead is running defense-in-depth on a story that passed `kiat-validate-spec` but touches critical paths (auth, payments, migrations).

## The review process

### Phase 1 — Read spec and understand the contract

Before looking at code, read the story spec at `delivery/epics/epic-X/story-NN.md`. Extract:
- the acceptance criteria the coder was aiming at,
- the API contracts they were supposed to implement,
- any database changes they were supposed to make,
- the failure modes the spec enumerated.

Without this, the rest of the review is guesswork — you can spot code smells without the spec but you can't verify that the code actually delivers what was asked for.

### Phase 2 — Verify the coder's test-patterns acknowledgment

The backend coder runs `kiat-test-patterns-check` at Step 0.5 of its workflow and emits a `TEST_PATTERNS: ACKNOWLEDGED` block in its handoff, listing which test-pattern blocks applied to this story. Your job is to cross-check:

1. **Grep the handoff for `TEST_PATTERNS: ACKNOWLEDGED`.** If it's missing, the handoff is incomplete — return `VERDICT: BLOCKED` citing the missing acknowledgment. Do not continue the review.
2. **For each block the coder loaded, verify the acknowledgment paragraph is verbatim.** Paraphrased or rewritten acknowledgments indicate the coder either didn't read the block or tried to fudge the check. Flag it as `BLOCKED`.
3. **Cross-check the acknowledged rules against the actual diff.** If the coder acknowledged Block F (Venom) rules but the diff contains a Venom test using real DB connections instead of mocks, that's drift — flag it with a file:line reference and return `BLOCKED`. The acknowledgment is written evidence the coder knew the rule, so a violation is a protocol issue, not just a bug.

This phase is fast when the coder did it right (30 seconds of grep). It's the phase that catches the worst failures when they didn't.

### Phase 3 — Apply the checklist

Read [`references/checklist.md`](references/checklist.md) and work through each category in order. Categories are ordered by blast radius — a migration bug or an RLS failure is much worse than a naming nit, so catching the high-impact categories first means you flag the right things as `BLOCKED`.

Load the checklist once at the start of the phase, not item by item. As you work through the code diff, keep the checklist open and check each category rather than trying to memorize 80 items.

### Phase 4 — Decide the verdict

Apply the decision logic below, then emit the output in the format below.

## Decision logic

| Situation | Verdict |
|---|---|
| All applicable checklist items pass, no concerns | `APPROVED` |
| Checklist passes but a judgment call needs human arbitration (architectural question, spec ambiguity uncovered during review, non-blocking performance tradeoff) | `NEEDS_DISCUSSION` |
| Any applicable checklist item fails with a concrete fix required | `BLOCKED` |
| You're unsure whether something is a problem | `NEEDS_DISCUSSION` — don't hide doubt behind `APPROVED` |
| You find one blocker plus some discussion points | `BLOCKED` takes precedence; mention the discussion points in the body |

There are three outcomes. If you catch yourself wanting a fourth — "approved but..." or "mostly blocked" — you're either unsure (`NEEDS_DISCUSSION`) or you found an issue (`BLOCKED`). Pick one.

## Output format

The first line of your output is parsed by Team Lead. It is one of three exact strings:

- `VERDICT: APPROVED`
- `VERDICT: NEEDS_DISCUSSION`
- `VERDICT: BLOCKED`

### If `APPROVED`

```
VERDICT: APPROVED

Spec compliance: all acceptance criteria met ✓
Test patterns: TEST_PATTERNS: ACKNOWLEDGED verified, no drift detected ✓
Database: migration <file>, RLS policy, idempotent, proper indexes ✓
Architecture: Clean Arch 4 layers, DI in main.go, interfaces used ✓
API contracts: HTTP method, path, request/response schemas match spec ✓
Security: RLS enforced, no secrets, input validation, parameterized queries ✓
Error handling: domain errors → HTTP status codes, no internal leakage ✓
Tests: <N> Venom tests (happy path + errors + RLS + auth) ✓
Clerk-auth skill: <NOT_APPLICABLE | PASSED>
```

The `Clerk-auth skill:` line reports whether you invoked `kiat-clerk-auth-review`. If the diff touches no auth-adjacent code, write `NOT_APPLICABLE`. If it does, you must invoke the Clerk skill and merge its verdict into yours.

### If `NEEDS_DISCUSSION`

```
VERDICT: NEEDS_DISCUSSION

Code works, tests pass, checklist clean. Needs Team Lead arbitration on:

1. <Category>: <summary> (file:line)
   - <the specific pattern or concern>
   - <why it might not be right but isn't clearly wrong>
   - Question: <the specific decision needed>

2. ...

Not blocking merge. Awaiting Team Lead / tech-spec-writer / user decision.
```

### If `BLOCKED`

```
VERDICT: BLOCKED

1. <Category>: <summary> (file:line)
   - <the concrete problem>
   - <the specific fix>

2. ...
```

List each blocker with a file:line reference and the fix. Vague blockers ("the architecture feels wrong") aren't actionable — be specific about what changes are needed.

## Merging with the Clerk auth skill

If the diff touches any auth-adjacent code, invoke [`kiat-clerk-auth-review`](../kiat-clerk-auth-review/SKILL.md) after Phase 3 and merge its verdict into yours:

| Your verdict | Clerk verdict | Combined verdict |
|---|---|---|
| APPROVED | PASSED | APPROVED |
| APPROVED | DISCUSSION | NEEDS_DISCUSSION |
| APPROVED | BLOCKED | BLOCKED (Clerk wins) |
| NEEDS_DISCUSSION | any | NEEDS_DISCUSSION or BLOCKED (worst case) |
| BLOCKED | any | BLOCKED (list both in the body) |

Whichever skill is stricter wins. Include a `Clerk-auth skill:` line in the body noting the Clerk verdict — don't hide it.

## Calibration notes

- The checklist is long because backend has many failure modes. It's not a suggestion that you nitpick — it's a map of the surface area. Skim what's obviously fine, focus on what's non-trivial.
- A "small PR" is not a reason to skip security checks. Migration bugs and RLS failures don't care about diff size.
- "Will fix in next PR" is not a valid outcome. Either the issue is fine to merge (say so and mark `APPROVED` with a note) or it isn't (mark `BLOCKED`).
- When you're unsure whether something is intentional, ask the coder before deciding — `NEEDS_DISCUSSION` exists specifically for this.
- Trust the toolchain on things the toolchain catches (lint, typecheck, test runners). Your value is in the judgment items: architecture, security, spec compliance, and drift from acknowledged rules.
