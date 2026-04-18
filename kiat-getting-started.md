# Kiat — Getting Started

Covers **Phase B** of the fork journey — the credentials setup that humans must do by hand before Kiat's agents can take over. Budget: **~30–45 minutes** with all accounts ready.

> **Where this fits in the bigger picture**:
> - **Phase A** (~2 min) — fork & clone the repo
> - **Phase B** (~30–45 min) — **this doc** — Clerk dev instance, JWT template, test users, `.env` file, GitHub secrets, optional GCP project
> - **Phase C** (~2–4 hours of pipeline) — run Team Lead on `delivery/epics/epic-00/story-01..04` to ship the backend / frontend / Playwright harness / CI workflow. Agents do this autonomously; you monitor and arbitrate `NEEDS_DISCUSSION` verdicts if they arise.
> - **Phase D** (~30–60 min) — run Team Lead on `delivery/epics/epic-01/story-01` for a learning walkthrough of the full pipeline.
> - **After D** — you're ready for real EPIC 02+ business stories via BMad.

> **Scope of this doc.** Humans do what agents can't: create third-party accounts, click dashboards, paste secrets into GitHub settings. Everything else (Go code, Next.js code, test files, CI YAML) is produced by Team Lead's pipeline in Phase C — not by this doc.

---

## 0. Prerequisites (install once per machine)

- **Git** ≥ 2.40
- **Docker Desktop** (or colima + docker CLI) — needed for `postgres`, `minio`, `smocker` containers
- **Go** ≥ 1.23
- **Node.js** ≥ 20 + **npm** ≥ 10
- **`gh`** CLI (optional but recommended for GitHub ops)
- **Claude Code** — the agent harness; this repo assumes Claude Code with the Kiat agents loaded

Verify:
```bash
git --version && docker --version && go version && node --version && npm --version
```

---

## 1. Fork + clone

```bash
# Fork github.com/sopial42/kiat on the web, then:
git clone git@github.com:<you>/<your-project>.git
cd <your-project>

# Rename remote references if needed — the fork carries Kiat's README/CLAUDE.md.
# Keep them until you're comfortable with the workflow; customize later.
```

---

## 2. Clerk — dev instance + JWT template

Kiat uses Clerk for auth in two modes: real Clerk (production, CI) and test-auth bypass (local-only offline). You need one **Clerk dev instance** per forked project (never share across clients).

### 2.1. Create the dev instance

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com) → "Add application".
2. Choose a name matching your project. Pick the email + password authentication method (the scaffold assumes this; you can add OAuth providers later).
3. Copy from the "API keys" page:
   - **Publishable key** (starts with `pk_test_...`) → goes into `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - **Secret key** (starts with `sk_test_...`) → goes into `CLERK_SECRET_KEY`

### 2.2. Create the `playwright-ci` JWT template

This is **load-bearing for Playwright E2E** — without it, the JWT swap in `global.setup.ts` fails and every authenticated test returns 401. See `delivery/specs/testing-playwright.md` section 4 for the full reasoning.

1. In the Clerk dashboard, open **JWT Templates** → **+ New template**.
2. Name it exactly `playwright-ci` (the name is referenced in code; don't rename).
3. Lifetime: **3600 seconds**.
4. Claims: leave the default (`sub` = user ID is automatically included; backend RLS uses this).
5. Signing algorithm: `RS256` (default).
6. Save.

### 2.3. Create two test users (A + B) for Playwright

Playwright specs need a seeded user A (primary test user) and user B (for RLS cross-user assertions).

1. In Clerk dashboard → **Users** → **+ Create user**.
2. Create `e2e-user-a@<your-project>.test` with a strong password. Copy the generated user ID (`user_...`).
3. Repeat for `e2e-user-b@<your-project>.test`.
4. Record email, password, and user ID for each in your `.env` (see step 4 below).

---

## 3. `.env` file

```bash
cp .env.example .env
```

Fill the following (the template has placeholders):

| Variable | Where it comes from |
|---|---|
| `CLERK_SECRET_KEY` | Clerk dashboard → API keys → Secret key |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk dashboard → API keys → Publishable key |
| `E2E_USER_A_EMAIL`, `E2E_USER_A_PASSWORD`, `E2E_USER_A_CLERK_ID` | Step 2.3 above |
| `E2E_USER_B_EMAIL`, `E2E_USER_B_PASSWORD`, `E2E_USER_B_CLERK_ID` | Step 2.3 above |
| `POSTGRES_*`, `MINIO_*`, `SMOCKER_*` | Defaults work for local dev; change only if you have port conflicts |
| `EXTERNAL_*_BASE_URL` | Only needed when you introduce an external upstream in EPIC 02+; leave commented for now |

**`.env` is gitignored** — never commit secrets. Only `.env.example` is tracked.

---

## 4. First local boot — what actually works before EPIC 00

On a fresh fork, **there is no Go code and no Next.js code yet** — `backend/` and `frontend/` are README-only directories describing what EPIC 00 will produce. So most `make` targets are documented stubs, not runnable yet.

```bash
# What works now:
make infra-up-test      # Starts postgres + minio + smocker containers ✓
make infra-down         # Stops them ✓

# What fails now (on purpose — will work after Phase C / EPIC 00):
make dev                # No backend binary yet
make dev-test           # Same
make test-back          # No go.mod yet → "go: no module found"
make test-venom         # Backend isn't running, no venom suite yet
make test-e2e-mocked    # No frontend, no Playwright config wired yet
make test-e2e           # Same + requires real Clerk
```

This is expected. The whole point of Phase C is to produce all the code these commands need. Do NOT try to bypass it by writing code yourself — the purpose of running Team Lead on EPIC 00 is to validate that **the agents work in your environment** (your Clerk keys, your Postgres, your docker setup). If you hand-write the bootstrap, you skip that validation.

If `make infra-up-test` works and `docker compose ps` shows three healthy containers (`postgres`, `minio`, `smocker`), Phase B is complete. Move to Phase C (section 5).

---

## 5. Ship EPIC 00 via Team Lead

EPIC 00 (see [`delivery/epics/epic-00/`](delivery/epics/epic-00/)) is **4 skeleton stories** ready to be implemented. Each one runs through the Team Lead pipeline autonomously.

In a **fresh Claude Code session** (not the one you used for BMad if any):

```bash
claude --agent kiat-team-lead
```

Then, one story at a time:

```
Run the full pipeline on delivery/epics/epic-00/story-01-backend-skeleton.md
```

Team Lead will:
1. Enter **Phase -1** because the story's technical sections are empty — spawn `kiat-tech-spec-writer` to fill them.
2. Run **Phase 0a** (spec validation) and **0b** (context budget check).
3. Launch `kiat-backend-coder` — produces Go code + Venom tests.
4. Launch `kiat-backend-reviewer` — verdict.
5. Fix/arbitrate cycles within the 45-min fix budget.
6. Emit a rollup event to `delivery/metrics/events.jsonl`.

Repeat for `story-02` (frontend), `story-03` (E2E harness), `story-04` (CI pipeline).

**Expected outcome after all 4 stories pass:** `make ci-local` is green, `make dev-test` runs a working app in your browser, and you can sign in / CRUD items / log out.

### 5.1. Limits — what Team Lead can't do in this phase

Team Lead produces code; it does NOT:
- Click dashboards — you've done Clerk above, you'll do GCP + GitHub secrets below.
- Push to GitHub (no repo URL known yet) — you do that at step 7.
- Validate end-to-end E2E with real Clerk in CI — that requires the GitHub secrets (step 6).

For the duration of EPIC 00, the real-backend Playwright specs are allowed to be marked `test.skip` with a comment linking back to this doc. You unskip them after step 6. This is explicitly fine; `make test-e2e-mocked` is the CI gate until then.

---

## 6. GitHub Environment secrets (for CI)

CI needs Clerk credentials + (optionally, if you use GCP deployment) a GCP service account key.

### 6.1. Create the GitHub environment

1. Go to your GitHub repo → **Settings → Environments → New environment** → name it `ci`.
2. Add these secrets:

| Secret | Value |
|---|---|
| `CLERK_SECRET_KEY` | Same as `.env` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Same as `.env` |
| `E2E_USER_A_EMAIL`, `E2E_USER_A_PASSWORD`, `E2E_USER_A_CLERK_ID` | Same as `.env` |
| `E2E_USER_B_EMAIL`, `E2E_USER_B_PASSWORD`, `E2E_USER_B_CLERK_ID` | Same as `.env` |
| `GCP_PROJECT_ID` | Step 6.2 below (only if deploying) |
| `GCP_SA_KEY` | Step 6.2 below (only if deploying) |

The `ci` environment name is referenced by `.github/workflows/ci.yml` (produced by EPIC 00 story-04).

### 6.2. GCP project (optional — skip if not deploying yet)

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com). Note the project ID.
2. Enable APIs: Cloud Run, Artifact Registry, Cloud SQL (if using managed Postgres).
3. Create a service account `kiat-ci-deployer` with roles: `roles/run.admin`, `roles/artifactregistry.writer`, `roles/iam.serviceAccountUser`.
4. Generate a JSON key for the service account. Copy the whole JSON into `GCP_SA_KEY` secret (GitHub handles multiline).
5. Add `GCP_PROJECT_ID` as a plain string secret.

Deployment workflow in `.github/workflows/deploy.yml` is out of scope for EPIC 00 story-04; add it in EPIC 02+ when you're ready.

---

## 7. First push + CI green

```bash
# You may want to squash the EPIC 00 commits or keep them as-is.
git log --oneline

# If the remote isn't set yet:
git remote add origin git@github.com:<you>/<your-project>.git

git push -u origin main
```

Go to your GitHub repo → **Actions** tab. Watch `ci.yml` run:
- Go test job
- Venom job (docker-compose-backed)
- Playwright job (docker-compose + Smocker + real Clerk)

**If all green**, congrats — you're at the "EPIC 00 done" baseline. A collaborator can now fork your fork and start shipping features on top.

**If red**, common causes in order of likelihood:
- `CLERK_SECRET_KEY` not set in the `ci` environment (tests fail at setup)
- `playwright-ci` JWT template missing in Clerk dashboard (Playwright tests 401)
- E2E test users not created or wrong IDs (`Clerk session id missing` in global.setup logs)

---

## 8. Handoff to your client

Once kiat-getting-started is done:
- Send your collaborator the repo URL and point them to [`kiat-how-to.md`](kiat-how-to.md) — they'll see the two-persona workflow and can start a BMad session immediately to describe their domain.
- They never need to touch Clerk, GCP, or GitHub settings unless they're also the tech lead.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `make infra-up-test` hangs on smocker | Port `8101` conflict — another Smocker instance? `docker ps` / change `SMOCKER_ADMIN_PORT` in `.env`. |
| Playwright global.setup errors "Clerk session id missing" | `@clerk/testing` couldn't sign in — password wrong? User not verified? Check Clerk dashboard → the user must be in "Active" state. |
| `make test-e2e` backend logs show "401 Unauthorized" despite Playwright sign-in | JWT swap failed. Verify `playwright-ci` template exists in Clerk dashboard with lifetime 3600. |
| CI fails at `go test ./...` on a clean run | Probably a lint/vet issue — reproduce locally with `make test-back`. |
| CI fails intermittently at Clerk step | Clerk rate limits on rapid pushes (PC04). Wait 15-30 min, re-run via `workflow_dispatch`. |
| Backend startup `FATAL: ENABLE_TEST_AUTH must be false in production` | GOOD — the guard fired. Remove `ENABLE_TEST_AUTH` from the production environment's secrets. |

For deeper issues: open an issue on `github.com/sopial42/kiat`.
