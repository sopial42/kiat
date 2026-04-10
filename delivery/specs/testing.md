# Testing Patterns: Playwright E2E & Venom Unit Tests

Anti-flakiness rules, pitfalls, and testing strategies for production-grade confidence.

---

## Playwright E2E Setup

**Location**: `frontend/e2e/`  
**Config**: `frontend/playwright.config.ts`  
**Fixtures**: `frontend/e2e/fixtures.ts` (database seeding helpers)

### Basic Config

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm start',  // CI: production build
    // Local: start frontend manually with `make dev`
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## Anti-Flakiness Rules (CRITICAL)

### Rule 1: NEVER use `waitForTimeout()`

```typescript
// ❌ BAD: Arbitrary wait, flakes on slow machines
await page.waitForTimeout(500);
await page.click('button');

// ✅ GOOD: Wait for element to be ready
await page.locator('button').waitFor({ state: 'visible' });
await page.click('button');
```

### Rule 2: NEVER use `serial` mode

```typescript
// ❌ BAD: If test 1 fails, tests 2-5 are skipped
test.describe.serial('workflow', () => {
  test('step 1', async () => { ... });
  test('step 2', async () => { ... });  // Skipped if step 1 fails
});

// ✅ GOOD: Each test independent, can run in parallel
test('step 1', async ({ page, context }) => { ... });
test('step 2', async ({ page, context }) => { ... });  // Runs even if step 1 fails
```

### Rule 3: Wait for data before clicking

```typescript
// ❌ BAD: Component renders async, callback captures stale state
test('create order', async ({ page }) => {
  await page.click('button:has-text("Create")');  // ← Button created async
  // Callback fired before data loaded
});

// ✅ GOOD: Wait for data to render first
test('create order', async ({ page }) => {
  await page.waitForSelector('[data-testid="order-form"]');  // Wait for form
  await page.fill('input[name="amount"]', '100');
  await page.click('button:has-text("Create")');
});
```

### Rule 4: Use `getByRole()` over `getByText()`

```typescript
// ❌ BAD: Brittle, fails if text changes or duplicated
await page.locator('button:has-text("Save")').click();

// ✅ GOOD: Role-based, accessible by default
await page.getByRole('button', { name: 'Save' }).click();

// If "Save" appears multiple times, be specific:
await page.getByRole('button', { name: /^Save$/ }).click();  // Exact match
```

### Rule 5: Use `{ exact: true }` for substring text

```typescript
// ❌ BAD: Matches "Save and Continue" when looking for "Save"
await page.locator('button:has-text("Save")').click();

// ✅ GOOD: Exact match
await page.getByRole('button', { name: 'Save', exact: true }).click();
```

### Rule 6: Wait for network idle

```typescript
// ❌ BAD: Click, then immediately assert (data might be loading)
await page.click('button');
expect(page.locator('p')).toContainText('Success');

// ✅ GOOD: Wait for network to finish
await page.click('button');
await page.waitForLoadState('networkidle');
expect(page.locator('p')).toContainText('Success');
```

### Rule 7: Don't assert transient UI

```typescript
// ❌ BAD: "Saving..." is transient, flakes randomly
expect(page.locator('.saving-indicator')).toBeVisible();

// ✅ GOOD: Assert final state
expect(page.locator('.save-success')).toBeVisible();  // Appears after save
```

### Rule 8: Use explicit waits for navigation

```typescript
// ❌ BAD: Click, arbitrary wait, then check URL
await page.click('button');
await page.waitForTimeout(500);
expect(page).toHaveURL('/dashboard');

// ✅ GOOD: Wait for navigation explicitly
await page.click('button');
await page.waitForURL('/dashboard');
expect(page).toHaveURL('/dashboard');
```

---

## Venom Unit Testing (Backend)

**Location**: `backend/venom/`  
**Pattern**: Table-driven tests with mocks

### Test Structure

```go
// backend/venom/user_test.go

func TestCreateUserUsecase(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
        wantCode string
    }{
        {
            name:     "happy path",
            email:    "test@example.com",
            wantErr:  false,
        },
        {
            name:     "invalid email",
            email:    "",
            wantErr:  true,
            wantCode: "INVALID_EMAIL",
        },
        {
            name:     "duplicate email",
            email:    "existing@example.com",  // Seeded before test
            wantErr:  true,
            wantCode: "DUPLICATE_EMAIL",
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Setup
            repo := &MockUserRepository{}
            uc := &usecase.CreateUserUsecase{Repo: repo}

            // Execute
            user, err := uc.Execute(context.Background(), tt.email, "Test User")

            // Assert
            if (err != nil) != tt.wantErr {
                t.Errorf("got error %v, want error %v", err != nil, tt.wantErr)
            }
            if tt.wantErr && !errors.Is(err, domain.ErrInvalidEmail) {
                t.Errorf("got error %v, want ErrInvalidEmail", err)
            }
        })
    }
}
```

### Mock Repository

```go
type MockUserRepository struct {
    SaveCalled bool
    SaveUser   *domain.User
    SaveErr    error
    
    FindByEmailCalled bool
    FindByEmailResult *domain.User
    FindByEmailErr    error
}

func (m *MockUserRepository) Save(ctx context.Context, user *domain.User) error {
    m.SaveCalled = true
    m.SaveUser = user
    return m.SaveErr
}

func (m *MockUserRepository) FindByEmail(ctx context.Context, email string) (*domain.User, error) {
    m.FindByEmailCalled = true
    return m.FindByEmailResult, m.FindByEmailErr
}
```

### Common Test Helpers

```go
// backend/venom/helpers.go

func setupTestDB(t *testing.T) *sql.DB {
    db, _ := sql.Open("postgres", os.Getenv("TEST_DATABASE_URL"))
    // Run migrations
    return db
}

func seedUser(t *testing.T, db *sql.DB, email, name string) uuid.UUID {
    id := uuid.New()
    db.ExecContext(context.Background(), 
        "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
        id, email, name,
    )
    return id
}

func cleanupTestData(t *testing.T, db *sql.DB) {
    db.ExecContext(context.Background(), "TRUNCATE users CASCADE")
}
```

---

## Common Pitfalls

### Pitfall 1: Stale Closure in React

**Problem**: Callback captures old state
```tsx
// ❌ BAD
const MyComponent = () => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      console.log(count);  // Always logs 0 (closure)
    }, 1000);
  }, []);  // No dependencies
};

// ✅ GOOD
useEffect(() => {
  const timer = setInterval(() => {
    console.log(count);  // Logs current count
  }, 1000);
}, [count]);  // Include dependency
```

### Pitfall 2: N+1 Renders

**Problem**: useQuery fires inside loop
```tsx
// ❌ BAD
{users.map(user => {
  const { data } = useQuery(['user', user.id], () => getUser(user.id));
  // 10 queries fired if 10 users (N+1)
  return <div>{data.name}</div>;
})}

// ✅ GOOD
const { data: usersWithDetails } = useQuery(['users'], () => getUsers());
// Single batch query
```

### Pitfall 3: Optimistic Locking Race

**Problem**: Rapid mutations use stale `updated_at`
```tsx
// ❌ BAD
const handleSelect = async (value) => {
  await selectZone.mutate(value);
  await clearOther.mutate(...);  // Race: stale updated_at
};

// ✅ GOOD: Sequence within one mutation
const { mutate } = useMutation(async (value) => {
  await api.selectZone(value);
  const updated = await api.getLatest();  // Fresh updated_at
  await api.clearOther(updated);
});
```

### Pitfall 4: useAutoSave Enabled Contract

**Problem**: `enabled` transitions `false→true` same render as data changes
```tsx
// ❌ BAD
const { data, mutation } = useForm();
const { useAutoSave } = useAutoSave({
  enabled: !isLoading,  // ← Transitions when data loads
  onSave: (data) => mutation.mutate(data),
});

// ✅ GOOD: Stable enabled condition
const shouldAutoSave = !isLoading && isReady;  // Decoupled from data
const { useAutoSave } = useAutoSave({
  enabled: shouldAutoSave,
  onSave: (data) => mutation.mutate(data),
});
```

### Pitfall 5: Unicode Escapes in JSX

**Problem**: `\u00e9` renders as code, not `é`
```tsx
// ❌ BAD
<p>{"\u00e9"}</p>  // Renders: \u00e9 (not é)

// ✅ GOOD
<p>{"é"}</p>  // Renders: é
```

---

## Testing Strategy

### Test Pyramid

1. **Unit Tests (70%)** — Venom: service logic, utilities
2. **Integration Tests (20%)** — Venom: API endpoints with mocks
3. **E2E Tests (10%)** — Playwright: full workflows

---

## CI/CD Testing

### Local Before Submit
```bash
npm run test:e2e          # Run Playwright
make test-back            # Run Venom
```

### CI Pipeline
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - run: go test ./backend/...   # Venom
    - run: npm run build            # Ensure no TS errors
    - run: npx playwright test      # Playwright (with production server)
```

**Note**: CI uses `npm start` (production build), NOT `npm run dev` (causes Clerk timeout).

---

## CI Gate (Merge Blocker)

CI is the **final gate** before merge. The rules are mechanical, not negotiable:

- **All tests must pass locally** before pushing. Never rely on CI to discover test failures — that wastes CI time and slows the whole team.
- **All tests must pass in CI** before merge. No merging with red CI, under any circumstance. If CI is red, diagnose the root cause; do not blindly retry.
- **If CI fails but local passes:** that's a flakiness signal, not a "retry until it passes" situation. Debug it using the anti-flakiness rules above. Common causes: `waitForTimeout`, `serial` mode, storageState token expiry, Clerk rate limits.
- **No skipping hooks or force-pushing to bypass CI.** See [git-conventions.md](git-conventions.md) for the immutability rules.

This rule is enforced at the Team Lead level (Phase 5 "Story Validation" requires all tests passing before a story is marked PASSED) and at the Kiat framework level (story cannot complete without green CI).

---

See also:
- [clerk-patterns.md](clerk-patterns.md) — Auth testing
- [security-checklist.md](security-checklist.md) — Security testing
- [git-conventions.md](git-conventions.md) — Branch and commit discipline
