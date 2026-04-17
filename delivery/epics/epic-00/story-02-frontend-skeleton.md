# Story 02: Frontend skeleton + Clerk wiring + items CRUD UI

**Epic**: [Epic 00 — Bootstrap](./_epic.md)

**Objective**: stand up the Next.js App Router frontend with Clerk auth (real mode + test-auth bypass branch), wire a minimal UI for creating and listing items, enforce the middleware at `src/middleware.ts`, and respect all hooks / RSC / design system conventions from day 1.

**T-Shirt Size**: M

**Scope**: frontend-only (consumes story-01 API)

---

## Business Context

### User story

As a **Tech Lead**, I want a fully-wired Next.js frontend with Clerk signin/signup, items CRUD UI, and the test-auth bypass branch correctly isolated, so that the client can see a working demo on day 1 and I can focus on business UI starting with story-05+.

### Acceptance criteria (user-facing)

- [ ] Visiting `/` when unauthenticated redirects to `/sign-in` (middleware-enforced, not hook-based)
- [ ] After Clerk sign-up, I land on `/items` and can create an item via a form
- [ ] My items are listed; User B's items are NOT visible in my session
- [ ] Switching to `make dev-test` boots the same UI with test-auth bypass (no Clerk), authenticating as a hardcoded test UUID

### Personas & domain links

- Persona: Tech Lead

### Business rationale

Minimal but production-shape UI proves the auth plumbing, RSC boundary, and design tokens work before any business UI ships.

### Mockups

> No Figma at EPIC 00. The frontend-coder uses the design system (see `delivery/specs/design-system.md`) and Shadcn primitives directly — no custom visual work.
>
> If a client wants visual polish on the bootstrap demo, add Figma URLs here and re-run Team Lead.

---

## Skills

> To be populated by `kiat-tech-spec-writer` at Phase -1.
>
> **Expected contextual skills**:
> - `kiat-clerk-auth-review` (triggered automatically by the reviewer — auth-adjacent code)
> - `kiat-ui-ux-search` (probably not needed for EPIC 00 — Shadcn primitives are enough; tech-spec-writer arbitrates)

---

## Acceptance Criteria (technical)

> To be filled by `kiat-tech-spec-writer`. Expected shape:
>
> - [ ] `src/middleware.ts` (NOT project root — PP13) intercepts requests to `/items/*` and redirects unauthenticated users to `/sign-in`
> - [ ] `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/items` returns 307 or 401 without cookies, 200 after Clerk sign-in
> - [ ] Client components that call `fetch('/api/items')` attach `Authorization: Bearer <jwt>` via a wrapper hook — bare `fetch` is BLOCKED by reviewer
> - [ ] The wrapper hook selection (`useTokenGetterClerk` vs `useTokenGetterTestAuth`) is resolved at **module load**, not in render (UA02-class conditional hook risk)
> - [ ] No JWT is serialised into a Client Component's props from a Server Component (PC06)

---

## Technical Specification

> To be authored by `kiat-tech-spec-writer`. The writer will reference:
>
> - [`delivery/specs/frontend-architecture.md`](../../specs/frontend-architecture.md)
> - [`delivery/specs/design-system.md`](../../specs/design-system.md)
> - [`delivery/specs/clerk-patterns.md`](../../specs/clerk-patterns.md) — two-mode provider, hook wrapper
> - [`delivery/specs/testing-pitfalls-frontend.md`](../../specs/testing-pitfalls-frontend.md) — PP13, PC06, PC07, UA02
> - [`delivery/specs/testing-playwright.md`](../../specs/testing-playwright.md) — read for the test plan even though this story is UI-only (story-03 adds the specs)

---

## Testing Plan

> Expected by the tech-spec-writer:
>
> - Unit: React hook tests for `use-auth` (both branches) and `use-auto-save`
> - E2E: a minimal navigation spec in `frontend/e2e/smoke.spec.ts` proving sign-in works — real E2E flows land in story-03

---

**Status**: 🟡 To be implemented.
