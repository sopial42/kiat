# Backend Review Checklist

This is the reference checklist loaded by `kiat-review-backend/SKILL.md` during Phase 3. Each category below is ordered by blast radius — higher categories first, because they cause the worst production incidents when they slip through.

Skim what's obviously fine in the diff and focus on what's non-trivial. A checklist item isn't a nit to flag — it's a question to answer. If the answer is "yes, the code handles this", move on.

Full project conventions live in `delivery/specs/backend-conventions.md`, `delivery/specs/architecture-clean.md`, `delivery/specs/api-conventions.md`, `delivery/specs/database-conventions.md`, and `delivery/specs/security-checklist.md`. This checklist summarizes the review-time checks; the specs are the source of truth for how to implement them.

## 1. Database and migrations

Migration bugs and RLS failures are the worst-case outcomes of a backend review that slips. They can corrupt data, leak between users, or make a table unrewindable. Check these first.

- **Migration file exists and is numbered sequentially.** Out-of-order migrations cause merge conflicts downstream and are a sign the coder didn't sync before adding theirs.
- **Migration is idempotent.** Use `IF NOT EXISTS` on table/column/index creation. If a deploy fails halfway and gets retried, a non-idempotent migration will crash on retry instead of no-opping.
- **Timestamps are `TIMESTAMPTZ`, not `TIMESTAMP`.** Timezone-naive timestamps have caused data bugs when the app moves between regions. The project convention is `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **`updated_at` is present on every mutable row.** Required for optimistic locking and for the `If-Unmodified-Since` pattern.
- **Go code uses `time.RFC3339Nano` to serialize timestamps**, not `time.RFC3339`. The Nano precision matters because the database stores microseconds — losing them means `updated_at` comparisons round-trip incorrectly and optimistic locking silently fails.
- **Foreign keys declare cascade behavior explicitly.** Use `ON DELETE CASCADE` for data owned by the parent row; use `ON DELETE RESTRICT` for shared references. A missing cascade clause inherits the database default, which varies.
- **Indexes exist on columns in the hot path.** Foreign keys, email lookups, `user_id` filters — anything queried frequently. Missing indexes are invisible in dev and catastrophic in prod.
- **RLS is enabled on any table that holds user-scoped data.** `ALTER TABLE X ENABLE ROW LEVEL SECURITY`. Missing RLS means a bug in the handler layer can leak data between users.
- **RLS policies reference `auth.uid()` correctly.** A policy that compares `user_id` to a hardcoded value, or that uses the wrong column, is functionally absent.
- **No N+1 queries.** Loops over a slice calling `repo.Get(id)` instead of `repo.GetMany(ids)` — common and expensive in prod.

## 2. Clean Architecture layering

The project uses 4 layers: domain, usecase, interface, external. The layering rules exist so that business logic is independent of HTTP and SQL — violating them means the code becomes hard to test and hard to refactor. Full details in `delivery/specs/architecture-clean.md`.

### Domain layer (`internal/domain/`)
- Entities are structs with behavior, not DTOs.
- Domain errors are named and specific (e.g., `ErrDuplicateEmail`, `ErrInvalidState`) — generic `errors.New("bad")` loses meaning at the handler boundary.
- Interfaces are defined here (not concrete types) so usecases can depend on abstractions.
- No imports of `net/http`, database drivers, or external SDKs. The domain is pure.

### Usecase layer (`internal/usecase/`)
- Services receive dependencies as interfaces through constructor DI.
- An `Execute()` (or similarly named) method orchestrates the operation.
- Errors are wrapped with context using `fmt.Errorf("action: %w", err)` — bare errors at the handler layer lose the call chain and make debugging awful.
- No HTTP concerns (no `*gin.Context`), no direct database access.

### Interface layer (`internal/interface/`)
- Handlers parse the HTTP request, call the usecase, and map domain errors to HTTP status codes.
- Repositories implement domain interfaces — the handler never sees the concrete repo type.
- Converters exist between domain entities and DB rows / HTTP payloads.
- Input validation happens here, before the usecase is called.

### External layer (`external/`, `main.go`)
- Database clients, third-party SDKs, configuration.
- Dependency injection is wired bottom-up: clients → repositories → usecases → handlers.
- Middleware is registered in a predictable order (logging → auth → rate limiting → route handler).
- Routes are wired to handlers; no business logic in `main.go`.

## 3. API contract compliance

The review checks that the code matches the spec, not that the spec is correct — if the spec is ambiguous, that's a `kiat-validate-spec` miss, not a review failure. Full error code conventions are in `delivery/specs/api-conventions.md`.

- **HTTP method matches the spec** (GET vs POST vs PATCH vs DELETE). A "create" endpoint using PUT instead of POST breaks REST expectations and client code.
- **Path matches the spec** exactly, including path parameters and trailing-slash behavior.
- **Request schema matches the spec** — every required field present, types match, validation rules enforced.
- **Response status is correct** for each outcome (201 Created for create, 200 OK for read, 204 No Content for delete, 409 Conflict for duplicate, etc.).
- **Response schema matches the spec** — every field the client expects is present with the correct type.
- **Error codes match the spec** — the named internal codes (e.g., `INVALID_INPUT`, `DUPLICATE_*`, `NOT_FOUND`, `RATE_LIMITED`) that the frontend parses.
- **Error responses include both code and message** — the frontend needs the code for programmatic handling and the message for UI.
- **Success responses include all the data** the spec promised (id, timestamps, derived fields).
- **Pagination is present** on list endpoints (limit, offset, total) when the spec calls for it.

## 4. Security

Security bugs are the worst reason for a review to miss something — they can leak data, enable takeover, or fail audits. Full security rules are in `delivery/specs/security-checklist.md`.

- **No secrets in code.** Every credential and URL comes from an environment variable. A grep for `sk_`, `eyJ`, or hex strings longer than 32 chars is a cheap sanity check.
- **Input validation** — size limits, format checks, type validation at the handler layer, before the usecase sees the request.
- **Parameterized queries only.** Bun ORM handles this when used correctly; any raw SQL with string interpolation is a SQL injection vector. Flag unconditionally.
- **RLS is enforced end-to-end.** There must be a test that proves User B cannot read User A's data — not just that the RLS policy exists, but that the code respects it.
- **Rate limiting on high-value endpoints** (login, signup, mutations that cost money). If the spec names a bucket size, check the code matches.
- **CORS headers allow specific origins**, not `*`. A permissive CORS header is a silent cross-origin data leak waiting to happen.
- **No internal error details leak to the client.** The handler returns a generic message and logs the real error server-side with a trace ID. Stack traces in HTTP responses are an information disclosure.
- **No sensitive data in logs.** Passwords, tokens, full credit card numbers, private keys — none of these belong in logs, even at debug level.

## 5. Error handling

Good error handling is what makes a 500 survivable. It's hard to add after the fact because each layer needs to propagate errors correctly.

- **Domain errors are specific** — named per failure mode (e.g., `ErrDuplicate*`, `ErrInvalid*`, `ErrNotFound`), not generic.
- **Usecase wraps errors with context** — `fmt.Errorf("create user: %w", err)` — so that the stack trace at the handler layer shows the call chain.
- **Handler maps domain errors to HTTP status codes** with an explicit switch (not a catch-all 500). The mapping itself is a review item:

  | Domain error | HTTP status | Error code |
  |---|---|---|
  | `domain.ErrInvalid*` | 400 | `INVALID_INPUT` |
  | `domain.ErrDuplicate*` | 409 | `DUPLICATE_*` |
  | `domain.ErrNotFound` | 404 | `NOT_FOUND` |
  | `auth.ErrUnauthorized` | 401 | `UNAUTHORIZED` |
  | other | 500 | `INTERNAL_ERROR` (logged with trace_id) |

- **Error messages are user-friendly** — generic at the HTTP boundary, detailed in logs.
- **500 errors log the real error** with a trace ID so on-call can correlate a user report to a log line.

## 6. Logging and observability

Logging is how you debug production. Underlogging means bugs are invisible; overlogging means the signal drowns in noise.

- **Info logs on successful operations** (create/update/delete) with the entity ID.
- **Error logs include the full error, the trace ID, and the relevant context** (user ID, resource ID, input summary).
- **Structured logging is used** — the project logger with fields, not `fmt.Sprintf` into a string.
- **No secrets logged**, even at debug level. It's a compliance problem and a rotation nightmare.
- **No PII beyond what's necessary** — don't log full emails or phone numbers unless the operation is about them.
- **Trace ID is propagated** from middleware into every log line so operations can be correlated.

## 7. Venom tests

Tests aren't a checkbox — they're the contract between the reviewer and production. A change without tests isn't verified, and a test without the right coverage is a false sense of security. Full test-pattern rules are in `delivery/specs/testing.md` and enforced at coder-side by `kiat-test-patterns-check`.

- **Happy path is tested** — the endpoint works with valid input.
- **Error cases are tested** — invalid input, duplicates, permission failures, not-found. Each named error code from the spec has a corresponding test.
- **Edge cases are tested** — empty strings, max length, boundary values, Unicode in text fields.
- **RLS is tested with real users** — seed a row as User A, try to read it as User B, assert empty result. Without this, RLS is assumed-working, not proven-working.
- **Auth is tested** — missing token returns 401, invalid token returns 401, valid token succeeds. Each protected route has at least one auth test.
- **Rate limiting is tested** (if applicable) — N requests pass, the N+1th is rejected.
- **Tests use mocks at the repository boundary** — real DB integration tests are slow and flaky. The repository layer is mocked in unit tests; integration tests live elsewhere.
- **Table-driven tests are used** for multiple-scenario coverage — a single test function with a slice of cases is more maintainable than N copy-pasted test functions.
- **No skipped tests** (`t.Skip()` or `// t.Skip(t)` markers) unless the skip has a ticket reference and an expected unblock date.

## 8. Code quality

These are nice-to-have improvements, not blockers. Most of them should be caught by the toolchain; flagging them in review is usually a sign the reviewer is in nit mode rather than judgment mode. Only flag if the toolchain doesn't catch it and the issue is non-trivial.

- **No TODO comments merged without ticket references.** A naked `// TODO` is a lie that will outlive the reviewer's memory.
- **Structured logger used instead of `fmt.Println`.** `Println` bypasses log levels and trace propagation.
- **No panics in production code paths.** Return errors; let the handler layer decide whether to 500 or degrade gracefully. `panic` in a service is a restart-the-pod event.
- **Naming follows Go conventions** — PascalCase for exported, camelCase for unexported, short names for short scopes.
- **Package names are lowercase and descriptive.** No `utils` or `helpers` packages.
- **Comments explain the "why" when the logic is non-obvious.** Comments that restate the code are noise.
