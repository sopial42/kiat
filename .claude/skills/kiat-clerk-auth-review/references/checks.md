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

## Category 8 — Middleware (App Router)

This category applies when `frontend/src/middleware.ts` (or `proxy.ts` on Next.js ≥15) is in the diff. The full canonical pattern lives in [`../../../../delivery/specs/clerk-patterns.md`](../../../../delivery/specs/clerk-patterns.md) §"Middleware (App Router)" — these checks are the review-time enforcement. Middleware is the entry-point file that gates every protected request, so subtle mistakes here have **whole-app blast radius**: an `auth.protect()` that rewrites to 404, an unjustified `publicRoutes` addition, or an unvalidated `redirect_url` are each one diff away from a security incident.

### 8.1 Unauthenticated requests use explicit `NextResponse.redirect()`, not `auth.protect()`

Grep the diff for `auth.protect()`. If present in `middleware.ts`, the default verdict is `NEEDS_DISCUSSION`. The coder must justify one of: (a) the project is on Pages Router (not App Router), (b) `signInUrl` is explicitly configured in `clerkMiddleware` AND the AC accepts that the redirect strips the originating URL, (c) the story has no AC about post-sign-in resume. Without one of those, escalate to `BLOCKED` with the prescribed fix: replace with `NextResponse.redirect(new URL('/sign-in?redirect_url=' + req.nextUrl.pathname + req.nextUrl.search, req.url), 307)` per `clerk-patterns.md` §Middleware.

*Why it matters*: in App Router middleware, `auth.protect()` rewrites to a 404 (sets `x-clerk-auth-reason: protect-rewrite`) when `signInUrl` isn't configured, and even when it is, strips the originating URL so the user lands on `/` after sign-in instead of the page they tried to reach. This silently fails ACs of the form *"redirect to /sign-in"* or *"user resumes on the page they originally requested"*. Robin's epic-00 story-02 hit this in production; the fix took half a day because the symptom (a 404 page) gives no hint that auth was involved.

### 8.2 `redirect_url` is built from the internal path, never from `req.url` or a user-controlled string

In `middleware.ts`, the `redirect_url` query parameter MUST be constructed from `req.nextUrl.pathname` (optionally + `req.nextUrl.search`), NOT from `req.url` (which contains the full origin), `req.headers.get('referer')`, or any value that could be attacker-controlled. Separately, downstream code that READS `?redirect_url=` and uses it to navigate (`router.push(redirectUrl)`, `<a href={redirectUrl}>`, `window.location = redirectUrl`) MUST validate the value: starts with `/`, contains no protocol scheme (`http:`, `https:`, `//`, `data:`, `javascript:`, `vbscript:`). Either gap = `BLOCKED`.

*Why it matters*: open-redirect vulnerability — OWASP A01 (Broken Access Control). An attacker who can craft `?redirect_url=https://evil.com` and trick a user into clicking the link (phishing email, embedded in a legitimate-looking link) controls where the user lands after sign-in. The user sees `your-app.com/sign-in?...`, signs in legitimately, gets redirected to the attacker's site that mimics the app, and enters their credentials again on a phishing page. Open-redirect is one of the most reliably exploited classes in modern web apps because users only check the domain of the URL they CLICK, not the domain they end up on.

### 8.3 Redirect uses HTTP 307, not 302

Grep for `NextResponse.redirect(...)` invocations in `middleware.ts`. The status must be `307` (or omitted — Next.js defaults to 307). `NextResponse.redirect(url, 302)` is `NEEDS_DISCUSSION`; the coder must justify why preserving the HTTP method isn't required.

*Why it matters*: `307 Temporary Redirect` preserves the HTTP method (POST stays POST after the redirect), which matters for unauthenticated form submissions. `302 Found` is browser-implementation-defined for non-GET methods — some browsers convert to GET, some don't. The discrepancy surfaces as "the form just doesn't work for some users" bugs that depend on browser version. Always 307 unless the coder has a documented reason.

### 8.4 Every `publicRoutes` addition is justified per route

Diff the `isPublicRoute` (or equivalently named) `createRouteMatcher` array. For every NEW entry, the PR description OR an inline code comment must explain: (a) the route is genuinely public by design (landing page, sign-in/sign-up, health probe), or (b) the route is authenticated by a different mechanism IN THE HANDLER (webhook signature validation, API key, mTLS). Unjustified additions = `BLOCKED`.

*Why it matters*: every entry in `publicRoutes` is a hole in the authentication boundary. A typo (`/admin` accidentally added instead of `/api/admin/health`) is a trivial-to-make, hard-to-spot privilege escalation. Forcing per-route justification creates a paper trail and forces the coder to think about WHY this route doesn't need session auth — the answer is rarely "it just doesn't". This is the line of defense against the most common middleware vulnerability: a `publicRoutes` entry that should not have been added.

### 8.5 Matcher and publicRoutes are not conflated

Two anti-patterns to flag in the diff:

- The `config.matcher` excludes auth routes (e.g. matcher pattern explicitly excludes `sign-in` / `sign-up`) instead of those routes being in `publicRoutes` → `BLOCKED`. The matcher is for "should middleware RUN at all"; auth gating is `publicRoutes`' job.
- The matcher is missing `/(api|trpc)(.*)` (or the equivalent for the project's API surface) → `NEEDS_DISCUSSION`. API routes need middleware to run for future cross-cutting concerns even when they're currently in `publicRoutes`.

*Why it matters*: shrinking the matcher to "exclude" routes from auth means future cross-cutting middleware logic (audit logs, request tracing, locale negotiation, A/B test cohort assignment, edge rate limiting) silently won't run on those routes. Six months later when the team adds request-tracing middleware, sign-in / sign-up / API routes are missing from the traces and nobody knows why. The fix at that point is a multi-file diff with regression risk; the prevention here is a one-line discipline that costs nothing today.

### 8.6 Middleware early-returns for public routes BEFORE calling `auth()`

In the middleware function body, the order MUST be:

```typescript
if (isPublicRoute(req)) return NextResponse.next();
const { userId } = await auth();
```

If `auth()` is called BEFORE the public-route check, OR if `auth()` is called for every request unconditionally, flag as `NEEDS_DISCUSSION`. The coder may have a reason (unified telemetry, session refresh on every request), but the default expectation is early-return.

*Why it matters*: `auth()` inspects the session cookie / Authorization header on every invocation. For static assets and genuinely public routes that the matcher accidentally caught (favicon, manifest, RSS feed), this is wasted cost — at scale it's a measurable latency hit on every page load AND a free amplification vector against Clerk's session store. Early-return is one line and removes the entire concern.

### 8.7 Server components / route handlers / Server Actions for protected resources also check `auth()`

Defense-in-depth. If the diff adds a route under `app/` that handles user-scoped data (renders user data, mutates user data, calls a backend endpoint that requires `userId`), grep the corresponding server component / `route.ts` / Server Action for either:

- `await auth()` and a check that `userId !== null`, OR
- `useAppAuth()` (the project wrapper) called in a Client Component down the tree with appropriate gating

Missing auth check at the page/handler/action level when the resource is user-scoped = `BLOCKED`, **regardless of what the middleware says**. The middleware redirect is a UX layer ("send unauthenticated users to sign-in"); the page/handler auth check is the security layer ("don't return user data to a missing/invalid session").

*Why it matters*: middleware is ONE diff away from being misconfigured (matcher change, `publicRoutes` addition, file rename, refactor). The page/handler/action auth check is what actually protects the data. Treating middleware as the only line of defense is a single-point-of-failure architecture; the second line catches every middleware mistake. Two layers, both must hold.

### 8.8 Test-auth bypass is handled symmetrically in middleware

If the project supports test-auth mode (`NEXT_PUBLIC_ENABLE_TEST_AUTH=true`, see Category 2 and `clerk-patterns.md` §"Test Auth Flow"), `middleware.ts` MUST handle it explicitly — EITHER short-circuit (skip the Clerk session check entirely when the flag is set, accept all requests as authenticated) OR detect the `X-Test-User-Id` header and treat it as proof of identity, matching the backend test-auth pattern. Middleware that runs Clerk's `auth()` unconditionally regardless of the test-auth flag will fail in test-auth mode (no Clerk session exists) and silently redirect every test request to `/sign-in`, breaking the entire test suite.

The production guard (Category 2.1) MUST still exist on the BACKEND side regardless — middleware-side test-auth handling does NOT replace the backend startup `log.Fatal` on test-auth-in-production. They are independent layers.

*Why it matters*: middleware that doesn't account for test-auth produces tests that pass locally (where `make dev` uses real Clerk and the middleware works) and fail in CI (where `make test-e2e-mocked` uses test-auth and the middleware redirects every request to /sign-in), or vice versa. The asymmetry between middleware and backend test-auth handling is a documented incident class — it surfaces as "tests work on my machine" debugging rabbit holes that take hours to bottom out, often with the wrong root cause guessed first.
