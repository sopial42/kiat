---
name: kiat-review-backend
description: >
  Structured backend code review checklist. Reviews Go + Gin API code against
  spec, architecture patterns (Clean Arch, DI), database migrations, security
  (RLS, secrets, rate limiting), error handling, and Venom tests. Guarantees
  consistent quality gate with deterministic output format.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Backend Code Review (Go + Gin + Clean Architecture)

Structured review process for backend features. **Output format is deterministic.**

---

## Review Process

### Phase 1: Read Spec + Understand Contract
1. **Read spec** (`story-NN.md`) — extract acceptance criteria, API contracts, DB changes
2. **Identify scope** — what endpoints? what migrations? what services?
3. **Understand acceptance** — when is this "done"?

### Phase 2: Code Audit (Checklist Below)
Apply checklist systematically. **Check each item, don't skip.**

### Phase 3: Report (3-way outcome — MANDATORY)
You MUST output **exactly one** of these three verdicts:

- ✅ **APPROVED** — All checklist items pass, code is merge-ready
- 💬 **NEEDS_DISCUSSION** — Code works and tests pass, but there is a judgment call the Team Lead must arbitrate (pattern efficiency concern, spec ambiguity uncovered during review, architectural question, non-blocking performance tradeoff). Coder is NOT asked to fix — a human/BMAD decision is needed.
- ❌ **BLOCKED** — One or more checklist items fail with concrete fix required. Coder must address before merge.

**Never invent a 4th outcome.** If you feel the need to, it means either:
- You're unsure → default to `NEEDS_DISCUSSION` with a specific question
- You found issues → `BLOCKED` with file:line references

---

## Review Checklist

### Database & Migrations ✓

- [ ] **Migration file exists** in `backend/migrations/` with sequential numbering
- [ ] **Idempotent** — uses `IF NOT EXISTS` (safe to re-run)
- [ ] **Timestamps** — `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- [ ] **Updated_at** — `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- [ ] **Updated_at precision** — Go code uses `time.RFC3339Nano` (not `time.RFC3339`)
- [ ] **Foreign keys** — `ON DELETE CASCADE` for owned data, `ON DELETE RESTRICT` for shared
- [ ] **Indexes** — created on frequently queried columns (email, user_id, foreign keys)
- [ ] **RLS policy** — `ALTER TABLE X ENABLE ROW LEVEL SECURITY` (if user data)
- [ ] **RLS correctness** — policy uses `user_id = auth.uid()` correctly
- [ ] **No N+1 queries** — batch loads, proper joins, not in loops

### Clean Architecture (4 Layers) ✓

**Domain Layer** (`internal/domain/`)
- [ ] Entities defined (struct with business logic)
- [ ] Domain errors defined (`ErrDuplicate*`, `ErrInvalid*`)
- [ ] Interfaces defined (not concrete types)
- [ ] No HTTP, no database, no external deps

**Usecase Layer** (`internal/usecase/`)
- [ ] Services with constructor DI
- [ ] Dependencies are interfaces, not concrete
- [ ] `Execute()` or similar method orchestrates flow
- [ ] Errors wrapped with context (`fmt.Errorf("action: %w", err)`)
- [ ] No HTTP, no database direct access

**Interface Layer** (`internal/interface/`)
- [ ] Handlers parse HTTP request → call usecase → convert domain errors to HTTP status
- [ ] Repositories implement domain interfaces
- [ ] Converters between domain and DB types
- [ ] Input validation before calling usecase

**External Layer** (`external/`, `main.go`)
- [ ] Database client, third-party APIs
- [ ] Dependency injection setup (bottom-up: clients → repos → usecases → handlers)
- [ ] Middleware setup
- [ ] Routes properly wired

### API Contracts ✓

- [ ] **HTTP method** matches spec (GET vs POST vs PATCH vs DELETE)
- [ ] **Path** matches spec (`/api/resource` vs `/api/resource/:id`)
- [ ] **Request schema** matches spec (required fields, types, validation)
- [ ] **Response status** correct (201 Created, 200 OK, 204 No Content, 409 Conflict, etc.)
- [ ] **Response schema** matches spec (all required fields present, types correct)
- [ ] **Error codes** match spec (INVALID_INPUT, NOT_FOUND, DUPLICATE_*, RATE_LIMITED, etc.)
- [ ] **Error response** includes Code + Message (no leaking internal errors)
- [ ] **Success response** includes all data (id, created_at, updated_at, etc.)
- [ ] **Pagination** (if list endpoint) — limit, offset, total in response

### Security ✓

- [ ] **No secrets in code** — all env vars (CLERK_KEY, DB_URL, API_KEYS, etc.)
- [ ] **Input validation** — size limits, format checks, type validation
- [ ] **SQL injection** — parameterized queries only (Bun ORM used correctly)
- [ ] **RLS enforced** — User B cannot read User A's data (testable)
- [ ] **Rate limiting** — applied to high-value endpoints (if spec mentions)
- [ ] **CORS headers** — if cross-origin, allows specific origins only (not `*`)
- [ ] **Error handling** — no internal stack traces leaked to client
- [ ] **Logging** — sensitive data NOT logged (passwords, tokens, emails)

### Error Handling ✓

- [ ] **Domain errors defined** — specific, named errors (not generic)
- [ ] **Usecase wraps errors** — adds context (`fmt.Errorf("action: %w", err)`)
- [ ] **Handler converts errors** — domain errors → HTTP status codes
- [ ] **Error messages user-friendly** — generic messages, not internal details
- [ ] **Stack traces logged** — with trace_id for debugging
- [ ] **500 errors** — generic message, actual error logged

**Example mapping:**
- `domain.ErrInvalidEmail` → 400 INVALID_INPUT
- `domain.ErrDuplicateEmail` → 409 DUPLICATE_EMAIL
- `domain.ErrNotFound` → 404 NOT_FOUND
- `auth.ErrUnauthorized` → 401 UNAUTHORIZED
- Database error → 500 INTERNAL_ERROR (logged with trace_id)

### Logging & Observability ✓

- [ ] **Info logs** — successful operations (created, updated, deleted)
- [ ] **Error logs** — with full error, trace_id, context
- [ ] **Structured logging** — using logger with fields (not string concat)
- [ ] **No secrets** — never log passwords, tokens, private keys
- [ ] **No PII** — limit email/phone logging (only if necessary)
- [ ] **Trace ID** — included in all logs for correlation

### Testing (Venom) ✓

- [ ] **Happy path tested** — endpoint works with valid input
- [ ] **Error cases tested** — invalid input, duplicates, permissions, not found
- [ ] **Edge cases tested** — empty strings, max length, boundary values
- [ ] **RLS tested** — User B cannot read User A's data (explicit test)
- [ ] **Auth tested** — missing token → 401, invalid token → 401
- [ ] **Rate limiting tested** — (if applicable) 10 requests pass, 11th blocked
- [ ] **Tests use mocks** — MockUserRepository, MockClerkClient (not real DB)
- [ ] **Table-driven tests** — structured test cases with name, input, expected output
- [ ] **No skip() or skip(t)** — all tests run in CI

### Code Quality ✓

- [ ] **No TODO comments** — all TODOs resolved or turned into issues
- [ ] **No console logs** — use structured logger
- [ ] **No panics** — errors handled gracefully (return error, don't panic)
- [ ] **Naming** — functions `camelCase`, types `PascalCase`, constants `SCREAMING_SNAKE_CASE`
- [ ] **Package names** — lowercase, concise, descriptive
- [ ] **Comments** — only where logic is non-obvious (not "increment i")

---

## Output Format (MACHINE-PARSEABLE — Team Lead parses first line)

**Line 1 MUST be exactly one of:**
- `VERDICT: APPROVED`
- `VERDICT: NEEDS_DISCUSSION`
- `VERDICT: BLOCKED`

---

**If APPROVED:**
```
VERDICT: APPROVED

Database: Migration 004_create_care_plans.sql ✓
Architecture: Clean Arch 4 layers, DI in main.go ✓
API: POST /care-plans, response schema matches ✓
Security: RLS on care_plans, no secrets ✓
Tests: 8 Venom tests (happy path + errors + RLS) ✓
Clerk-auth skill: N/A (no auth-touching code) | PASSED (ran kiat-clerk-auth-review)
```

**If NEEDS_DISCUSSION:**
```
VERDICT: NEEDS_DISCUSSION

Code works, tests pass, checklist clean. But I need Team Lead arbitration on:

1. Pattern concern (file:line)
   - Handler uses direct repository call instead of usecase layer
   - Code is correct and tested, but bypasses Clean Arch for this simple read
   - Question: Is this an intentional exception or should we add a usecase?

2. Spec ambiguity (story-NN.md, line 42)
   - Spec says "rate limit POST /care-plans" but doesn't specify the bucket
   - Coder implemented per-user (5/min), but per-IP is more common
   - Question: Per-user or per-IP? BMAD should clarify.

→ Not blocking merge. Awaiting Team Lead / BMAD decision.
```

**If BLOCKED:**
```
VERDICT: BLOCKED

1. Database (file:line)
   - Migration 004 not idempotent (missing IF NOT EXISTS on index)
     `CREATE INDEX idx_care_plans_user ON care_plans(user_id);` → add IF NOT EXISTS

2. Architecture (file:line)
   - Service depends on concrete PostgresUserRepository, not interface
     `type CreateCarePlanService struct { repo *repository.PostgresUserRepository }`
     → Should be `repo domain.CarePlanRepository`

3. Error Handling (file:line)
   - Handler leaks internal error to client
     `c.JSON(500, err.Error())` → Should return generic message + log with trace_id

4. Testing (file:line)
   - RLS not tested (User B can read User A's care plans)
     → Add test: seedCarePlan(db, userAID), getCarePlans(db, userBID) should be empty
```

---

## Decision Logic (3-way)

| Situation | Verdict |
|---|---|
| All checklist items pass, no concerns | `APPROVED` |
| Checklist passes BUT you have a judgment call that needs a human | `NEEDS_DISCUSSION` |
| Any checklist item fails with a concrete fix required | `BLOCKED` |
| You're unsure whether something is a problem | `NEEDS_DISCUSSION` (never hide doubt as APPROVED) |
| You found 1 blocker + some discussion points | `BLOCKED` (blockers take precedence; mention discussion points in the body) |

---

## Notes

- Don't skip items because "this is a small PR" → security bypasses are small too
- Don't assume git history is accurate → review actual code
- Don't mark "will fix in next PR" → must be done now
- When in doubt, ask coder for clarification (don't assume intent)
