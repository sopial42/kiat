# Pattern: Test Gate Automation

**Problem**: Tests might pass locally but fail in CI. Tests might fail randomly. Unclear who fixes test failures.

**Solution**: CI is the gate. Agents debug failures. Clear ownership.

---

## Test Execution Flow

```
Local Dev:
  Coder runs Playwright: npm run test:e2e
  If fail → debug + fix locally
  If pass → submit for review
  
Code Review:
  Reviewer checks: "Are tests written?"
  
Pre-Merge (CI):
  GitHub Actions runs Playwright
  If fail → BLOCK MERGE
  If pass → Ready for merge button
  
Merge:
  Human clicks merge only if CI green ✅
```

---

## Rule 1: Coder Runs Tests Before Submitting

### Playwright E2E (Frontend)

```bash
# Local run before submitting
npm run test:e2e

# If fail:
#   1. Read error
#   2. Add logging to test
#   3. Run again
#   4. Fix code or test
#   5. Rerun all tests
#   6. Max 3 iterations
```

**If failing after 3 tries:**
- Coder escalates: "Test failing despite 3 attempts. Root cause: [describe]"
- Reviewer or human debugs

### Venom (Backend)

```bash
# Local run before submitting
make test-back

# If fail:
#   1. Read error
#   2. Check test logic vs code logic
#   3. Fix code or test
#   4. Rerun
#   5. Max 3 iterations
```

---

## Rule 2: Tests are NOT Optional

**Tests failing = Code not ready.**

```
Coder: "Code ready for review"

Reviewer: "Tests passing? 'make test-back' says no."

Coder: "Oh, I didn't run them. Let me fix test failures first."
```

**Blocker in checklist:**
- [ ] Tests passing (both Venom and Playwright)

---

## Rule 3: CI is the Source of Truth

### GitHub Actions runs Playwright + Venom

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - run: npm run build
    - run: npm run test:e2e  # Playwright
    - run: make test-back    # Venom
    - if: failure()
      run: echo "Tests failed"
```

**If CI fails and local passes:**
- Network/timing difference
- Coder reruns locally with better logging
- Tests are NOT flaky (they're deterministic)

**If CI passes and local fails:**
- Local environment issue (old dependencies?)
- Coder sync: `npm install`, `make clean`, rerun

**Rule: Never merge if CI red.**

---

## Rule 4: Clear Test Ownership

### Who Fixes Test Failures?

| Scenario | Who Fixes |
|----------|-----------|
| Playwright test fail locally | Frontend-Coder |
| Venom test fail locally | Backend-Coder |
| Tests pass locally, fail in CI | Coder reruns with CI env simulator |
| Tests fail in CI, critical issue | Human escalates if not fixable in 1 hour |

---

## Anti-Flakiness Checklist (in testing-patterns.md)

**Coders must follow these:**

- [ ] No `waitForTimeout()` (use explicit waits)
- [ ] No `page.waitForNavigation()` (use `expect(page).toHaveURL()`)
- [ ] No `serial: true` (tests independent)
- [ ] Wait for data to render before asserting
- [ ] Use `getByRole()` not just text
- [ ] Use `{ exact: true }` if text is substring of other text
- [ ] Use `networkidle` wait when data-dependent

---

## Example: Debug Failing Test

**Test fails:**
```
❌ Feature form: auto-save works
   Error: Timeout waiting for "Saved" indicator
```

**Coder debug (iteration 1):**
```typescript
// Add logging
test('Feature form: auto-save works', async ({ page, browser }) => {
  await page.goto('/...');
  
  const nameInput = page.getByLabel('Feature name');
  await nameInput.fill('My Feature');
  
  // Debug: Check if input value set
  console.log('Input value after fill:', await nameInput.inputValue());
  
  // Debug: Check if "Saving" appears
  const savingText = page.getByText('Saving...');
  console.log('Saving indicator visible?', await savingText.isVisible());
  
  // Original assertion
  await expect(page.getByText('Saved')).toBeVisible();
});
```

**Run:** `npm run test:e2e -- feature.spec.ts --debug`

**Observation:** "Saving..." appears but "Saved" never does → mutation not completing.

**Coder fix (iteration 2):**
```typescript
// The issue: test doesn't wait for mutation to complete
// Fix: wait for specific network response

test('Feature form: auto-save works', async ({ page, browser }) => {
  const responsePromise = page.waitForResponse(
    response => response.url().includes('/api/feature') && response.status() === 200
  );
  
  await nameInput.fill('My Feature');
  await responsePromise;  // Wait for mutation
  
  await expect(page.getByText('Saved')).toBeVisible();
});
```

**Run:** `npm run test:e2e -- feature.spec.ts`

**Result:** ✅ Test passes

---

## CI Workflow (Human Perspective)

```
1. Coder submits code + tests passing locally
2. Reviewer approves code quality
3. Human pushes "Merge" button
4. GitHub Actions runs:
   - npm run build
   - npm run test:e2e
   - make test-back
5. If all pass: Merge completes
6. If any fail: Merge blocked
   - Coder gets notification
   - Coder reruns locally to understand why CI failed
   - Coder fixes and submits new commit
7. CI reruns automatically
8. Once all green: Merge possible
```

---

## What Causes CI-Only Failures?

### Common causes:
1. **Race conditions** in Playwright (test runs faster in CI)
   - Fix: Add explicit waits, remove waitForTimeout

2. **Network timing** (CI network slower/faster than local)
   - Fix: Use `networkidle` waits, not time-based waits

3. **Database state** (CI starts fresh, local has old data)
   - Fix: Always cleanup test data (use helpers.cleanupTestData)

4. **Timing assumptions** (test assumes X loads in <100ms)
   - Fix: Wait for visible, not for time passage

---

## Checklist: Before Saying "Tests Pass"

- [ ] `npm run test:e2e` passes (Playwright, all scenarios)
- [ ] `make test-back` passes (Venom, all unit tests)
- [ ] No console errors (warnings OK)
- [ ] No timeout assertions (if test takes >30s per case, investigate)
- [ ] Tests are deterministic (run 3x, should all pass)
- [ ] Test data cleaned up (no orphaned records)
- [ ] Test timing not brittle (no waitForTimeout, explicit waits)

---

## Summary

| Phase | Who | Action | Gate |
|-------|-----|--------|------|
| Development | Coder | Run tests locally | ✅ Pass before submit |
| Code Review | Reviewer | Verify tests exist | ✅ Tests in checklist |
| Pre-Merge | CI | Run full test suite | ✅ All green |
| Merge | Human | Click merge if CI ✅ | ✅ No merge if red |

**Test gate is automated. CI blocks bad merges. Done.**

---

**Next**: Read `skill-orchestration.md` to understand when to use skills vs agents.
