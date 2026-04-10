# Backend-Coder Checklist: "Am I Done?"

Before saying "Backend code ready for review", check ALL:

## Database ✓
- [ ] Migration file exists in `backend/migrations/` (numbered sequentially)
- [ ] Migration is idempotent (safe to re-run)
- [ ] `created_at` and `updated_at` fields added
- [ ] RLS policy included (if user data)
- [ ] RLS policy tested (User B can't see User A's data)

## API Handlers ✓
- [ ] Handler function created
- [ ] HTTP method correct (GET, POST, PATCH, DELETE)
- [ ] Request validation implemented
- [ ] Response schema matches spec
- [ ] Error codes correct (INVALID_INPUT, NOT_FOUND, CONFLICT)
- [ ] Handler wired in `main.go` (route registered)

## Service Logic ✓
- [ ] Service method created (business logic separated)
- [ ] No N+1 queries (batch load data)
- [ ] Error handling uses AppError pattern (no panics)
- [ ] Input sanitization (if user-provided)

## Testing ✓
- [ ] Venom test file exists
- [ ] Happy path test (create → read → verify)
- [ ] Validation test (invalid input → error)
- [ ] Edge case test (optional: concurrent, network fail)
- [ ] RLS test (permission boundary)
- [ ] All tests passing locally (`make test-back`)

## Security ✓
- [ ] No secrets in code (use env vars)
- [ ] No hardcoded API keys or passwords
- [ ] RLS policy enforces access control
- [ ] Input validation prevents injection

## Logging & Debugging ✓
- [ ] Structured logging added (not just println)
- [ ] trace_id included in logs
- [ ] No secrets logged
- [ ] Error context included

## Code Quality ✓
- [ ] No unused imports
- [ ] No commented-out code
- [ ] Clear variable names
- [ ] Functions are small and focused
- [ ] Error messages are helpful

## Final Check ✓
- [ ] Run `make test-back` → all pass
- [ ] Run `git diff` → review changes
- [ ] Create branch with story name
- [ ] Commit message descriptive
- [ ] Ready to hand off to Backend-Reviewer

---

**If any checkbox unchecked**: Fix before submitting.

**If unsure**: Ask in chat before submitting.
