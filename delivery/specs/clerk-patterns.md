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
    // ClerkProvider auto-detects NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY from env;
    // set the env var, don't repeat it as a prop.
    <ClerkProvider>
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

## Middleware (App Router)

This section is the project-canonical pattern for `middleware.ts` (or `proxy.ts` on Next.js ≥15). It **overrides** the upstream Clerk skill's [`clerk-nextjs-patterns/references/middleware-strategies.md`](../../.claude/skills/clerk-nextjs-patterns/references/middleware-strategies.md) on one specific point: Kiat-default App Router projects use **explicit `NextResponse.redirect()`**, not `auth.protect()`, for unauthenticated requests. The upstream skill's "Public-First" and "Protected-First" samples (which use `auth.protect()`) remain valid context for non-App-Router projects and for projects that have explicitly configured `signInUrl` in `clerkMiddleware` and don't need post-sign-in resume URLs — but they are NOT the Kiat default.

### Why explicit redirect over `auth.protect()`

Calling `auth.protect()` from App Router middleware **rewrites** the request to a generic 404 (with the header `x-clerk-auth-reason: protect-rewrite`) when `signInUrl` isn't explicitly configured in `clerkMiddleware`. Even when `signInUrl` IS configured, the resulting redirect strips the originating URL — the user signs in and lands on `/`, not the page they tried to reach. ACs of the form *"unauthenticated user is redirected to /sign-in"* or *"after sign-in, the user lands on the page they originally requested"* silently fail.

The explicit redirect is more verbose but **predictable**: always 307, always carries the resume URL, doesn't depend on `clerkMiddleware` config or SDK version, doesn't depend on Clerk's implicit "is this a page or an API route?" heuristic. For a framework whose stories routinely include both ACs above, explicit is the only correct default.

### Canonical pattern

```typescript
// frontend/src/middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

// Public routes — auth NOT required to reach these.
// Anything not matched here REQUIRES authentication.
//
// SECURITY: this list is the project's authentication boundary. Every PR that
// adds an entry must justify it: either (a) the route is genuinely public by
// design (e.g. /sign-in, /api/health), or (b) the route has its own auth
// mechanism in the handler (e.g. webhook signature validation). Adding a
// route to publicRoutes "to get around auth" is a vulnerability — the
// reviewer flags it as BLOCKED.
const isPublicRoute = createRouteMatcher([
  '/',                       // landing page
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/health',             // probe endpoint, no auth
  '/api/webhooks/(.*)',      // authenticated by signature in the handler, NOT by session
]);

export default clerkMiddleware(async (auth, req) => {
  // Early-return for public routes BEFORE calling auth() — auth() inspects
  // the session cookie / Authorization header on every invocation, and
  // running it for static assets or genuinely public routes is wasted cost.
  if (isPublicRoute(req)) {
    return NextResponse.next();
  }

  const { userId } = await auth();
  if (!userId) {
    // Explicit 307 redirect to sign-in, preserving the URL the user wanted
    // so they resume there after sign-in.
    //
    // SECURITY: redirect_url is set from req.nextUrl.pathname + search —
    // an INTERNAL path, never req.url or any user-controlled origin. If
    // downstream code reads ?redirect_url= and uses it to navigate, that
    // code MUST validate the value starts with '/' and contains no
    // protocol scheme (http, //, data:, javascript:). An attacker who
    // can craft ?redirect_url=https://evil.com and trick a user into
    // clicking owns the post-sign-in landing page.
    const signInUrl = new URL('/sign-in', req.url);
    signInUrl.searchParams.set(
      'redirect_url',
      req.nextUrl.pathname + req.nextUrl.search,
    );
    return NextResponse.redirect(signInUrl, 307);
  }

  return NextResponse.next();
});

// Matcher: which paths the middleware RUNS on (orthogonal to publicRoutes
// above, which controls which paths inside that set are EXEMPT from auth).
//
// Including /(api|trpc)(.*) in the matcher even though /api/(.*) appears in
// publicRoutes is intentional and correct — it future-proofs for when you
// add a non-public API route under /api/private/. See "Matcher vs
// publicRoutes orthogonality" below.
export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};
```

### Security-critical points

These are non-negotiable. Each one is enforced by the `kiat-clerk-auth-review` skill (see [`../../.claude/skills/kiat-clerk-auth-review/references/checks.md`](../../.claude/skills/kiat-clerk-auth-review/references/checks.md) §"Middleware (App Router)").

1. **Open-redirect prevention** — `redirect_url` is set from `req.nextUrl.pathname + req.nextUrl.search` (an internal path), NEVER from `req.url` or any user-controlled origin. Downstream code that reads `?redirect_url=` and uses it to navigate MUST validate the value: starts with `/`, contains no protocol scheme (`http:`, `https:`, `//`, `data:`, `javascript:`, `vbscript:`). One unguarded `<a href={redirectAfterSignIn}>` is one phishing campaign.

2. **Use `307`, not `302`** — `307 Temporary Redirect` preserves the HTTP method (POST stays POST after redirect), which matters for unauthenticated form submissions. `302 Found` is browser-implementation-defined for non-GET methods and historically unreliable. Always 307.

3. **Matcher vs publicRoutes orthogonality** — `config.matcher` controls which paths the middleware RUNS on; `isPublicRoute` controls which paths inside that set are EXEMPT from auth. They are **independent axes**. Common mistake: shrinking the matcher to "exclude sign-in" instead of adding sign-in to publicRoutes — the former skips middleware entirely, which means future cross-cutting logic (audit logs, locale detection, A/B test cohort assignment) won't run on sign-in either. **Rule**: edit `publicRoutes` for auth changes; edit `matcher` only when middleware genuinely should not run (static assets, favicons, build-output paths).

4. **Defense in depth — middleware is FIRST line, not the only one** — server components, route handlers (`app/api/**/route.ts`), and Server Actions for protected resources MUST also call `await auth()` and reject `userId === null` (or use `useAppAuth()` on the client side via the project wrapper). Never rely on middleware alone — a misconfigured matcher or one wrong `publicRoutes` entry is one diff away. Treat middleware as a UX layer ("send unauthenticated users to sign-in") and treat the page/handler/action auth checks as the security layer ("don't return user data to a missing/invalid session").

5. **Test-auth interaction** — when `NEXT_PUBLIC_ENABLE_TEST_AUTH=true`, `<ClerkProvider>` is conditionally skipped (per §"Test Auth Flow" above), but middleware still runs because `clerkMiddleware` doesn't read `NEXT_PUBLIC_*` env vars at the edge. The middleware MUST either short-circuit on the test-auth flag (skip the Clerk session check entirely) OR detect the `X-Test-User-Id` header and treat it as proof of identity — match whichever pattern the backend test-auth middleware uses for symmetry. **Whichever you choose, the production guard MUST exist** (see §"Production Safety" → Guard 1 above and [`deployment.md`](deployment.md) §"Production Safety Guards" → Guard 1).

6. **`auth()` is cheap-but-not-free** — it inspects the session cookie / Authorization header on every invocation. Always early-return for public routes BEFORE calling `auth()`. Running `auth()` on every CSS/font/image request that the matcher accidentally caught is a measurable latency hit at scale and a free DoS vector against the Clerk session store.

7. **Webhooks in `publicRoutes` is NOT "no auth"** — it's "different auth mechanism". Webhook routes (`/api/webhooks/(.*)`) appear in `publicRoutes` because they authenticate via HMAC signature validation in the handler, NOT via Clerk session. The reviewer must verify: every route in `publicRoutes` is either genuinely unauthenticated by design (`/api/health`) OR has its own signature/token validation in the handler. NEVER add a route to `publicRoutes` "because the auth check is annoying" — that's a vulnerability dressed as a refactor.

8. **`auth.protect()` is allowed only with explicit justification** — if a story specifically uses Pages Router, OR has explicitly configured `signInUrl` in `clerkMiddleware` AND the AC accepts the rewrite-to-404 behavior AND the story doesn't need a resume URL, `auth.protect()` is acceptable. The reviewer flags `auth.protect()` in `middleware.ts` as `NEEDS_DISCUSSION` by default; the story's coder is expected to defend the choice. The default Kiat answer is the explicit-redirect pattern above.

### Counter-example to recognize but NOT use

The upstream Clerk skill's [`clerk-nextjs-patterns/references/middleware-strategies.md`](../../.claude/skills/clerk-nextjs-patterns/references/middleware-strategies.md) shows two patterns:

```typescript
// Public-First
export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) await auth.protect();   // ← rewrites to 404 in App Router
});

// Protected-First
export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) await auth.protect();     // ← same problem
});
```

Both rely on `auth.protect()` and inherit its rewrite-to-404 behavior on App Router. Reviewers will recognize these as patterns from the upstream skill and ask: "why didn't you use the project's explicit-redirect pattern?" The answer must be one of the explicit justifications in security point #8 above; "the upstream skill showed this" is not sufficient.

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
