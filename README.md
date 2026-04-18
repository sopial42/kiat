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

## Quick start

```bash
# 1. Fork + clone
git clone git@github.com:<you>/kiat.git && cd kiat

# 2. Set up secrets (see kiat-getting-started.md for how)
cp .env.example .env
# Fill Clerk keys, GCP SA key, etc.

# 3. Run the stack
make dev-test   # offline-capable: test-auth bypass + Smocker for external APIs
# OR
make dev        # real Clerk + real external upstreams (needs real credentials)

# 4. Verify everything passes
make test-back          # Go unit tests (no containers)
make test-venom         # Backend HTTP black-box against Smocker
make test-e2e-mocked    # Playwright mocked (fast)
make test-e2e           # Full stack: real backend + real Clerk + Smocker
```

Four modes, two axes (auth + external mocks):

| Mode | Auth | External APIs |
|---|---|---|
| `make dev` | Real Clerk | Real upstreams |
| `make dev-test` | Test-auth bypass | Smocker |
| `make test-venom` | Test-auth bypass | Smocker |
| `make test-e2e` | Real Clerk | Smocker |

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

## Your first feature — end-to-end in five steps

1. **Fork and set up** — follow [`kiat-getting-started.md`](kiat-getting-started.md).
2. **Capture the domain with BMad** — in a Claude Code session at the repo root, run a BMad skill (`bmad-product-brief`, `bmad-create-epics-and-stories`, etc.). BMad writes to `delivery/business/` (glossary, personas, rules) and creates stories in `delivery/epics/epic-NN/story-NN-slug.md`, populating only the `## Business Context` section.
3. **Hand off to Team Lead** — close the BMad session, relaunch with `claude --agent kiat-team-lead`, and point it at the new story file. Team Lead enters Phase -1 (spawns `kiat-tech-spec-writer` to enrich the story with technical sections), then launches backend + frontend coders in parallel, reviewers, test gates.
4. **Watch the pipeline run** — Team Lead streams its phase log. At the end you get either `story_rollup: passed` or an escalation for you to resolve.
5. **Run locally, verify, commit** — `make dev` to poke the feature in a browser, `make ci-local` to run the full gate, then push. CI green on GitHub → ready to ship.

A walkthrough story already exists at [`delivery/epics/epic-01/story-01-edit-display-name.md`](delivery/epics/epic-01/story-01-edit-display-name.md) — a business-neutral "edit your display name from the navbar" feature. Run Team Lead on it once to see the full pipeline produce working code. Then delete or adapt it for your first real feature.

---

## Linking a visual reference to a story

Stories that involve UI carry a `## Mockups` section under `## Business Context`. The rule is tight:

**If a visual reference exists (a live Figma URL OR static screenshots), it's the binding reference.** Tech-spec-writer does NOT restate visual decisions in the spec — it links. Frontend-coder matches pixel-close. Deviations (rendering constraints, accessibility, existing primitives) are discussed, never decided unilaterally.

Two valid shapes, pick one per story:

### Shape A — Live Figma URL (preferred when the designer maintains it actively)

```markdown
## Mockups

- [Navbar — collapsed](https://figma.com/file/XXX/...?node-id=1)
- [Navbar — user menu open](https://figma.com/file/XXX/...?node-id=2)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=3)
```

URLs only. **Never check in PNG/SVG exports alongside a live Figma** — they go stale silently when the designer updates, and they bloat the repo.

### Shape B — Static screenshots (when there's no active Figma, or the client doesn't use Figma)

```markdown
## Mockups

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
