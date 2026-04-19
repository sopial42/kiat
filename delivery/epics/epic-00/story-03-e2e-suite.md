# Story 03: Playwright E2E suite (JWT swap, real-backend, Smocker scenarios)

**Status**: 📝 Drafted

**Epic**: [Epic 00 — Bootstrap](./_epic.md)

**Objective**: ship the canonical Playwright harness — `global.setup.ts` with JWT swap, `e2e/real-backend/` directory with at least one real-backend spec, centralised `page.route()` response builders with CORS exposure headers, and Smocker scenario seeding for backend-to-external mocks. After this story, any future story involving UI can add specs by copy-pasting the canonical structure.

**T-Shirt Size**: M

**Scope**: infra

**Scope justification**: bootstrap scaffolding — ships the canonical Playwright harness (JWT swap, real-backend mode, Smocker seeding, CORS exposure headers) so every future story inherits the test infrastructure by copy-paste. Not a product feature.

**User signal**: none

---

## Business Context

### User story

As a **Tech Lead**, I want a Playwright harness that catches prod regressions (missing auth headers, mock-only blind spots, CORS exposure misses) **before merge**, so that I don't burn a deploy cycle on a regression that should have been caught in CI.

### Acceptance criteria (user-facing)

- [ ] `make test-e2e` runs the full stack (docker-compose + backend + frontend + Smocker) and Playwright against it
- [ ] At least one spec in `frontend/e2e/real-backend/` proves the items CRUD works end-to-end with real Clerk auth + real Postgres + Smocker-mocked external (if any)
- [ ] At least one mocked spec asserts `route.request().headers()['authorization']` and `Access-Control-Expose-Headers` (PC06 + PP14 discipline baked in from day 1)
- [ ] CI runs `make test-e2e` and it passes on the first push

### Personas & domain links

- Persona: Tech Lead

### Business rationale

Playwright discipline is the **most expensive thing to fix later**. Story-03 ships the canonical structure once so every subsequent story is a copy-paste rather than a reinvention. Directly addresses the Playwright + Clerk footguns logged in [`testing-pitfalls-frontend.md`](../../specs/testing-pitfalls-frontend.md) (PP12, PP14, PP15, PC06, PC07).

### Mockups

No mockups — test harness, no UI.

---

## Skills

> To be populated by `kiat-tech-spec-writer`.

---

## Acceptance Criteria (technical)

> To be filled. Expected shape:
>
> - [ ] `frontend/e2e/global.setup.ts` signs in User A, swaps the Testing Token for a `playwright-ci` template JWT, writes `playwright/.clerk/user-a.json`
> - [ ] `frontend/e2e/real-backend/items-real.spec.ts` creates an item through the UI, verifies it via SQL helper (not `page.request`), verifies the `Authorization: Bearer <jwt>` header shape via `route.request().headers()` inside a `page.route` assertion
> - [ ] `frontend/e2e/fixtures/mock-responses.ts` centralises `page.route()` response-builder helpers, with `Access-Control-Expose-Headers` baked in for any custom header — this mocks at the browser layer for frontend-only tests
> - [ ] `frontend/e2e/fixtures/smocker/*.yml` holds the shared Smocker scenarios consumed by both Venom and Playwright — mocks at the backend-to-external layer
> - [ ] `scripts/smocker-seed.sh` seeds the Smocker admin API before Playwright starts (already shipped as a prerequisite)
> - [ ] No `waitForTimeout` anywhere (PP01); all waits are `waitForResponse` or `expect.poll`

---

## Technical Specification

> Reference reading: [`testing-playwright.md`](../../specs/testing-playwright.md) is the canonical how-to and already contains the full code for `global.setup.ts` + spec structure. The coder implements from that spec rather than inventing.
>
> [`testing-pitfalls-frontend.md`](../../specs/testing-pitfalls-frontend.md) + [`smocker-patterns.md`](../../specs/smocker-patterns.md) are mandatory reads for the coder.

---

## Testing Plan

The test IS the deliverable. Reviewer checks:
- Canonical structure matches testing-playwright.md
- Every pitfall checklist item (PP01-PP15, PC01-PC07, UA01-UA03) is respected
- Smocker seed script is idempotent (can run twice without breaking)

---

## Review Log

_(no cycles run yet)_

---

## Prod Validation

_(not yet validated)_
