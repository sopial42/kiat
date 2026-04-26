# Deployment & Environment

Project-level rules for environment variables, local development modes, and production safety guards.

This doc is stack-specific — adapt the values (Clerk, Cloud Run, PostgreSQL, etc.) to your project's actual stack. The **structure** and **safety rules** are universal.

---

## Local Development Modes

Kiat-based projects typically have two development modes: real external services, and offline bypass for fast iteration.

### Mode 1 — Real services (`make dev`)

- Real Clerk auth (internet required)
- Real Postgres (local docker-compose)
- Real MinIO / S3 (local)
- Use for: Playwright E2E, production-like testing, manual QA

### Mode 2 — Test bypass (`make dev-offline`)

- Test auth bypass (`ENABLE_TEST_AUTH=true` + `X-Test-User-Id` header)
- Fast, offline-capable
- Use for: Venom backend tests, rapid local iteration, unit-level work

**Rule:** use `make dev` when testing anything user-facing. Use `make dev-offline` only for backend isolation.

---

## Environment Variables

### Backend (`backend/.env`)

```bash
# Database — TWO connection strings, one physical database, by design.
# The split enforces RLS-correctness (see "Database Roles" section below
# and database-conventions.md §"Row-Level Security"). DO NOT collapse them.
DATABASE_URL=postgresql://app_user:yyy@localhost:5432/dbname             # Runtime — backend reads this for HTTP requests. Role: NOSUPERUSER NOBYPASSRLS.
MIGRATION_DATABASE_URL=postgresql://app_migrator:xxx@localhost:5432/dbname # Migrations — `make migrate` and deploy boot read this. Role: NOSUPERUSER NOBYPASSRLS CREATEROLE + GRANT CREATE.

# Auth (Clerk — adapt to your provider)
CLERK_SECRET_KEY=sk_test_...
ENABLE_TEST_AUTH=false          # MUST be false in production

# Environment marker (used by production guard)
ENV=development                 # development | staging | production

# Observability
TRACE_HEADER=X-Trace-Id
LOG_LEVEL=info
```

### Frontend (`frontend/.env.local`)

```bash
# API endpoint
NEXT_PUBLIC_API_URL=http://localhost:8080

# Auth (Clerk publishable key — injected at runtime, see "Docker Image Promotability" below)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_ENABLE_TEST_AUTH=false
```

### Secrets rule

**Never commit secrets** (`CLERK_SECRET_KEY`, `DATABASE_URL` with real credentials, AWS keys, etc.). Use `.env.example` with placeholder values to document the required vars, and add the real `.env` to `.gitignore`. See [security-checklist.md](security-checklist.md) for the full secret handling rules.

---

## Database Roles (RLS-correctness contract)

This section is the deployment-side of the RLS architecture in [`database-conventions.md`](database-conventions.md) §"Row-Level Security (RLS)". Read that first for the schema-level pattern; this section covers how the deploy environment provisions roles and wires connection strings.

### The three roles

| Tier | Role | Where it's provisioned | What connects with it |
|---|---|---|---|
| 1 | `postgres` (dev — default in Postgres image) / `cloudsqlsuperuser` / `rds_superuser` (prod) | The DB image / managed-DB control plane — exists by default | Cluster bootstrap, one-off DDL, the rare `BYPASSRLS` backfill (see below). **Never connects at runtime, never connects for routine migrations.** |
| 2 | `app_migrator` | Bootstrap script (dev) / Terraform / cloud CLI (prod) — provisioned by tier 1, before the first deploy | `MIGRATION_DATABASE_URL` — read by `make migrate` and the deploy boot script |
| 3 | `app_user` | Bootstrap script (dev) / Terraform / cloud CLI (prod) — provisioned by tier 1, before the first deploy | `DATABASE_URL` — read by the backend at request time |

Tiers 2 and 3 are both `NOSUPERUSER NOBYPASSRLS`. Tier 2 additionally has `CREATEROLE` and `GRANT CREATE ON SCHEMA public`. Neither tier 2 nor tier 3 should ever be granted `BYPASSRLS` — see "Backfills" in `database-conventions.md` for the rare cross-user backfill case, which uses a one-statement `SET LOCAL ROLE <tier-1-role>` instead.

### Per-environment provisioning

| Environment | Tier 1 source | Tier 2 / Tier 3 provisioning |
|---|---|---|
| **Dev (docker-compose)** | `postgres` superuser comes built-in with the Postgres image | A `bootstrap.sql` mounted into `/docker-entrypoint-initdb.d/` runs once on first volume creation and provisions both `app_migrator` and `app_user`. Volume reset → bootstrap re-runs. |
| **CI (ephemeral DB service)** | The CI workflow's Postgres service (e.g. GitHub Actions `services: postgres`) starts with the default `postgres` superuser | Same `bootstrap.sql` is applied as the first step of the test job, before `make migrate`. CI's job is to *catch* RLS bugs, so connecting the test backend as `app_user` is mandatory. |
| **Prod (managed Postgres)** | Cloud-provided admin role (`cloudsqlsuperuser`, `rds_superuser`, etc.) | Terraform / Pulumi / cloud CLI provisions `app_migrator` and `app_user` before the first deploy, with passwords stored in the cloud secret manager. The deploy pipeline never touches roles. |

### Two connection strings, never one

The backend MUST read `DATABASE_URL` and have no access to `MIGRATION_DATABASE_URL`. Conversely, `make migrate` and the deploy boot script MUST read `MIGRATION_DATABASE_URL` and have no access to `DATABASE_URL`. Two reasons:

1. **Defense in depth**: a bug in handler code that "needs admin privileges" cannot accidentally use `MIGRATION_DATABASE_URL` because the secret isn't injected into the runtime container.
2. **Audit clarity**: when a security audit asks "what role can this process adopt?", the answer is one role, not two.

In Cloud Run / Kubernetes, this is a per-service env var injection. The runtime service's secret-mount only includes `DATABASE_URL`; the migration job (or init container) only includes `MIGRATION_DATABASE_URL`. They are different deployments with different secrets.

---

## Production Safety Guards

The framework has two critical runtime guards that **must exist** in any Kiat-based project.

### Guard 1: `ENABLE_TEST_AUTH` must not leak to production

**Failure mode:** if `ENABLE_TEST_AUTH=true` reaches production, any HTTP request with a crafted `X-Test-User-Id` header bypasses authentication entirely. This is a total auth bypass and must crash the process on startup.

**Implementation (Go example):**

```go
func main() {
    if os.Getenv("ENABLE_TEST_AUTH") == "true" && os.Getenv("ENV") == "production" {
        log.Fatal("ENABLE_TEST_AUTH cannot be true in production — refusing to start")
        os.Exit(1)
    }
    // ... rest of startup
}
```

This guard is **enforced by the `kiat-clerk-auth-review` skill** — any diff that touches auth middleware is checked for the guard's presence. Missing guard → `CLERK_VERDICT: BLOCKED`.

### Guard 2: runtime `DATABASE_URL` must not name a superuser or `BYPASSRLS` role

**Failure mode**: if `DATABASE_URL` resolves to `postgres`, `cloudsqlsuperuser`, `rds_superuser`, or any role with `SUPERUSER` or `BYPASSRLS`, every HTTP request silently bypasses RLS. Cross-tenant data leak, invisible in dev (one user) and unit tests (no cross-user setup), surfaces only when a customer notices their data in another customer's UI. By far the worst-case Postgres failure mode; this guard is non-negotiable.

**Implementation (Go example, runs at startup before serving any traffic):**

```go
func main() {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    if err != nil { log.Fatal(err) }

    // Verify the connection role is NOSUPERUSER NOBYPASSRLS. If it isn't,
    // refuse to start — RLS would be inert and we'd silently leak.
    var rolsuper, rolbypassrls bool
    err = db.QueryRow(`
        SELECT rolsuper, rolbypassrls
        FROM pg_roles
        WHERE rolname = current_user
    `).Scan(&rolsuper, &rolbypassrls)
    if err != nil { log.Fatal("could not verify db role:", err) }

    if rolsuper || rolbypassrls {
        log.Fatalf("DATABASE_URL role %q has rolsuper=%v rolbypassrls=%v — refusing to start (RLS would be silently inert)",
            currentUser, rolsuper, rolbypassrls)
    }
    // ... rest of startup
}
```

This guard is **enforced by the `kiat-review-backend` skill** at review time and by the runtime check above at deploy time. Both must hold; the runtime check is the last line of defense if an env var is misconfigured at deploy.

---

## Docker Image Promotability

For any setup that promotes the same Docker image from staging to production (e.g., Cloud Run), **environment-dependent values must be injected at runtime, not baked at build time**.

### Specific rule: Clerk publishable key

❌ **Wrong:**
```dockerfile
# Dockerfile
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
RUN npm run build
```

This bakes the staging key into the image, making promotion to production impossible (production has a different Clerk instance).

✅ **Right:**
- Dockerfile does NOT bake `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `layout.tsx` and `middleware.ts` read the key at runtime from `process.env.CLERK_PUBLISHABLE_KEY`
- Cloud Run / K8s injects the correct value per environment

**Same principle applies** to any `NEXT_PUBLIC_*` env var whose value differs between environments. If the value is the same everywhere (e.g., a feature flag default), baking it at build time is fine.

---

## Deploy Checklist (before first production deploy)

**Auth & environment**
- [ ] `ENV=production` is set in production runtime
- [ ] `ENABLE_TEST_AUTH` is unset or explicitly `false` in production
- [ ] Production guard 1 (`os.Exit(1)` on test-auth leak) is present and tested
- [ ] `CLERK_SECRET_KEY` is in production secret manager, not in the image
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is injected at runtime, not baked

**Database roles & RLS**
- [ ] Tier-2 role `app_migrator` provisioned via Terraform / cloud CLI: `NOSUPERUSER NOBYPASSRLS CREATEROLE LOGIN` + `GRANT CREATE ON SCHEMA public` + `GRANT app_user TO app_migrator`
- [ ] Tier-3 role `app_user` provisioned via Terraform / cloud CLI: `NOSUPERUSER NOBYPASSRLS LOGIN`
- [ ] `MIGRATION_DATABASE_URL` injected ONLY into the migration job / init container (not into the runtime service)
- [ ] `DATABASE_URL` injected ONLY into the runtime service (not into the migration job)
- [ ] Both URLs in production secret manager, not baked into images
- [ ] Production guard 2 (startup check that `current_user` has `rolsuper=false` AND `rolbypassrls=false`) is present and tested
- [ ] No migration in `backend/migrations/` grants `SUPERUSER` or `BYPASSRLS` to `app_user` or `app_migrator` — `git grep -E "(SUPERUSER|BYPASSRLS)" backend/migrations/` returns only `NOSUPERUSER` / `NOBYPASSRLS` lines and the bootstrap script
- [ ] Every user-scoped table has BOTH `ENABLE ROW LEVEL SECURITY` AND `FORCE ROW LEVEL SECURITY` (verify via `psql` against the prod DB before announcing GA)

**Network & observability**
- [ ] CORS origins are specific (not `*`)
- [ ] Rate limits are configured on high-value endpoints
- [ ] Logging level is `info` or above (no `debug` in production)
- [ ] Trace IDs propagate through all logs (for incident debugging)
