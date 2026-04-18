# Kiat — Agent-First SaaS Starter

> Fork this repo. Your clients describe their domain via **BMad**, you ship the code via **`kiat-team-lead`** (which orchestrates a pipeline of spec-writer, parallel backend/frontend coders, and reviewers). Stack: Go + Gin + Bun backend, Next.js + Clerk frontend, Postgres + RLS, Playwright + Venom tests, Smocker for external API mocks, GitHub Actions CI.

---

## Where to start

Three files, read in this order:

| Doc | For what |
|---|---|
| **[`kiat-getting-started.md`](kiat-getting-started.md)** | One-time setup: Clerk dev instance, JWT template, GCP project, GitHub secrets, `.env`. ~30 min with all accounts ready. |
| **[`kiat-how-to.md`](kiat-how-to.md)** | Workflow: how BMad and the tech agents collaborate, how stories flow, how to ship your first feature. |
| **[`delivery/specs/`](delivery/specs/README.md)** | Technical conventions (architecture, auth, testing, CI, design-system). Read on demand when you start coding. |

If you only have 2 minutes, keep reading below.

---

## What you get when you fork

**Specs + stories + scaffolding + working agents.** NOT compiled code. The `backend/` and `frontend/` directories are skeleton READMEs — the actual Go and Next.js source is produced on your fork, by Kiat's own agents, when you run them for the first time (Phase C below).

This is intentional: each fork gets **fresh code produced by the same pipeline the forker will use for every subsequent feature**. Running EPIC 00 on day 1 validates that the pipeline works end-to-end in your environment (your Clerk instance, your GCP, your CI). If the agents can't ship EPIC 00, they can't ship EPIC 02 either — better to discover that on day 1.

## Quick start — the 4 phases

```
Phase A — Fork & clone                    (~2 min)
Phase B — Credentials setup               (~30–45 min, human only)
Phase C — Run Team Lead on EPIC 00        (~2–4 hours of pipeline, mostly automated)
Phase D — Run Team Lead on EPIC 01        (~30–60 min, walkthrough of the full loop)
   → after D, you're ready for real EPIC 02+ business stories via BMad
```

### Phase A — Fork & clone

```bash
git clone git@github.com:<you>/kiat.git && cd kiat
```

### Phase B — Credentials setup (follow `kiat-getting-started.md`)

Clerk dev instance + `playwright-ci` JWT template + test users + `.env` + (optionally) GCP project + GitHub Environment secrets. **This is the only part Kiat's agents cannot do for you** — third-party dashboards need human hands.

```bash
cp .env.example .env
# Fill Clerk keys, E2E user credentials, etc. per kiat-getting-started.md
```

### Phase C — Ship EPIC 00 via Team Lead

In a fresh Claude Code session at the repo root:

```bash
claude --agent kiat-team-lead
```

Then, one story at a time:

```
Run the full pipeline on delivery/epics/epic-00/story-01-backend-skeleton.md
```

Repeat for `story-02` (frontend), `story-03` (Playwright harness), `story-04` (CI workflow). Team Lead spawns `kiat-tech-spec-writer` at Phase -1 for each story (technical sections are empty — they get filled), then backend and/or frontend coders in parallel, then reviewers, test gates, 45-min fix budget, rollup event.

**After all 4 stories pass**: `make ci-local` green, `make dev-offline` boots a working app (sign-in / items CRUD / sign-out), `.github/workflows/ci.yml` exists. This is the "EPIC 00 done" baseline — the agents just proved they work in your environment.

### Phase D — Run Team Lead on EPIC 01

```
Run the full pipeline on delivery/epics/epic-01/story-01-edit-display-name.md
```

EPIC 01 is a **learning walkthrough** — a pre-written business story (navbar + edit your display name) that exercises the full BMad-to-production loop without requiring you to do any BMad work yet. After it passes, you've seen the pipeline produce a cross-layer feature from a complete spec. Delete the EPIC 01 folder if you don't want the demo feature, or keep it as reference.

### Runtime modes (after Phase C ships the code)

Two families: **dev loops** (you iterate in a browser) and **test suites** (automated, CI-equivalent). Two axes vary: auth + external API source.

**Dev loops** — you in a browser, iterating on UI or API:

| Mode | Auth | External APIs | When to use |
|---|---|---|---|
| `make dev` | Real Clerk | Real upstreams | Preview with real credentials before shipping |
| `make dev-offline` | Test-auth bypass | Smocker | Fast iteration without internet / Clerk round-trip |

**Test suites** — automated, no browser, one-shot runs:

| Mode | Auth | External APIs | What it runs |
|---|---|---|---|
| `make test-back` | — | In-process Go fakes | Go unit tests (colocated `*_test.go`) |
| `make test-venom` | Test-auth bypass | Smocker | Backend HTTP contract suite (Venom YAML) |
| `make test-e2e-mocked` | Real Clerk | `page.route()` mocks | Playwright, frontend isolated |
| `make test-e2e` | Real Clerk | Smocker | Playwright, full stack (CI-equivalent) |

---

## The two personas

Every Kiat repo is a shared workspace between two roles:

| You are the… | You interact via… | You write in… |
|---|---|---|
| **Client / Product owner** | BMad (any Claude Code session invoking `bmad-*` skills) | `delivery/business/` + the `## Business Context` section of each story |
| **Tech lead** | `kiat-team-lead` (`claude --agent kiat-team-lead`) | Nothing directly — Team Lead spawns writer + coders + reviewers |

Folder-level contracts (see [`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md)) keep each persona in their lane.

Humans **never** invoke `kiat-tech-spec-writer` or the coders directly. Team Lead is the single entry point for every technical request.

---

## Your first real feature — after EPIC 00 and EPIC 01

Once Phases A-D above are done, you're in the state where every new feature follows this loop:

1. **Capture the domain with BMad** — in a Claude Code session at the repo root, run a BMad skill (`bmad-product-brief`, `bmad-create-epics-and-stories`, `bmad-create-story`…). BMad writes to `delivery/business/` (glossary, personas, rules) and creates stories in `delivery/epics/epic-NN/story-NN-slug.md`, populating only the `## Business Context` section.
2. **Hand off to Team Lead** — close the BMad session, relaunch with `claude --agent kiat-team-lead`, and point it at the new story file. Team Lead enters Phase -1 (spawns `kiat-tech-spec-writer` to enrich the story with technical sections), then launches backend + frontend coders in parallel, reviewers, test gates.
3. **Watch the pipeline run** — Team Lead streams its phase log. At the end you get either `story_rollup: passed` or an escalation for you to resolve.
4. **Run locally, verify, commit** — `make dev` to poke the feature in a browser, `make ci-local` to run the full gate, then push. CI green on GitHub → ready to ship.

This is the loop for every story from EPIC 02 onwards. EPIC 00 (infra) and EPIC 01 (learning walkthrough) were one-time events to prove the agents work in your environment.

---

## Linking a visual reference to a story

Stories that involve UI carry a `### Mockups` sub-section under `## Business Context`. The rule is tight:

**If a visual reference exists (a live Figma URL OR static screenshots), it's the binding reference.** Tech-spec-writer does NOT restate visual decisions in the spec — it links. Frontend-coder matches pixel-close. Deviations (rendering constraints, accessibility, existing primitives) are discussed, never decided unilaterally.

Two valid shapes, pick one per story:

### Shape A — Live Figma URL (preferred when the designer maintains it actively)

```markdown
### Mockups

- [Navbar — collapsed](https://figma.com/file/XXX/...?node-id=1)
- [Navbar — user menu open](https://figma.com/file/XXX/...?node-id=2)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=3)
```

URLs only. **Never check in PNG/SVG exports alongside a live Figma** — they go stale silently when the designer updates, and they bloat the repo.

### Shape B — Static screenshots (when there's no active Figma, or the client doesn't use Figma)

```markdown
### Mockups

- ![Navbar — collapsed](../../business/mockups/story-01/navbar-collapsed.png)
- ![User menu — open](../../business/mockups/story-01/user-menu-open.png)
- ![Edit profile modal](../../business/mockups/story-01/edit-modal.png)
```

Files live under `delivery/business/mockups/story-NN/` — the only place binary design assets belong in this repo. When screenshots ARE the reference (frozen design, no live Figma), they can't "go stale" because they ARE the source of truth.

**One shape or the other per story, never both** (avoids drift between a live Figma and cached PNGs).

### When no visual reference exists

Write `No mockups — implementer uses the existing design system`. The frontend-coder will use Shadcn primitives with default Tailwind and not invent a visual direction.

**EPIC 00 scaffold is design-neutral by construction.** No custom layout, no palette, no typography decisions. This leaves the canvas blank so your first visual reference — whenever it arrives — doesn't have to fight an existing design. See `kiat-how-to.md` → "Scaffold teaches patterns, not aesthetics".

---

## Where to dig deeper

| I want to understand… | Go to |
|---|---|
| The full agent pipeline (Phase -1, 0a, 0b, coders, reviewers, 45-min fix budget, Phase 7 prod smoke) | [`kiat-how-to.md`](kiat-how-to.md) + [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md) |
| BMad modes (Explore / Capture / Plan / Review) | [`kiat-how-to.md`](kiat-how-to.md) + [`delivery/business/README.md`](delivery/business/README.md) |
| Clean Architecture, API conventions, DB migrations, RLS | [`delivery/specs/README.md`](delivery/specs/README.md) |
| Clerk auth flows (real + test-auth bypass + JWT swap for Playwright) | [`delivery/specs/clerk-patterns.md`](delivery/specs/clerk-patterns.md) |
| Playwright canonical patterns (global.setup, real-backend specs, fixtures) | [`delivery/specs/testing-playwright.md`](delivery/specs/testing-playwright.md) |
| Smocker (the one mock pattern for external APIs) | [`delivery/specs/smocker-patterns.md`](delivery/specs/smocker-patterns.md) |
| Meta-rules for any Claude session in this repo | [`CLAUDE.md`](CLAUDE.md) |

---

## Philosophy (one sentence each)

- **Spec before code.** A vague request is a bug.
- **One source of truth per rule.** If it's in `delivery/specs/X.md`, don't restate it in another doc or a prompt — link.
- **Context budget is finite.** Agents load only what the current task requires.
- **Audit trail over trust.** Required skills are invoked; the audit line in the output is the proof.
- **Scaffold teaches patterns, not aesthetics.** EPIC 00 is design-neutral; your Figma drives everything visual from EPIC 01+.

---

## Contributing back to Kiat

If you improve a framework-level rule (agent behaviour, skill, spec that applies beyond your project), open a PR against `github.com/sopial42/kiat`. Project-specific changes stay in your fork.
