# Smocker — External API Mocking for E2E

Canonical pattern for mocking **external third-party APIs** during end-to-end tests in this stack. Smocker stands between the backend and real upstreams during `make test-e2e`, giving deterministic, offline-capable E2E runs while preserving the full frontend-backend wiring.

Loaded by coders/reviewers whenever a story touches the integration boundary between the backend and an external HTTP dependency (any new upstream, any new fetcher, any change to existing external calls).

> **Related docs:**
> - [`testing-pitfalls-backend.md`](testing-pitfalls-backend.md) — TD06 (Venom fixture mode), the complement to Smocker
> - [`testing-playwright.md`](testing-playwright.md) — Playwright global.setup integration
> - [`testing.md`](testing.md) — Test pyramid, CI orchestration
> - [`deployment.md`](deployment.md) — Env var conventions, production guards

---

## 1. Why Smocker (and why not just fixtures)

The backend talks to external APIs (payment provider, identity provider, third-party data source, etc.). During E2E, we cannot:

- **Hit the real upstream** — rate limits, flakiness, credentials, possible state mutation on the other end
- **Mock at the frontend layer** (`page.route`) — the request never reaches the backend, so we don't exercise the real wiring (see PP15)

**Two patterns, two layers, both needed:**

| Pattern | Layer | Use case |
|---|---|---|
| **Fixtures** (TD06) | Inside the backend process | Venom tests — backend swaps `HTTPClient` for a `FixtureClient` that reads testdata JSON |
| **Smocker** (this doc) | Out of process, via docker-compose | E2E tests — backend makes real HTTP calls to Smocker, which returns pre-seeded responses |

Both patterns coexist because Playwright runs the real backend binary (single `cmd/api/main.go`) — fixtures require code changes inside the binary, Smocker just swaps URLs.

**Why fixtures aren't enough on their own:** Playwright E2E exercises the frontend-backend boundary. If the backend is running as a production-shape binary hitting real upstream URLs, the test cannot mock those upstreams without either (a) a different binary for tests (defeats the purpose) or (b) an HTTP-level mock server. Smocker is (b).

**Why Smocker isn't enough on its own:** Venom runs many test cases per suite, each making HTTP calls to the backend. Having Smocker in the loop adds container overhead, network latency, and a second source of test failure. Fixtures embedded in the Go test process are faster and more stable for that layer.

---

## 2. When to use Smocker

**Use Smocker when:**
- Writing an E2E spec in `frontend/e2e/real-backend/` that exercises a flow hitting an external API
- The story introduces a new external HTTP dependency
- You need to assert the backend's behavior on specific upstream responses (429, 500, malformed JSON, etc.)

**Do NOT use Smocker when:**
- Writing Venom tests — use TD06 fixtures instead
- Writing Go unit tests — use httptest + `FixtureClient` fake
- Writing mocked Playwright specs (`e2e/<name>.spec.ts`) — use `page.route()`
- The external call is inside the Playwright test process itself (e.g., Playwright calling Clerk Backend API directly) — use `@clerk/backend` helpers

---

## 3. Docker-compose integration

Smocker runs as a service in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:17
    # ...

  minio:
    image: minio/minio
    # ...

  smocker:
    image: thiht/smocker:0.18
    ports:
      - "8100:8080"      # Mock server — backend calls this
      - "8101:8081"      # Admin API — Playwright seeds this
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8081/version"]
      interval: 2s
      timeout: 2s
      retries: 10
```

**Key ports:**
- `8100` — the mock-serving HTTP endpoint. Backend config points here.
- `8101` — the admin API. Playwright's global.setup POSTs scenarios here.

---

## 4. Backend configuration (env var swap)

Every external HTTP client reads its base URL from env:

```go
// backend/external/sources/external_a/client.go
type Client struct {
    baseURL string
    http    *http.Client
}

func NewClient() *Client {
    return &Client{
        baseURL: os.Getenv("EXTERNAL_A_BASE_URL"), // https://api.external-a.com in prod, http://smocker:8080/external-a in E2E
        http:    &http.Client{Timeout: 10 * time.Second},
    }
}
```

**`.env.example`:**
```bash
# Production
EXTERNAL_A_BASE_URL=https://api.external-a.com
EXTERNAL_B_BASE_URL=https://other-upstream.example

# E2E (overridden by Makefile target)
# EXTERNAL_A_BASE_URL=http://localhost:8100/external-a
# EXTERNAL_B_BASE_URL=http://localhost:8100/external-b
```

**Makefile target that enables E2E:**

```makefile
test-e2e:
	docker compose up -d postgres minio smocker
	# Wait for smocker admin API
	./scripts/wait-for.sh http://localhost:8101/version
	# Seed scenarios
	./scripts/smocker-seed.sh
	# Start backend with Smocker-routed URLs
	EXTERNAL_A_BASE_URL=http://localhost:8100/external-a \
	EXTERNAL_B_BASE_URL=http://localhost:8100/external-b \
	ENABLE_TEST_AUTH=false \
	./backend/bin/api &
	# Start frontend
	cd frontend && npm run build && npm start &
	# Run Playwright
	cd frontend && npx playwright test
```

**Path prefix convention:** use `http://smocker:8100/<source-slug>` so each upstream has its own namespace on the Smocker side. Simplifies debugging and scenario isolation.

---

## 5. Mock scenarios — YAML format

Smocker scenarios are YAML files describing request/response pairs:

```yaml
# frontend/e2e/fixtures/smocker/external_a.happy.yml
- request:
    method: GET
    path: /external-a/v1/search
    query_params:
      id: "abc-123"
  response:
    status: 200
    headers:
      Content-Type:
        - application/json
    body: |
      {
        "result": {
          "id": "abc-123",
          "name": "Test Entity",
          "status": "active"
        }
      }

- request:
    method: GET
    path: /external-a/v1/search
    query_params:
      id: "not-found-id"
  response:
    status: 404
    body: '{"error": "not_found"}'
```

**Conventions:**
- One file per upstream per scenario: `<source>.happy.yml`, `<source>.errors.yml`, `<source>.ratelimit.yml`
- Keep path prefix consistent with the Smocker-routed URL (see section 4)
- Commit realistic payload shapes — capture from the real upstream via `curl` when possible, not hand-crafted
- Fields not exercised by the test can be elided (Smocker doesn't enforce schema); assert only what your backend consumes

---

## 6. Seeding Smocker from Playwright or Makefile

### Option A: shell script (simple)

```bash
# scripts/smocker-seed.sh
#!/usr/bin/env bash
set -euo pipefail

SMOCKER_ADMIN="${SMOCKER_ADMIN:-http://localhost:8101}"
SCENARIOS_DIR="${1:-frontend/e2e/fixtures/smocker}"

# Reset
curl -sSf -X POST "${SMOCKER_ADMIN}/reset" >/dev/null

# Load each YAML
for yaml in "${SCENARIOS_DIR}"/*.yml; do
  echo "Seeding ${yaml}..."
  curl -sSf -X POST "${SMOCKER_ADMIN}/mocks" \
    -H "Content-Type: application/x-yaml" \
    --data-binary "@${yaml}" >/dev/null
done

echo "Smocker seeded from ${SCENARIOS_DIR}"
```

Called from the `test-e2e` Makefile target before starting the backend.

### Option B: per-spec seeding from Playwright (advanced)

For specs that need different upstream responses, seed inside the spec:

```typescript
// e2e/real-backend/external-a-errors.spec.ts
import { test, expect } from '@playwright/test';

const SMOCKER_ADMIN = 'http://localhost:8101';

test.beforeEach(async ({ request }) => {
  // Reset scenarios before each test
  await request.post(`${SMOCKER_ADMIN}/reset`);
});

test('UI shows graceful error when external source returns 500', async ({ page, request }) => {
  // Seed a 500 response scenario
  await request.post(`${SMOCKER_ADMIN}/mocks`, {
    headers: { 'Content-Type': 'application/x-yaml' },
    data: `
- request:
    method: GET
    path: /external-a/v1/search
  response:
    status: 500
    body: '{"error":"upstream_down"}'
    `,
  });

  await page.goto('/search');
  await page.getByLabel(/^Query$/).fill('test');
  await page.getByRole('button', { name: 'Search', exact: true }).click();

  await expect(page.getByRole('alert')).toContainText(/temporarily unavailable/i);
});
```

**Tradeoff:** per-spec seeding keeps test state local (easier to reason about), but adds boilerplate and coupling to Smocker's admin API. Start with Option A (shell seed), escalate to Option B when a spec needs a specific failure scenario.

---

## 7. Production guard (MANDATORY)

The same safety pattern as `ENABLE_TEST_AUTH` and `*_USE_FIXTURES` — crash loud on misconfiguration:

```go
// backend/cmd/api/main.go — init()
func init() {
    env := os.Getenv("ENV")
    if env != "production" {
        return
    }

    // Detect any smocker-routed URL leaking into prod
    for _, pair := range os.Environ() {
        parts := strings.SplitN(pair, "=", 2)
        key, val := parts[0], parts[1]
        if !strings.HasSuffix(key, "_BASE_URL") {
            continue
        }
        if strings.Contains(val, "smocker") || strings.Contains(val, "localhost:8100") {
            log.Fatalf("FATAL: %s=%q looks like a Smocker URL in production", key, val)
        }
    }
}
```

**Also extend the existing production guards** (document in `deployment.md`):

```go
// Same init, check DB and auth flags
if env == "production" {
    if os.Getenv("ENABLE_TEST_AUTH") == "true" {
        log.Fatal("ENABLE_TEST_AUTH must be false in production")
    }
    if strings.Contains(os.Getenv("DATABASE_URL"), "localhost") {
        log.Fatal("DATABASE_URL points at localhost in production — likely misconfig")
    }
    // All *_USE_FIXTURES must be unset/false
    for _, pair := range os.Environ() {
        parts := strings.SplitN(pair, "=", 2)
        if strings.HasSuffix(parts[0], "_USE_FIXTURES") && parts[1] == "true" {
            log.Fatalf("FATAL: %s=true in production", parts[0])
        }
    }
}
```

**Philosophy:** crash early at binary start-up is always cheaper than serving a single wrong response. Every time a new test-mode env var is introduced, it MUST be paired with a production guard in this same `init()` block.

---

## 8. Recording real responses (bootstrapping new scenarios)

When adding a new external source, capture a real response first, then strip/anonymize, then commit:

```bash
# Capture
curl -s \
  -H "Authorization: Bearer $EXTERNAL_A_TOKEN" \
  "https://api.external-a.com/v1/search?id=real-entity-123" \
  | jq '.' > /tmp/capture.json

# Inspect, remove secrets, replace identifying data with test-friendly values
# Then shape into the Smocker YAML format above
```

This keeps scenarios realistic (the backend's response parsing is exercised against real shapes) without risking credential leaks.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend 502/connection refused on external call | Smocker container not up | `docker compose ps smocker`; `docker compose logs smocker` |
| Smocker returns 404 for every request | Scenarios not seeded | Re-run `scripts/smocker-seed.sh`; check `curl http://localhost:8101/mocks` |
| Backend hits real upstream in E2E | `EXTERNAL_*_BASE_URL` not overridden | Check `make test-e2e` target exports all `_BASE_URL` vars |
| Test passes locally, fails in CI | Scenario YAML not in image / workflow | Ensure `.github/workflows/ci.yml` runs the same seed script |
| Production crash at startup `FATAL: X_BASE_URL looks like a Smocker URL` | Env var leak from staging to prod | GOOD — the guard fired. Fix the deploy config. |
| Smocker admin API slow | Scenario list too large | `curl -X POST /reset` between specs; avoid accumulating |
| Can't write scenario for a dynamic ID | Path with variables | Use Smocker's path matchers (`path: /external-a/v1/entity/{id}`) |

---

## 10. What Smocker is NOT

- **Not a replacement for Venom fixtures** — different test layer, different tradeoffs (see section 1)
- **Not a test framework** — it's a mock HTTP server; the test framework is Playwright
- **Not production-facing** — guarded out of prod via section 7; never deploy Smocker to anything user-facing
- **Not a contract tester** — if you need to verify the backend handles upstream schema drift, use contract tests (pact, etc.); Smocker just replays what you told it to

---

See also:
- [testing-pitfalls-backend.md](testing-pitfalls-backend.md) — TD06 fixtures pattern for Venom
- [testing-playwright.md](testing-playwright.md) — Playwright real-backend spec structure
- [deployment.md](deployment.md) — Production guards and env var conventions
- [backend-conventions.md](backend-conventions.md) — External client package structure
