---
name: kiat-validate-spec
description: >
  Pre-coding spec validation skill. Invoked by kiat-team-lead at Phase 0 BEFORE
  launching any coder. Detects ambiguity, missing acceptance criteria, undefined
  edge cases, vague verbs, and cross-layer contract mismatches in BMAD-written
  story specs. Catches the "what does 'valid email' mean?" class of failures at
  the point where fixing them is cheapest: BMAD is still in the conversation
  and no code has been written. Outputs a machine-parseable 3-way verdict.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Spec Validation Skill

**Purpose:** The earliest failure point in the Kiat pipeline is an ambiguous
BMAD spec. A single vague word ("validate", "handle", "process") can trigger a
multi-cycle review ping-pong downstream because the coder interprets it one
way and the reviewer expects another. This skill catches those ambiguities
**before** any coder is launched — when BMAD is still in the loop and a
5-minute clarification costs infinitely less than a 45-minute retry cycle.

**When invoked:** By `kiat-team-lead` in Phase 0, after the pre-flight context
budget check passes, BEFORE launching coders.

**Input:** The story spec file (`delivery/epic-X/story-NN.md`).

**Output:** `SPEC_VERDICT: CLEAR | NEEDS_CLARIFICATION | BLOCKED` on line 1
(machine-parseable, Team Lead parses deterministically).

---

## Spec Validation Checklist (Run every category)

### ✓ Category 1: Acceptance Criteria Completeness

- [ ] **Every acceptance criterion is testable** — each criterion can be
      converted to a Venom or Playwright assertion. "User can save the form"
      is NOT testable; "POST /patients returns 201 with {id, created_at}" is.
- [ ] **Success state is explicit** — spec says what "done" looks like, not
      just what the feature does.
- [ ] **Failure states are enumerated** — spec lists which errors the user
      should see, not just "handle errors gracefully".
- [ ] **Empty states defined** — spec says what the UI shows when there is no
      data (empty list, first visit, etc.).
- [ ] **Loading states defined** — spec says what the UI shows while fetching
      (skeleton, spinner, disabled button).

### ✓ Category 2: Vague Verb Scan (GREP EXPLICITLY)

Grep the spec for these vague verbs. Each match is a **potential BLOCKER**
unless the spec defines exactly what the verb means in context.

| Vague verb | Why it's dangerous |
|---|---|
| "handle" | "Handle errors" — how? Show toast? Retry? Silent fail? |
| "validate" | "Validate email" — format regex? DNS check? Disposable domain block? |
| "process" | "Process the file" — sync? async? streaming? chunks? |
| "manage" | "Manage user state" — stored where? For how long? |
| "support" | "Support mobile" — which breakpoints? Which devices? |
| "optimize" | "Optimize performance" — measured how? What threshold? |
| "ensure" | "Ensure security" — against which threat model? |
| "proper" | "Proper error handling" — defined by whom? |
| "robust" | "Robust retry logic" — how many attempts? With what backoff? |
| "efficient" | "Efficient query" — what's the current baseline? |
| "reasonable" | "Reasonable timeout" — 5s? 30s? 5min? |

**Rule:** If you find any of these verbs and the spec does NOT define the
precise behavior within 3 lines of the match, that's a `NEEDS_CLARIFICATION`.

### ✓ Category 3: API Contract Completeness (if backend work)

- [ ] **HTTP method explicit** — GET, POST, PATCH, DELETE named
- [ ] **Path explicit** — exact URL, including path params
- [ ] **Request schema complete** — every field named with type + required/optional
- [ ] **Response schema complete** — success shape AND error shapes
- [ ] **Status codes enumerated** — which status for which case (201, 400, 409, 404, 500)
- [ ] **Error codes named** — not just HTTP status, but the internal code
      (`INVALID_INPUT`, `DUPLICATE_EMAIL`, etc.)
- [ ] **Idempotency specified** — if PATCH/PUT, is it idempotent? Expected behavior on replay?
- [ ] **Rate limiting specified** — if high-value endpoint, what's the limit?

### ✓ Category 4: Database Contract Completeness (if DB work)

- [ ] **Migration scope explicit** — which tables created/altered
- [ ] **Columns named with types** — `created_at TIMESTAMPTZ` not "timestamp"
- [ ] **Foreign keys and cascade behavior specified** — `ON DELETE CASCADE` or `RESTRICT`?
- [ ] **RLS policy scope explicit** — which rows can user X see?
- [ ] **Indexes mentioned** — which columns queried frequently
- [ ] **Seeds/fixtures described** — if tests need reference data

### ✓ Category 5: UI Contract Completeness (if frontend work)

- [ ] **Figma reference included** — explicit file/frame URL, not "see design"
- [ ] **Component tree sketched** — which Shadcn components to use
- [ ] **Interaction states listed** — hover, focus, disabled, loading, error
- [ ] **Mobile breakpoints specified** — 320, 640, 1024 explicitly?
- [ ] **Accessibility notes included** — ARIA labels, keyboard nav
- [ ] **Auto-save / manual save specified** — if form, which mode?

### ✓ Category 6: Cross-Layer Contract Consistency

When a story touches both backend AND frontend:
- [ ] **Field names match** — backend `userId` vs frontend `user_id` = BLOCKER
- [ ] **Types match** — backend `int64` vs frontend `string` = BLOCKER
- [ ] **Error shapes match** — frontend can parse backend's error codes
- [ ] **Timestamps agree** — frontend expects `RFC3339Nano`, backend produces it

### ✓ Category 7: Edge Case Enumeration

- [ ] **Concurrency handling** — if 2 users edit same resource, what happens?
- [ ] **Network failure** — offline, timeout, partial response — expected behavior?
- [ ] **Size boundaries** — max length, max items, pagination threshold
- [ ] **Authorization edges** — what can User B do with User A's resource?
- [ ] **Empty input** — empty string, empty array, null vs undefined
- [ ] **Unicode / i18n** — accents, RTL, emoji in inputs

### ✓ Category 8: Testability

- [ ] **At least one happy path test scenario described** — concrete, reproducible
- [ ] **At least one error scenario described** — which error, which response
- [ ] **Test data seeding explained** — how to set up preconditions (if complex)
- [ ] **E2E flow documented** — if multi-step user journey, the full path

---

## Output Format (MACHINE-PARSEABLE — Team Lead parses first line)

**Line 1 MUST be exactly one of:**
- `SPEC_VERDICT: CLEAR`
- `SPEC_VERDICT: NEEDS_CLARIFICATION`
- `SPEC_VERDICT: BLOCKED`

---

**If CLEAR:**
```
SPEC_VERDICT: CLEAR

Story: story-NN-patient-form
Acceptance criteria: 7 listed, all testable ✓
Vague verb scan: 0 matches ✓
API contract: POST /patients, full schema, 3 error codes ✓
DB contract: migration 004, RLS policy defined, indexes ✓
UI contract: Figma link, component tree, 4 interaction states ✓
Cross-layer: field names/types consistent ✓
Edge cases: 5 enumerated (concurrency, network, size, auth, empty) ✓
Testability: happy path + 3 error scenarios described ✓

→ Safe to launch coders.
```

**If NEEDS_CLARIFICATION:**
```
SPEC_VERDICT: NEEDS_CLARIFICATION

Story works conceptually but has ambiguities that will cause review ping-pong.
Returning to BMAD with specific questions — do NOT launch coders yet.

Questions for BMAD:

1. Vague verb: "validate email" (line 34)
   - Format regex only? DNS lookup? Disposable domain block?
   - Recommendation: pick one, add to spec as "email validation rule".

2. Missing error code (line 52)
   - Spec says "return error if user exists" but no error code specified
   - Question: DUPLICATE_EMAIL (409)? INVALID_INPUT (400)? CONFLICT (409)?

3. Undefined empty state (frontend)
   - UI mockup shows patient list, but spec doesn't describe "no patients yet"
   - Question: show empty illustration + "Create your first patient" CTA?

4. Concurrency not addressed
   - PATCH endpoint — what if 2 users edit same patient simultaneously?
   - Question: optimistic locking (updated_at check)? Last-write-wins? 409 Conflict?

→ Waiting for BMAD clarification before proceeding.
```

**If BLOCKED:**
```
SPEC_VERDICT: BLOCKED

Story cannot proceed as-written — fundamental gaps prevent any sensible
coding attempt.

1. Missing acceptance criteria
   - Spec describes "the feature" in prose but lists zero acceptance criteria
   - A coder cannot know when the story is "done"

2. Cross-layer contract mismatch
   - Backend section: "POST /patients returns patient_id (int)"
   - Frontend section: "form expects UUID string from POST /patients"
   - One of these must change before coding starts

3. No Figma reference
   - UI work described in prose only ("a nice form with good spacing")
   - Frontend-coder cannot match an invisible design

→ BMAD must rewrite this story before it can be validated.
```

---

## Decision Logic (3-way)

| Situation | Verdict |
|---|---|
| All checklist items pass | `CLEAR` |
| Minor ambiguities (1-4 vague verbs, missing edge cases) → BMAD can answer in 5 min | `NEEDS_CLARIFICATION` |
| Structural gaps (no acceptance criteria, missing API contract, cross-layer mismatch, no Figma) | `BLOCKED` |
| You found 1 structural gap + several ambiguities | `BLOCKED` (structural gaps take precedence) |
| You're unsure whether something is a problem | `NEEDS_CLARIFICATION` (never hide doubt as CLEAR) |

---

## Notes

- This skill is **fast** on purpose. It's a 5-minute check that saves 45-minute
  retry cycles downstream. Err toward flagging, not flagging-free.
- `NEEDS_CLARIFICATION` is not a failure — it's the skill doing its job. Most
  stories will have 1-3 clarifications on first pass; that's normal and cheap.
- `BLOCKED` is rare and means BMAD wrote something that doesn't meet minimum
  bar (no acceptance criteria, no API contract, etc.). Escalate to user, don't
  try to patch.
- The grep pass in Category 2 is mechanical — do it even if the spec "looks
  fine". Vague verbs hide in well-written prose.
