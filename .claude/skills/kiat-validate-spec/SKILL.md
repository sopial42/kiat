---
name: kiat-validate-spec
description: >
  Pre-coding spec validation for Kiat stories. Use this skill to detect
  ambiguity, missing acceptance criteria, undefined edge cases, vague verbs,
  and cross-layer contract mismatches before any coder is launched. The
  cheapest place to fix a bad spec is while BMAD is still in the conversation
  and no code has been written yet — a 5-minute clarification here prevents
  45-minute retry cycles downstream. Reach for this whenever a new story
  arrives, when an existing story is being re-scoped, or when a coder escalates
  that the spec isn't answerable as written.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Spec Validation

## Why this skill exists

The earliest failure point in the Kiat pipeline is an ambiguous story spec. A single vague word — "validate", "handle", "process" — can trigger a multi-cycle review ping-pong because the coder interprets it one way and the reviewer expects another. Every such cycle burns ~45 minutes of agent time and breaks the flow state of whoever is orchestrating.

This skill catches those ambiguities *before* any coder runs. When BMAD is still in the loop, a clarification costs five minutes; once a coder has planned around a misreading, the same clarification costs a retry cycle plus the cognitive overhead of unwinding the wrong mental model. The math heavily favours catching things early, so the skill is deliberately tuned to err on the side of flagging — a false positive costs a question, a false negative costs a retry.

**When to invoke:** At Phase 0 of the Team Lead workflow, after the pre-flight context budget check passes, before launching any coder. Also use it when a coder escalates mid-story with "I can't tell what this means" — the skill's checklist usually surfaces the ambiguity quickly.

**Input:** the story spec file at `delivery/epics/epic-X/story-NN.md`.

**Output:** `SPEC_VERDICT: CLEAR | NEEDS_CLARIFICATION | BLOCKED` on line 1, followed by a short report.

## The checklist

Run each category. The categories are ordered so that structural gaps (which force `BLOCKED`) surface before ambiguity questions (which resolve to `NEEDS_CLARIFICATION`).

### 1. Acceptance criteria completeness

A coder cannot know when a story is "done" unless the spec says so. Check that:

- Every acceptance criterion is **testable** — it can be converted into a Venom or Playwright assertion. "User can save the form" is not testable; "`POST /resource` returns 201 with `{id, created_at}`" is.
- The success state is **explicit** — the spec describes what done looks like, not just what the feature does.
- Failure states are **enumerated** — the spec lists which specific errors the user should see, not just "handle errors gracefully".
- Empty and loading states are **defined** — the spec describes what the UI shows when there is no data, and what it shows while fetching.

If any of these are structurally missing (zero acceptance criteria, no mention of failure cases), that's a `BLOCKED` — the coder has nothing to aim at.

### 2. Vague verb scan

Grep the spec literally for the verbs below. They hide in well-written prose and are the most common source of review ping-pong because each one can mean five different things.

| Verb | Why it's dangerous |
|---|---|
| handle | "Handle errors" — show toast? retry? silent fail? |
| validate | "Validate email" — format regex? DNS lookup? disposable domain block? |
| process | "Process the file" — sync? async? streaming? chunks? |
| manage | "Manage user state" — stored where? for how long? |
| support | "Support mobile" — which breakpoints? which devices? |
| optimize | "Optimize performance" — measured how? what threshold? |
| ensure | "Ensure security" — against which threat model? |
| proper | "Proper error handling" — defined by whom? |
| robust | "Robust retry logic" — how many attempts? what backoff? |
| efficient | "Efficient query" — what's the current baseline? |
| reasonable | "Reasonable timeout" — 5s? 30s? 5 min? |

Run the scan mechanically — every story should be grepped even if it looks fine. If a match appears and the spec doesn't define the precise behavior within ~3 lines of the match, flag it as `NEEDS_CLARIFICATION`. One vague verb is enough; you don't need to find a pattern.

### 3. API contract completeness (if the story touches the backend)

Coders building an endpoint need every contract detail or they'll invent one. Check that the spec specifies:

- HTTP method and exact path (including any path parameters)
- Request schema — every field named, with type and required/optional
- Response schema — both success and error shapes, with types
- Status codes for each scenario (201, 400, 409, 404, 500 as applicable)
- Internal error codes beyond just HTTP status — the named codes the frontend will parse. Project conventions live in [`delivery/specs/api-conventions.md`](../../../delivery/specs/api-conventions.md).
- Idempotency behavior for PATCH/PUT — is a replay safe?
- Rate limiting rules for high-value endpoints (if applicable)

Missing HTTP method, missing path, or missing status-code-for-error-case are usually `BLOCKED` — the coder can't proceed without inventing a contract. Missing error code names are usually `NEEDS_CLARIFICATION`.

### 4. Database contract completeness (if the story touches the DB)

Check that migrations, columns, and access rules are spelled out:

- Which tables are created or altered, and which columns (with precise types, e.g., `TIMESTAMPTZ` not "timestamp")
- Foreign keys and cascade behavior (`ON DELETE CASCADE` for owned data vs `RESTRICT` for shared)
- Row-level security scope — which rows can user X read? Project conventions live in [`delivery/specs/database-conventions.md`](../../../delivery/specs/database-conventions.md).
- Indexes on any columns that will be queried in hot paths
- Seed or fixture data if the tests need reference rows

### 5. UI contract completeness (if the story touches the frontend)

A UI story without a design reference forces the coder to invent a design. Check that the spec includes:

- A Figma reference (explicit file/frame URL, not "see design")
- A rough component tree — which design-system primitives to reuse vs which custom components to build
- Interaction states listed: hover, focus, disabled, loading, error
- Responsive breakpoints called out explicitly if they differ from the project defaults
- Accessibility notes (ARIA labels, keyboard navigation) for any non-trivial widget
- Auto-save vs manual save specified for forms

Missing Figma on a new-component story is usually `BLOCKED`. Missing interaction states is usually `NEEDS_CLARIFICATION`.

### 6. Cross-layer contract consistency

When a story touches backend and frontend together, the two sides have to agree. Read both sections and check:

- Field names match across the layers (camelCase versus snake_case mismatch is a silent bug)
- Types match (a backend `int64` doesn't serialize into a frontend `string` without coordination)
- Error shapes match (the frontend can parse the error codes the backend emits)
- Timestamp formats agree (project conventions are in [`delivery/specs/backend-conventions.md`](../../../delivery/specs/backend-conventions.md))

Any mismatch here is `BLOCKED` — one side will have to change before coding starts, and delaying that decision just puts the cost on whoever hits the merge conflict later.

### 7. Edge case enumeration

The spec should mention, even briefly, how the feature behaves at the edges:

- Concurrency: if two users edit the same resource, what happens?
- Network failure: offline, timeout, partial response
- Size boundaries: max length, max items, pagination thresholds
- Authorization edges: what can User B do with User A's resource?
- Empty input: empty string, empty array, null vs undefined
- Unicode and i18n: accents, right-to-left scripts, emoji in input

Missing all of these is a yellow flag, not automatically `BLOCKED`. One or two unaddressed edges is `NEEDS_CLARIFICATION`. If the story involves a PATCH endpoint and concurrency is never mentioned, that's specifically worth flagging — it's the single most common gap that causes data-loss bugs in review.

### 8. Testability

A story that can't be tested is a story that can't be verified as done. Check that:

- At least one happy-path scenario is described concretely (not "it should work")
- At least one error scenario is described with the expected response
- Test data seeding is explained if the preconditions are non-trivial
- The full E2E flow is documented if the feature is a multi-step journey

## Output format

The first line of your output is parsed by Team Lead to decide the next step, so it has to be one of three exact strings. The rest of the output is free-form human-readable.

**Line 1 is one of:**
- `SPEC_VERDICT: CLEAR`
- `SPEC_VERDICT: NEEDS_CLARIFICATION`
- `SPEC_VERDICT: BLOCKED`

### If `CLEAR`

```
SPEC_VERDICT: CLEAR

Story: story-NN-<slug>
Acceptance criteria: <N> listed, all testable
Vague verb scan: <N> matches (all defined in context)
API contract: <summary>
DB contract: <summary or "N/A">
UI contract: <summary or "N/A">
Cross-layer: <consistent or "N/A">
Edge cases: <list>
Testability: <summary>

→ Safe to launch coders.
```

### If `NEEDS_CLARIFICATION`

```
SPEC_VERDICT: NEEDS_CLARIFICATION

Story works conceptually but has ambiguities that will cause review ping-pong.
Returning to BMAD with specific questions — do not launch coders yet.

Questions for BMAD:

1. <Category>: <brief description> (line <N>)
   - <the specific ambiguity>
   - Question: <the specific clarification needed>
   - Recommendation: <if you have one>

2. ...
```

List each question concretely with a spec line reference. Concreteness matters: a question like "what do you mean by validate?" is easier to answer than "the spec is vague about validation".

### If `BLOCKED`

```
SPEC_VERDICT: BLOCKED

Story cannot proceed as written — fundamental gaps prevent a sensible coding
attempt.

1. <Gap category>
   - <what's missing>
   - <why it's structural, not just ambiguous>

2. ...

→ BMAD must rewrite this story before it can be validated.
```

## Decision logic

| Situation | Verdict |
|---|---|
| All checklist items pass | `CLEAR` |
| Minor ambiguities (1-4 vague verbs, missing edge cases) that BMAD can answer in a few minutes | `NEEDS_CLARIFICATION` |
| Structural gaps (no acceptance criteria, missing API contract, cross-layer mismatch, no Figma on a new-component story) | `BLOCKED` |
| You find one structural gap and several ambiguities | `BLOCKED` (structural gaps take precedence; list the ambiguities in the body too) |
| You're unsure whether something is a real problem | `NEEDS_CLARIFICATION` (never hide doubt behind `CLEAR`) |

## Notes on calibration

- This skill is deliberately fast — five minutes of scanning, not a deep architectural review. It's a cheap early gate, not a replacement for the reviewer's later checks.
- `NEEDS_CLARIFICATION` is the normal outcome on first pass, not a failure. Most real stories will come back with 1-3 clarifications; that's the skill doing its job. Don't apologize for returning questions.
- `BLOCKED` is rare and means BMAD wrote something that doesn't meet the minimum bar. Don't try to patch it — escalate to the user.
- The grep pass in Category 2 is the highest-yield mechanical step. Do it even when the spec reads smoothly — vague verbs hide well.
