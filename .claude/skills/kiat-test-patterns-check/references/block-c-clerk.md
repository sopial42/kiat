# Block C — Clerk auth

**Trigger:** any `@clerk/*` import, any protected route, any use of the project's auth wrapper hook.

## Rules and reasons

**Import hooks from the project's auth wrapper, not directly from `@clerk/nextjs`.** The wrapper is typically named `useAppAuth` and lives in a project path like `@/shared/hooks/use-app-auth`.

> *Why*: the wrapper detects when the app is running in test-auth mode and returns mock auth state instead of hitting the real Clerk API. A direct import silently bypasses that, so the component hits Clerk during CI — burning rate limits (see below) and breaking test-auth-dependent tests.

**In Playwright tests, use the project's safe sign-out wrapper (e.g., `clerkSignOutSafe({ redirectUrl: '/sign-in' })`), not bare `clerk.signOut()`.**

> *Why*: bare `signOut()` triggers a cross-origin redirect to `accounts.dev`. In CI the browser follows that redirect and gets stuck on Clerk's domain, which destroys the browser context. Downstream tests in the same file fail with "context closed" errors that look like flakiness but are deterministic.

**`signOut()` is server-side destructive.** It invalidates every session sharing the same Testing Token, not just the current browser context.

> *Why*: parallel test shards share tokens. One test calling `signOut()` can kill sessions in sibling shards that happen to be using the same token — producing "cascading failure" patterns that are hard to reproduce locally.

**`clerkSetup()` is called at most once per test run** (global setup, not `beforeEach`).

> *Why*: Clerk rate-limits the setup endpoint. Parallel shards × repeated setup calls hit `429 Too Many Requests` and the whole run fails with an unhelpful error.

**The Clerk publishable key is injected at runtime via env var**, not baked into the Docker image at build time.

> *Why*: baking couples the image to a specific environment. Promoting a staging image to prod means the frontend still points at the staging Clerk instance — users sign in but every API call returns 401 because the backend validates against prod Clerk.

## Required acknowledgment (paste verbatim)

> I will use the project's auth wrapper hook exclusively, use a safe sign-out wrapper with `redirectUrl` in tests, call `clerkSetup()` only once per run, and ensure the publishable key is runtime-injected.

## Related

The reviewer has a dedicated Clerk specialist skill, [`kiat-clerk-auth-review`](../../kiat-clerk-auth-review/SKILL.md), that runs a cross-layer deep-dive (frontend hook + middleware + backend JWT + E2E fixtures) on any auth-adjacent diff. If your change touches any Clerk trigger, expect a thorough cross-check from that skill — the rules above are a subset of what it checks.

## Common drift caught by reviewers

- Direct `import { useAuth } from '@clerk/nextjs'` — reviewer flags: must use the project's auth wrapper.
- Test calls bare `clerk.signOut()` without a redirect URL — reviewer flags: will destroy CI context.
- `clerkSetup` inside `beforeEach` or multiple `beforeAll` blocks — reviewer flags: rate limit risk.
