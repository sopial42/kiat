# Story NN: [Title]

**Status**: 📝 Drafted

**Epic**: [Epic X](../_epic.md)

**Objective**: [What does this story deliver? 1-2 sentences]

**T-Shirt Size**: S / M / L

**Scope**: backend-only | frontend-only | both | infra

> The `**Status**:` line above is the single source of truth for this story's state. Values and transitions defined in [`../README.md#status-lifecycle`](../README.md#status-lifecycle). Team Lead flips it automatically as phases run.

---

## Business Context

> Section written by BMad (or by the user before the tech-spec-writer runs).
> The tech-spec-writer NEVER modifies, reformats, or moves this section — it
> only adds and enriches the technical sections below.
>
> Write this section in the project's business language. For French-domain
> projects (French users, French regulations, French-speaking stakeholders),
> writing in French preserves nuances that translation would flatten. The
> tech-spec-writer reads this section regardless of its language and writes
> the technical sections below in English (the framework default, aligned
> with code and API conventions).
>
> **⚠️ Required reading before this story (delete if not applicable)**:
> [`_epic.md` — Target architecture](./_epic.md#target-architecture) — this
> story [creates | extends | activates] the shared artifact described
> there. Follow the per-story evolution to avoid architecture choices that
> will be redone in a later story. Rule and rationale: [`../README.md#target-architecture`](../README.md#target-architecture).
>
> If this story touches an artifact that no other story in the epic
> touches (typical for independent backend fetchers, isolated migrations,
> standalone services), **delete the blockquote above** and proceed.

### User story

As a [persona], I want [goal], so that [value].

### Acceptance criteria (user-facing)

- [ ] [User-facing criterion: what the user can do, see, or experience]
- [ ] ...

### Personas & domain links

_Link only the entries that actually matter for this specific story. Don't list the full folder._

- Persona: [link to `delivery/business/personas.md#<persona>`]
- Domain term: [link to `delivery/business/glossary.md#<term>`]
- Business rule: [link to `delivery/business/business-rules.md#<rule>`]
- User journey this story is a slice of: [link to `delivery/business/user-journeys.md#<journey>`]

### Business rationale

[1-3 sentences: why this need exists, what pain it solves, why now.]

### Mockups

> Two valid shapes, pick one per story (never mix). Full rules:
> [`../README.md#mockups--how-ui-designs-flow-into-stories`](../README.md#mockups--how-ui-designs-flow-into-stories)
> and [`../../../kiat-how-to.md#5-visual-references--figma-urls-or-static-screenshots`](../../../kiat-how-to.md).

**Shape A — Live Figma URL** (use when the designer actively maintains Figma):

```
- [Screen A](https://figma.com/file/XXXX/...?node-id=YYYY)
- [Screen B — empty state](https://figma.com/file/XXXX/...?node-id=ZZZZ)
```

**Shape B — Static screenshots** (use when there's no active Figma, or the client doesn't use Figma):

```
- ![Screen A](../../business/mockups/story-NN/screen-a.png)
- ![Screen B — empty state](../../business/mockups/story-NN/screen-b-empty.png)
```

**No UI in this story**: write `No mockups — implementer uses the existing design system`.

Delete the two unused shapes above and keep only the one that applies. The frontend-coder reads whatever is present (WebFetch for Figma URLs, Read for PNGs since Claude is multimodal) and matches pixel-close.

---

## Skills

> Populated by `kiat-tech-spec-writer` when it writes the story.
> Read by `kiat-team-lead` at Phase 0b (context budget pre-flight) and by the coders at Step 1.
> See [`.claude/specs/available-skills.md`](../../.claude/specs/available-skills.md) for the registry of contextual skills.

**Base (auto-loaded by coder agents, no action needed):**
- `kiat-test-patterns-check` — Step 0.5 acknowledgment of applicable test patterns

**Contextual for this story:**

<!--
If no additional skills are needed for this story, write:
  No additional skills required.

Otherwise list each contextual skill from .claude/specs/available-skills.md with a one-line justification:
  - <skill-name> — <why this story needs it>

Example:
  - kiat-ui-ux-search — this story introduces a new card component that needs layout and typography recommendations
  - differential-review — this story touches auth middleware, adversarial security analysis warranted

Rule of thumb: be stingy. Every contextual skill adds tokens to the coder's context budget.
Only list skills the story genuinely needs. When in doubt, leave it out — the coder can escalate if missing.
-->

---

## Acceptance Criteria (technical)

> Written by the tech-spec-writer. These are **testable at the technical
> boundary** (HTTP contract, DB state, assertion on a specific UI element)
> — not user-facing language. If the user-facing criteria in `## Business
> Context` translate 1:1 into technical checks, this section can simply
> say `See Business Context acceptance criteria.` and skip the list.

- [ ] Criterion 1 (testable at the HTTP / DB / UI assertion level)
- [ ] Criterion 2
- [ ] Criterion 3

[Example: "`POST /api/photos` with a ≤20MB multipart upload returns `201 Created` and the photo URL resolves with a `200 OK` HEAD request within 3 seconds."]

---

## Technical Specification

### Database Changes

[If any schema changes needed]

```sql
-- File: backend/migrations/NNN_description.sql
CREATE TABLE IF NOT EXISTS feature_x (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS policy
ALTER TABLE feature_x ENABLE ROW LEVEL SECURITY;

CREATE POLICY feature_x_user_isolation ON feature_x
  USING (user_id = auth.uid());
```

### API Contracts

[If backend changes needed]

**Endpoint 1: Create Feature**

```
POST /api/features

Request:
  {
    "name": "Feature Name",
    "description": "Description"
  }

Response (201 Created):
  {
    "id": "uuid",
    "name": "Feature Name",
    "created_at": "2026-04-09T10:00:00Z"
  }

Error (400 Bad Request):
  {
    "code": "INVALID_INPUT",
    "message": "name is required (max 255 characters)"
  }

Error (409 Conflict):
  {
    "code": "CONFLICT",
    "message": "Feature name already exists"
  }
```

### Frontend Changes

[If UI/component changes needed]

**New Component**: `FeatureForm`
- Props: `onSuccess` callback, optional `initial` data
- State: Form values, save status
- Behavior: Auto-save after 500ms of inactivity

**New Hook**: `useFeatureCreate`
- Returns: `{ mutate, isPending, error }`
- Auto-invalidates query cache on success

**Styling**: 
- Use Shadcn `<Form>`, `<Input>`, `<Textarea>`, `<Button>`
- Border radius: `rounded-[16px]` for button
- Responsive: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`

### Edge Cases & Error Handling

- [ ] Network timeout → Show error toast with retry button
- [ ] Duplicate name → Show 409 error, suggest rename
- [ ] Large text in description → Truncate at 1000 chars, show warning
- [ ] File too large (if upload) → Show clear error with size limit
- [ ] Offline → Queue mutation, show "offline" banner, retry when online
- [ ] Double-click submit → Prevent duplicate submission (disable button)

---

## Testing Plan

### Backend (Venom Tests)

```
backend/venom/feature_test.go

- TestCreateFeature_Happy: Create feature, verify ID returned, name stored
- TestCreateFeature_Validation: Empty name → INVALID_INPUT error
- TestCreateFeature_Duplicate: Same name twice → CONFLICT error
- TestCreateFeature_RLS: User B cannot read User A's feature (via RLS)
```

### Frontend (Playwright E2E Tests)

```
frontend/e2e/feature.spec.ts

- Test: Happy path - fill form, save, verify in UI
- Test: Validation - empty name shows error message
- Test: Auto-save - changes automatically saved after 500ms
- Test: Error recovery - network error shown, retry works
- Test: Offline - mutation queued, retried when online
```

### Manual Testing (if needed)

- [ ] Browser: Chrome, Firefox, Safari
- [ ] Mobile: iOS Safari, Android Chrome
- [ ] Network: Throttled to 3G (slow save)

---

## Acceptance Criteria Mapping

| Acceptance Criterion | Test Coverage |
|---------------------|---------------|
| User can create feature | E2E: Happy path |
| User sees validation errors | E2E: Validation test |
| Feature persists after reload | E2E: Reload after save |
| User cannot see other users' features | Venom: RLS test |

---

## Notes

[Any additional context?]

- Related story: [Story N](./story-NN-other.md)
- Known constraints: [e.g., "Must work offline"]
- Future enhancement: [e.g., "Batch upload (story 5)"]

---

## Implementation Notes for Coder

[Optional: hints for the coder to avoid common mistakes]

- Backend: Don't forget to wire handler in `main.go`
- Frontend: Use `useAutoSave` hook, not manual `useEffect` debounce
- Testing: Include RLS test (User B can't read User A's data)
- Logging: Include feature_id in logs for debugging

---

## Review Log

> Append-only. Team Lead writes one cycle block per review round, following the
> schema in [`../README.md#review-log`](../README.md#review-log). Keep the
> `<!-- REVIEW_LOG_BLOCK_BEGIN -->` / `<!-- REVIEW_LOG_BLOCK_END -->` markers intact —
> they are contract markers that tooling and Team Lead use to locate cycles.

_(no cycles run yet)_

---

## Prod Validation

> Filled by Team Lead at Phase 7 for production-affecting stories. Protocol in
> [`../../../.claude/agents/kiat-team-lead.md`](../../../.claude/agents/kiat-team-lead.md) Phase 7.

_(not yet validated)_
