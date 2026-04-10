# Block G — Async Mutations / Optimistic Locking

**Trigger:** any `useMutation`, any PATCH endpoint, any `updated_at` check in Go

## Mandatory rules

### Backend (Go)

- `updated_at` uses `time.RFC3339Nano` precision for serialization and comparison. `time.RFC3339` drops microseconds and breaks optimistic locking.
- Compare `updated_at` at the `Truncate(time.Microsecond)` level, not exact equality — PostgreSQL TIMESTAMPTZ has microsecond precision but Go has nanosecond; round before compare.
- Bun ORM: `Returning("col").Exec(ctx)` does **NOT** scan the returned values. Use `.Scan(ctx)` instead if you need the returned column values.
- PATCH null-clearing: Go `json.Unmarshal` can't distinguish absent fields from `null` for `*int` / `*string` pointer fields. Use raw JSON parsing with explicit `ClearX bool` flags — see [`../../../../delivery/specs/backend-conventions.md`](../../../../delivery/specs/backend-conventions.md) "PATCH null clearing" section.

### Frontend (React)

- Rapid sequential mutations on the same resource (select → clear → select again) MUST chain via a **promise ref pattern**, NOT separate `useMutation` calls. Separate calls race on the stale `updated_at` and produce 409 conflicts.
- On **409 Conflict**: show a user-friendly error, refetch the resource, let the user retry. Don't auto-retry (may cause a silent overwrite of another user's changes).

## Required acknowledgment (paste verbatim)

> I will use `time.RFC3339Nano` for timestamps, chain rapid mutations via a promise ref, handle 409 with refetch-and-retry, and use `.Scan(ctx)` for Bun Returning queries.

## Common drift caught by reviewers

- Go code uses `time.RFC3339` for timestamp JSON — reviewer flags: breaks optimistic locking
- Frontend fires two independent `useMutation` calls in rapid sequence — reviewer flags: race condition, use promise ref
- Bun query uses `.Returning("id").Exec(ctx)` but the returned id isn't read — reviewer flags: Exec doesn't scan, use `.Scan(ctx)`
- PATCH handler can't distinguish `{"field": null}` from `{}` — reviewer flags: needs raw JSON parsing + ClearField flag
