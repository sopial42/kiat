---
name: kiat-clerk-auth-review
description: >
  Dedicated Clerk authentication review skill. Invoked by kiat-backend-reviewer and
  kiat-frontend-reviewer whenever a diff touches auth-adjacent code (imports from
  @clerk/*, useAppAuth, Authorization header handling, JWT validation, test-auth
  bypass flags, or Playwright auth setup). Catches the 12+ documented Clerk
  footguns that kiat-review-backend/kiat-review-frontend checklists miss because Clerk
  logic hides across layers (frontend hooks, middleware, backend JWT validation,
  E2E fixtures).
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Clerk Auth Review Skill

**Purpose:** Clerk is a high-risk failure vector. Auth bugs silently bypass RLS,
invalidate sessions across test contexts, or crash in production when test-auth
bypasses leak. The general `kiat-review-frontend` / `kiat-review-backend` skills are too
broad to catch these — this skill exists to enforce the **Clerk-specific**
checks.

---

## WHEN TO INVOKE THIS SKILL (Hard Trigger Rules)

The parent reviewer (`kiat-backend-reviewer` or `kiat-frontend-reviewer`) **MUST** invoke
this skill if **any** of the following pattern matches the code diff:

### Frontend triggers
1. Any import from `@clerk/nextjs`, `@clerk/testing`, `@clerk/clerk-react`
2. Any reference to `useAppAuth`, `useAuth`, `useUser`, `useSignIn`, `useSignOut`
3. Any `<ClerkProvider>`, `<SignedIn>`, `<SignedOut>`, `<SignIn>`, `<SignUp>`, `<UserButton>` component
4. Any change to `middleware.ts` (root or near Clerk)
5. Any Playwright test in `frontend/e2e/**` that uses `clerkSetup`, `clerk.signIn`, `clerk.signOut`, `storageState`, or calls `page.request.*` for authenticated endpoints
6. Any change to `frontend/e2e/helpers/auth*.ts` or `signInAsUserB` / `restoreUserA` / `clerkSignOutSafe`
7. Any reference to `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` or `NEXT_PUBLIC_ENABLE_TEST_AUTH`
8. Any `Authorization: Bearer ...` header construction in client code

### Backend triggers
1. Any import from Clerk Go SDK (`github.com/clerk/clerk-sdk-go/*`)
2. Any change to `ClerkAuthMiddleware` or middleware that reads `Authorization` header
3. Any reference to `ENABLE_TEST_AUTH`, `X-Test-User-Id`, or `ENV=production` guard
4. Any JWT parsing / verification logic
5. Any new protected route registration (reviewer must check middleware applies)
6. Any test that seeds a user via `E2E_CLERK_USER_A_ID` / `E2E_CLERK_USER_B_ID`

**If none of the above patterns appear in the diff, output:**
```
CLERK_SCOPE: NOT_APPLICABLE
```
and return control to the parent reviewer.

**If any pattern appears, you MUST run the full checklist below.**

---

## CLERK CHECKLIST (Run every item — no skipping)

### ✓ Category 1: Provider & Hook Hygiene (Frontend)

- [ ] **`useAppAuth()` used, NOT `useAuth()` directly** — Every hook must go
      through `@/shared/hooks/use-app-auth` so test-auth mode works. Direct
      `import { useAuth } from '@clerk/nextjs'` is a BLOCKER.
- [ ] **`<ClerkProvider>` present in `layout.tsx`** — Only when
      `NEXT_PUBLIC_ENABLE_TEST_AUTH=false`. If test mode is on, ClerkProvider
      must be skipped (conditional render).
- [ ] **`publishableKey` passed explicitly** — `<ClerkProvider publishableKey={process.env.CLERK_PUBLISHABLE_KEY}>`.
      NEVER rely on `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` baked at build time —
      Docker image must be promotable staging→prod. Same for `middleware.ts`.
- [ ] **No hook called outside provider tree** — `useAppAuth()` in a server
      component is a BLOCKER (server components can't use Clerk hooks).

### ✓ Category 2: Test-Auth Bypass Safety (Backend)

- [ ] **Production guard present** — `main.go` MUST have:
      ```go
      if os.Getenv("ENABLE_TEST_AUTH") == "true" && os.Getenv("ENV") == "production" {
          log.Fatal("ENABLE_TEST_AUTH cannot be true in production")
          os.Exit(1)
      }
      ```
      Missing = BLOCKER.
- [ ] **`X-Test-User-Id` header only honored when `ENABLE_TEST_AUTH=true`** —
      If the middleware reads it unconditionally, that's a BLOCKER (auth
      bypass via crafted header).
- [ ] **Real Clerk JWT validation path exercised in at least one test** — Not
      only the test-bypass path. Otherwise prod-only bugs ship.

### ✓ Category 3: JWT & Token Handling

- [ ] **No hardcoded JWTs in code** — Test tokens live in `.env`, never in
      source. Hardcoded `sk_test_*` or `eyJ...` strings = BLOCKER.
- [ ] **Token lifespan considered in Playwright storageState** — If test uses
      `storageState` for User A, there must be a re-save mechanism (e.g.
      `clerkSetup` with `playwright-ci` template using a 3600s JWT) OR the test
      re-signs in fresh. 25-day-old baked tokens = BLOCKER.
- [ ] **No JWT in localStorage / sessionStorage** — Must be in HttpOnly cookie
      OR in-memory. `localStorage.setItem('token', ...)` = BLOCKER (XSS exfil).
- [ ] **Authorization header used, not cookie-only for API** — JWT in
      `Authorization: Bearer` for backend calls (prevents CSRF). Missing = MAJOR.

### ✓ Category 4: SignOut & Session Destruction

- [ ] **`clerk.signOut()` NEVER called without `redirectUrl`** — In Playwright
      tests, must use `clerkSignOutSafe({ redirectUrl: '/sign-in' })` or
      equivalent. Plain `signOut()` redirects to `accounts.dev` cross-origin in
      CI and destroys the browser context. BLOCKER if found in tests.
- [ ] **`signOut()` is server-side destructive** — Invalidates ALL sessions
      sharing the Testing Token. Tests that call `signOut()` without isolating
      the browser context are BLOCKER (cascading test failures).

### ✓ Category 5: User B / RLS Test Isolation

- [ ] **User B tests use isolated browser context** — `signInAsUserB(browser)`
      receives the `browser` object (spawns new context), NOT `page`. Using
      `signInAsUserB(page)` = BLOCKER (pollutes User A's session).
- [ ] **`restoreUserA` re-saves storageState** — After a User B test, User A's
      storageState must be refreshed with a fresh 3600s JWT. Missing re-save
      makes subsequent tests flaky.
- [ ] **Every RLS-sensitive endpoint has a User B test** — "User B cannot
      read/modify User A's data" must exist in Venom OR Playwright. Missing =
      BLOCKER on any endpoint that reads user-scoped data.

### ✓ Category 6: Rate Limits & CI Safety

- [ ] **`clerkSetup()` called at most once per test run** — Not in each test
      file, not in `beforeEach`. Clerk rate-limits `clerkSetup` — parallel
      shards × repeated setup = `429 Too Many Requests`.
- [ ] **Retry strategy documented** — If CI hits Clerk rate limit, the team
      knows to `workflow_dispatch` after ~15-25 min cooldown (not blindly
      re-run).

### ✓ Category 7: Secrets & Env Vars

- [ ] **`CLERK_SECRET_KEY` only in backend env, never frontend** — If seen in
      `frontend/.env*` or `NEXT_PUBLIC_*`, BLOCKER.
- [ ] **`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` NOT baked at Docker build time** —
      Must be injected at Cloud Run runtime. Check Dockerfile + build scripts.
      Baking it = BLOCKER for image promotability.
- [ ] **Test user IDs (`E2E_CLERK_USER_A_ID`, `E2E_CLERK_USER_B_ID`) from env** —
      Not hardcoded in test files.

---

## OUTPUT FORMAT (machine-parseable, parent reviewer merges into its verdict)

**Line 1 MUST be exactly one of:**
- `CLERK_SCOPE: NOT_APPLICABLE`  (no triggers matched the diff)
- `CLERK_VERDICT: PASSED`         (all checklist items pass)
- `CLERK_VERDICT: DISCUSSION`     (a Clerk judgment call needs arbitration)
- `CLERK_VERDICT: BLOCKED`        (one or more checklist items fail)

**If PASSED:**
```
CLERK_VERDICT: PASSED

Provider & hooks: useAppAuth used, ClerkProvider conditional, publishableKey runtime ✓
Test-auth safety: production guard present, X-Test-User-Id gated ✓
JWT: no hardcoded tokens, Authorization header used, no localStorage ✓
SignOut: clerkSignOutSafe used, redirectUrl set ✓
RLS tests: User B isolated context, restoreUserA refreshes ✓
Rate limits: clerkSetup called once per run ✓
Secrets: CLERK_SECRET_KEY backend-only, publishableKey runtime-injected ✓
```

**If DISCUSSION:**
```
CLERK_VERDICT: DISCUSSION

All hard checks pass, but a judgment call is needed:

1. JWT lifespan (file:line)
   - Storage state refreshed every 3600s, but CI shards sometimes run > 1 hour
   - Question: raise to 7200s (more Clerk API load) or add mid-run refresh hook?
```

**If BLOCKED:**
```
CLERK_VERDICT: BLOCKED

1. Category 1 — Provider & Hooks (file:line)
   - Direct `import { useAuth } from '@clerk/nextjs'` in components/Header.tsx:12
     → Must use `useAppAuth()` from `@/shared/hooks/use-app-auth` so test-auth mode works

2. Category 4 — SignOut (file:line)
   - Playwright test `e2e/auth.spec.ts:34` calls `clerk.signOut()` without redirectUrl
     → Will redirect cross-origin to accounts.dev in CI and destroy context
     → Use `clerkSignOutSafe({ redirectUrl: '/sign-in' })`

3. Category 2 — Test-auth safety (main.go:42)
   - Production guard missing: `ENABLE_TEST_AUTH=true` + `ENV=production` does not exit
     → Add os.Exit(1) check at startup
```

---

## Parent Reviewer Integration

When `kiat-backend-reviewer` or `kiat-frontend-reviewer` invokes this skill:

1. Parent reviewer runs its own skill (`kiat-review-backend` / `kiat-review-frontend`) **first**
2. If Clerk triggers match the diff, parent then runs `kiat-clerk-auth-review`
3. Parent **merges verdicts** into its own top-line `VERDICT:`:
   - If parent=APPROVED and clerk=PASSED → `VERDICT: APPROVED`
   - If parent=APPROVED and clerk=BLOCKED → `VERDICT: BLOCKED` (clerk wins)
   - If parent=APPROVED and clerk=DISCUSSION → `VERDICT: NEEDS_DISCUSSION`
   - If parent=BLOCKED → `VERDICT: BLOCKED` (always wins, list both)
4. Parent includes a `Clerk-auth skill:` line in the output body showing the
   clerk verdict (never hides it).

---

## Notes

- This skill exists because Clerk footguns are cross-layer (frontend hook +
  middleware + backend JWT + E2E fixture), and the general reviewers miss them.
- Hardening this checklist came from real pitfalls: cross-origin signOut in CI,
  User B session pollution, baked publishableKey blocking image promotion,
  `useAuth` vs `useAppAuth` divergence.
- If a new Clerk pitfall is discovered in production, add it to this skill —
  it's the one place guaranteed to be re-read by every auth-touching review.
