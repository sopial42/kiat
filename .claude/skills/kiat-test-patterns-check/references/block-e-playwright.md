# Block E — Playwright E2E tests

**Trigger:** any test file under `frontend/e2e/`.

## Rules and reasons

**Use explicit waits, not `page.waitForTimeout(ms)`.** Prefer `locator.waitFor()`, `expect(locator).toBeVisible()`, or `page.waitForLoadState('networkidle')`.

> *Why*: hard-coded waits are the single most common source of E2E flakiness. A 500ms wait is too short when CI is slow and too long when CI is fast — you'll either see false failures on slow runs or wasted time on fast ones. Explicit waits block only as long as needed, so they're both faster *and* more reliable.

**Avoid `test.describe.serial()`.** Each test should be independent.

> *Why*: serial mode makes the first failing test block all downstream tests in the block. This hides real bugs (you only see the first failure, not the cascade) and makes flakiness harder to diagnose because a single intermittent failure looks like a mass outage.

**Use `getByRole()` over `getByText()`.**

> *Why*: role-based selectors match the accessible name, which is stable against copy changes, localization, and styling. Text-based selectors break the moment a designer tweaks button text or a translator changes the string.

**Seed test data via SQL helpers, not API calls.**

> *Why*: API seeding is subject to the same RLS, rate limiting, and side effects as real user traffic. SQL seeding is deterministic — it runs as the database superuser, bypasses RLS, and has no rate limit. For test setup, determinism wins over realism.

**Clean up test data after each test**, typically in `afterEach` via a cleanup helper.

> *Why*: leftover rows pollute subsequent tests. The first run passes, the second run sees "already exists" errors, the third run passes again because cleanup partially ran — classic flaky pattern.

**Wait for `networkidle` after navigation if the page fires async queries on mount.**

> *Why*: the navigation promise resolves as soon as the HTML is delivered, but the data fetch hasn't started yet. Asserting content immediately after navigation races the fetch.

**Don't assert transient UI states.** Assert the final state instead.

> *Why*: `'Saving...'` is visible for a few hundred milliseconds; asserting it races the assertion against the state transition. Asserting `'Saved'` (the final state) always works because Playwright will wait for it.

**In CI, run Playwright against a built bundle (`npm start`), not the dev server (`npm run dev`).**

> *Why*: the dev server has HMR, source maps, and slow initial compile — all of which cause Clerk init timeouts and redirect loops in CI. A built bundle behaves the way production behaves.

Full anti-flakiness spec is in `delivery/specs/testing.md` section 0.

## Required acknowledgment (paste verbatim)

> I will use explicit waits (no `waitForTimeout`), avoid `serial` mode, use `getByRole()` selectors, seed via SQL helpers, and assert only final UI states.

## Common drift caught by reviewers

- `page.waitForTimeout(500)` anywhere — reviewer flags: hard-coded waits are flaky by design.
- `test.describe.serial(...)` — reviewer flags: masks bugs and obscures failure causes.
- `getByText('Save')` when a button has "Save" as its accessible name — reviewer flags: should be `getByRole('button', { name: 'Save' })`.
- Test asserts `'Saving...'` — reviewer flags: transient state, will race.
- Seeding via `POST /api/resource` — reviewer flags: should use a SQL helper for determinism.
