# Story 04: CI pipeline (GitHub Actions, test gates, deploy placeholder)

**Status**: 📝 Drafted

**Epic**: [Epic 00 — Bootstrap](./_epic.md)

**Objective**: `.github/workflows/ci.yml` that runs the full test gate (`make ci-local`) on every push / PR, caches Go modules and npm, and is green on the first push after clone.

**T-Shirt Size**: S

**Scope**: infra / CI only

---

## Business Context

### User story

As a **Tech Lead**, I want CI green on the first push with zero manual intervention, so that every future PR inherits a deterministic quality gate without me having to configure it per project.

### Acceptance criteria (user-facing)

- [ ] Fresh fork of kiat → push to `main` → CI runs → all jobs green within ~10 minutes
- [ ] Any PR with a failing Go unit test / Venom test / Playwright spec is auto-blocked from merge
- [ ] No secret lives in the workflow file — all secrets come from GitHub Environment secrets (Clerk keys, test user credentials)

### Personas & domain links

- Persona: Tech Lead

### Business rationale

CI setup is the hidden cost at every project start. Doing it once in kiat means every fork inherits it free.

### Mockups

No mockups.

---

## Skills

> To be populated by `kiat-tech-spec-writer`.

---

## Acceptance Criteria (technical)

> To be filled. Expected shape:
>
> - [ ] `.github/workflows/ci.yml` has three jobs: `backend` (go test), `venom` (Venom HTTP suite with docker-compose), `e2e` (Playwright with docker-compose + Smocker)
> - [ ] Workflow uses `GITHUB_TOKEN` only; Clerk secrets come from a `ci` environment
> - [ ] Go modules cached via `actions/setup-go` with `cache: true`
> - [ ] npm cached via `actions/setup-node` with `cache: 'npm'`
> - [ ] Playwright browsers cached via `actions/cache` keyed on `package-lock.json`
> - [ ] No `--no-verify`, no skipping of pre-commit hooks, no `continue-on-error: true`

---

## Technical Specification

> To be authored by `kiat-tech-spec-writer`. The writer references:
>
> - [`delivery/specs/deployment.md`](../../specs/deployment.md) — env var matrix
> - [`delivery/specs/git-conventions.md`](../../specs/git-conventions.md) — PR discipline, CI gate philosophy
> - [`delivery/specs/testing-pitfalls-frontend.md`](../../specs/testing-pitfalls-frontend.md) — PC04 (Clerk rate limiting under rapid CI pushes), PP08 (npm start not dev in CI)

---

## Testing Plan

The pipeline IS the deliverable. Reviewer pushes a deliberate breaking commit (e.g., remove a Venom assertion), confirms CI goes red, reverts.

---

## Review Log

_(no cycles run yet)_

---

## Prod Validation

_(not yet validated)_
