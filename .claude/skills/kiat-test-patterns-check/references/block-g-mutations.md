# Block G — Async mutations and optimistic locking

**Trigger:** any `useMutation`, any PATCH endpoint, any `updated_at` comparison in Go.

## Rules and reasons

### Backend (Go)

**`updated_at` is serialized and parsed with `time.RFC3339Nano`**, not `time.RFC3339`.

> *Why*: PostgreSQL `TIMESTAMPTZ` stores microsecond precision. `time.RFC3339` drops anything finer than seconds, so the roundtrip `DB → JSON → back to Go` loses precision. The next comparison sees a different timestamp and optimistic locking silently fails — the client's "no conflict" response doesn't match the DB state.

**Compare `updated_at` at `Truncate(time.Microsecond)` granularity**, not exact equality.

> *Why*: Go's `time.Time` supports nanoseconds while Postgres stops at microseconds. A direct equality comparison between a Go-side `time.Time` and a Postgres-round-tripped one will usually fail because of the sub-microsecond drift.

**Bun's `.Returning("col").Exec(ctx)` does not scan the returned values.** Use `.Scan(ctx)` when you need them.

> *Why*: this is a Bun ORM footgun. `Exec` runs the query and discards returned columns. Code that writes `.Returning("id").Exec(ctx)` reads as if it's getting the id but actually gets nothing — subtle bug because the compiler is happy.

**For PATCH null-clearing, use raw JSON parsing with an explicit `ClearX bool` flag** for each nullable pointer field.

> *Why*: Go's `json.Unmarshal` can't distinguish `{"field": null}` from `{}` for `*int` or `*string` — both produce a nil pointer. Without the explicit flag, a client trying to clear a field is indistinguishable from a client that simply didn't include it. Full pattern is in `delivery/specs/backend-conventions.md`, "PATCH null clearing" section.

### Frontend (React)

**Chain rapid sequential mutations on the same resource via a promise ref**, not separate `useMutation` calls.

> *Why*: separate `useMutation` calls each read the current `updated_at` at call time. When the user does "select → clear → select" in quick succession, the second and third mutations fire before the first resolves — they all see the same `updated_at` and the last two race into 409 Conflict. A promise ref ensures each mutation waits for the previous to resolve, so the `updated_at` is always current.

**On 409 Conflict, show a user-friendly error, refetch the resource, and let the user retry manually.** Don't auto-retry.

> *Why*: a 409 means someone else updated the resource in parallel. Auto-retry silently overwrites that other change — classic lost-update bug. Showing the conflict gives the user a chance to see what changed and decide what to do.

## Required acknowledgment (paste verbatim)

> I will use `time.RFC3339Nano` for timestamps, chain rapid mutations via a promise ref, handle 409 with refetch-and-retry, and use `.Scan(ctx)` for Bun Returning queries.

## Common drift caught by reviewers

- Go code uses `time.RFC3339` for timestamp JSON — reviewer flags: breaks optimistic locking.
- Frontend fires two independent `useMutation` calls in rapid sequence — reviewer flags: race condition, use a promise ref.
- Bun query uses `.Returning("id").Exec(ctx)` but the returned id isn't read — reviewer flags: `Exec` doesn't scan, use `.Scan(ctx)`.
- PATCH handler can't distinguish `{"field": null}` from `{}` — reviewer flags: needs raw JSON parsing with an explicit clear flag.
