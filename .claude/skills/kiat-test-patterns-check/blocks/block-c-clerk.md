# Block C — Clerk Auth

**Trigger:** any `@clerk/*` import, any protected route, any `useAppAuth` usage

## Mandatory rules

- Import hooks from `@/shared/hooks/use-app-auth`, NEVER directly from `@clerk/nextjs`. The app-auth wrapper respects the test-auth bypass mode.
- In Playwright tests, use `clerkSignOutSafe({ redirectUrl: '/sign-in' })` — NEVER bare `clerk.signOut()`. Bare signOut triggers a cross-origin redirect to accounts.dev in CI and destroys the browser context.
- `signOut()` is **server-side destructive** — invalidates ALL sessions sharing the Testing Token, causing cascading test failures.
- `clerkSetup()` must be called **at most once per test run** — it's rate-limited. Calling it in `beforeEach` will hit Clerk's 429.
- `publishableKey` MUST be injected at RUNTIME via env var (e.g., Cloud Run env), NEVER baked into the Docker image at build time. Baking breaks image promotability across environments.

## Required acknowledgment (paste verbatim)

> I will use `useAppAuth()` exclusively, use `clerkSignOutSafe({ redirectUrl: '/sign-in' })` in tests, call `clerkSetup()` only once per run, and ensure the publishable key is runtime-injected.

## Related skill

**Reviewers** have a dedicated Clerk specialist skill: [`kiat-clerk-auth-review`](../../kiat-clerk-auth-review.md). It's a cross-layer deep-dive (frontend hook + middleware + backend JWT + E2E fixtures). If your diff touches any of the Clerk triggers, the reviewer MUST run that skill — expect thorough scrutiny.

## Common drift caught by reviewers

- Direct `import { useAuth } from '@clerk/nextjs'` — reviewer flags: must use `useAppAuth()` wrapper
- Test calls `clerk.signOut()` without `redirectUrl` — reviewer flags: will destroy CI context
- `clerkSetup` inside `beforeEach` or multiple `beforeAll` blocks — reviewer flags: rate limit risk
