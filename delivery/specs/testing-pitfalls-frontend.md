# Frontend Testing Pitfalls & Decisions (Playwright E2E)

Living registry of pitfalls and anti-patterns for Playwright E2E tests. Loaded by `kiat-frontend-coder` and `kiat-frontend-reviewer` when the story involves writing or modifying Playwright specs.

> **Relationship to other docs:**
> - [`testing.md`](testing.md) — Test pyramid structure, CI gate, commands.
> - [`testing-playwright.md`](testing-playwright.md) — Canonical positive patterns for Playwright (fixtures, JWT swap, real-backend discipline). This file = what NOT to do; that file = what TO do.
> - [`testing-pitfalls-backend.md`](testing-pitfalls-backend.md) — Venom/Go pitfalls.
> - [`clerk-patterns.md`](clerk-patterns.md) — Clerk auth flows, test mode, token handling.
> - [`design-system.md`](design-system.md) — Colors, spacing, accessibility tokens.

---

## How to maintain this file

After each story that discovers a surprising Playwright failure, add an entry. Number sequentially (PP01, PP02...). Template at the bottom.

**Size budget:** 5k tokens max. Frontend pitfalls tend to be more numerous (browser flakiness, async rendering, Clerk quirks).

---

## Playwright pitfalls

### PP01: NEVER use `waitForTimeout()` — use `waitForResponse()` + `expect.poll()`

**Symptom:** Auto-save flakes in CI (2s too short) and wastes time locally (save done in 200ms).
**Rule:** `page.waitForResponse(predicate, { timeout: 15_000 })` for network sync, then `expect.poll(() => sqlQuery(), { timeout: 10_000 })` for DB verification.
**Pattern:**
```typescript
await page.waitForResponse(
  (r) => r.url().includes("/api/items/") && r.ok(),
  { timeout: 15_000 },
);
await expect.poll(
  async () => (await getAuditLogCount(userId)).count,
  { timeout: 10_000 },
).toBeGreaterThan(0);
```

### PP02: NEVER use `serial` mode — one flaky test cascades to 10+ skipped

**Symptom:** 1 test fails → 12 "did not run". Catastrophic appearance, single root cause.
**Rule:** Default to independent tests with `beforeEach(cleanupTestData)`. `serial` only for genuinely stateful chains (rare).

### PP03: `getByText("short")` without `{ exact: true }` matches substrings

**Symptom:** `getByText("User")` matches "User", "Users list", "Type of user" → strict mode violation.
**Rule:** Always `{ exact: true }` for short text. Prefer `getByRole()` over `getByText()` when form labels share text.

### PP04: `page.request.get()` does NOT carry Clerk auth headers

**Symptom:** API verification via `page.request.get("/api/...")` returns 401 with real Clerk auth.
**Rule:** Never use `page.request` for backend verification. Use SQL helpers (superuser PG pool, bypasses auth + RLS).

### PP05: Wait for data before clicking action buttons (stale closure)

**Symptom:** Button handler depends on API data that hasn't loaded yet. React `useEffect` runs after paint.
**Rule:** Wait for a data-driven element: `await expect(page.getByText("Expected label")).toBeVisible({ timeout: 10_000 })` before clicking.

### PP06: Add `networkidle` after `page.goto()` for data-heavy pages

**Symptom:** Intermittent "data not found" because React Query fetches start after hydration.
**Rule:** `await page.waitForLoadState("networkidle")` after `goto()` on pages that fetch data on mount.

### PP07: Double-click guard on form submissions and inline inputs

**Symptom:** Fast double-click submits form twice before React re-renders.
**Rule:** `isSubmittingRef` guard in form hooks. `isConfirmingRef` for Enter+blur double-fire on inline inputs.
**Pattern:**
```typescript
const isSubmittingRef = useRef(false);
const onSubmit = useCallback(() => {
  if (isSubmittingRef.current) return;
  isSubmittingRef.current = true;
  void form.handleSubmit((data) => mutation.mutate(data))();
}, [form, mutation]);
```

### PP08: `npm run dev` in CI causes Clerk JS initialization timeouts

**Symptom:** `window.Clerk` not defined within 30s on cold CI runner (dev server compiles on-demand).
**Rule:** `npm start` (production server) in CI. `npm run dev` for local only.
**Config:**
```typescript
webServer: process.env.CI
  ? { command: "npm start", url: TARGET_URL, timeout: 60_000 }
  : undefined,
```

### PP09: Short label match catches similar labels in localized forms

**Symptom:** Substring match — `getByLabel("Name")` matches both "Name" and "First name" labels. Same trap applies to `getByLabel("Nom")` matching "Prénom" in French forms.
**Rule:** Use regex with word boundary: `page.getByLabel(/^Name$/)`.

### PP10: `getByRole("option", { name: "15" })` matches across open/closed dropdowns

**Symptom:** Date selector "15" matches in both day and month selects.
**Rule:** `{ name: "15", exact: true }` for all option selectors.

### PP11: `getByRole("tab")` matches across multiple tab bars

**Symptom:** Page renders 2+ tab components — `getByRole("tab", { name: "X" })` matches both → strict mode.
**Rule:** Use `.first()` or scope with container: `page.getByTestId("main-tabs").getByRole("tab", { name: "X" })`.

---

## Clerk-specific pitfalls

### PC01: `clerk.signOut()` is SERVER-SIDE destructive

**Symptom:** After User B test calls `signOut()`, all subsequent tests silently authenticate as User B.
**Rule:** ALWAYS use isolated browser contexts for User B tests. After assertions: `context.close()` + `restoreUserA(browser)`.
**Pattern:**
```typescript
const { page: pageB, context } = await signInAsUserB(browser);
// ... assertions ...
await context.close();
await restoreUserA(browser);
```

### PC02: `setupClerkTestingToken` shares state across all contexts

**Rule:** Fresh `browser.newContext()` is NOT a clean slate — it inherits the testing environment's active user. Must `signOut()` before `signIn()` as User B.

### PC03: `clerk.signOut()` redirects cross-origin in CI

**Symptom:** `signOut()` navigates to `accounts.xxxx.dev` → Playwright execution context destroyed.
**Rule:** Use `signOutOptions: { redirectUrl: "/sign-in" }` to stay on localhost.

### PC04: Clerk API rate limiting with rapid CI pushes

**Symptom:** All shards fail at `clerkSetup()` with "Too Many Requests".
**Mitigation:** Avoid rapid consecutive pushes. Use `workflow_dispatch` after rate limit clears (~15-30 min).

### PC05: StorageState JWT expiry cascade after signOut

**Symptom:** RLS test passes, then 10-15 subsequent tests fail with 401 after ~60s.
**Rule:** `restoreUserA()` must replicate the same long-lived JWT replacement as `global.setup.ts`.

### PC06: `page.route` mocks hide missing `Authorization` headers — CI is blind to 401-in-prod

**Symptom:** A client component calls `fetch('/api/...', { cache: 'no-store' })` with NO `headers` field. Every Playwright test that uses `page.route('**/api/...')` to mock that endpoint passes green — the mocked response is returned regardless of what headers the request carries (or doesn't). The `real-backend` smoke test, if any, also passes because it runs in test-auth mode with `storageState` pre-seeded. The bug only surfaces against prod: every authenticated poll returns 401.

**Rule:** `page.route` intercepts fetch at the browser layer, BEFORE the request hits the network or serialises headers. So a test that mocks an auth-gated endpoint cannot assert that auth headers were sent — it can only assert what the frontend did with the mocked response. To catch missing-auth regressions in Playwright, the test must inspect `route.request().headers()` inside the route handler and assert the expected auth shape:

```ts
await page.route('**/api/items*', async (route) => {
  const authz = route.request().headers()['authorization'];
  const testUser = route.request().headers()['x-test-user-id'];
  // In CI (real-Clerk storageState mode):
  expect(authz?.startsWith('Bearer ')).toBe(true);
  expect(testUser).toBeUndefined();
  await route.fulfill({ status: 200, body: JSON.stringify(...) });
});
```

Every new Playwright spec covering an authenticated endpoint MUST include at least one `route.request().headers()` assertion. No exceptions. This is the only defence against bare-`fetch` regressions (see `clerk-patterns.md` → "Authenticated fetch from client components" + `kiat-clerk-auth-review` Category 3.5).

**Prevention:** the `kiat-clerk-auth-review` skill hard-triggers on any new `fetch(` to `/api/...` in a `'use client'` file (trigger #9). Reviewers that hit this trigger MUST walk the diff and confirm the fetch attaches auth AND confirm at least one Playwright spec asserts the header on the mocked route. If both are missing, BLOCKED.

### PC07: AC writing — assert the branch that CI actually runs, not the imagined one

**Symptom:** Story AC says "Playwright test proves `X-Test-User-Id` is attached on every poll". Coder implements, CI runs in real-Clerk mode (`NEXT_PUBLIC_ENABLE_TEST_AUTH=false` + storageState signin), the test either fails or gets silently rewritten by the coder to assert `Authorization: Bearer` instead (the CI-executable branch). Reviewer flags as `NEEDS_DISCUSSION`.

**Rule:** Spec writers MUST check the CI config before writing auth-related AC. The two modes in this stack:

| Mode | Trigger | CI? | Auth transport |
|---|---|---|---|
| `make dev` / production | `NEXT_PUBLIC_ENABLE_TEST_AUTH=false` | **YES** (real-Clerk with storageState signin) | `Authorization: Bearer <JWT>` |
| `make dev-test` | `NEXT_PUBLIC_ENABLE_TEST_AUTH=true` | NO (local dev only) | `X-Test-User-Id: <uuid>` |

An AC that says "test asserts `X-Test-User-Id`" is asserting the non-CI branch, which means CI will either fail the assertion or — worse — the coder rewrites the test silently and the AC text drifts from reality. The correct framing for a story that targets CI coverage is:

- "Playwright test asserts `Authorization: Bearer <...>` is present on every poll to `/api/<endpoint>` and `X-Test-User-Id` is absent" (CI-executable), OR
- "Playwright test covers BOTH branches symmetrically via two Playwright projects — one `real-clerk`, one `test-auth`" (explicit dual coverage; requires test-harness work).

Writing "test asserts test-auth branch" without the dual-project harness is a spec-writer error. The `kiat-tech-spec-writer` self-validation should flag any AC that names an auth header not attached in the CI-executable branch.

**Prevention:** spec-writer reads `Makefile` test-e2e target for the `NEXT_PUBLIC_ENABLE_TEST_AUTH` value BEFORE drafting auth-related ACs. If the value is `false`, AC asserts Bearer. If `true`, AC asserts `X-Test-User-Id`. Never blind-copy an AC template that doesn't match the project's CI config. See also the Team Lead "prompt hygiene" rule in `.claude/agents/kiat-team-lead.md` which generalises this to all CI/runtime facts.

---

## UI/Accessibility pitfalls

### UA01: Hardcoded light gray colors fail WCAG AA contrast

**Symptom:** `text-[#99a1af]` gives 2.6:1 contrast (AA requires 4.5:1).
**Rule:** Use `text-muted-foreground` (4.8:1). For disabled elements: `aria-disabled="true"`.

### UA02: `useAutoSave` `enabled` must NOT transition with `data` in same render

**Symptom:** First edit silently swallowed — auto-save never fires.
**Rule:** `enabled` must become `true` in a **separate render** from the first `data` change. Use stable conditions (`data !== initialData && !isLoading`), not data-derived ones computed in the same render.

### UA03: Transient UI states (saving indicators) are unreliable to assert

**Symptom:** Indicator like "Saving..." lasts < 100ms — assertion times out.
**Rule:** Use broad regex (`/Saving/`) then verify via SQL. The indicator is a hint, not a guarantee.

---

## Real-backend discipline pitfalls

### PP12: `@clerk/testing` Testing Tokens → `getToken()` returns null

**Symptom:** Real-backend E2E tests get 401 from the API. The page loads (Clerk middleware accepts the Testing Token), but `useAuth().getToken()` returns `null` client-side — so `fetch('/api/...', { headers: { Authorization: 'Bearer ...' } })` sends no JWT. The backend rejects with `UNAUTHORIZED`.

**Rule:** After `clerk.signIn()`, use `createClerkClient().sessions.getToken(sessionId, 'playwright-ci')` to swap the Testing Token for a real long-lived JWT. Replace both `__session` and `__clerk_db_jwt` cookies in the storageState file. This requires a custom JWT template named `playwright-ci` (lifetime: 3600s) in the Clerk **dev** instance dashboard.

**Prevention:** Any story that adds real-backend E2E tests with Clerk auth MUST verify that `getToken()` returns a non-null JWT in the test. A page-level-only test (navigation, auth gating) doesn't catch this — the bug only surfaces when the frontend makes authenticated API calls. See [clerk-patterns.md](clerk-patterns.md) for the full pattern and security guardrails, and [testing-playwright.md](testing-playwright.md) for the canonical `global.setup.ts` implementation.

### PP13: `middleware.ts` silently ignored when placed outside `src/`

**Symptom:** Clerk auth is never enforced — all routes return 200 even for unauthenticated requests. No error, no warning, no redirect to `/sign-in`. The middleware file exists, the code is correct, but `auth.protect()` never runs. The `TestAuthProvider` (client-side, used in `ENABLE_TEST_AUTH=true` mode) masks the problem because it handles auth without the middleware. The bug only surfaces the first time someone runs `make dev` (real Clerk mode) and notices they can access protected routes without signing in.

**Rule:** In a Next.js project that uses the `src/` directory pattern (`src/app/`, `src/components/`, etc.), the middleware file MUST be at `src/middleware.ts` — not at the project root. Next.js discovers middleware at exactly two locations: `<project>/middleware.ts` or `<project>/src/middleware.ts`. If the app dir is `src/app/`, the root-level `middleware.ts` is outside the resolution scope and is silently skipped. There is no error, no warning until a very recent Next.js version, and none of the dev-mode hot-reloading output mentions it.

**Prevention:** After creating or moving `middleware.ts`, always verify it runs: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/<protected-route>` must NOT return 200 for an unauthenticated request. Check for `x-clerk-auth-status` in response headers — if absent, the middleware is not executing. Add this check to the story-level smoke test for any story that touches auth routing.

### PP14: Playwright `route.fulfill` mocks must expose custom response headers via `Access-Control-Expose-Headers`

**Symptom:** Frontend code reads a custom response header (e.g. `X-Correlation-Id`) fine against the real backend but reads `null` in Playwright E2E tests. The request is mocked via `page.route(...).fulfill({ headers: { 'X-Correlation-Id': '...' } })`, the header IS in the mocked response, yet `response.headers.get('X-Correlation-Id')` returns `null` inside the app. No error in the console, no network warning — the header is simply invisible to JS. Downstream features silently degrade (polling never starts, correlation IDs lost, etc.) and a test that should have failed noisily passes because the degraded state is indistinguishable from the "no header sent" branch.

**Rule:** Cross-origin fetch (frontend on `localhost:3000`, backend on `localhost:8080` — Playwright baseURL vs. API origin) requires the server to include `Access-Control-Expose-Headers: <header-name>` alongside any custom response header, otherwise the browser's CORS layer strips the header from JS even though it arrives over the wire. This applies identically to mocks: a `route.fulfill({ headers: { 'X-Custom': 'v' } })` response that lacks `Access-Control-Expose-Headers: X-Custom` will expose the header to the Network tab but NOT to `response.headers.get(...)`. The real backend already emits this header via its CORS middleware — mocks must mirror it. The list is comma-separated and case-sensitive per the HTTP spec; include every custom header the frontend reads.

```ts
await route.fulfill({
  status: 200,
  headers: {
    'Content-Type': 'application/json',
    'X-Correlation-Id': 'abc-123',
    'Access-Control-Expose-Headers': 'X-Correlation-Id',  // ← required for cross-origin
  },
  body: JSON.stringify(envelope),
});
```

**Prevention:** Any Playwright helper that mocks a response carrying a custom header the frontend reads (`response.headers.get('X-...')`) MUST set `Access-Control-Expose-Headers` in the same fixture. Grep rule for review: if a `route.fulfill` contains a `X-*` header key, the same `headers` object must list that key in `Access-Control-Expose-Headers`. Centralising mock-response builders in `frontend/e2e/fixtures/` (rather than inlining per-spec) makes this enforceable. When adding a new custom header on the backend, add it to both the CORS middleware and every mock fixture that returns the corresponding endpoint in a single commit.

### PP15: Mock-based Playwright specs are necessary but insufficient for stories touching fetch / polling / auth-header surfaces

**Symptom:** Multiple consecutive stories merged with CI fully green, then manifested user-visible regressions within hours on production — `Authorization` header missing on poll requests, progressive reveal killed after a single tick on a backend timing race, and a secondary polling endpoint overwriting the authoritative envelope post-load. Every pre-merge Playwright run had passed. The common cause: all these specs relied on `page.route(...)` to intercept API calls at the browser layer. A browser-level mock resolves the request before it ever leaves the network stack, so the mock cannot observe a missing request header, cannot replicate a server-side timing race, and cannot reveal a divergence between the real envelope shape and what a secondary polling endpoint returns. The tests were passing on a fiction — they verified that the component *would* behave correctly given a perfect backend, not that the real wiring *actually* works.

**Rule:** Any story that modifies one of the following surfaces MUST add or extend a spec under `frontend/e2e/real-backend/` that exercises the full `fetch → backend → upstream` chain without `page.route` on the affected endpoints:
  (i) a component that fetches a route under `/api/*` (new endpoint, new consumer, or changed request shape);
  (ii) a polling loop (tick cadence, termination condition, or request construction);
  (iii) any site that builds an auth header (manual `Authorization` construction, token refresh, wrapper hook swap);
  (iv) the boundary between "rendered from the authoritative prop" and "rendered from a polled side-channel" (the class of regressions where a secondary endpoint overwrites the envelope).

Mock-based specs are still valuable for validation states, error branches, and edge cases that are hard to reproduce against a real backend — but a mock-only test plan does NOT satisfy the review bar for this class of change. The real-backend spec asserts SHAPE (progressive reveal happens, header is present, post-load state is stable), not specific upstream statuses, so it stays robust against transient upstream flakiness. See [testing-playwright.md](testing-playwright.md) for the canonical real-backend spec structure.

**Prevention:** `kiat-frontend-reviewer` checks, on any diff touching the four surfaces above, that the test additions include at least one assertion running against a real backend (i.e. a new or extended file under `frontend/e2e/real-backend/` that does NOT call `page.route` on the endpoint in question). If only mocks are present, return `NEEDS_DISCUSSION` and ask why the discipline does not apply to this story. Note the limit: CI real-backend specs detect frontend regressions, but they run against the local stack — they do not catch prod-only infra drift (distinct Clerk instance, upstream credential differences, IP allowlists). Post-deploy prod smoke is a separate concern handled by Team Lead's Phase 7.

---

## Technical decisions

### TD01: Playwright tests run against real Clerk auth in CI

**Decision:** `make test-e2e` starts backend with `ENABLE_TEST_AUTH=false`. Playwright uses `@clerk/testing` with real JWT (swapped via `playwright-ci` template — see PP12 and testing-playwright.md).
**Rationale:** Tests the full auth flow including middleware, token refresh, RLS.

### TD02: Playwright uses port 3100, not 3000

**Decision:** `playwright.config.ts` uses port 3100 to avoid conflicts with a `make dev` instance running on 3000.

### TD03: Every authenticated endpoint must have at least one Playwright spec under `frontend/e2e/real-backend/`

**Decision:** Mock-based specs (`page.route`) are allowed for error branches and edge cases, but the happy path against any `/api/*` surface must exercise the real backend. Enforced by reviewer (see PP15).

---

## Pitfall template

```markdown
### PPNN / PCNN / UANN: <short title>

**Symptom:** <what went wrong>
**Rule:** <what to do instead>
**Prevention:** <how to catch this before it happens>
```

---

See also:
- [testing.md](testing.md) — Test pyramid, Playwright config, anti-flakiness rules
- [testing-playwright.md](testing-playwright.md) — Canonical positive patterns (fixtures, JWT swap, real-backend spec structure)
- [clerk-patterns.md](clerk-patterns.md) — Auth flows, `clerkSetup()`, `signInAsUserB()`
- [design-system.md](design-system.md) — Color tokens, contrast requirements
- [frontend-architecture.md](frontend-architecture.md) — RSC boundary, hooks patterns
