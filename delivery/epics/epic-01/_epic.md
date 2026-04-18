# Epic 01: User profile — navbar and editable display name

**Status**: 📝 Drafted

> Story-01 is shipped as a learning example, ready for Team Lead to execute. See [`../README.md#status-lifecycle`](../README.md#status-lifecycle) for transitions.

**Outcome**: after this epic, a signed-in user has a navbar with their display name and can edit it from a modal. This is the **first "real" feature** on top of the EPIC 00 infrastructure — a starter demonstration of how Kiat's pipeline builds features end-to-end (backend + frontend + tests in parallel), with explicit guidance on bringing your own visual reference.

---

## Business Context

> Section written as a starter example (by Kiat maintainers, standing in for BMad). In your fork, **feel free to delete this epic entirely** and start with your own EPIC 01 from a real BMad session — or keep it as a learning run for the pipeline.

### Outcome

The user can see who they are at a glance (navbar with display name) and can change how their name is shown across the app without touching Clerk directly. This is a standard user-profile primitive that every SaaS needs; it's also the minimum set of pieces that exercises:

- A new DB column via migration (on the foundational `users` table from EPIC 00)
- A backend `PATCH /api/users/me` endpoint with validation + RLS
- A frontend navbar with user menu + an edit-profile modal with optimistic update
- A Playwright real-backend spec covering the full edit → reload → persistence flow

### Impacted personas

- **Signed-in user** — wants their name visible and editable.

### Business hypotheses & risks

- **Hypothesis**: display name is a universal-enough feature that every forker sees the value of the walkthrough regardless of their actual business.
- **Risk**: none — this is a learning feature, deletable without consequence.

---

## Stories

- [story-01 — Add editable display name with navbar](./story-01-edit-display-name.md) — single story, cross-layer (backend + frontend + E2E), demonstrating parallel coder launch

Potential follow-ups (not implemented, listed as future direction):
- Avatar upload (MinIO-backed) → exercises file upload patterns
- Profile page with multiple fields → exercises form composition
- Cross-user visibility ("see who's signed in") → exercises list queries + RLS relaxation

---

## Out of scope for EPIC 01

- Email change (Clerk-level operation, has its own verification flow)
- Password change (Clerk handles it, don't reinvent)
- Account deletion (business question — hard delete vs soft? reach out to BMad before adding)
- Admin views ("see all users") — requires RLS relaxation patterns, kept for EPIC 02+

---

## Definition of DONE for EPIC 01

- [ ] Signed-in user sees their display name in the navbar
- [ ] "Edit profile" modal opens from the user menu
- [ ] Changing the name persists (survives reload)
- [ ] `make test-venom` and `make test-e2e` green
- [ ] CI green on GitHub

---

## Reviewer verdicts log

_Filled in as stories close._
