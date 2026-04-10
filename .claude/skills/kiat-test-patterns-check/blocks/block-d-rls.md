# Block D — RLS (Row-Level Security)

**Trigger:** any user-scoped data, any table with a `user_id` foreign key, any endpoint that reads per-user data

## Mandatory rules

- Migration MUST include `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;` **AND** an actual policy (the ENABLE alone blocks everything without a policy).
- RLS test is REQUIRED: seed data as User A, attempt read as User B, assert the result is empty or 403.
- User B tests in Playwright MUST use an **isolated browser context**: `signInAsUserB(browser)` NOT `signInAsUserB(page)`. Passing `page` pollutes User A's session.
- After a User B test, `restoreUserA(browser)` re-saves storageState with a fresh JWT. Without this, subsequent User A tests flake because the storageState token is stale.
- Never rely on application-layer filtering alone — RLS is the enforcement layer. Application filtering is defense-in-depth, not the primary gate.

## Required acknowledgment (paste verbatim)

> I will add an RLS policy in the migration, write an explicit User B test proving they cannot read User A's data, and use `signInAsUserB(browser)` with isolated browser context.

## Common drift caught by reviewers

- Migration has `ENABLE ROW LEVEL SECURITY` but no `CREATE POLICY` — reviewer flags: table is now fully locked (no one can read)
- Test uses `signInAsUserB(page)` instead of `signInAsUserB(browser)` — reviewer flags: context pollution
- No User B read test for a new endpoint that returns user-scoped data — reviewer flags: acknowledged rule required RLS test
- `restoreUserA` is called but its storageState refresh is commented out — reviewer flags: subsequent tests will flake
