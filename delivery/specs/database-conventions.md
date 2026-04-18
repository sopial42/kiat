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

**Required for**: Any table with user data

### Enable RLS

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### Create Policy (User Isolation)

```sql
-- Users can only see their own data
CREATE POLICY user_own_data ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY user_own_insert ON users
    FOR INSERT WITH CHECK (id = auth.uid());

CREATE POLICY user_own_update ON users
    FOR UPDATE USING (id = auth.uid());

CREATE POLICY user_own_delete ON users
    FOR DELETE USING (id = auth.uid());
```

**Pattern**: `WHERE user_id = auth.uid()` (user can only access their own records)

### RLS for Related Data (user-owned rows)

```sql
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    ...
);

ALTER TABLE items ENABLE ROW LEVEL SECURITY;

CREATE POLICY item_user_isolation ON items
    USING (user_id = auth.uid());
```

### RLS for Nested Data (child rows inheriting parent's scope)

```sql
CREATE TABLE item_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    label VARCHAR(64) NOT NULL,
    ...
);

ALTER TABLE item_tags ENABLE ROW LEVEL SECURITY;

-- User can only access tags on items they own
CREATE POLICY item_tag_user_isolation ON item_tags
    USING (
        item_id IN (
            SELECT id FROM items WHERE user_id = auth.uid()
        )
    );
```

### Service Role Bypass

Migrations run as `service_role` (superuser), which **bypasses RLS**.

```sql
GRANT ALL ON users TO service_role;
GRANT ALL ON items TO service_role;
GRANT ALL ON item_tags TO service_role;
```

This allows migrations to INSERT/UPDATE/DELETE data during seeding.

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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_own ON users USING (id = auth.uid());
```

### Related Data (user-owned rows)

```sql
CREATE TABLE IF NOT EXISTS items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id);
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
CREATE POLICY items_user_isolation ON items
    USING (user_id = auth.uid());
```

### Nested Data (child rows inheriting parent's scope)

```sql
CREATE TABLE IF NOT EXISTS item_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    label VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_item_tags_item ON item_tags(item_id);
ALTER TABLE item_tags ENABLE ROW LEVEL SECURITY;
CREATE POLICY item_tags_user_isolation ON item_tags
    USING (
        item_id IN (
            SELECT id FROM items WHERE user_id = auth.uid()
        )
    );
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

### ❌ Mistake 3: No RLS on User Data

```sql
-- WRONG
CREATE TABLE items (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    ...
    -- No RLS! User B can query User A's data
);

-- GOOD
CREATE TABLE items (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    ...
);
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
CREATE POLICY items_isolation ON items
    USING (user_id = auth.uid());
```

### ❌ Mistake 4: Cascading Delete Without Thought

```sql
-- WRONG
REFERENCES users(id) ON DELETE CASCADE  -- ← If user is deleted, all data gone forever

-- BETTER (for critical data)
REFERENCES users(id) ON DELETE RESTRICT  -- ← Prevent deletion if data exists
```

---

## Testing RLS

In tests, verify User B cannot read User A's data:

```go
// Seed User A's data
seedCarePlan(db, userAID)

// Attempt to read as User B
plans, err := getCarePlans(db, userBID)
assert.NoError(t, err)
assert.Equal(t, 0, len(plans))  // ← User B sees nothing
```

---

See also:
- [backend-conventions.md](backend-conventions.md) — Database interaction patterns
- [testing.md](testing.md) — Testing RLS policies
