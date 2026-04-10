---
name: kiat-review-frontend
description: >
  Structured frontend code review checklist. Reviews React + TypeScript + Shadcn
  code against spec, design system (colors, spacing, typography), accessibility
  (WCAG), responsive design, hooks patterns, and Playwright E2E tests. Guarantees
  consistent quality gate with deterministic output format. Also validates against
  react-best-practices and composition-patterns skills.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Frontend Code Review (Next.js + React + Shadcn/UI)

Structured review process for frontend features. **Output format is deterministic.**

---

## Review Process

### Phase 1: Read Spec + Design System
1. **Read spec** (`story-NN.md`) — extract acceptance criteria, UI mockups, user flows
2. **Read design system** (`design-system.md`) — colors, spacing, typography, component library
3. **Understand visual requirements** — when does UI match Figma?

### Phase 2: Code Audit (Checklist Below)
Apply checklist systematically. **Check each item, don't skip.**

### Phase 3: Report (3-way outcome — MANDATORY)
You MUST output **exactly one** of these three verdicts:

- ✅ **APPROVED** — All checklist items pass, code is merge-ready
- 💬 **NEEDS_DISCUSSION** — Code works and tests pass, but there is a judgment call the Team Lead must arbitrate (Figma vs design-system ambiguity, UX tradeoff, accessibility edge case, performance concern). Coder is NOT asked to fix — a human/BMAD/designer decision is needed.
- ❌ **BLOCKED** — One or more checklist items fail with concrete fix required. Coder must address before merge.

**Never invent a 4th outcome.** If you feel the need to, it means either:
- You're unsure → default to `NEEDS_DISCUSSION` with a specific question
- You found issues → `BLOCKED` with file:line references

---

## Review Checklist

### Spec Compliance ✓

- [ ] **Acceptance criteria met** — all requirements from spec implemented
- [ ] **UI matches Figma** — layout, spacing, colors, typography as designed
- [ ] **API contracts** — component calls correct backend endpoints with correct payload
- [ ] **User flows** — happy path and error flows match spec
- [ ] **Edge cases** — empty states, loading states, error states all handled

### Components & Structure ✓

- [ ] **Uses Shadcn/UI** — Button, Input, Form, Card, Dialog, Select, Checkbox, Radio, etc.
- [ ] **Custom components only when needed** — Shadcn doesn't cover use case
- [ ] **Props typed** — TypeScript `interface ComponentProps { ... }`, no `any`
- [ ] **Client/Server boundary** — `'use client'` where hooks/state used (useState, useQuery, etc.)
- [ ] **No prop drilling** — if 3+ levels deep, use Context or extract hook
- [ ] **Composition clean** — not monolithic components
- [ ] **Error boundaries** — try/catch around useQuery/useMutation errors
- [ ] **Ref cleanup** — useEffect dependencies correct, no memory leaks

### Styling & Design System ✓

- [ ] **Tailwind classes only** — no inline styles, no CSS modules
- [ ] **Colors from design system** — Kotai Blue #273D54, Sky Blue #52ACD9, etc.
- [ ] **No hardcoded hex values** — all from `globals.css` `@theme` variables
- [ ] **Border radius correct** — `rounded-[16px]` for buttons/cards/inputs, `rounded-full` only for circles
- [ ] **Spacing consistent** — `p-4 sm:p-6 lg:p-8` (progressive), `gap-4` patterns
- [ ] **Typography correct** — Nunito for headings (font-bold), Inter for body
- [ ] **Dark mode** — if applicable, follows `@media (prefers-color-scheme: dark)`
- [ ] **Reduced motion** — animations respect `motion-safe` and `motion-reduce`

### Responsive Design ✓

- [ ] **Mobile-first** — base styles for mobile, then `sm:`, `md:`, `lg:` breakpoints
- [ ] **Grid responsive** — `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` pattern
- [ ] **Flex responsive** — 3+ items stack on mobile, row on larger screens
- [ ] **Padding responsive** — `p-4 sm:p-6 lg:p-8` (not fixed padding)
- [ ] **Tested at breakpoints** — 320px (mobile), 640px (tablet), 1024px (desktop)
- [ ] **No horizontal scroll** — all content fits viewport

### Accessibility (WCAG AA) ✓

- [ ] **Labels on inputs** — every input has `<label htmlFor="id">` or `aria-label`
- [ ] **Buttons accessible** — text content (not just icons), or `aria-label`
- [ ] **Form labels linked** — `<input id="email">` + `<label htmlFor="email">`
- [ ] **ARIA roles** — dialog, button, button role on divs if needed, menu roles
- [ ] **ARIA attributes** — `aria-expanded`, `aria-label`, `aria-labelledby` where needed
- [ ] **Keyboard nav** — Tab order logical, Enter submits, Escape closes modals
- [ ] **Focus visible** — focus indicators not removed, contrast visible
- [ ] **Color not only indicator** — success = green + checkmark (not just green)
- [ ] **Alt text on images** — or `aria-hidden="true"` if decorative
- [ ] **Contrast ratio** — WCAG AA minimum (4.5:1 body, 3:1 large text)
- [ ] **Axe-core scan passes** — no violations (warnings OK)

### Hooks & State ✓

- [ ] **useQuery pattern** — cache key matches data, not firing in loops
- [ ] **useMutation pattern** — invalidateQueries after success, onError handling
- [ ] **useAutoSave enabled contract** — `enabled` condition is stable (not `!isLoading`)
- [ ] **useEffect dependencies** — correct dependencies list, no missing deps
- [ ] **useState vs useRef** — transient values use refs (not state)
- [ ] **No stale closures** — callbacks in useEffect have correct dependencies
- [ ] **Custom hooks** — extracted logic, named `use*`, reusable

### Error Handling & Edge Cases ✓

- [ ] **Error boundary** — useQuery/useMutation errors caught and displayed
- [ ] **Error toast** — shows user-friendly message (not internal error)
- [ ] **Retry mechanism** — error screen offers "Retry" button
- [ ] **Empty states** — list empty, search no results, etc. all handled
- [ ] **Loading states** — spinners, skeletons, disabled buttons during fetch
- [ ] **Offline handling** — detects `navigator.onLine`, shows banner, queues mutations
- [ ] **No console errors** — zero errors in DevTools (warnings OK)
- [ ] **No unhandled promise rejections** — async functions have .catch() or try/catch

### Forms & Validation ✓

- [ ] **Validation errors shown** — field-level error messages (not just red border)
- [ ] **Disabled submit while invalid** — form can't be submitted with errors
- [ ] **Disabled submit while pending** — prevent double-submit during mutation
- [ ] **Focus on error** — first invalid field focused (or error announced)
- [ ] **Success feedback** — "Saved ✓" message or redirect after success
- [ ] **Auto-save if applicable** — form saves as user types (500ms debounce)
- [ ] **Dirty flag** — shows unsaved changes warning if leaving page

### Playwright E2E Tests ✓

- [ ] **Happy path tested** — user can complete the feature end-to-end
- [ ] **Error cases tested** — validation errors, network errors, empty states
- [ ] **Edge cases tested** — max length input, special characters, boundary values
- [ ] **Accessibility tested** — using `getByRole()` (not `getByText()`)
- [ ] **No flakiness** — no `waitForTimeout()`, `serial` mode, or transient UI assertions
- [ ] **Data seeded correctly** — uses SQL helpers (seedPatient, seedZone, etc.)
- [ ] **Data cleaned up** — cleanup after each test (`cleanupTestData()`)
- [ ] **Offline tested** — if offline feature, test it fails gracefully
- [ ] **Mobile viewport** — if responsive, test at 320px and 640px
- [ ] **No skipped tests** — all tests run (no `.only`, no `.skip`)

### Performance ✓

- [ ] **No N+1 queries** — batch load, not per-item queries
- [ ] **No unnecessary re-renders** — use `useMemo`, `useCallback` for deps
- [ ] **No memory leaks** — useEffect cleanup functions close connections/timers
- [ ] **No bundle bloat** — no huge libraries added for one feature
- [ ] **Images optimized** — using `<Image>` component, lazy loaded
- [ ] **Suspense boundaries** — nested for better UX (if applicable)

### Code Quality ✓

- [ ] **No TODO comments** — all TODOs resolved or turned into issues
- [ ] **No console.log** — use logger if needed, remove debug logs
- [ ] **Naming clear** — variables/functions descriptive, not `temp`, `data`, `x`
- [ ] **No hardcoded strings** — magic numbers in constants file, i18n for user text
- [ ] **Imports organized** — no circular deps, clean import order
- [ ] **No `any` types** — proper TypeScript typing throughout
- [ ] **Comments minimal** — code is self-documenting, comments only for "why" not "what"

### Security ✓

- [ ] **No secrets in code** — API keys, URLs in env vars only
- [ ] **No dangerouslySetInnerHTML** — or sanitized with DOMPurify
- [ ] **XSS safe** — React auto-escapes, user input never directly rendered
- [ ] **No localStorage for secrets** — sessions/tokens in secure HttpOnly cookies
- [ ] **CSRF safe** — using JWT in Authorization header (not cookies)
- [ ] **Rate limiting aware** — (if applicable) aware of rate limits, shows message

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

Spec: All acceptance criteria met, UI matches Figma ✓
Components: Shadcn used, TypeScript typed, no prop drilling ✓
Styling: Tailwind + design tokens, responsive (320/640/1024px tested) ✓
Accessibility: Labels, ARIA, keyboard nav, axe-core ✓ (WCAG AA)
Hooks: useQuery cache key correct, useMutation invalidates, useAutoSave enabled stable ✓
E2E: 12 Playwright tests (happy path + errors + offline) ✓
Performance: No N+1, no memory leaks, images optimized ✓
Clerk-auth skill: N/A (no auth-touching code) | PASSED (ran kiat-clerk-auth-review)
```

**If NEEDS_DISCUSSION:**
```
VERDICT: NEEDS_DISCUSSION

Code works, tests pass, checklist clean. But I need Team Lead arbitration on:

1. Design ambiguity (file:line)
   - Figma shows border-radius 8px on the new dialog
   - design-system.md specifies 16px as the global default
   - Question: Is this dialog an intentional exception (update design-system.md) or a Figma mistake?

2. UX tradeoff (file:line)
   - Auto-save debounce is 500ms — feels snappy but causes 2x network calls per second on slow networks
   - Question: Raise to 1000ms? Needs BMAD/UX call.

→ Not blocking merge. Awaiting Team Lead / BMAD / Designer decision.
```

**If BLOCKED:**
```
VERDICT: BLOCKED

1. Styling (file:line)
   - Hardcoded hex value instead of design token
     `className="bg-[#52acd9]"` → Should be `className="bg-[var(--color-primary-light)]"`

2. Accessibility (file:line)
   - Input missing label
     `<input type="email" placeholder="Email">` → Add `<label htmlFor="email">Email:</label>`

3. Hooks (file:line)
   - useAutoSave enabled contract broken
     `enabled: !isLoading` → Transitions false→true with data → Use stable condition: `const shouldSave = !isLoading && isReady`

4. E2E Tests (file:line)
   - Test uses getByText instead of getByRole
     `page.locator('button:has-text("Save")')` → Use `page.getByRole('button', { name: 'Save' })`
   - Test has waitForTimeout (flaky)
     `page.waitForTimeout(500)` → Use explicit wait: `await page.locator('[data-testid="success"]').waitFor()`
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

- Don't skip accessibility for "MVP" → accessibility is a baseline, not a feature
- Don't assume mobile will be done later → test responsive now
- Don't mark "will refactor" → must be clean code now
- When in doubt about Figma, compare side-by-side and ask designer
- E2E flakiness is YOUR problem to solve, not the coder's — guide them to patterns in testing.md
