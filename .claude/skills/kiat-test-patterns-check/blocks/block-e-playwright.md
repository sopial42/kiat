# Block E — Playwright E2E Tests

**Trigger:** any test file under `frontend/e2e/**`

## Mandatory rules (anti-flakiness — `delivery/specs/testing.md` Section 0)

- **NEVER** use `page.waitForTimeout(ms)`. Use explicit waits: `locator.waitFor()`, `expect(locator).toBeVisible()`, or `page.waitForLoadState('networkidle')`.
- **NEVER** use `test.describe.serial()`. Cascading failures hide real bugs and make flakiness harder to diagnose.
- Prefer `getByRole()` over `getByText()` — more stable against copy changes and translation.
- Seed data via SQL helpers (`seedPatient`, `seedZone`, etc. from `frontend/e2e/helpers/db.ts`), NOT via API calls. SQL seeding bypasses RLS and is deterministic.
- Clean up test data after each test with `cleanupTestData()` (usually in `afterEach`).
- Wait for `networkidle` after navigation if the page fires async queries on mount.
- Never assert **transient** UI states (`Saving...`) — they race the assertion. Assert **final** states (`Saved`) instead.
- In CI, never use `npm run dev` as the Playwright webServer — always `npm start` against a built bundle. `npm run dev` causes Clerk JS init timeouts and redirect loops.

## Required acknowledgment (paste verbatim)

> I will use explicit waits (no `waitForTimeout`), avoid `serial` mode, use `getByRole()` selectors, seed via SQL helpers, and assert only final UI states.

## Common drift caught by reviewers

- `page.waitForTimeout(500)` anywhere — reviewer flags: hard-coded waits are flaky by design
- `test.describe.serial('...', () => {...})` — reviewer flags: first test failing blocks all subsequent, masks bugs
- `getByText('Save')` where a button has text "Save" — reviewer flags: should be `getByRole('button', { name: 'Save' })`
- Test asserts `'Saving...'` is visible — reviewer flags: this is transient, will race
- E2E seeds via `POST /api/patients` — reviewer flags: should use SQL helper for determinism
