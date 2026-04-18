# Smocker — The Universal External-API Mock

Canonical pattern for mocking **external third-party APIs** in every Kiat test and dev mode that involves a running backend binary. Smocker stands between the backend and real upstreams, giving deterministic, offline-capable runs while preserving the full HTTP wiring.

Loaded by coders/reviewers whenever a story touches the integration boundary between the backend and an external HTTP dependency (any new upstream, any new fetcher, any change to existing external calls).

> **Related docs:**
> - [`testing-pitfalls-backend.md`](testing-pitfalls-backend.md) — Venom pitfalls VP01-VP08 / GS01-GS03 and decisions TD01-TD07 (all of which assume Smocker as the external mock)
> - [`testing-playwright.md`](testing-playwright.md) — Playwright global.setup integration
> - [`testing.md`](testing.md) — Test pyramid, CI orchestration
> - [`deployment.md`](deployment.md) — Env var conventions, production guards

---

## 1. Philosophy — one mock pattern for external HTTP

The backend talks to external APIs (payment provider, identity provider, third-party data source, etc.). In every dev/test mode that runs a real backend binary, those upstream URLs must point somewhere we control — otherwise we hit rate limits, credential walls, and flaky infrastructure.

**Kiat uses exactly one pattern for this: Smocker.**

| Test layer | Backend running? | External API mocking |
|---|---|---|
| Go unit tests (`make test-back`) | ❌ No (pure `go test ./...`) | **In-process fake** injected in `_test.go` — NOT Smocker |
| Venom HTTP suite (`make test-venom`) | ✅ Yes | **Smocker** |
| `make dev-offline` (offline dev loop) | ✅ Yes | **Smocker** |
| Playwright E2E (`make test-e2e`) | ✅ Yes | **Smocker** |

**The boundary that matters**: the moment a real `go run` or `./backend/bin/api` process is up and making real HTTP calls, external URLs point at Smocker. Before that boundary (pure unit tests), the standard Go test-double pattern applies and Smocker is not involved.

**Why one pattern instead of two** (previous drafts of this doc proposed a parallel in-process fixture client; the unified approach won for these reasons):

- **Consistency**: devs learn Smocker once, apply it across dev-offline / Venom / Playwright. No cognitive switch at layer boundaries.
- **Realism**: Smocker receives actual HTTP from the production-shape binary — every header, timeout, retry, and error-handling path is exercised. A parallel in-process client short-circuits all of that.
- **Debuggability**: Smocker's admin UI (`http://localhost:8101`) shows every request received, matched scenario, and mismatch. Far better than grepping Go logs.
- **Hot iteration on error scenarios**: simulating a 503, a timeout, a malformed JSON response is trivial in YAML — no recompile needed.
- **Onboarding a new upstream**: one `.env` line + one YAML scenario file. No new Go package, no `*_USE_FIXTURES` env var, no production guard.
- **No drift between mocks**: a dual pattern meant keeping two sources of truth (Go `testdata/*.json` + Smocker YAML) in sync. Forgetting either produced silent divergence. Unified = single source.

**The trade-off we accepted**: `make test-venom` now requires the Smocker container. Startup is one-time per session (~2s), scenario seeding is <100ms per file. The real-HTTP traversal cost per testcase is negligible (localhost, <10ms). Net: a few seconds slower than the old fixture pattern, in exchange for one mental model across the stack.

---

## 2. When to use Smocker (and when NOT to)

**Use Smocker** whenever a running backend process calls an external HTTP API in any of:
- `frontend/e2e/real-backend/` specs (Playwright E2E)
- `frontend/e2e/` mocked specs where the flow requires the backend to actually reach its external dependency
- `backend/tests/venom/**/*.venom.yml` suites (Venom HTTP)
- `make dev-offline` local iteration (offline, deterministic)

**Do NOT use Smocker when**:
- Writing Go unit tests (`*_test.go` colocated files) — use a Go fake (`FakeXxxClient` struct in `_test.go`) injected into the usecase. Smocker can't run under `go test ./...` because the test runner doesn't know about docker-compose. See [`testing-pitfalls-backend.md:GS01`](testing-pitfalls-backend.md).
- Writing `frontend/e2e/` mocked specs that only need to intercept the **frontend's** call to `/api/*`. Those use `page.route()` at the browser layer. Smocker sits one layer deeper (backend ↔ external), not browser ↔ backend.
- Mocking calls made by the Playwright test process itself (e.g., the test calling Clerk's backend API for JWT swap). Those use `@clerk/backend` helpers directly.

The rule of thumb: **"real backend running AND real HTTP leaving the binary → Smocker."** Everything else, different tool.

---

## 3. Docker-compose integration

Smocker runs as a service in `docker-compose.yml`:

```yaml
services:
  smocker:
    image: thiht/smocker:0.18
    ports:
      - "8100:8080"      # Mock server — backend calls this
      - "8101:8081"      # Admin API — seeding, inspection
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8081/version"]
      interval: 2s
      timeout: 2s
      retries: 10
```

Brought up by:
- `make infra-up-test` — starts `postgres minio smocker` together
- Referenced by `make dev-offline`, `make test-venom`, `make test-e2e` as a dependency

**Key ports:**
- `8100` — mock-serving HTTP. Backend `EXTERNAL_*_BASE_URL` env vars point here in test modes.
- `8101` — admin API. Seeding scripts POST scenarios here. UI accessible in a browser for debugging.

---

## 4. Backend configuration — one env var per upstream

Every external HTTP client reads its base URL from an env var:

```go
// backend/external/sources/external_a/client.go
type Client struct {
    baseURL string
    http    *http.Client
}

func NewClient() *Client {
    return &Client{
        baseURL: os.Getenv("EXTERNAL_A_BASE_URL"),
        http:    &http.Client{Timeout: 10 * time.Second},
    }
}
```

**`.env.example`:**
```bash
# Production value
EXTERNAL_A_BASE_URL=https://api.external-a.example

# In make dev-offline / test-venom / test-e2e, the Makefile overrides to:
#   EXTERNAL_A_BASE_URL=http://localhost:8100/external-a
# (see Makefile targets for the authoritative list)
```

**Path prefix convention**: `http://localhost:8100/<source-slug>`. Each upstream gets its own namespace on the Smocker side — simplifies debugging and scenario isolation. The Makefile targets apply this convention automatically; sources only need to declare the production URL in `.env.example`.

---

## 5. Scenarios — YAML format

Scenario files live under `frontend/e2e/fixtures/smocker/`, one file per upstream per scenario:

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

**Why these scenarios live under `frontend/e2e/fixtures/smocker/` even though they're used by Venom too**: single seed path, single refresh workflow, single team mental model. A sibling location like `backend/tests/fixtures/smocker/` would create two seed scripts and two divergent sets. The path is historical (E2E came first); conceptually, read it as `shared/fixtures/smocker/`.

**Conventions:**
- One file per upstream per scenario: `<source>.happy.yml`, `<source>.errors.yml`, `<source>.ratelimit.yml`, `<source>.malformed.yml`
- Prefix the path with the source slug (matches the `BASE_URL` routing convention, section 4)
- **Realistic shapes only** — capture from the real upstream via `curl`, strip secrets, commit. Hand-crafted payloads drift from production and hide parsing bugs.
- Elide fields your backend doesn't consume (Smocker doesn't enforce schema; keep YAML readable).

---

## 6. Seeding Smocker

### Option A: shell script (simple, the default)

```bash
# scripts/smocker-seed.sh — runs before every test target that uses Smocker
SMOCKER_ADMIN="${SMOCKER_ADMIN:-http://localhost:8101}"
SCENARIOS_DIR="${1:-frontend/e2e/fixtures/smocker}"

curl -sSf -X POST "${SMOCKER_ADMIN}/reset" >/dev/null
for yaml in "${SCENARIOS_DIR}"/*.yml; do
  curl -sSf -X POST "${SMOCKER_ADMIN}/mocks" \
    -H "Content-Type: application/x-yaml" \
    --data-binary "@${yaml}" >/dev/null
done
```

Already shipped at `scripts/smocker-seed.sh`. Called from `make dev-offline`, `make test-venom`, `make test-e2e`.

### Option B: per-spec seeding (advanced, for error-scenario specs)

For a Playwright spec that needs a specific failure injected:

```typescript
test.beforeEach(async ({ request }) => {
  await request.post('http://localhost:8101/reset');
});

test('UI shows graceful error when external source returns 500', async ({ page, request }) => {
  await request.post('http://localhost:8101/mocks', {
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
  // ... exercise the flow, assert the UI reaction ...
});
```

Start with Option A; escalate to Option B only when a spec needs a scenario the shared seed doesn't provide.

---

## 7. Production guard (MANDATORY)

`backend/cmd/api/main.go` `init()` MUST `log.Fatal` at startup when `ENV=production` and any of these hold:

- `ENABLE_TEST_AUTH=true`
- Any `EXTERNAL_*_BASE_URL` contains `smocker` or `localhost:8100` or `127.0.0.1:8100`
- `DATABASE_URL` contains `localhost` or `127.0.0.1`

Example:

```go
func init() {
    env := os.Getenv("ENV")
    if env != "production" {
        return
    }

    if os.Getenv("ENABLE_TEST_AUTH") == "true" {
        log.Fatal("FATAL: ENABLE_TEST_AUTH must be false in production")
    }

    for _, pair := range os.Environ() {
        parts := strings.SplitN(pair, "=", 2)
        if len(parts) != 2 {
            continue
        }
        key, val := parts[0], parts[1]

        if strings.HasSuffix(key, "_BASE_URL") {
            if strings.Contains(val, "smocker") ||
               strings.Contains(val, "localhost:8100") ||
               strings.Contains(val, "127.0.0.1:8100") {
                log.Fatalf("FATAL: %s=%q points at Smocker in production", key, val)
            }
        }
    }

    if du := os.Getenv("DATABASE_URL"); strings.Contains(du, "localhost") || strings.Contains(du, "127.0.0.1") {
        log.Fatal("FATAL: DATABASE_URL points at localhost in production")
    }
}
```

**Philosophy:** crash early at binary start-up is always cheaper than serving a single wrong response. Every new test-mode env var MUST be paired with a production guard in this same `init()` block, in the same commit.

---

## 8. Recording real responses (bootstrapping new scenarios)

When adding a new external source, capture a real response first, then sanitize, then shape into YAML:

```bash
# 1. Capture
curl -s \
  -H "Authorization: Bearer $EXTERNAL_A_TOKEN" \
  "https://api.external-a.example/v1/search?id=real-entity-123" \
  | jq '.' > /tmp/capture.json

# 2. Inspect — remove secrets, replace identifying data with test-friendly values

# 3. Shape into the Smocker YAML format (section 5) under
#    frontend/e2e/fixtures/smocker/external_a.happy.yml

# 4. Commit both the backend client code AND the scenario file in the same PR.
```

**Refresh workflow** (when upstream shape or values drift):
- Re-run step 1 against a known entity
- Diff `jq` output against the existing scenario's response body
- Update the YAML scenario to match; update any Venom assertions that reference field values that changed
- Commit together

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend 502/connection refused on external call | Smocker container not up | `docker compose ps smocker`; `docker compose logs smocker` |
| Smocker returns 404 for every request | Scenarios not seeded | Re-run `scripts/smocker-seed.sh`; check `curl http://localhost:8101/mocks` |
| Backend hits real upstream in a test mode | `EXTERNAL_*_BASE_URL` not overridden | Check the Makefile target — every test recipe MUST override every `_BASE_URL` to `http://localhost:8100/<slug>` |
| Test passes locally, fails in CI | Scenario YAML not committed | Ensure `frontend/e2e/fixtures/smocker/*.yml` is tracked, not gitignored |
| Production crash at startup `FATAL: X_BASE_URL points at Smocker` | Env var leak from staging to prod | GOOD — the guard fired. Fix the deploy config. |
| Smocker admin API slow | Scenario list too large | `curl -X POST /reset` between specs; avoid accumulating |
| Can't match a path with a dynamic ID | Path with variables | Use Smocker's path matchers (`path: /external-a/v1/entity/{id}`) |
| Go unit test wants to exercise external call | Unit tests don't use Smocker | Inject a `FakeXxxClient` in the usecase test — see GS01 |

---

## 10. What Smocker is NOT

- **Not used in Go unit tests** — `go test ./...` runs without any container. Use in-process fakes there.
- **Not a contract tester** — if you need to verify the backend handles upstream schema drift, use a contract testing tool (pact, etc.); Smocker replays what you told it to.
- **Not production-facing** — guarded out of prod via section 7; never deploy Smocker to anything user-facing.
- **Not a replacement for Playwright** — Smocker mocks external APIs seen BY the backend. Frontend ↔ backend wiring is still tested by Playwright end-to-end.

---

See also:
- [testing-pitfalls-backend.md](testing-pitfalls-backend.md) — Venom pitfalls and TD06 (why Smocker over in-process fixtures)
- [testing-playwright.md](testing-playwright.md) — Playwright real-backend spec structure and Smocker seeding from tests
- [deployment.md](deployment.md) — Production guards and env var conventions
- [backend-conventions.md](backend-conventions.md) — External client package structure
