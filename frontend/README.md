# Frontend — Next.js App Router + React + Shadcn/UI + Tailwind

> **Status**: Skeleton placeholder. The working code will land in EPIC 00 (see [`delivery/epics/epic-00/`](../delivery/epics/epic-00/)).

## Planned structure

```
frontend/
├── src/
│   ├── app/                            # Next.js App Router (RSC + Client components)
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # landing / marketing
│   │   ├── sign-in/[[...rest]]/page.tsx
│   │   ├── sign-up/[[...rest]]/page.tsx
│   │   └── (app)/                      # authenticated app routes
│   │       └── items/
│   │           └── page.tsx            # canonical example resource
│   ├── middleware.ts                   # MUST live under src/ (PP13) — Clerk auth
│   ├── components/
│   │   ├── ui/                         # Shadcn/UI primitives (generated)
│   │   └── features/
│   │       └── items/
│   │           ├── ItemList.tsx
│   │           └── ItemForm.tsx
│   ├── hooks/
│   │   ├── use-auth.ts                 # Clerk wrapper with test-auth branch (PC07, PP13)
│   │   └── use-auto-save.ts            # stable enabled condition (UA02)
│   └── lib/
│       └── api.ts                      # fetch wrapper attaching Authorization header
├── e2e/                                # Playwright specs — see testing-playwright.md
│   ├── global.setup.ts                 # Clerk signin + JWT swap to playwright-ci template
│   ├── fixtures/
│   │   ├── auth.ts                     # signInAsUserB, restoreUserA, SQL helpers
│   │   ├── mock-responses.ts           # centralised route.fulfill bodies (with ACEH)
│   │   └── smocker/                    # YAML scenarios for external APIs
│   ├── smoke.spec.ts                   # mocked flows (baseline E2E)
│   └── real-backend/                   # real-backend specs (PP15 compliance)
│       └── smoke-real.spec.ts
├── playwright.config.ts
├── package.json
├── next.config.ts
└── tailwind.config.ts
```

## Auth branches (see [`clerk-patterns.md`](../delivery/specs/clerk-patterns.md))

Two modes, selected at build time by `NEXT_PUBLIC_ENABLE_TEST_AUTH`:

| Mode | `NEXT_PUBLIC_ENABLE_TEST_AUTH` | Provider | Transport | When used |
|---|---|---|---|---|
| Real Clerk | `false` | `<ClerkProvider>` | `Authorization: Bearer <JWT>` | `make dev`, production, CI Playwright |
| Test-auth | `true` | `<TestAuthProvider>` | `X-Test-User-Id: <uuid>` | `make dev-offline` (local iteration only) |

**Hook selection is done at module level**, not in render — avoids conditional hook calls (see [`testing-pitfalls-frontend.md:UA02`](../delivery/specs/testing-pitfalls-frontend.md) and the pattern in `use-auth.ts`):

```typescript
const useTokenGetter = IS_TEST_AUTH ? useTokenGetterTestAuth : useTokenGetterClerk;
export function useAuthenticatedFetch() {
  const getToken = useTokenGetter();  // safe — no conditional hook call
  // ...
}
```

## Hard rules (see [`frontend-architecture.md`](../delivery/specs/frontend-architecture.md))

1. **Middleware at `src/middleware.ts`**, never at project root (PP13)
2. **No JWT serialisation to client-component props** — resolve tokens at call time via hook (PC06)
3. **Every client `fetch('/api/...')` attaches the auth header via the wrapper hook** — bare `fetch()` is a reviewer BLOCKER
4. **Custom response headers readable by JS require** `Access-Control-Expose-Headers` — both on the real backend and in every Playwright mock (PP14)
5. **`getByText('short')` + `getByRole('button', { name })`** take `{ exact: true }` when labels may collide

## Testing

See [`testing-playwright.md`](../delivery/specs/testing-playwright.md) for canonical patterns — the single source of truth for how to write Playwright correctly in this stack.

Quick reminders:
- `make test-e2e-mocked` — mocked E2E, fast iteration
- `make test-e2e` — full stack with docker-compose (pg + minio + smocker) + real backend
- No `waitForTimeout` ever; use `waitForResponse` + `expect.poll` (PP01)
- Any `/api/*` surface needs at least one real-backend spec (PP15)

## Where this code comes from

EPIC 00 (bootstrap) materializes this skeleton. Subsequent epics build business features on top.
