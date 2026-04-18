# Story 01: Backend skeleton + auth middleware + items CRUD + RLS

**Epic**: [Epic 00 — Bootstrap](./_epic.md)

**Objective**: stand up the Go backend with Clean Architecture 4 layers, wire Clerk JWT + test-auth middleware with the mandatory production guards, and ship a generic `items` CRUD resource under row-level security.

**T-Shirt Size**: M

**Scope**: backend-only

---

## Business Context

> Section written by BMad (or the user before the tech-spec-writer runs).
> The tech-spec-writer NEVER modifies, reformats, or moves this section.

### User story

As a **Tech Lead**, I want a fully-wired backend with auth, DB migrations, and a generic CRUD resource, so that I can **ship a new client engagement's first business story in a few hours instead of reinventing infra**.

### Acceptance criteria (user-facing)

- [ ] After `make dev` + sign-up via Clerk, I can POST a new item and see it persisted in Postgres
- [ ] Authenticated User B cannot read User A's items (RLS enforced at the DB level, not just at the handler)
- [ ] Starting the backend with `ENV=production ENABLE_TEST_AUTH=true` crashes immediately with a clear log message

### Personas & domain links

- Persona: Tech Lead (no business persona — this is infra)

### Business rationale

This is the infra baseline. Every future business story depends on it. Getting it right once means we never touch it again.

### Mockups

No mockups — backend-only story, no UI.

---

## Skills

> To be populated by `kiat-tech-spec-writer` at Phase -1.

**Base (auto-loaded by coder agents):**
- `kiat-test-patterns-check`

**Contextual for this story:** (tech-spec-writer decides; expected: auth security review will trigger `kiat-clerk-auth-review` in the reviewer phase.)

---

## Acceptance Criteria (technical)

> To be filled by `kiat-tech-spec-writer` at Phase -1. Expected shape:
>
> - [ ] A `users` table is shipped as **foundational** — columns at minimum: `id UUID PRIMARY KEY` (matches the Clerk user ID subject claim), `created_at`, `updated_at`. No RLS on this table itself; it's read-only from the app layer and upserted on first authenticated request via a middleware (or an explicit "sync" endpoint). Future epics add columns (e.g., `display_name` in EPIC 01).
> - [ ] The `items` table has `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE` + RLS policy keyed on `auth.uid()`.
> - [ ] `POST /api/items` with valid JWT returns 201 and persists `{id, title, user_id, created_at, updated_at}`
> - [ ] `GET /api/items` returns only the authenticated user's items
> - [ ] RLS policy verified via `SET LOCAL request.jwt.claim.sub = '<other-uuid>'` in a Venom testcase returns zero rows for another user's data
> - [ ] `init()` in `cmd/api/main.go` calls `log.Fatal` when `ENV=production` AND any of `ENABLE_TEST_AUTH=true`, `DATABASE_URL` containing `localhost`/`127.0.0.1`, or any `EXTERNAL_*_BASE_URL` containing `smocker`/`localhost:8100`/`127.0.0.1:8100`
> - [ ] `backend/tests/venom/items/items.venom.yml` covers: happy POST, happy GET, 401 without JWT, 400 on validation error, RLS isolation

---

## Technical Specification

> To be authored by `kiat-tech-spec-writer` at Phase -1. The writer will reference:
>
> - [`delivery/specs/architecture-clean.md`](../../specs/architecture-clean.md) — 4-layer structure
> - [`delivery/specs/backend-conventions.md`](../../specs/backend-conventions.md) — folder naming, error codes
> - [`delivery/specs/api-conventions.md`](../../specs/api-conventions.md) — REST envelope shape
> - [`delivery/specs/database-conventions.md`](../../specs/database-conventions.md) — migrations, RLS policy template
> - [`delivery/specs/clerk-patterns.md`](../../specs/clerk-patterns.md) — JWT validation, test-auth bypass, modes
> - [`delivery/specs/testing-pitfalls-backend.md`](../../specs/testing-pitfalls-backend.md) — VP04 UUID rule, VP05 cleanup rule, VP08 RLS pattern
> - [`delivery/specs/security-checklist.md`](../../specs/security-checklist.md) — RLS testing, secret management

---

## Testing Plan

> Expected by the tech-spec-writer (indicative):
>
> - Unit: colocated `_test.go` in `internal/application/item/` covering validation and use-case orchestration
> - Handler: `internal/interface/handler/item_handler_test.go` via httptest
> - Black-box: `backend/tests/venom/items/items.venom.yml` (TD07 canonical template)
> - RLS: Venom testcase wrapping a `SET LOCAL request.jwt.claim.sub` in a transaction (VP08)

---

## Notes

- This is the canonical "item" resource template — keep it business-neutral so clients can fork, rename to their own domain entity (patients, orders, invoices, whatever) without confusion.
- Production guards are the single most load-bearing piece — if they pass code review without a reviewer catching a missing guard, the whole safety model breaks.

---

## Implementation Notes for Coder

> To be filled by `kiat-tech-spec-writer` at Phase -1.

---

**Status**: 🟡 To be implemented — Team Lead will orchestrate tech-spec-writer + backend-coder + backend-reviewer when you invoke it on this file.
