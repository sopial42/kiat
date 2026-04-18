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
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

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

## Production Safety Guards

The framework has one critical runtime guard that **must exist** in any Kiat-based project.

### Guard: `ENABLE_TEST_AUTH` must not leak to production

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

- [ ] `ENV=production` is set in production runtime
- [ ] `ENABLE_TEST_AUTH` is unset or explicitly `false` in production
- [ ] Production guard (`os.Exit(1)` on test-auth leak) is present and tested
- [ ] `CLERK_SECRET_KEY` is in production secret manager, not in the image
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is injected at runtime, not baked
- [ ] `DATABASE_URL` points to production DB with restricted credentials
- [ ] CORS origins are specific (not `*`)
- [ ] Rate limits are configured on high-value endpoints
- [ ] Logging level is `info` or above (no `debug` in production)
- [ ] Trace IDs propagate through all logs (for incident debugging)
