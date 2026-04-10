# Clerk Auth Review Checks

This is the reference loaded by `kiat-clerk-auth-review/SKILL.md` when at least one trigger matches the diff. Categories are ordered by blast radius — the first few cause production outages or data leaks, the later ones cause CI flakiness.

Each check starts with the rule, then a "why it matters" block that explains the incident the rule comes from. When you report a blocker, cite the "why" — it helps the coder understand the fix rather than just the rule.

Full project Clerk patterns are in [`delivery/specs/clerk-patterns.md`](../../../../delivery/specs/clerk-patterns.md). This checklist is the review-time subset.

## Category 1 — Provider and hook hygiene (frontend)

### 1.1 The project's auth wrapper hook is used, not `useAuth` directly

Hooks that need to respect the test-auth bypass mode should go through the project's wrapper (typically `useAppAuth` in `@/shared/hooks/use-app-auth` or the equivalent path — check the project's convention). A direct import like `import { useAuth } from '@clerk/nextjs'` skips the wrapper.

*Why it matters*: the wrapper is the layer that detects when the app is running in test-auth mode and returns mock auth state instead of hitting the real Clerk API. A direct `useAuth` import ignores that, so a component using it will silently hit Clerk during CI runs. This burns Clerk rate limits (see Category 6) and breaks tests that depend on test-auth behavior.

### 1.2 `<ClerkProvider>` is conditional on the test-auth flag

`<ClerkProvider>` should only wrap the app tree when `NEXT_PUBLIC_ENABLE_TEST_AUTH=false`. When test-auth is on, the provider is skipped — typically via a conditional render in `layout.tsx`.

*Why it matters*: ClerkProvider makes network calls to Clerk on mount. In test-auth mode, those calls are unwanted and can cause race conditions on CI where the provider's async init races with the test's sign-in step. Unconditional provider = unreliable test runs.

### 1.3 `publishableKey` is passed explicitly from a runtime env var

`<ClerkProvider publishableKey={process.env.CLERK_PUBLISHABLE_KEY}>` — not relying on the Next.js auto-injection of `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` baked at build time. Same rule for `middleware.ts`.

*Why it matters*: the `NEXT_PUBLIC_*` env var is baked into the Docker image at build time. If the image is built against the staging publishable key and promoted to prod, the frontend still points at the staging Clerk instance — users sign in against staging but the backend validates against prod. Symptoms: users can log in but every API call returns 401. Passing the key explicitly at runtime (via Cloud Run env, Kubernetes secret, etc.) makes the image promotable across environments.

### 1.4 Hooks are not called from server components

`useAppAuth()` (or any Clerk hook) called from a server component is a build-time error on Next.js App Router. Move the hook-using code into a `'use client'` boundary.

*Why it matters*: this is caught by the build, so it's rarely in a merged diff — but when it is, it means someone forced the build through. The check is a safety net.

## Category 2 — Test-auth bypass safety (backend)

### 2.1 Production guard is present at startup

`main.go` should contain:

```go
if os.Getenv("ENABLE_TEST_AUTH") == "true" && os.Getenv("ENV") == "production" {
    log.Fatal("ENABLE_TEST_AUTH cannot be true in production")
}
```

Missing this guard is a `BLOCKED`.

*Why it matters*: `ENABLE_TEST_AUTH=true` makes the backend accept a `X-Test-User-Id` header as a proof of identity, bypassing JWT validation. If this flag is ever set in production — even accidentally via a misconfigured env var — anyone who knows a valid user ID can impersonate any user. The startup guard is the only thing preventing a one-character config mistake from becoming a full account takeover.

### 2.2 `X-Test-User-Id` is only honored when `ENABLE_TEST_AUTH=true`

The middleware should check `ENABLE_TEST_AUTH` before reading the header. An unconditional read (`if header := c.GetHeader("X-Test-User-Id"); header != "" { ... }`) is a `BLOCKED`.

*Why it matters*: same incident class as 2.1. If the header is honored unconditionally, the startup guard in 2.1 becomes the only line of defense, and defense in depth means you want both.

### 2.3 At least one test exercises the real JWT validation path

Tests that only use the test-auth bypass leave the JWT path untested. At least one backend test should exercise real JWT validation (e.g., via a mock Clerk client that returns a valid response).

*Why it matters*: bugs in the real JWT path only surface in production. A test suite that passes because every test uses `X-Test-User-Id` gives a false sense of security.

## Category 3 — JWT and token handling

### 3.1 No hardcoded JWTs in source

Tokens, secret keys, and long base64 strings that look like JWTs have no business in source control. Test tokens live in `.env*` files, never in code. A grep for `sk_test_`, `eyJ`, or hex strings 32+ chars long is a cheap sanity check.

*Why it matters*: a leaked test token can be extracted by anyone with repo access. A leaked production secret key is an incident. Committing tokens also means rotation requires a new commit, which breaks the audit trail of when the rotation happened.

### 3.2 Playwright storage state has a re-save mechanism

If tests use `storageState` for a logged-in user, there must be a way to refresh that state when the JWT expires — either `clerkSetup` with a short-lived template token, or a fresh sign-in on each test run. Storage states baked months ago with long-lived tokens are a `BLOCKED`.

*Why it matters*: a 25-day-old token in storage state will sometimes work and sometimes fail, depending on the Clerk session expiry. The resulting test flakiness is incredibly hard to debug because the failure only happens at token expiry, not on every run.

### 3.3 Tokens aren't stored in `localStorage` or `sessionStorage`

Auth tokens in `localStorage.setItem('token', ...)` are extractable by any script on the page, including injected ad scripts or XSS payloads. Tokens should live in HttpOnly cookies or in-memory state only.

*Why it matters*: XSS is a common vulnerability class, and if your tokens are in localStorage, any XSS instantly becomes an account takeover. HttpOnly cookies are exfiltration-resistant.

### 3.4 API calls use the `Authorization: Bearer` header, not cookies

Client-to-API auth uses the explicit header construction, not cookie-based auth. This prevents CSRF attacks.

*Why it matters*: cookie-based auth sends credentials on every request, including cross-origin requests. An attacker can craft a form on their own site that submits to your API and the user's cookie will be attached. Bearer tokens must be explicitly attached by client code, so cross-origin attackers can't forge requests.

## Category 4 — Sign-out and session destruction

### 4.1 `clerk.signOut()` is never called without `redirectUrl` in Playwright tests

Tests should call the project's safe sign-out wrapper (`clerkSignOutSafe({ redirectUrl: '/sign-in' })` or equivalent), not bare `clerk.signOut()`.

*Why it matters*: bare `signOut()` in Playwright triggers a cross-origin redirect to `accounts.dev`. In CI, the browser context follows that redirect and gets stuck on Clerk's domain, which destroys the test context. Symptoms: test hangs, followed by a cascade of downstream test failures with "context closed" errors. Setting an explicit `redirectUrl` back to the app domain keeps the context usable.

### 4.2 `signOut()` is understood to be server-side destructive

`signOut()` invalidates all sessions that share a Testing Token on the Clerk server, not just the current browser context. Tests that call `signOut()` without isolating their browser context will cascade-fail across parallel test runs.

*Why it matters*: parallel test shards share Clerk Testing Tokens. One test calling `signOut()` invalidates the session for every other shard that was using the same token, producing "cascading failure" patterns in CI that look like flakiness but are actually deterministic session kills.

## Category 5 — User B / RLS test isolation

### 5.1 User B tests use an isolated browser context

Tests that switch to User B receive the `browser` object and spawn a fresh context, not the `page` from the User A test. Passing `page` pollutes User A's session.

*Why it matters*: a browser context has its own cookies and localStorage. Reusing User A's page for User B means both users share a context, and whichever sign-in runs last wins. The RLS test silently tests the wrong user and always passes.

### 5.2 User A's storage state is refreshed after User B tests

After running a User B test, the User A storage state should be re-saved with a fresh token so the next User A test doesn't use a stale session.

*Why it matters*: without refresh, the storage state slowly drifts from reality and tests become flaky as the session ages out.

### 5.3 Every RLS-sensitive endpoint has a User B negative test

For every endpoint that reads user-scoped data, there should be a test that explicitly verifies User B cannot read User A's data. This test lives in either Venom or Playwright.

*Why it matters*: RLS can be silently broken by a missing `WHERE user_id = ...` clause. The only way to catch it is to try to read someone else's data from a different user's context. "It works for me" is not a test for RLS.

## Category 6 — Rate limits and CI safety

### 6.1 `clerkSetup()` is called at most once per test run

`clerkSetup()` should run in a global `beforeAll` or equivalent, not in `beforeEach` or per-file setup.

*Why it matters*: Clerk rate-limits the setup endpoint. Parallel shards × repeated setup calls easily hit `429 Too Many Requests`, at which point the whole CI run fails with an unhelpful error. The fix — calling setup once — is a one-line change but catches a class of failures that look random.

### 6.2 Rate-limit retry strategy is documented

If the team has a convention for what to do when CI hits a Clerk rate limit (e.g., "wait 15-25 minutes, then `workflow_dispatch` the job"), it should be written somewhere reachable. Ad-hoc re-runs without waiting just consume more budget.

*Why it matters*: this is less of a code check and more of a process check. The review can flag "there's no documented retry strategy" as a `DISCUSSION` item, not a blocker.

## Category 7 — Secrets and environment variables

### 7.1 `CLERK_SECRET_KEY` is backend-only

The Clerk secret key should never appear in `frontend/.env*` files or in any `NEXT_PUBLIC_*` variable. If it does, it's leaked to every browser user.

*Why it matters*: the secret key can mint JWTs. Anyone with it can impersonate any user. It's the most sensitive secret in the auth system and should never reach the client bundle.

### 7.2 Publishable key is not baked at Docker build time

See 1.3 — the publishable key should be injected at runtime, not hardcoded into the image at build.

*Why it matters*: image promotability. Same incident class as 1.3.

### 7.3 Test user IDs come from environment variables

`E2E_CLERK_USER_A_ID` and `E2E_CLERK_USER_B_ID` (or the project's equivalent) should come from env vars, not be hardcoded in test files.

*Why it matters*: hardcoded test user IDs tie tests to a specific Clerk tenant. If the tenant is recreated (or the tests run against a different tenant), every test fails. Env vars make the tests portable.
