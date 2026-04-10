# Block D — Row-level security

**Trigger:** any user-scoped data, any table with a `user_id` (or equivalent ownership) foreign key, any endpoint that reads per-user data.

## Rules and reasons

**The migration enables RLS *and* defines at least one policy.** `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;` without a matching `CREATE POLICY` statement is a footgun.

> *Why*: enabling RLS without a policy means the table is *fully locked* — no one can read anything, including the backend service. The first read after deploy returns zero rows and the feature looks broken. Catching this in review is easy; catching it after deploy is a rollback.

**An explicit User B negative test exists for every RLS-sensitive endpoint.** Seed a row as User A, attempt to read it as User B, assert empty result or 403.

> *Why*: RLS can be silently broken by a missing `WHERE user_id = ...` clause. The only way to verify it works is to try reading someone else's data from a different user's context. "It works when I sign in" is not evidence that RLS is enforced — the query might just happen to return the user's own rows because that's what they asked for.

**In Playwright, User B sign-in spawns a fresh browser context.** The project's helper typically takes a `browser` argument and creates a new context (e.g., `signInAsUserB(browser)`) rather than reusing the existing `page`.

> *Why*: browser contexts own their own cookies and storage. Reusing User A's context for User B means both users share one context, and whichever sign-in runs last wins. The "test" silently runs both operations as the same user and always passes.

**After a User B test, User A's storage state is refreshed.**

> *Why*: without refresh, the User A storage state slowly drifts from reality as its token ages. Subsequent User A tests flake as the session expires.

**RLS is the primary enforcement layer, not just defense in depth.** Don't rely on application-layer filtering alone.

> *Why*: application filtering can be bypassed by a bug in a single handler. RLS is enforced by the database regardless of how the query is written, so even a broken handler can't leak data.

## Required acknowledgment (paste verbatim)

> I will add an RLS policy in the migration, write an explicit User B test proving they cannot read User A's data, and use an isolated browser context for the User B Playwright session.

## Common drift caught by reviewers

- Migration has `ENABLE ROW LEVEL SECURITY` but no `CREATE POLICY` — reviewer flags: table is fully locked, nothing is readable.
- Test passes `page` to the User B sign-in helper instead of `browser` — reviewer flags: context pollution, both operations run as the same user.
- No User B read test for a new endpoint returning user-scoped data — reviewer flags: acknowledged rule required an RLS test.
- Storage state refresh is commented out after a User B test — reviewer flags: subsequent User A tests will flake.
