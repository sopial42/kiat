# Epic 00: Bootstrap — stack fonctionnel prêt à recevoir des stories métier

**Status**: 📝 Drafted

> Framework, specs, and skeletons are shipped (`aa7e245` and onward). Code is not yet implemented — each story flips to 🚧 In Progress when Team Lead picks it up, and this epic auto-aggregates to 🚧 when any child is in progress. See [`../README.md#status-lifecycle`](../README.md#status-lifecycle).

**Outcome**: a fresh fork of kiat can run `make dev` end-to-end on day 1 — auth Clerk fonctionnelle, 1 CRUD générique (items) persisté en Postgres sous RLS, suite Playwright verte, CI GitHub Actions verte au premier push. Une fois EPIC 00 done, la stack ne doit plus jamais être retouchée pour des raisons d'infra — toutes les stories suivantes ajoutent uniquement du métier.

---

## Business Context

> Section written by BMad (or the user before the tech-spec-writer runs).
> The tech-spec-writer NEVER modifies, reformats, or moves this section.

### Outcome

After this epic, any new Kiat-based engagement starts with:
- Users can sign up, log in, log out via Clerk
- Users can CRUD a generic "item" resource (placeholder for any domain entity the client will introduce)
- Tests run green locally and in CI (unit, integration, E2E)
- External API mocking infrastructure (Smocker) is wired for future upstreams — same mock pattern used by Venom, dev-test, and Playwright
- Every production guard is in place: `log.Fatal` at startup if `ENV=production` AND (test-auth enabled, or DATABASE_URL points at localhost, or any EXTERNAL_*_BASE_URL points at Smocker)

### Impacted personas

- **Tech Lead** (you) — forks the repo, runs `make dev`, confirms the stack is alive
- **Client / Product Owner** — opens the same repo, runs BMad to start articulating their domain; no tech setup required

### Business hypotheses & risks

- **Hypothesis**: once EPIC 00 ships, the time from "new client engagement" to "first story in progress" is under 2 hours.
- **Risk**: Clerk dev instance setup can block non-tech clients — document the exact setup steps so the tech lead handles it in <15 minutes.

---

## Stories

- [story-01 — Backend skeleton + auth middleware + items CRUD + RLS](./story-01-backend-skeleton.md)
- [story-02 — Frontend skeleton + Clerk wiring + items CRUD UI](./story-02-frontend-skeleton.md)
- [story-03 — Playwright E2E suite (JWT swap, real-backend, Smocker scenarios)](./story-03-e2e-suite.md)
- [story-04 — CI pipeline (GitHub Actions, test gates, deploy placeholder)](./story-04-ci-pipeline.md)

> Stories 01–04 are to be written by `kiat-tech-spec-writer` (invoked via Team Lead) when you're ready to implement them. The skeleton files exist but only contain the Business Context sketch — technical sections land at Phase -1.

---

## Out of scope for EPIC 00

Deliberately excluded to keep the bootstrap minimal:
- Redis / any caching layer (YAGNI at bootstrap — add when a real business story requires it)
- Multi-tenant / organization scoping (user-scoped RLS is enough at day 1)
- File upload to MinIO (infra is up, but no story exercises it yet)
- Deploy pipeline to Cloud Run / Fly / other (placeholder CI job only)
- Production guards for any env var not yet introduced (each new env var ships its guard in the same commit)

---

## Definition of DONE for EPIC 00

- [ ] `make dev` boots backend + frontend; user can sign up via Clerk, CRUD an item, see RLS prevent User B from reading User A's items
- [ ] `make dev-test` boots the stack in test-auth bypass mode offline (no internet needed beyond Docker pulls)
- [ ] `make test-back` green (Go colocated tests)
- [ ] `make test-venom` green (Venom black-box HTTP suite)
- [ ] `make test-e2e` green (full docker-compose + Smocker + Playwright real-backend)
- [ ] `.github/workflows/ci.yml` runs the same commands and is green on push
- [ ] `cmd/api/main.go init()` crashes with a clear message when `ENV=production` + any test flag is set
- [ ] README's "Who runs what" section remains accurate
- [ ] Every spec in `delivery/specs/` is still authoritative (no drift between specs and the code shipped)

---

## Reviewer verdicts log

_Filled in as stories close._
