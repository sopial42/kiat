---
name: kiat-clerk-auth-review
description: >
  Dedicated Clerk authentication review specialist for Kiat stories. Use this
  skill whenever a code diff touches auth-adjacent code — any Clerk SDK
  import, any protected route change, any JWT handling, any Authorization
  header construction, any test-auth bypass flag, any Playwright auth fixture,
  or any change to the project's auth wrapper hook or middleware. Clerk
  failures are cross-layer (frontend hook + middleware + backend JWT + E2E
  fixtures) and the general review skills miss them because Clerk logic is
  spread across files. This skill exists to catch the 12+ documented Clerk
  footguns before they ship. Invoked by kiat-backend-reviewer and
  kiat-frontend-reviewer whenever their diff matches any trigger below.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Clerk Auth Review

## Why this skill exists

Clerk is the highest-density footgun surface in the Kiat stack. Auth bugs silently bypass row-level security, invalidate sessions across CI contexts, or crash production when test-auth bypass flags leak. They also tend to hide across layers — a single mistake can live in a frontend hook, the root middleware, the backend JWT handler, a Playwright fixture, and an environment variable, all at once.

The general review skills (`kiat-review-backend`, `kiat-review-frontend`) have ~100 items each; Clerk gets skimmed under that load. This skill isolates the Clerk checks so that when it runs, it runs with full focus. It's stricter than the general reviewers because each item on its list corresponds to a real production or CI incident that cost hours to debug.

The parent reviewer invokes this skill conditionally, based on whether the diff matches any trigger below. If no trigger matches, the skill returns `CLERK_SCOPE: NOT_APPLICABLE` without running the checklist.

## Trigger rules

Invoke this skill if the diff matches **any** of the patterns below. The list is long because Clerk touches many places — anywhere you see one of these, you should run the full check.

### Frontend triggers

1. Any import from `@clerk/nextjs`, `@clerk/testing`, or `@clerk/clerk-react`.
2. Any reference to `useAuth`, `useUser`, `useSignIn`, `useSignOut`, or the project's auth wrapper hook (typically `useAppAuth`).
3. Any `<ClerkProvider>`, `<SignedIn>`, `<SignedOut>`, `<SignIn>`, `<SignUp>`, or `<UserButton>` component.
4. Any change to `middleware.ts` (root or anything Clerk-related).
5. Any Playwright test under `frontend/e2e/` that uses `clerkSetup`, `clerk.signIn`, `clerk.signOut`, `storageState`, or authenticated `page.request.*` calls.
6. Any change to the project's Playwright auth helpers (user switching, storage state management, safe sign-out wrappers).
7. Any reference to `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` or `NEXT_PUBLIC_ENABLE_TEST_AUTH`.
8. Any `Authorization: Bearer ...` header construction in client code.

### Backend triggers

1. Any import from the Clerk Go SDK (`github.com/clerk/clerk-sdk-go/*`).
2. Any change to `ClerkAuthMiddleware` or any middleware that reads the `Authorization` header.
3. Any reference to `ENABLE_TEST_AUTH`, `X-Test-User-Id`, or the `ENV=production` guard.
4. Any JWT parsing or verification logic.
5. Any new protected route registration — you should verify the middleware actually applies to it.
6. Any test that seeds a user via `E2E_CLERK_USER_A_ID` / `E2E_CLERK_USER_B_ID` (or the project's equivalent env vars).

If none of these match the diff, return `CLERK_SCOPE: NOT_APPLICABLE` and hand control back to the parent reviewer.

## The checklist

When at least one trigger matches, read [`references/checks.md`](references/checks.md) and run through each category. The checks are ordered by blast radius — a test-auth bypass leaking to production is much worse than a minor hook import style issue, so the categories with the highest impact come first.

Every check in the reference file has a rationale ("why it matters"). When you report a blocker, cite the rationale so the coder understands the fix, not just the rule.

## Output format

The first line of your output is one of four exact strings, merged by the parent reviewer into its top-line `VERDICT:`:

- `CLERK_SCOPE: NOT_APPLICABLE` — no triggers matched the diff.
- `CLERK_VERDICT: PASSED` — all checks pass.
- `CLERK_VERDICT: DISCUSSION` — a judgment call needs arbitration.
- `CLERK_VERDICT: BLOCKED` — one or more checks fail.

### If `NOT_APPLICABLE`

```
CLERK_SCOPE: NOT_APPLICABLE

Diff does not touch auth-adjacent code. Skipping checklist.
```

### If `PASSED`

```
CLERK_VERDICT: PASSED

Provider & hooks: auth wrapper used consistently, ClerkProvider conditional on test-auth, publishable key runtime-injected ✓
Test-auth safety: production guard present, test user header gated ✓
JWT: no hardcoded tokens, Authorization header used, no localStorage for tokens ✓
SignOut: safe wrapper used with redirectUrl in tests ✓
RLS tests: User B isolated context, storage state refresh ✓
Rate limits: clerkSetup called once per run ✓
Secrets: CLERK_SECRET_KEY backend-only, publishable key runtime-injected ✓
```

### If `DISCUSSION`

```
CLERK_VERDICT: DISCUSSION

All hard checks pass, but a judgment call needs arbitration:

1. <Category>: <brief> (file:line)
   - <the specific pattern or tradeoff>
   - Question: <what needs to be decided>
```

### If `BLOCKED`

```
CLERK_VERDICT: BLOCKED

1. <Category>: <brief> (file:line)
   - <what's wrong>
   - <why it's a blocker — the production or CI incident it would cause>
   - <the specific fix>

2. ...
```

## Parent reviewer integration

The parent reviewer (`kiat-review-backend` or `kiat-review-frontend`) runs its own skill first. If Clerk triggers match, the parent then runs this skill and merges the verdicts:

| Parent verdict | Clerk verdict | Combined verdict |
|---|---|---|
| APPROVED | NOT_APPLICABLE | APPROVED |
| APPROVED | PASSED | APPROVED |
| APPROVED | DISCUSSION | NEEDS_DISCUSSION |
| APPROVED | BLOCKED | BLOCKED |
| NEEDS_DISCUSSION | any | NEEDS_DISCUSSION or worse |
| BLOCKED | any | BLOCKED (list both in the body) |

The stricter verdict wins, and the parent always includes a `Clerk-auth skill:` line in the output body showing the Clerk outcome — never hide it.

## Maintenance

This skill exists because Clerk footguns are cross-layer and the general reviewers miss them. Each check in `references/checks.md` was added because a real incident cost the team hours to debug — cross-origin signOut in CI, User B session pollution, baked publishable keys blocking image promotion, `useAuth` vs wrapper divergence.

When a new Clerk pitfall is discovered in production, add it to `references/checks.md` — this is the one place guaranteed to be re-read by every auth-touching review. Also update `delivery/specs/clerk-patterns.md` to keep the project docs in sync.
