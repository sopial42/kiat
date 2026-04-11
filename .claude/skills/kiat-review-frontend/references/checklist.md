# Frontend Review Checklist

This is the reference checklist loaded by `kiat-review-frontend/SKILL.md` during Phase 3. Categories are ordered by blast radius — items that affect real users (accessibility, spec compliance, data correctness) come before cosmetic concerns.

Skim what's obviously fine; focus attention on the non-trivial items. A checklist entry isn't a nit to flag — it's a question to answer. If the code clearly handles it, move on.

Project-wide rules live in `delivery/specs/frontend-architecture.md`, `delivery/specs/design-system.md`, `delivery/specs/testing.md`, and `delivery/specs/security-checklist.md`. This file summarizes the review-time checks; the specs are the source of truth for how to implement them.

## 1. Spec compliance

The first thing to verify is that the code delivers what the spec asked for. A beautifully-written component that misses half the acceptance criteria is still a miss.

- **Every acceptance criterion is met** — cross-reference the spec's criteria against the diff.
- **The UI matches the Figma reference** — layout, spacing, colors, typography. Divergence should be either intentional (and explained in the handoff) or flagged.
- **The component calls the correct backend endpoints** with the correct request shape. A wrong endpoint or a missing field silently breaks the feature even when the UI looks right.
- **User flows match the spec** — happy path and failure path both match what the story spec describes.
- **Empty, loading, and error states are all handled.** If the spec mentioned them, check they're implemented; if it didn't, check the coder at least made a reasonable choice and flag the spec gap back to `kiat-validate-spec`.

## 2. Accessibility (WCAG AA)

Accessibility is a baseline, not a feature. Missing it means real users can't use the product — and retrofitting is several times more expensive than getting it right during the review. The project targets WCAG AA.

- **Every input has an associated label** — either `<label htmlFor="id">` or `aria-label` on the input. A visual `<p>` or `<span>` next to the input is not a label to a screen reader.
- **Buttons are accessible** — they have visible text content, or an `aria-label` if the button is icon-only. A bare `<button><Icon /></button>` is invisible to a screen reader.
- **Form controls are linked to their labels** by matching `id` / `htmlFor`. Implicit association via nesting works too, but explicit is clearer.
- **ARIA roles and attributes are used correctly** where the default semantics aren't enough: `aria-expanded` on disclosure triggers, `aria-labelledby` for dialogs, `role="dialog"` on modal containers.
- **Keyboard navigation works end to end.** Tab order is logical, Enter submits forms, Escape closes modals. If the feature can't be used without a mouse, that's a bug.
- **Focus is visible.** Removing the focus outline without replacing it makes the UI unusable for keyboard users.
- **Color is never the only indicator.** A red border alone for an error is invisible to color-blind users — pair it with an icon or text.
- **Images have alt text** or `aria-hidden="true"` if decorative. Missing `alt` triggers screen reader failure modes.
- **Contrast meets WCAG AA** — 4.5:1 for body text, 3:1 for large text. The project design tokens are meant to pass; if the code uses raw hex values, check the contrast explicitly.
- **An axe-core scan passes** — if the project has automated a11y testing, run it and check there are no violations.

## 3. Styling and design system

The design system exists so that every component feels like part of the same product. Drift from it creates inconsistency that compounds over stories.

- **Styles come from Tailwind classes** — no inline `style={{}}` attributes, no CSS modules outside `globals.css`. Inline styles bypass the theme and can't respond to dark mode or `prefers-reduced-motion`.
- **Colors come from project design tokens**, defined in [`delivery/specs/design-system.md`](../../../delivery/specs/design-system.md) and wired through `globals.css` `@theme` variables. Hardcoded hex values (`bg-[#52acd9]`) bypass the token system and will drift when the palette is updated.
- **Border radius, spacing, and typography follow the project scale.** If the design system specifies a spacing scale (`p-4 sm:p-6 lg:p-8`), diverging from it on one component breaks visual rhythm.
- **Font families come from the project's typography tokens.** Don't hardcode font-family; use the token names defined in the design system.
- **Dark mode is respected** if the project supports it. A hardcoded light-mode color will look wrong in dark mode.
- **Motion preferences are respected.** Animations gated on `motion-safe:` will be skipped by users with `prefers-reduced-motion` — an accessibility requirement.

## 4. Responsive design

The project targets mobile, tablet, and desktop. Breaking at a breakpoint means breaking for every user on that device class.

- **Styling is mobile-first.** Base styles target mobile, then `sm:`, `md:`, `lg:` add progressive enhancement.
- **Grids and layouts collapse gracefully** — `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` is the common pattern.
- **Flex layouts stack on narrow screens** if they have 3+ items.
- **Padding scales progressively** — `p-4 sm:p-6 lg:p-8` — rather than being a fixed value that either feels cramped on mobile or wasteful on desktop.
- **Tested at the project breakpoints.** Common targets are 320px (narrow mobile), 640px (tablet), 1024px (desktop); the project may have different targets in `design-system.md`.
- **No horizontal scroll.** Content must fit the viewport at every breakpoint. Overflow is usually a sign of a fixed-width child inside a responsive parent.

## 5. Components and structure

Well-structured components are easier to test, compose, and change. Poor structure shows up as prop drilling, monolithic files, and tangled effects.

- **Shadcn/UI primitives are reused** — Button, Input, Form, Card, Dialog, Select, Checkbox, Radio. Building a custom button that reimplements 80% of `<Button>` is almost always a mistake.
- **Custom components exist only when Shadcn doesn't cover the use case.** When a custom component is introduced, it's named clearly and colocated with its usage.
- **Props are fully typed.** No `any` — a TypeScript `interface ComponentProps { ... }` or inline type. `any` propagates silently and defeats the point of using TS.
- **The client / server boundary is correct.** `'use client'` is present on files that use hooks, state, or browser-only APIs. Missing it on a hook-using file throws at build time; present on a file that doesn't need it bloats the bundle.
- **No prop drilling more than 2-3 levels deep.** If a prop has to traverse 4+ components, extract a Context or a custom hook instead.
- **Composition is clean.** A component that does layout + fetching + form state + side effects is a maintenance trap — split it.
- **Refs and effects clean up properly.** A `useEffect` that sets up a subscription must return a cleanup function.

## 6. Hooks and state management

Hooks are the most subtle source of frontend bugs because they look correct until they re-render at the wrong time. Full project hook conventions are in `delivery/specs/frontend-architecture.md`.

- **`useQuery` cache keys match the data shape.** If the key doesn't include the parameter that varies, the wrong data will be served from cache. If it's not stable between renders, the query fires in a loop.
- **`useMutation` invalidates the relevant queries on success.** Without invalidation, the UI shows stale data until the user manually refreshes.
- **`useMutation` handles errors via `onError` or the error state.** A silent failure is worse than a visible one.
- **`useAutoSave` uses a stable `enabled` flag.** The contract is that `enabled` must not transition `false → true` in the same render that `data` changes, or the first save will see undefined data. Use a derived flag like `const shouldSave = isReady && dataLoaded` rather than `enabled: !isLoading`.
- **`useEffect` has a correct dependency array.** Missing deps cause stale closures; extra deps cause re-run loops. ESLint's exhaustive-deps rule catches most of this, but a review should double-check on non-trivial effects.
- **Transient values use `useRef`, not `useState`.** Putting a value in state when it doesn't need to trigger a re-render causes unnecessary renders.
- **Custom hooks are named with `use*`** and extract reusable logic. A 200-line component with 10 `useState`s is a hook waiting to be extracted.

## 7. Error handling and edge cases

How the code behaves when things go wrong matters more than how it behaves when things go right — the happy path is easy.

- **`useQuery` and `useMutation` errors are caught and displayed.** An error boundary or an inline error UI — not a silent console.error.
- **Error messages are user-friendly**, not internal error strings. The user should be told what happened and what to do next, not "Error: 500".
- **Retry is available** when appropriate. A failed fetch should offer the user a way to retry without a full page reload.
- **Empty states are handled** — empty list, search with no results, first-time user. Each empty state should have a clear CTA or explanation.
- **Loading states are present** — spinners, skeletons, disabled buttons. A form with no loading state can be submitted twice during a slow network.
- **Offline behavior is handled** if the project supports it — detect `navigator.onLine`, show a banner, queue mutations.
- **No unhandled promise rejections.** Every `async` function has `.catch()` or `try/catch` at the appropriate boundary.

## 8. Forms and validation

Forms are where input meets state — most frontend bugs live here.

- **Validation errors are shown per-field**, not as a single form-level red border. Users need to know which field is wrong.
- **Submit is disabled while the form is invalid**, to prevent the user from smashing submit and getting a confusing error.
- **Submit is disabled while the mutation is pending**, to prevent double-submission.
- **The first invalid field receives focus** when the user tries to submit, or is announced via an `aria-live` region for screen readers.
- **Success feedback is clear** — a toast, a redirect, or an inline confirmation.
- **Auto-save is implemented** per the project's `useAutoSave` contract if the spec calls for it.
- **A dirty flag warns on navigation** if unsaved changes would be lost.

## 9. Playwright E2E tests

E2E tests prove the feature works end-to-end. The project's anti-flakiness rules are in [`delivery/specs/testing.md`](../../../delivery/specs/testing.md); a common subset is enforced at coder time via `kiat-test-patterns-check`.

- **The happy path is tested.** The user can complete the feature from start to finish.
- **Error cases are tested** — validation failures, network errors, empty states.
- **Edge cases are tested** — long input, special characters, Unicode.
- **Selectors use `getByRole()`** rather than `getByText()` — more stable against copy changes and translation.
- **No `waitForTimeout()`.** Hard-coded waits are the single most common cause of flakiness. Use `expect(locator).toBeVisible()` or `locator.waitFor()` instead.
- **No `test.describe.serial()`.** Serial mode makes cascading failures — the first failing test blocks all downstream tests and hides the real bug.
- **Test data is seeded via SQL helpers**, not via API calls. API seeding is subject to the same RLS and rate limiting as real users and is non-deterministic.
- **Test data is cleaned up** after each test (usually in `afterEach`), so tests don't pollute each other.
- **The feature is tested at mobile viewport** if it's responsive.
- **No `.only` or `.skip` left behind.** Every test runs in CI.

## 10. Performance

Performance issues usually don't surface until production. A review is one of the cheaper places to catch the obvious ones.

- **No N+1 queries in data fetching.** Batch loads are preferred to per-item queries.
- **No unnecessary re-renders.** `useMemo` and `useCallback` on expensive computations and stable callback refs. A component re-rendering on every parent render is a waste of CPU.
- **`useEffect` cleanup functions are present** for subscriptions, timers, and event listeners. Without cleanup, these leak across renders.
- **Heavy libraries aren't imported for one feature.** A 200kB library for a single function call is an unnecessary bundle cost.
- **Images use the project's image component** and are lazy-loaded where appropriate.
- **Suspense boundaries are nested** for better UX if the project uses server components.

## 11. Security

Frontend security is mostly about not shooting yourself in the foot with unsafe DOM manipulation.

- **No secrets in client code.** API keys, service URLs — everything that runs in the browser is public. The only secrets in frontend code are public publishable keys.
- **No `dangerouslySetInnerHTML`** without sanitization via a library like DOMPurify. Raw HTML from user input is an XSS vector.
- **User input is never rendered as HTML.** React auto-escapes text, but any manual `innerHTML` manipulation needs review.
- **Auth tokens aren't in `localStorage`.** `localStorage` is readable from any script on the page, making tokens exfiltrable via XSS. Use HttpOnly cookies or in-memory storage.
- **Auth uses the `Authorization` header**, not cookies, for API calls — this prevents CSRF.

## 12. Code quality

Most of these should be caught by the toolchain. Only flag them in review if the toolchain doesn't and the issue is non-trivial.

- **No merged TODO comments without ticket references.**
- **No `console.log` in production code.** Use the project logger if logging is needed.
- **Clear naming** — `selectedUserId`, not `data` or `x`.
- **No magic numbers or hardcoded user-facing strings** — extract to constants or the i18n system.
- **Imports are organized** — no circular dependencies, clean import order.
- **No `any` types** — TypeScript should be fully typed.
- **Comments explain "why"** for non-obvious logic, not "what" the code literally does.
