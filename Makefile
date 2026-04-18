# Kiat Makefile — canonical dev/test commands
#
# All state (ports, credentials, Clerk keys, env-specific URLs) comes from
# the root .env file. `.env` is gitignored; `.env.example` documents every
# variable. Do not invent dev/test commands outside this file — if a command
# is missing, add it here and document it in delivery/README.md.
#
# Four modes. Two axes vary (auth + external API source):
#
#   make dev       — real Clerk, real external upstreams
#                    (requires Clerk keys + upstream credentials)
#   make dev-test  — test-auth bypass, Smocker for externals
#                    (offline-capable, fast iteration without real upstreams)
#   make test-venom — test-auth bypass, Smocker for externals
#                    (same stack as dev-test; Venom runs YAML suite against it)
#   make test-e2e  — real Clerk, Smocker for externals
#                    (CI-equivalent; Playwright runs against this stack)
#
# Smocker is the universal external-API mock pattern across dev-test, Venom,
# and E2E. See delivery/specs/smocker-patterns.md for the why. Production
# mode (ENV=production) is the only mode that hits real upstreams.
#
# See delivery/specs/deployment.md for the production env var matrix.

.PHONY: help dev dev-test infra-up infra-down test-back test-venom test-e2e test-e2e-mocked ci-local clean

# Load .env if present (gitignored; copy from .env.example)
ifneq (,$(wildcard .env))
  include .env
  export
endif

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─────────────────────────────────────────────────────────────
# Infrastructure (docker-compose)
# ─────────────────────────────────────────────────────────────

infra-up: ## Start postgres + minio (needed for `make dev` — real upstreams, no Smocker)
	docker compose up -d postgres minio
	@echo "Waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-kiat} >/dev/null 2>&1; do sleep 0.5; done
	@echo "postgres ready."

infra-up-test: ## Start postgres + minio + smocker (needed for dev-test, test-venom, test-e2e)
	docker compose up -d postgres minio smocker
	@echo "Waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-kiat} >/dev/null 2>&1; do sleep 0.5; done
	@./scripts/wait-for-smocker.sh
	@./scripts/smocker-seed.sh frontend/e2e/fixtures/smocker

infra-down: ## Stop all containers (data volumes preserved)
	docker compose down

infra-destroy: ## Stop containers AND wipe data volumes (⚠️ destructive)
	docker compose down -v

# ─────────────────────────────────────────────────────────────
# Dev loops
# ─────────────────────────────────────────────────────────────

dev: infra-up ## Run backend + frontend with REAL Clerk and REAL external upstreams
	@echo "TODO(EPIC-00): wire backend + frontend dev servers"
	@echo "Expected:"
	@echo "  - backend on :8080 with ENABLE_TEST_AUTH=false and all EXTERNAL_*_BASE_URL pointing at real APIs"
	@echo "  - frontend on :3000 with NEXT_PUBLIC_ENABLE_TEST_AUTH=false"

dev-test: infra-up-test ## Run backend + frontend with test-auth bypass + Smocker for externals (offline-capable)
	@echo "TODO(EPIC-00): wire dev-test targets"
	@echo "Expected:"
	@echo "  - backend on :8080 with ENABLE_TEST_AUTH=true and all EXTERNAL_*_BASE_URL overridden to http://localhost:8100/<slug>"
	@echo "  - frontend on :3000 with NEXT_PUBLIC_ENABLE_TEST_AUTH=true"
	@echo "  - Smocker scenarios seeded from frontend/e2e/fixtures/smocker/*.yml"

# ─────────────────────────────────────────────────────────────
# Test gates (CI-equivalent locally)
# ─────────────────────────────────────────────────────────────

test-back: ## Run all Go colocated tests (no containers — uses in-process fakes per GS01)
	cd backend && go test ./...

test-venom: infra-up-test ## Run Venom YAML suite against backend in test-auth mode with Smocker
	@echo "TODO(EPIC-00): start backend with ENABLE_TEST_AUTH=true + Smocker-routed upstream URLs,"
	@echo "             then run venom against :8080"

test-e2e-mocked: ## Run Playwright mocked specs only (fast, no backend needed — page.route only)
	cd frontend && npx playwright test --grep-invert "real-backend"

test-e2e: infra-up-test ## Run full Playwright suite against real backend + real Clerk + Smocker
	@echo "TODO(EPIC-00): start backend with ENABLE_TEST_AUTH=false + Smocker-routed upstream URLs,"
	@echo "             start frontend with npm start (NEXT_PUBLIC_ENABLE_TEST_AUTH=false),"
	@echo "             run playwright test"

ci-local: test-back test-venom test-e2e ## Run the full CI gate locally (same commands CI uses)

# ─────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────

clean: ## Remove local build artifacts
	cd backend && go clean -cache
	cd frontend && rm -rf .next node_modules/.cache
