# Story 01: Add editable display name with navbar

**Status**: 📝 Drafted

**Epic**: [Epic 01 — User profile](./_epic.md)

**Objective**: add a `display_name` column on the `users` table, expose a `PATCH /api/users/me` endpoint to update it, and surface it in a new navbar with an "Edit profile" modal. Cross-layer story showcasing Team Lead's parallel backend + frontend coder launch.

**T-Shirt Size**: M

**Scope**: both (backend migration + API, frontend navbar + modal + hook)

---

## Business Context

> Section written as a starter example (standing in for BMad). In a real BMad session this section would be the output of `bmad-create-story` with real personas from `delivery/business/personas.md`. Here we write it by hand for pedagogy.

### User story

As a **signed-in user**, I want to see my display name in the navbar and change it from an edit-profile modal, so that the app reflects how I prefer to be addressed without me having to dive into Clerk account settings.

### Acceptance criteria (user-facing)

- [ ] When I'm signed in, the top-right of every authenticated page shows my display name (falls back to my Clerk email prefix if I haven't set one yet).
- [ ] Clicking the display name opens a dropdown with an "Edit profile" option.
- [ ] "Edit profile" opens a modal with a single text input for display name.
- [ ] Saving a valid value (1–80 chars, trimmed) closes the modal and updates the navbar immediately (optimistic).
- [ ] Refreshing the page keeps the new name.
- [ ] Signing in as a different user shows THAT user's display name, never mine.
- [ ] If I submit an empty or too-long name, the modal shows an inline error and doesn't close.

### Personas & domain links

- Persona: Signed-in user (no dedicated persona file needed for this starter story; future stories may link `../../business/personas.md#<persona>`)

### Business rationale

First "real" feature on the EPIC 00 scaffold. Demonstrates the two-persona workflow (business intent written cleanly, tech-spec-writer enriches, parallel coders ship) while delivering an actually-useful SaaS primitive.

### Mockups

**No visual reference shipped with this starter** — implementer uses Shadcn primitives (`<DropdownMenu>`, `<Dialog>`, `<Form>`, `<Input>`, `<Button>`) with the design system's default tokens. The layout is deliberately functional, not branded.

**This is exactly where your visual reference would go** when you adapt or replace this story. Two valid shapes (see `kiat-how-to.md` section 5):

```markdown
### Mockups

<!-- Pick ONE shape — live Figma OR static screenshots. Never both. -->

#### Option A — Live Figma URL
- [Navbar — signed-in state](https://figma.com/file/XXX/...?node-id=1)
- [User menu — open](https://figma.com/file/XXX/...?node-id=2)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=3)

#### Option B — Static screenshots
- ![Navbar](../../business/mockups/story-01/navbar.png)
- ![User menu](../../business/mockups/story-01/user-menu.png)
- ![Edit modal](../../business/mockups/story-01/edit-modal.png)
```

When you add one of these, the frontend-coder will match it pixel-close. The tech-spec-writer will NOT restate visual decisions in this story's technical sections — it links to the reference and the coder fills the gap.

---

## Skills

> To be populated by `kiat-tech-spec-writer` at Phase -1.
>
> Likely skills (writer decides): `kiat-clerk-auth-review` (auto-triggered by reviewer — any Clerk-adjacent diff), optionally `kiat-ui-ux-search` if a client brings a visual reference that introduces new component categories.

**Base (auto-loaded by coder agents):**
- `kiat-test-patterns-check`

**Contextual for this story:** _to be filled by tech-spec-writer._

---

## Acceptance Criteria (technical)

> To be filled by `kiat-tech-spec-writer` at Phase -1. Expected shape:
>
> **Backend**
> - [ ] Migration `NNN_add_display_name_to_users.sql` adds `display_name VARCHAR(80) NULL` to the `users` table (nullable — existing rows stay valid)
> - [ ] `PATCH /api/users/me` with `{ "display_name": "Jane" }` returns 200 and the updated user resource
> - [ ] Validation: `display_name` must be 1–80 chars after trim; empty or too-long → 400 `VALIDATION_ERROR`
> - [ ] `GET /api/users/me` returns `{ id, display_name, created_at, updated_at }`
> - [ ] RLS: User A cannot PATCH User B's user row (verified via Venom testcase with `SET LOCAL request.jwt.claim.sub`)
>
> **Frontend**
> - [ ] New `<Navbar>` component visible on every authenticated route (mounted in `(app)/layout.tsx`)
> - [ ] Navbar shows `display_name` or falls back to email prefix; subscribed to the same data source as the edit modal (single source of truth via TanStack Query key)
> - [ ] "Edit profile" modal uses Shadcn `<Dialog>` + `<Form>` + `<Input>`; submit triggers `PATCH /api/users/me` with optimistic update
> - [ ] On validation error from backend, inline error shown; modal doesn't close
> - [ ] `fetch` attaches `Authorization: Bearer <jwt>` via the wrapper hook (PC06 compliance)
>
> **Tests**
> - [ ] Venom: happy PATCH, 400 empty, 400 too-long, 401 without JWT, RLS cross-user
> - [ ] Playwright real-backend: sign in → open modal → change name → verify navbar updates → reload → name persists
> - [ ] Playwright mocked: error branch — backend returns 400, modal shows inline error, doesn't close

---

## Technical Specification

> To be authored by `kiat-tech-spec-writer` at Phase -1. The writer will reference:
>
> - [`delivery/specs/architecture-clean.md`](../../specs/architecture-clean.md) — 4-layer structure for the new usecase
> - [`delivery/specs/backend-conventions.md`](../../specs/backend-conventions.md)
> - [`delivery/specs/api-conventions.md`](../../specs/api-conventions.md) — envelope + error codes
> - [`delivery/specs/database-conventions.md`](../../specs/database-conventions.md) — migration + RLS
> - [`delivery/specs/clerk-patterns.md`](../../specs/clerk-patterns.md) — auth wrapper hook
> - [`delivery/specs/frontend-architecture.md`](../../specs/frontend-architecture.md) — TanStack Query patterns, modal state, optimistic update
> - [`delivery/specs/design-system.md`](../../specs/design-system.md) — tokens (defaults kept if no visual reference)
> - [`delivery/specs/testing-pitfalls-backend.md`](../../specs/testing-pitfalls-backend.md) — VP04 UUID, VP05 cleanup, VP08 RLS
> - [`delivery/specs/testing-playwright.md`](../../specs/testing-playwright.md) — real-backend spec structure

---

## Testing Plan

> To be detailed by the tech-spec-writer. Indicative:
>
> **Backend** (`backend/tests/venom/users/users.venom.yml`):
> - `update_happy` — PATCH with valid name → 200, assert persisted
> - `update_trimmed` — PATCH with leading/trailing spaces → 200, name stored trimmed
> - `update_empty` — PATCH with "" → 400 VALIDATION_ERROR
> - `update_too_long` — PATCH with 81 chars → 400 VALIDATION_ERROR
> - `update_unauthorized` — PATCH without JWT → 401
> - `update_rls_isolation` — User A's JWT, target User B's ID in DB → cannot affect User B
>
> **Frontend**:
> - `frontend/e2e/real-backend/display-name-real.spec.ts` — sign in → open modal → change name → assert navbar update → reload → assert persistence
> - `frontend/e2e/display-name.spec.ts` (mocked) — error branch: backend returns 400 → inline error → modal stays open

---

## Notes

- Don't invent new tokens in `@theme` for this story — Shadcn defaults + Tailwind defaults are sufficient. If a forker brings a visual reference that requires custom tokens, add them in the commit that matches the reference.
- The navbar will be needed in every future authenticated page; mounting it in `(app)/layout.tsx` means future stories don't have to rewire it.
- If you're following this story as a walkthrough: after it ships, look at the diff Team Lead produced. That's what a "feature commit" looks like in Kiat.

---

## Implementation Notes for Coder

> To be filled by `kiat-tech-spec-writer`. Hints the writer may choose to include:
>
> - Use a TanStack Query key like `['users', 'me']` for both the navbar read and the modal mutation's optimistic update, so cache invalidation is trivial.
> - On first sign-in, the `users` row may not exist yet if EPIC 00 story-01 shipped a "lazy upsert" pattern — test covers this edge case (GET /me returns 404 → UI should auto-POST /me with a default).
> - Match navbar height to Shadcn's default (`h-14`) unless a visual reference says otherwise.

---

## Review Log

_(no cycles run yet)_

---

## Prod Validation

_(not yet validated)_

---

> Launch Team Lead on this file to see the full pipeline (writer → backend + frontend coders in parallel → reviewers → verdict) produce working code. Status flips to 🚧 In Progress at Phase 0b, then ✅ Done at Phase 6 (and Phase 7 if prod-affecting).
