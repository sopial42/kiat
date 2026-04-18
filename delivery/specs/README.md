# `delivery/specs/` — Technical Conventions

Single source of truth for **how code gets built** in this stack. One doc per concern, read on demand.

Agents (coders, reviewers, tech-spec-writer) load these files per their own routing logic — see each agent's frontmatter. Humans read them when they want to understand, modify, or extend a convention.

**Do not duplicate content across files.** If a rule exists in one doc, link to it from others; don't restate.

---

## What's in this folder

### Architecture

| File | Scope |
|---|---|
| [`architecture-clean.md`](architecture-clean.md) | Clean Architecture 4 layers (domain / application / infrastructure / interface), dependency direction rules |
| [`ARCHITECTURE-OVERVIEW.md`](ARCHITECTURE-OVERVIEW.md) | High-level stack overview, one-pager visual of the whole system |
| [`service-communication.md`](service-communication.md) | How services/layers talk to each other, dependency injection patterns |

### Backend

| File | Scope |
|---|---|
| [`backend-conventions.md`](backend-conventions.md) | Project structure, naming, error codes, logging |
| [`api-conventions.md`](api-conventions.md) | REST envelope shape, HTTP status codes, error format |
| [`database-conventions.md`](database-conventions.md) | Migration rules, RLS policies, timestamp columns, indexing |

### Frontend

| File | Scope |
|---|---|
| [`frontend-architecture.md`](frontend-architecture.md) | Next.js App Router, RSC boundary, hook patterns, client fetch discipline |
| [`design-system.md`](design-system.md) | Color/spacing/typography **protocol** — values stay at Tailwind v4 defaults until a visual reference arrives |

### Auth

| File | Scope |
|---|---|
| [`clerk-patterns.md`](clerk-patterns.md) | Real Clerk mode + test-auth bypass, JWT template setup, middleware placement, auth wrapper hook |

### Testing

| File | Scope |
|---|---|
| [`testing.md`](testing.md) | Test pyramid (70% Go unit / 20% Venom / 10% Playwright), CI gate, commands |
| [`testing-pitfalls-backend.md`](testing-pitfalls-backend.md) | Venom YAML pitfalls (VP01-VP08) and Go test rules (GS01-GS03); decisions TD01-TD07 |
| [`testing-playwright.md`](testing-playwright.md) | Canonical Playwright patterns — global.setup JWT swap, real-backend specs, fixtures structure |
| [`testing-pitfalls-frontend.md`](testing-pitfalls-frontend.md) | Playwright + Clerk footguns (PP01-PP15, PC01-PC07, UA01-UA03) |
| [`smocker-patterns.md`](smocker-patterns.md) | Universal external-API mocking via Smocker (dev-offline / Venom / E2E). Go unit tests use in-process fakes. |

### Operational

| File | Scope |
|---|---|
| [`security-checklist.md`](security-checklist.md) | OWASP top-10 gate, secrets management, RLS testing |
| [`deployment.md`](deployment.md) | Env vars, production guards, deployment targets |
| [`git-conventions.md`](git-conventions.md) | Branch model, commit message format, PR discipline |
| [`project-memory.md`](project-memory.md) | Emergent cross-story decisions captured as project-specific notes (grows over time) |

---

## When you need to add a new convention

Before creating a new file here, check: does the rule belong to one of the existing docs? Prefer extending over creating — this folder grows linearly and a proliferation of small files fragments context.

New file threshold: a convention that spans its own coherent topic (e.g., "queue-patterns" if you introduce a job queue) and is at least 300 lines of non-trivial content.

When in doubt, write it into `project-memory.md` first; promote to a dedicated file if it grows.

---

## Where this docs live in the pipeline

```
Story spec (delivery/epics/…) ──┐
                                ├──► tech-spec-writer reads relevant specs on demand
                                │    to write the story's technical sections
CLAUDE.md ambient context ──────┤
                                ├──► coders read relevant specs on demand
                                │    during implementation
Agent frontmatter (auto-load) ──┤
                                └──► reviewers cross-check implementation against specs
```

Each agent's `## Read the minimum necessary context` step is the authoritative list of "when to read which file". See [`.claude/agents/`](../../.claude/agents/).

---

## Ownership

Files here are **framework-owned** — the Kiat framework ships them as the starting stack conventions. A forked project can customize them, but the customizations are now **project-owned** and will diverge from upstream Kiat. If a customization is broadly useful, consider opening a PR against `github.com/sopial42/kiat`.

The business side (personas, domain rules, user journeys) lives in the sibling [`delivery/business/`](../business/) — BMad's territory, never overlaps with these specs.
