# Block F — Venom backend tests

**Trigger:** any test file under `backend/venom/`.

## Rules and reasons

**Tests are table-driven** with a slice of structured cases: `name`, `input`, `expected output`, `expected error`. Each case becomes a subtest via `t.Run(tc.name, ...)`.

> *Why*: table-driven tests force uniform coverage of multiple scenarios and make the test intent clear at a glance. Copy-pasted test functions are harder to maintain — when the interface changes, you have to update N functions instead of one test table.

**Repositories are mocked in unit tests**, not backed by a real database connection.

> *Why*: unit tests should be fast and deterministic. Real DB connections introduce I/O latency, require a running Postgres, and depend on the state of the database between runs. Integration tests with real Postgres are a different layer — they live elsewhere in the test pyramid.

**Coverage includes the happy path plus at least two error cases per handler.** Error cases should include invalid input, conflict/duplicate, and permission denial where applicable.

> *Why*: every handler has more failure modes than success modes, and errors are where bugs hide. A test suite with only happy-path coverage passes on day one and fails the first time production hits an edge case.

**If the handler touches user-scoped data, there's an RLS test** (see Block D for the User A / User B pattern).

> *Why*: see Block D.

**No `t.Skip()` calls in committed tests.** If a test needs to be skipped, either fix it or delete it. Don't leave silent skips.

> *Why*: a skipped test is a test that isn't running. Over time these accumulate and the test suite becomes a lie about what's covered. If a skip is temporary (e.g., waiting on a fixture), it needs a ticket reference and a deletion date — otherwise delete the test.

## Required acknowledgment (paste verbatim)

> I will write table-driven tests with mocked repositories, covering happy path + at least 2 error cases + an RLS test if applicable. No t.Skip() calls.

## Common drift caught by reviewers

- Tests connect directly to Postgres — reviewer flags: that's an integration test, not a unit test; use mocks.
- Only a happy-path test, no error cases — reviewer flags: acknowledged rule required 2+ error cases.
- `t.Skip("will fix later")` left in committed code — reviewer flags: protocol violation, no silent skips.
- User-scoped endpoint has no User B test — reviewer flags: see Block D.
