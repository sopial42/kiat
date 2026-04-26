# Database Conventions: Migrations & RLS

Standards for writing idempotent migrations and Row-Level Security policies.

---

## Migration Files

**Location**: `backend/migrations/`

**Naming**: `NNN_description.sql` (3-digit number, snake_case description)

```
migrations/
├── 001_create_users.sql
├── 002_create_items.sql
├── 003_add_item_tags.sql
└── 004_add_rls_policies.sql
```

**Numbering**: Sequential, starting at 001. Run in order.

---

## Migration Structure

### ✅ Good: Idempotent

```sql
-- backend/migrations/001_create_users.sql

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

**Rules**:
- Use `IF NOT EXISTS` (idempotent — safe to run multiple times)
- Always include `id` (UUID primary key)
- Always include `created_at`, `updated_at` (TIMESTAMPTZ, default now())
- Use `TIMESTAMPTZ` (timezone-aware, UTC by default)
- Create indexes on frequently queried columns (email, foreign keys)

### ❌ Bad: Not Idempotent

```sql
-- ❌ WRONG
CREATE TABLE users (  -- ← Will fail if table exists
    id SERIAL PRIMARY KEY,
    ...
);

CREATE INDEX idx_users_email ON users(email);  -- ← No IF NOT EXISTS
```

---

## Timestamps

**Data Type**: `TIMESTAMPTZ` (timezone-aware)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ...
);
```

**Why TIMESTAMPTZ?**
- Stores time in UTC, displays in local time
- Prevents timezone-related bugs
- Allows comparisons across timezones

**In Go**: Use `time.RFC3339Nano` (microsecond precision)
```go
user.UpdatedAt = time.Now()  // time.RFC3339Nano format
```

---

## Foreign Keys & Cascading Deletes

**Pattern**:
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**ON DELETE CASCADE**: When user is deleted, all orders are deleted automatically

**Alternatives**:
- `ON DELETE RESTRICT` — Prevent delete if child records exist
- `ON DELETE SET NULL` — Set child's foreign key to NULL (column must be nullable)

**Use CASCADE when**: Logical ownership (an item belongs to a user, a tag belongs to an item)

---

## Row-Level Security (RLS)

**Required for**: any table with user-scoped data.

**Stack**: vanilla PostgreSQL 15+. This project does **not** use Supabase, Hasura, or any vendor extension that ships its own claim helpers (`auth.uid()`, `current_user_id()`, etc.). The mechanism below is built on stock PostgreSQL primitives only.

**Iron rule**: RLS must NEVER be disabled at runtime. Migrations connect as a superuser by necessity (they CREATE TABLE / POLICY / ROLE); the backend MUST connect at request time as a non-superuser, non-BYPASSRLS role and `SET LOCAL ROLE app_user` inside every transaction. There is no exception. There is no "service role" pattern. A backend that connects as a superuser silently disables RLS for every request — this is the most catastrophic, hardest-to-detect failure mode in a Postgres app.

### The four-step pattern (mandatory for every user-scoped table)

```sql
-- Step 1 + 2: ENABLE *and* FORCE.
-- Without FORCE, the table OWNER (the role that ran the migration) bypasses
-- RLS unconditionally. The owner is typically the migration runner, which is
-- often the same connection the backend uses in dev. FORCE is what makes the
-- policy fire for the table owner too.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- Step 3: idempotent policy (Postgres has no CREATE POLICY IF NOT EXISTS).
DROP POLICY IF EXISTS users_own ON users;
CREATE POLICY users_own ON users
    USING      (id = current_setting('request.jwt.claim.sub', true)::uuid)
    WITH CHECK (id = current_setting('request.jwt.claim.sub', true)::uuid);

-- Step 4: grant table privileges to the application role.
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;
```

**Why `current_setting('request.jwt.claim.sub', true)::uuid`**: vanilla Postgres has no built-in "current user JWT claim" function. We expose the JWT subject by writing it into a session-level GUC (`request.jwt.claim.sub`) at the start of every transaction. The policy reads the GUC back. The `, true` second argument means "return NULL if unset" rather than erroring — so a misconfigured request returns zero rows (loud, easy to detect) rather than 500-ing.

### Database roles — the three-tier model

Three roles, three lifecycles, two `DATABASE_URL`s. The reason there are three (not one) is that `CREATE TABLE` does not require `SUPERUSER` and querying user data should never allow bypassing RLS. The temptation to use a single all-powerful role for everything (the `service_role` pattern) is exactly the trap this section exists to prevent.

| Tier | Role | When it connects | Privileges |
|---|---|---|---|
| 1 | **Bootstrap superuser** — `postgres` (dev) / cloud admin role like `cloudsqlsuperuser`, `rds_superuser` (prod) | Cluster setup, one-off DDL, disaster recovery — **never at runtime, never for routine migrations** | True or near-true superuser. Used only to provision the other two roles, plus rare `BYPASSRLS` backfills (see below). |
| 2 | **`app_migrator`** — schema owner | `make migrate`, deploy boot — **never serves HTTP requests** | `NOSUPERUSER NOBYPASSRLS CREATEROLE LOGIN` + `GRANT CREATE ON SCHEMA public`. Can DDL but cannot bypass RLS. (Doesn't need to bypass — migrations don't query user data; DDL is unaffected by RLS.) |
| 3 | **`app_user`** — runtime | Every HTTP request the backend serves | `NOSUPERUSER NOBYPASSRLS LOGIN` + per-table `GRANT SELECT, INSERT, UPDATE, DELETE`. RLS fires on every query. |

**Two connection strings, one physical database:**

```
MIGRATION_DATABASE_URL=postgres://app_migrator:xxx@db/app   # used by `make migrate`, deploy boot
DATABASE_URL=postgres://app_user:yyy@db/app                  # used by the backend at request time
```

The backend reads `DATABASE_URL` and never sees `MIGRATION_DATABASE_URL`. The migration runner reads `MIGRATION_DATABASE_URL` and never sees `DATABASE_URL`. They are separate concerns with separate failure modes — and separating them is what makes RLS-correctness mechanically enforceable.

**Why the migration role doesn't need `SUPERUSER`**: `CREATE TABLE`, `CREATE INDEX`, `CREATE POLICY`, `ALTER TABLE`, `GRANT` — none of these require superuser. They require ordinary CREATE privilege on the schema (and `CREATEROLE` if the migration provisions roles). `SUPERUSER` is conflated with "DDL privileges" only by vendors that ship a single overloaded role (Supabase's `service_role`, Firebase's "admin"). In vanilla Postgres they are independent attributes.

**Why the migration role doesn't need `BYPASSRLS`**: migrations do DDL. DDL is not subject to RLS. The handful of migrations that backfill user-scoped data need an explicit one-statement bypass — see the "Backfills" section below — but the migration role itself stays `NOBYPASSRLS` so a typo in a future migration can't silently leak data.

#### Bootstrap (run once, by tier 1)

```sql
-- bootstrap.sql — runs once at cluster setup, never again.
-- Dev: lives in /docker-entrypoint-initdb.d/ so docker-compose runs it on
-- first volume creation. Prod: applied by Terraform / cloud CLI / DBA before
-- the first deploy. Either way, run by the tier-1 superuser.

CREATE ROLE app_migrator NOSUPERUSER NOBYPASSRLS CREATEROLE LOGIN PASSWORD '<from-secrets>';
CREATE ROLE app_user     NOSUPERUSER NOBYPASSRLS            LOGIN PASSWORD '<from-secrets>';

GRANT CREATE ON SCHEMA public TO app_migrator;
GRANT USAGE  ON SCHEMA public TO app_user;
GRANT app_user TO app_migrator;  -- so app_migrator can GRANT to app_user (PG requires membership)
```

**Why `CREATEROLE` on `app_migrator`**: lets the migrator run idempotent `CREATE ROLE app_user IF NOT EXISTS` blocks inside migrations as a defensive backup. `CREATEROLE` is **not** a superuser privilege — it's a separate role attribute that grants only role management.

**Why `GRANT app_user TO app_migrator`**: PostgreSQL requires the grantor to be a member of the role being granted. Without this line, `GRANT SELECT ON items TO app_user` inside a migration fails with `permission denied for role app_user`.

#### Idempotent role re-creation (defensive backup in migrations)

If you can't guarantee the bootstrap ran (dev DB recreated from scratch, ephemeral CI database, etc.), include a defensive `IF NOT EXISTS` block in the first RLS-touching migration. It no-ops in clean environments and self-heals in drifted ones. Requires `app_migrator` to have `CREATEROLE`.

```sql
-- 001_bootstrap_app_user.sql (idempotent — safe to re-run)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        -- Defensive fallback: bootstrap-provisioned roles are LOGIN; this
        -- defensive copy is NOLOGIN because we're inside a migration with
        -- no password material at hand. Production never reaches this branch.
        CREATE ROLE app_user NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO app_user;
```

In production with infra-provisioned roles, this block is a no-op. In ephemeral dev/CI databases where bootstrap may not have run, it self-heals.

**Never grant `SUPERUSER` or `BYPASSRLS` to `app_user` or `app_migrator`. Ever.** A single misplaced `ALTER ROLE` is a complete RLS bypass.

### Per-request RLS context (mandatory in repository code)

The connection is already `app_user` per `DATABASE_URL` (above). Two more things must happen on every request for RLS to actually work:

1. **`SET LOCAL ROLE app_user`** — defense-in-depth. The DSN may resolve to a different effective role at runtime (PgBouncer pool role, Cloud SQL IAM-mapped role, accidental DSN swap during deploy). `SET LOCAL ROLE` makes the per-tx role explicit and unambiguous, regardless of what the connection-time role happened to be.
2. **`SET LOCAL request.jwt.claim.sub = '<uuid>'`** — sets the GUC the policy reads. Without this, `current_setting(..., true)` returns NULL and the policy denies everything (loud failure: zero rows returned).

`SET LOCAL` automatically reverts at COMMIT/ROLLBACK, so there is no cross-request leak. The repository layer wraps every query in a transaction that does both:

```go
// backend/internal/interface/repository/<entity>.go — illustrative pattern.
// The exact file may evolve; the wrapper shape is the contract.
func (r *Repo) withRLSTx(ctx context.Context, userID uuid.UUID, fn func(*sql.Tx) error) (err error) {
    tx, err := r.db.BeginTx(ctx, nil)
    if err != nil { return fmt.Errorf("begin tx: %w", err) }
    defer func() { if err != nil { _ = tx.Rollback() } }()

    // Switch to the app_user role for the duration of the tx. SET LOCAL
    // automatically reverts at COMMIT/ROLLBACK — no cross-request leak.
    if _, err = tx.ExecContext(ctx, "SET LOCAL ROLE app_user"); err != nil {
        return fmt.Errorf("set rls role: %w", err)
    }
    // SET LOCAL doesn't accept parameter binding for the value, but
    // uuid.UUID.String() produces canonical hex with no SQL-special chars,
    // so direct format-into-string is safe here (and only here).
    if _, err = tx.ExecContext(ctx,
        fmt.Sprintf("SET LOCAL request.jwt.claim.sub = '%s'", userID.String())); err != nil {
        return fmt.Errorf("set rls context: %w", err)
    }

    if err = fn(tx); err != nil { return err }
    if err = tx.Commit(); err != nil { return fmt.Errorf("commit: %w", err) }
    return nil
}
```

Every public repository method calls `withRLSTx` and runs its SQL inside the closure. A repository method that issues SQL outside this wrapper is a review-blocking bug.

### RLS for related data (user-owned rows)

```sql
CREATE TABLE items (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE items FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS items_user_isolation ON items;
CREATE POLICY items_user_isolation ON items
    USING      (user_id = current_setting('request.jwt.claim.sub', true)::uuid)
    WITH CHECK (user_id = current_setting('request.jwt.claim.sub', true)::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON items TO app_user;
```

### RLS for nested data (child rows inheriting parent's scope)

```sql
CREATE TABLE item_tags (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id    UUID        NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    label      VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE item_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_tags FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS item_tags_user_isolation ON item_tags;
CREATE POLICY item_tags_user_isolation ON item_tags
    USING (
        item_id IN (
            SELECT id FROM items
            WHERE user_id = current_setting('request.jwt.claim.sub', true)::uuid
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON item_tags TO app_user;
```

### Backfills that touch user-scoped data

When a schema migration backfills user-scoped data (recomputing a derived column, normalizing a format, populating a new NOT NULL field), the `UPDATE` runs as `app_migrator`. Because `app_migrator` is `NOSUPERUSER NOBYPASSRLS` and the table has `FORCE ROW LEVEL SECURITY`, the migration is subject to the policy. The migration session has no `request.jwt.claim.sub` set, so the policy's predicate evaluates to NULL and the UPDATE matches **zero rows**. The migration silently no-ops.

This is the correct security posture (`app_migrator` shouldn't be able to read or write arbitrary user data through normal SQL). To do a legitimate cross-user backfill, the migration MUST temporarily and explicitly switch to the bootstrap superuser for the one statement that needs the bypass:

```sql
-- backend/migrations/NNN_backfill_<reason>.sql

-- One-shot RLS bypass — explicit, scoped to one statement, auditable.
-- Reason: <one paragraph explaining why this backfill cannot be RLS-respecting>
-- Reviewer must verify: <what to grep for, what invariant to check>
SET LOCAL ROLE postgres;  -- or the cloud's tier-1 role; the name varies per env
UPDATE items SET legacy_flag = derived_function(...);
RESET ROLE;
```

Three properties this pattern preserves and "permanent BYPASSRLS on app_migrator" doesn't:
- **Scoped**: bypass holds for one statement, then `RESET ROLE` restores `app_migrator`.
- **Auditable**: every bypass appears in `git grep "SET LOCAL ROLE postgres"` (or equivalent for your tier-1 role name). Security review can enumerate them.
- **Loud**: the role switch lives in the migration file. A new dev reading the migration sees the bypass immediately, with the comment explaining why.

**Anti-pattern — granting `BYPASSRLS` to `app_migrator` "just for migrations"**: the whole architecture rests on the property that no role the application can adopt at any time bypasses RLS. Every permanent exception erodes the property until the property is gone. Cumulative drift, not one bad commit, is how this fails.

**Anti-pattern — dropping the policy or `ALTER TABLE NO FORCE ROW LEVEL SECURITY` for the duration of a migration**: if the migration crashes mid-flight (network blip, deploy interruption, OOM), RLS stays disabled. Catastrophic, hard to detect, hard to recover.

### Migrations vs. runtime — explicit contract

| Connection | Role | Connects via | RLS behavior |
|---|---|---|---|
| Cluster bootstrap (one-off) | Tier 1 — superuser (`postgres` / cloud admin) | Direct admin connection | Bypasses RLS by design. Never used at runtime, never used for routine migrations. |
| Schema migration (`make migrate`, deploy boot) | Tier 2 — `app_migrator` (`NOSUPERUSER NOBYPASSRLS CREATEROLE`) | `MIGRATION_DATABASE_URL` | DDL is unaffected by RLS. Backfills that touch user-scoped data hit the policy and no-op (see "Backfills" above). |
| Backend at request time (correct) | Tier 3 — `app_user` (`NOSUPERUSER NOBYPASSRLS`) + `SET LOCAL ROLE app_user` per tx | `DATABASE_URL` | RLS fires; policy gates every query. |
| Backend with `DATABASE_URL` pointing at tier 1 | Superuser | `DATABASE_URL` (misconfigured) | **CATASTROPHIC** — RLS silently bypassed for every request. The deploy spec's job is to make this configuration impossible. |
| Backend with `DATABASE_URL` pointing at `app_migrator` | `app_migrator` | `DATABASE_URL` (misconfigured) | RLS fires (good), but `app_migrator` has DDL privileges the runtime should never have (bad). Deploy spec must prevent this configuration too. |
| Backend with `DATABASE_URL` correct but missing `SET LOCAL ROLE app_user` | `app_user` | `DATABASE_URL` | RLS fires correctly. The `SET LOCAL ROLE` is defense-in-depth; not strictly required when the connection is already `app_user`, but mandatory because pool roles, IAM-mapped roles, and accidental DSN swaps can flip the effective role. |
| Backend with `DATABASE_URL` correct but missing `SET LOCAL request.jwt.claim.sub` | `app_user` | `DATABASE_URL` | RLS fires; policy evaluates `current_setting(...)` to NULL → all queries return zero rows. Loud failure, easy to detect. |

---

## Unique Constraints

**Enforce uniqueness**:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,  -- ← Each user has unique email
    ...
);

-- Or with named constraint:
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    CONSTRAINT users_email_unique UNIQUE (email),
    ...
);
```

**Composite unique constraint**:
```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    UNIQUE(user_id, preference_key)  -- ← Each user can have this key only once
);
```

---

## Common Table Patterns

### Users Table

```sql
CREATE TABLE IF NOT EXISTS users (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email      VARCHAR(255) NOT NULL UNIQUE,
    name       VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_own ON users;
CREATE POLICY users_own ON users
    USING      (id = current_setting('request.jwt.claim.sub', true)::uuid)
    WITH CHECK (id = current_setting('request.jwt.claim.sub', true)::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;
```

### Related Data (user-owned rows)

```sql
CREATE TABLE IF NOT EXISTS items (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL,
    status     VARCHAR(50)  NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id);

ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE items FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS items_user_isolation ON items;
CREATE POLICY items_user_isolation ON items
    USING      (user_id = current_setting('request.jwt.claim.sub', true)::uuid)
    WITH CHECK (user_id = current_setting('request.jwt.claim.sub', true)::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON items TO app_user;
```

### Nested Data (child rows inheriting parent's scope)

```sql
CREATE TABLE IF NOT EXISTS item_tags (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id    UUID        NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    label      VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_item_tags_item ON item_tags(item_id);

ALTER TABLE item_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_tags FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS item_tags_user_isolation ON item_tags;
CREATE POLICY item_tags_user_isolation ON item_tags
    USING (
        item_id IN (
            SELECT id FROM items
            WHERE user_id = current_setting('request.jwt.claim.sub', true)::uuid
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON item_tags TO app_user;
```

---

## Naming Conventions

### Tables
- Plural, lowercase, snake_case
- `users`, `items`, `item_tags`

### Columns
- Lowercase, snake_case
- Foreign keys: `{table}_id` (e.g., `user_id`, `item_id`)
- Timestamps: `created_at`, `updated_at`
- Status: `status` (not `user_status`)

### Indexes
- `idx_{table}_{column}` (e.g., `idx_users_email`, `idx_items_user`)

### Constraints
- `{table}_{column}_{type}` (e.g., `users_email_unique`, `orders_user_fk`)

---

## Common Mistakes

### ❌ Mistake 1: Missing IF NOT EXISTS

```sql
-- WRONG
CREATE TABLE users (...)  -- Fails on second migration run

-- GOOD
CREATE TABLE IF NOT EXISTS users (...)  -- Safe to rerun
```

### ❌ Mistake 2: Wrong Timestamp Type

```sql
-- WRONG
created_at TIMESTAMP  -- ← No timezone, database default may vary

-- GOOD
created_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- ← Explicit timezone
```

### ❌ Mistake 3: No RLS on user data

```sql
-- WRONG
CREATE TABLE items (
    id      UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    ...
    -- No RLS! Any user can query any other user's data
);

-- GOOD
CREATE TABLE items (
    id      UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    ...
);
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE items FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS items_isolation ON items;
CREATE POLICY items_isolation ON items
    USING      (user_id = current_setting('request.jwt.claim.sub', true)::uuid)
    WITH CHECK (user_id = current_setting('request.jwt.claim.sub', true)::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON items TO app_user;
```

### ❌ Mistake 4: Cascading delete without thought

```sql
-- WRONG
REFERENCES users(id) ON DELETE CASCADE  -- ← If user is deleted, all data gone forever

-- BETTER (for critical data)
REFERENCES users(id) ON DELETE RESTRICT  -- ← Prevent deletion if data exists
```

### ❌ Mistake 5: ENABLE without FORCE

```sql
-- WRONG: works in tests with non-owner roles, silently fails in production
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
-- ...policy here...

-- GOOD: also fires for the table owner (the migration runner, often the
-- same role the backend uses in dev)
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE items FORCE  ROW LEVEL SECURITY;
```

Without `FORCE`, the table owner is exempt from RLS regardless of policies. This matters because the migration runner *is* the owner — if the backend ever connects as that role, the policy is silently inert. `FORCE` is one line; never skip it.

### ❌ Mistake 6: Backend connects as a superuser at runtime

```
DATABASE_URL=postgres://postgres:...@db/app   # ❌ "postgres" is superuser → RLS bypassed for every request

DATABASE_URL=postgres://app_user:...@db/app   # ✅ NOSUPERUSER NOBYPASSRLS → RLS fires
```

The connection role and the per-request `SET LOCAL ROLE app_user` are two layers of defense. **Both** must hold. A superuser connection bypasses RLS even with `FORCE` and even with the `SET LOCAL ROLE` switch (because `SET LOCAL ROLE` is a no-op when the session is already a superuser-equivalent in the relevant sense for some RLS paths). The deployment spec is responsible for ensuring `DATABASE_URL`'s role is `NOSUPERUSER NOBYPASSRLS` in production.

### ❌ Mistake 7: Repository method that issues SQL outside the RLS wrapper

```go
// WRONG: bypasses the wrapper, no SET LOCAL ROLE, no SET LOCAL claim → either
// returns 0 rows (if connecting as app_user) or returns ALL rows (if connecting
// as a superuser-ish role). Either way, the test doesn't catch it because the
// happy-path query returns "something".
func (r *Repo) listLegacy(ctx context.Context, userID uuid.UUID) ([]Item, error) {
    rows, err := r.db.QueryContext(ctx, "SELECT * FROM items")
    // ...
}

// GOOD: every query goes through withRLSTx, no exceptions.
func (r *Repo) List(ctx context.Context, userID uuid.UUID) ([]Item, error) {
    var out []Item
    err := r.withRLSTx(ctx, userID, func(tx *sql.Tx) error {
        rows, err := tx.QueryContext(ctx, "SELECT * FROM items")
        // ...
    })
    return out, err
}
```

---

## Testing RLS

The test must go through the **repository layer** (which sets the role and the JWT claim), not naked SQL. A test that runs raw SQL against the connection bypasses both protections and proves nothing.

```go
// Seed via repoA (whose withRLSTx sets request.jwt.claim.sub to userAID)
require.NoError(t, repoA.Save(ctx, userAID, item))

// Attempt to read via repoB (whose withRLSTx sets request.jwt.claim.sub to userBID)
items, err := repoB.List(ctx, userBID)
require.NoError(t, err)
require.Empty(t, items, "user B must not see user A's data")
```

Equivalently, write a Venom HTTP test that authenticates as User A, creates an item, then authenticates as User B and asserts the list is empty. The Venom version is stronger because it exercises the same code path the production frontend uses.

---

See also:
- [backend-conventions.md](backend-conventions.md) — Database interaction patterns
- [testing.md](testing.md) — Testing RLS policies
