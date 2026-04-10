# Block F — Venom Backend Tests

**Trigger:** any test file under `backend/venom/**`

## Mandatory rules

- Use **table-driven tests** with structured cases: `name`, `input`, `expected output`, `expected error`. Each case becomes a subtest via `t.Run(tc.name, ...)`.
- Use **mocks** for repositories (`MockUserRepository`, `MockCarePlanRepository`, etc.). NOT real DB connections in unit tests — that's integration tests, a different layer.
- Coverage: **happy path + at least 2 error cases per handler**. Error cases should include invalid input, conflict/duplicate, and permission denied.
- RLS test REQUIRED if the handler touches user-scoped data (see Block D for the User A / User B pattern).
- **No `t.Skip()`** in committed tests. If a test needs to be skipped, fix it or delete it — never commit a silent skip.

## Required acknowledgment (paste verbatim)

> I will write table-driven tests with mocked repositories, covering happy path + at least 2 error cases + an RLS test if applicable. No t.Skip() calls.

## Common drift caught by reviewers

- Tests connect directly to Postgres in unit tests — reviewer flags: that's an integration test, not a unit test; use mocks
- Only a happy-path test, no error cases — reviewer flags: acknowledged rule required 2+ error cases
- `t.Skip("will fix later")` left in committed code — reviewer flags: protocol violation, no silent skips
- User-scoped endpoint has no User B test — reviewer flags: see Block D rule on RLS testing
