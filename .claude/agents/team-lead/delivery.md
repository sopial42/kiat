# Team Lead — Stage 4: Delivery

> Loaded on demand after validation passes. Covers **Phase 1** (scope), **Phase 2** (parallel coder launch), and **Phase 3** (test feedback loop). At the end of this stage, both coders have reported back with a passing test suite at their layer and a `TEST_PATTERNS: ACKNOWLEDGED` block.

---

## Phase 1 — Scope the story

**One story per Team Lead invocation.** Stories run STRICTLY SEQUENTIAL. Team Lead never starts story N+1 until story N is committed (Phase 6 Gate 1 enforces the commit). If a user passes a list of stories, Team Lead handles the first one and explicitly directs the user to relaunch for the next.

This rule is non-negotiable. The 2026-05-01 incident — 4 epic-09 stories run in parallel, all touching the same cross-cutting registry files (`applies-to.ts`, `types.ts`, `party-detail-card.tsx`, `main.go`), mutual interference, 25 E2E failures, all work lost — is the canonical example of why. Cross-cutting files are listed in [`delivery/specs/cross-cutting-files.md`](../../../delivery/specs/cross-cutting-files.md); even when no individual story names them, multi-story waves nearly always collide there.

Within a single story, backend + frontend coders still run in parallel — that's a different axis (same context, no cross-cutting risk). See "Parallel backend + frontend" in the main `kiat-team-lead.md`.

Read the story spec. Determine:
- Backend only? → launch `kiat-backend-coder` alone
- Frontend only? → launch `kiat-frontend-coder` alone
- **Both?** → launch both **in parallel within this story** (single message with two `Agent` tool calls)
- Database changes? → ensure the backend coder's context includes `database-conventions.md`

---

## Phase 2 — Launch coders

Hand each coder the story file path and tell them which per-story specs to load (taken from the story's `## Skills` section plus the ambient docs listed in the coder's own agent definition). **If the story involves writing tests**, explicitly remind the coder to load the relevant pitfalls doc (`testing-pitfalls-backend.md` or `testing-pitfalls-frontend.md`) — these are on-demand docs that coders may skip if not prompted.

Coders will run their own Step 0 (budget self-check) and Step 0.5 (`kiat-test-patterns-check`). Wait for completion. Each coder reports back with file list + test summary + a `TEST_PATTERNS: ACKNOWLEDGED` block.

---

## Phase 3 — Test and feedback loop

When coders report completion:
- Backend: expect `make test-back` green
- Frontend: expect `npm run test:e2e` green

If tests fail:
1. Ask the coder what failed (test name + error)
2. Classify:
   - **Obvious fix** (typo, off-by-one, missing import) → ask coder to fix and rerun
   - **Transient flake** → ask coder to fix root cause (explicit wait, proper seeding) and rerun
   - **Design issue** (spec ambiguous, wrong approach) → escalate to `kiat-tech-spec-writer` / user, do not retry
3. Record approximate elapsed minutes for the rollup (`fix_budget_used_min`) — retrospective metric only, see "Retry budget" in main orchestrator.

---

## Smart re-run rule (saves wall-clock when fix is isolated)

After a fix, the default is to re-run **only the test(s) that failed**, not the full suite — Team Lead doesn't need exhaustive verification on every retry inside the inner fix loop.

Examples:
- Coder fixes a typo in `parties_create_pp_nationality_default.venom.yml` → re-run only `venom run backend/tests/venom/bootstrap/parties_create_pp_nationality_default.venom.yml`
- Coder fixes a `getByText` in `recherche-en-cours-fixes.spec.ts` → re-run only `npx playwright test recherche-en-cours-fixes.spec.ts`

**Exception — full suite required when the fix touches a cross-cutting file** listed in [`delivery/specs/cross-cutting-files.md`](../../../delivery/specs/cross-cutting-files.md). A cross-cutting fix can break tests that were previously green elsewhere; isolated re-run would miss the regression. In that case, the coder runs the full suite (`make test-back` and/or `make test-e2e`).

The full integration re-run still happens once at Phase 6 Gate 2 (post-commit, pre-rollup), independent of the inner-loop choices made here.
