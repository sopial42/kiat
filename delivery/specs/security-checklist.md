# Security Checklist: OWASP & Best Practices

Security requirements every feature must address before merge.

---

## Pre-Review Checklist

### Input Validation (OWASP A03)

- [ ] All user input validated for type, length, format
- [ ] Size limits enforced (forms, file uploads, JSON body)
- [ ] Email validation (format check)
- [ ] No SQL injection (parameterized queries only)
- [ ] No script injection (sanitize user text before rendering)

**Example (Go)**:
```go
// Validate input size
if len(req.Name) > 255 {
    return c.JSON(http.StatusBadRequest, ...)
}

// Use parameterized queries
user := &User{}
db.WithContext(ctx).Where("email = ?", email).Scan(user)  // ✅ Safe
```

**Example (React)**:
```tsx
// Sanitize before rendering
import DOMPurify from 'dompurify';

const CleanHTML = ({ html }) => (
  <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />
);
```

### Secrets Management (OWASP A02)

- [ ] No API keys, passwords, tokens in code
- [ ] All secrets in env vars (or .env.local, .env)
- [ ] Secrets rotated after test (if used for testing)
- [ ] No secrets in git history (use `.gitignore`)
- [ ] No hardcoded connection strings

**Good**:
```go
clerkSecret := os.Getenv("CLERK_SECRET_KEY")  // ✅ From env var
```

**Bad**:
```go
clerkSecret := "sk_test_abc123..."  // ❌ Hardcoded
```

### Authentication & Authorization (OWASP A01, A04)

- [ ] All endpoints require authentication (except public ones)
- [ ] JWT validated on every request
- [ ] User context extracted from JWT
- [ ] RLS enforced at database layer (users can't access other users' data)

**Test case**:
```go
// User B should NOT see User A's data
seedCarePlan(db, userAID, ...)
plans := getCarePlans(db, userBID)  // Query as User B
assert.Equal(t, 0, len(plans))  // ← Should be empty
```

### Row-Level Security (RLS) (OWASP A01)

- [ ] Every table with user data has RLS enabled
- [ ] RLS policy uses `user_id = auth.uid()` or equivalent
- [ ] RLS tested (User B can't read User A's data)
- [ ] CASCADE deletes clean up related data

**Policy structure**:
```sql
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
CREATE POLICY items_isolation ON items
    USING (user_id = auth.uid());
```

### Rate Limiting (OWASP A04)

- [ ] High-value endpoints have rate limiting (per-user quota)
- [ ] Rate limit headers in response
- [ ] 429 status code when exceeded
- [ ] Tested: Verify rate limit is enforced

**Example**:
```go
// Limit to 10 requests per minute per user
if isRateLimited(userID, "create_item") {
    return c.JSON(http.StatusTooManyRequests, ErrorResponse{
        Code: "RATE_LIMITED",
        Message: "too many requests, try again later",
    })
}
```

### Error Handling (OWASP A01)

- [ ] No internal error details leaked to users
- [ ] Error messages user-friendly
- [ ] Stack traces logged (not in HTTP response)
- [ ] Trace ID included in error for debugging

**Bad**:
```go
c.JSON(http.StatusInternalServerError, err)  // ❌ Leaks details
```

**Good**:
```go
log.WithField("trace_id", ctx.Value("trace_id")).WithError(err).Error("failed to create")
c.JSON(http.StatusInternalServerError, ErrorResponse{
    Code: "INTERNAL_ERROR",
    Message: "failed to create resource",
})
```

### CORS (Cross-Origin Resource Sharing) (OWASP A07)

- [ ] CORS headers correct (if API called from browser)
- [ ] Only allow trusted origins
- [ ] Credentials allowed only if necessary

**Setup (Go)**:
```go
r.Use(cors.New(cors.Config{
    AllowOrigins:     []string{"https://example.com"},  // ✅ Specific
    AllowMethods:     []string{"GET", "POST", "PATCH", "DELETE"},
    AllowCredentials: true,
}))
```

**Bad**:
```go
AllowOrigins: []string{"*"}  // ❌ Allows any origin
```

### CSRF Protection (Cross-Site Request Forgery) (OWASP A01)

- [ ] POST/PATCH/DELETE require CSRF token (if using cookies)
- [ ] Token validated on backend

**Note**: If using **JWT tokens in Authorization header**, CSRF is not needed.

### Dependency Vulnerabilities (OWASP A06)

- [ ] No critical security vulnerabilities in dependencies
- [ ] Dependencies kept up-to-date
- [ ] `go mod tidy` run before commit
- [ ] `npm audit` run before commit

**Commands**:
```bash
go mod tidy
go list -json -m all | nancy sleuth  # Check Go vulnerabilities
npm audit                            # Check Node vulnerabilities
```

---

## Database Security

### Timestamps (Optimistic Locking)

- [ ] All records have `created_at`, `updated_at`
- [ ] Updates use optimistic locking (check `updated_at` before update)
- [ ] Concurrent update attempts fail gracefully (return 409 Conflict)

### Foreign Keys

- [ ] All relationships have foreign key constraints
- [ ] Use `ON DELETE CASCADE` for owned data (order → user)
- [ ] Use `ON DELETE RESTRICT` for shared data (must cascade-aware)

### Indexes

- [ ] Indexes on frequently queried columns (email, user_id, foreign keys)
- [ ] Prevents N+1 query attacks

---

## Frontend Security

### XSS Prevention (Cross-Site Scripting) (OWASP A03)

- [ ] No `dangerouslySetInnerHTML` without sanitization
- [ ] React escapes text by default ✅
- [ ] Sanitize user-provided HTML with DOMPurify

**Bad**:
```tsx
<div dangerouslySetInnerHTML={{ __html: userText }} />  // ❌ XSS risk
```

**Good**:
```tsx
<div>{userText}</div>  // ✅ Auto-escaped by React
```

### Sensitive Data in DOM

- [ ] No passwords, tokens, secrets in HTML (even in hidden attributes)
- [ ] Sensitive data only in memory, cleared on logout
- [ ] localStorage/sessionStorage only for non-sensitive data (user preferences)

### File Upload Security

- [ ] File type validated (extension + MIME type)
- [ ] File size limited (prevent DoS)
- [ ] Files scanned for malware (if mission-critical)
- [ ] Files stored in secure location (S3 with ACLs, not public web root)

**Example**:
```go
// Validate file size
const maxSize = 10 * 1024 * 1024  // 10MB
if file.Size > maxSize {
    return c.JSON(http.StatusBadRequest, ...)
}

// Validate MIME type
if !isAllowedMimeType(file.Header.Get("Content-Type")) {
    return c.JSON(http.StatusBadRequest, ...)
}
```

---

## Logging & Monitoring (OWASP A09)

- [ ] Security-relevant events logged (login, auth failure, permission denied)
- [ ] Logs include trace ID (for correlation)
- [ ] Logs NOT stored in version control
- [ ] Logs rotated (prevent disk fill)
- [ ] Logs reviewed for suspicious patterns (if possible)

**What to log**:
- ✅ User login/logout
- ✅ Auth failures (invalid token, expired)
- ✅ Permission denied (RLS violation attempt)
- ✅ High-value actions (create, delete, export)
- ❌ Passwords, tokens, secrets
- ❌ PII (emails, phone numbers, unless necessary)

---

## Testing Security

### Unit Tests

- [ ] RLS policy tested (User B can't read User A's data)
- [ ] Input validation tested (invalid input → error)
- [ ] Authentication tested (no token → 401)
- [ ] Authorization tested (insufficient permissions → 403)

### E2E Tests

- [ ] User A can access their data
- [ ] User A can't access User B's data
- [ ] Rate limiting works (10 requests → blocked on 11th)
- [ ] File upload size limit enforced

---

## Security Review Workflow

1. **Before submission**: Developer checks own code against this list
2. **During review**: Reviewer verifies compliance
3. **Before merge**: CI must pass security checks (if applicable)

---

## Common Vulnerabilities to Avoid

| Vulnerability | Prevention |
|---|---|
| SQL Injection | Parameterized queries, Bun ORM |
| XSS | React auto-escapes, DOMPurify for HTML |
| CSRF | JWT tokens in headers (not cookies) |
| Auth bypass | Validate JWT, check RLS |
| RLS bypass | Every query includes user filter |
| Secret leaks | Env vars only, .gitignore |
| Weak password | Delegate to Clerk (uses standards) |
| Rate limit bypass | Per-user limits, timestamp-based |

---

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Bun ORM Security](https://bun.uptrace.dev/)
- [React Security](https://react.dev/learn/security)
- [Go Security Checklist](https://golang.org/security)

---

See also:
- [backend-conventions.md](backend-conventions.md) — Error handling, logging
- [database-conventions.md](database-conventions.md) — RLS, migrations
- [clerk-patterns.md](clerk-patterns.md) — Auth security
