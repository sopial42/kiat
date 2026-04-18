# Clerk Auth Patterns: Real Auth & Test Mode

Authentication flows, token handling, and testing strategies.

---

## Development Modes

### Mode 1: Real Clerk Auth (`make dev`)

- Backend: `ENABLE_TEST_AUTH=false`
- Frontend: `NEXT_PUBLIC_ENABLE_TEST_AUTH=false`
- Requires: Internet, Clerk API keys
- Use for: E2E testing, production-like testing, manual QA

**Setup**:
```bash
# backend/.env
ENABLE_TEST_AUTH=false
CLERK_SECRET_KEY=sk_test_...

# frontend/.env.local
NEXT_PUBLIC_ENABLE_TEST_AUTH=false
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Mode 2: Test Auth Bypass (`make dev-offline`)

- Backend: `ENABLE_TEST_AUTH=true` + `X-Test-User-Id` header
- Frontend: `NEXT_PUBLIC_ENABLE_TEST_AUTH=true`
- No internet needed, fast for local development
- Use for: Rapid local iteration, Venom unit tests

**Setup**:
```bash
# backend/.env
ENABLE_TEST_AUTH=true

# frontend/.env.local
NEXT_PUBLIC_ENABLE_TEST_AUTH=true
```

---

## Real Auth Flow (E2E)

### 1. Frontend: Sign In with Clerk

```tsx
import { useSignIn } from '@clerk/nextjs';

export function SignInPage() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async () => {
    if (!isLoaded) return;
    
    try {
      const result = await signIn.create({
        identifier: email,
        password: password,
      });
      
      if (result.status === 'complete') {
        setActive({ session: result.createdSessionId });
        // ✅ User is now signed in
      }
    } catch (err) {
      console.error('Sign in failed:', err);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
      <button type="submit">Sign In</button>
    </form>
  );
}
```

### 2. Frontend: Get JWT Token

```tsx
import { useAuth } from '@clerk/nextjs';

export function ApiCall() {
  const { getToken } = useAuth();

  const handleClick = async () => {
    const token = await getToken();  // ← JWT from Clerk
    const response = await fetch('/api/users', {
      headers: { Authorization: `Bearer ${token}` },
    });
    // ...
  };

  return <button onClick={handleClick}>Fetch Users</button>;
}
```

### 3. Backend: Verify JWT

```go
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.JSON(http.StatusUnauthorized, ...)
            c.Abort()
            return
        }

        // Verify with Clerk
        claims, err := verifyClerkToken(token)
        if err != nil {
            c.JSON(http.StatusUnauthorized, ...)
            c.Abort()
            return
        }

        c.Set("user_id", claims.Sub)  // ← User ID from JWT
        c.Next()
    }
}
```

### 4. Frontend: Sign Out

```tsx
import { useClerk } from '@clerk/nextjs';

export function SignOutButton() {
  const { signOut } = useClerk();

  const handleSignOut = async () => {
    await signOut();
    window.location.href = '/sign-in';  // ← Redirect after sign out
  };

  return <button onClick={handleSignOut}>Sign Out</button>;
}
```

---

## Test Auth Flow

### Backend (No JWT Verification)

```go
// In main.go
if os.Getenv("ENABLE_TEST_AUTH") == "true" {
    // Skip JWT verification, use X-Test-User-Id header
    r.Use(testAuthMiddleware())
} else {
    r.Use(clerkAuthMiddleware())
}

func testAuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        userID := c.GetHeader("X-Test-User-Id")
        if userID == "" {
            c.JSON(http.StatusUnauthorized, ...)
            c.Abort()
            return
        }
        c.Set("user_id", userID)
        c.Next()
    }
}
```

### Frontend (No ClerkProvider)

```tsx
// In layout.tsx (when NEXT_PUBLIC_ENABLE_TEST_AUTH=true)
import { TestAuthProvider } from '@/shared/providers/test-auth';

export default function RootLayout({ children }) {
  if (process.env.NEXT_PUBLIC_ENABLE_TEST_AUTH === 'true') {
    return <TestAuthProvider>{children}</TestAuthProvider>;
  }
  
  return (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  );
}
```

---

## Production Safety

### Guard: Test Auth + Production Env

```go
func init() {
    if os.Getenv("ENABLE_TEST_AUTH") == "true" && os.Getenv("ENV") == "production" {
        log.Fatal("ENABLE_TEST_AUTH must be false in production")
    }
}
```

**Why?** Prevents accidental deployment of test mode to production, which would bypass authentication entirely.

---

## Playwright E2E Testing with Real Clerk

### 1. Setup Test User (Before Tests)

```tsx
// frontend/e2e/helpers/auth.ts

export async function clerkSetup() {
  const apiClient = new clerkClient.ClerkClient({
    secretKey: process.env.CLERK_SECRET_KEY,
  });

  // Create test user (or reuse existing)
  const user = await apiClient.users.createUser({
    emailAddress: [process.env.E2E_CLERK_USER_A_EMAIL],
    password: process.env.E2E_CLERK_USER_A_PASSWORD,
  });

  return user.id;
}
```

### 2. Sign In During Test

```tsx
// frontend/e2e/auth.spec.ts

import { test, expect } from '@playwright/test';
import { clerkSetup } from './helpers/auth';

test.beforeAll(async () => {
  await clerkSetup();
});

test('user can sign in', async ({ page }) => {
  await page.goto('/sign-in');
  
  // Sign in
  await page.fill('input[name="email"]', process.env.E2E_CLERK_USER_A_EMAIL);
  await page.fill('input[name="password"]', process.env.E2E_CLERK_USER_A_PASSWORD);
  await page.click('button[type="submit"]');
  
  // Wait for redirect to dashboard
  await page.waitForURL('/dashboard');
  expect(page.url()).toContain('/dashboard');
});
```

### 3. Save Session for Reuse

```tsx
test.beforeEach(async ({ page }) => {
  // Load pre-authenticated session
  await page.context().addCookies([
    {
      name: '__session',
      value: process.env.CLERK_SESSION_COOKIE,
      domain: 'localhost',
      path: '/',
    },
  ]);
});
```

---

## Clerk Review Rules (authoritative source)

**The authoritative list of Clerk gotchas and review rules lives in the framework skill, not here.**

See [`.claude/skills/kiat-clerk-auth-review/SKILL.md`](../../.claude/skills/kiat-clerk-auth-review/SKILL.md) for:
- Hard trigger rules (when the skill MUST run on a diff)
- 7-category review checklist (provider/hooks, test-auth safety, JWT handling, signOut destruction, RLS isolation, rate limits, secrets)
- Machine-parseable output format consumed by reviewers
- Verdict merging rules with parent review

**Why this separation?** The framework skill is the **enforcement contract** — reviewers invoke it mechanically on every auth-touching diff, and it outputs a structured verdict. This file (`clerk-patterns.md`) is the **how-to guide** — it shows authentication flows, code examples, test setup, and webhook handling for humans and agents learning the project's Clerk setup.

If a rule is in the skill, do not restate it here. If a code example or tutorial is here, do not restate the formal rule in the skill. **One source of truth per artifact.**

---

## Webhooks (Optional)

If using Clerk webhooks to sync data:

```go
// backend/external/clerk/webhook.go

func HandleClerkWebhook(c *gin.Context) {
    // Verify webhook signature
    signature := c.GetHeader("svix-signature")
    body, _ := io.ReadAll(c.Request.Body)
    
    if !verifyWebhookSignature(signature, body) {
        c.JSON(http.StatusUnauthorized, ...)
        return
    }

    var event ClerkEvent
    json.Unmarshal(body, &event)

    switch event.Type {
    case "user.created":
        // Sync user to database
        createUser(event.Data.User)
    case "user.deleted":
        // Delete user
        deleteUser(event.Data.User.ID)
    }

    c.JSON(http.StatusOK, map[string]string{"success": "true"})
}
```

---

## Best Practices (project-specific usage)

For general Clerk security rules (JWT storage, validation, signOut, rate limits, production guards), see the authoritative source:
[`.claude/skills/kiat-clerk-auth-review/SKILL.md`](../../.claude/skills/kiat-clerk-auth-review/SKILL.md).

This section only covers **project-specific** Clerk usage habits that don't belong in the framework skill:

- **Two dev modes** (`make dev` real auth, `make dev-offline` bypass) — pick the right one for your task. Venom tests run against `make dev-offline`; Playwright E2E needs `make dev`.
- **Test user seed IDs** come from `E2E_CLERK_USER_A_ID` / `E2E_CLERK_USER_B_ID` env vars — never hardcode them in test files.
- **Webhook handler location** (if used): `backend/external/clerk/webhook.go` — see the Webhooks section above.
- **Session state in Playwright** lives in `storageState` files generated by `clerkSetup()`. Refresh them if they expire (3600s JWT lifetime).

---

See also:
- [`.claude/skills/kiat-clerk-auth-review/SKILL.md`](../../.claude/skills/kiat-clerk-auth-review/SKILL.md) — Framework review checklist (authoritative rules)
- [security-checklist.md](security-checklist.md) — General auth security
- [testing.md](testing.md) — E2E testing with Clerk
- [deployment.md](deployment.md) — Env vars and production guards
