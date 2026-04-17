# Kiat Makefile — canonical dev/test commands
#
# All state (ports, credentials, Clerk keys, env-specific URLs) comes from
# the root .env file. `.env` is gitignored; `.env.example` documents every
# variable. Do not invent dev/test commands outside this file — if a command
# is missing, add it here and document it in delivery/README.md.
#
# Three modes:
#   make dev       — real Clerk, real upstreams (requires Clerk keys + upstream credentials)
#   make dev-test  — test-auth bypass + fixture upstreams (offline-capable, fast iteration)
#   make test-e2e  — full stack with Smocker for externals (CI-equivalent)
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

infra-up: ## Start postgres + minio (needed for dev, dev-test, venom tests)
	docker compose up -d postgres minio
	@echo "Waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-kiat} >/dev/null 2>&1; do sleep 0.5; done
	@echo "postgres ready."

infra-up-e2e: ## Start postgres + minio + smocker (needed for test-e2e)
	docker compose up -d postgres minio smocker
	@./scripts/wait-for-smocker.sh

infra-down: ## Stop all containers (data volumes preserved)
	docker compose down

infra-destroy: ## Stop containers AND wipe data volumes (⚠️ destructive)
	docker compose down -v

# ─────────────────────────────────────────────────────────────
# Dev loops
# ─────────────────────────────────────────────────────────────

dev: infra-up ## Run backend + frontend with real Clerk (requires Clerk keys + real upstream credentials)
	@echo "TODO(EPIC-00): wire backend + frontend dev servers"
	@echo "Expected:"
	@echo "  - backend on :8080 with ENABLE_TEST_AUTH=false"
	@echo "  - frontend on :3000 with NEXT_PUBLIC_ENABLE_TEST_AUTH=false"

dev-test: infra-up ## Run backend + frontend with test-auth bypass + fixture upstreams (offline)
	@echo "TODO(EPIC-00): wire dev-test targets"
	@echo "Expected:"
	@echo "  - backend on :8080 with ENABLE_TEST_AUTH=true + every *_USE_FIXTURES=true"
	@echo "  - frontend on :3000 with NEXT_PUBLIC_ENABLE_TEST_AUTH=true"

# ─────────────────────────────────────────────────────────────
# Test gates (CI-equivalent locally)
# ─────────────────────────────────────────────────────────────

test-back: ## Run all Go colocated tests (no containers needed — TD04)
	cd backend && go test ./...

test-venom: infra-up ## Run Venom YAML black-box HTTP suite
	@echo "TODO(EPIC-00): start backend in test-auth mode + run venom against :8080"

test-e2e-mocked: ## Run Playwright mocked specs only (fast, no backend)
	cd frontend && npx playwright test --grep-invert "real-backend"

test-e2e: infra-up-e2e ## Run full Playwright suite (real backend + Smocker)
	@./scripts/smocker-seed.sh frontend/e2e/fixtures/smocker
	@echo "TODO(EPIC-00): start backend with ENV=e2e + Smocker-routed upstream URLs"
	@echo "             start frontend with npm start"
	@echo "             run playwright test"

ci-local: test-back test-venom test-e2e ## Run the full CI gate locally (same commands CI uses)

# ─────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────

clean: ## Remove local build artifacts
	cd backend && go clean -cache
	cd frontend && rm -rf .next node_modules/.cache
