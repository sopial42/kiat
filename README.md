# Kiat — Agent-First SaaS Starter

> Fork this repo. Your clients describe their domain via **BMad**, you ship the code via **`kiat-team-lead`** (which orchestrates a pipeline of spec-writer, parallel backend/frontend coders, and reviewers). Stack: Go + Gin + Bun backend, Next.js + Clerk frontend, Postgres + RLS, Playwright + Venom tests, Smocker for external API mocks, GitHub Actions CI.

---

## What you get when you fork

**Specs + stories + scaffolding + working agents.** NOT compiled code. The `backend/` and `frontend/` directories are skeleton READMEs — the actual Go and Next.js source is produced on your fork, by Kiat's own agents, when you run them for the first time (Phase C below).

This is intentional: each fork gets **fresh code produced by the same pipeline the forker will use for every subsequent feature**. Running EPIC 00 on day 1 validates that the pipeline works end-to-end in your environment (your Clerk instance, your GCP, your CI). If the agents can't ship EPIC 00, they can't ship EPIC 02 either — better to discover that on day 1.

---

## The two personas

Every Kiat repo is a shared workspace between two roles, each with its own entry point and its own folder:

| You are the… | You interact via… | You write in… |
|---|---|---|
| **Client / Product owner** | BMad (any Claude Code session invoking `bmad-*` skills) | `delivery/business/` + the `## Business Context` section of each story |
| **Tech Lead** | `kiat-team-lead` (`claude --agent kiat-team-lead`) | Nothing directly — Team Lead spawns writer + coders + reviewers |

**Why this split**: the business layer and the technical layer evolve on different clocks and with different authors. Collapsing them into one document turns every edit into a merge conflict between people who shouldn't be merging. Folder-level contracts ([`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md)) keep each persona in their lane.

Humans **never** invoke `kiat-tech-spec-writer` or the coders directly. Team Lead is the single entry point for every technical request.

---

## Quick start — the 5 phases

```
Phase A   — Fork & clone                    (~2 min)
Phase A.5 — Install pinned Claude skills    (~30 sec — REQUIRED before any agent run)
Phase B   — Credentials setup               (~30–45 min, human only — detailed in kiat-getting-started.md)
Phase C   — Run Team Lead on EPIC 00        (~2–4 hours of pipeline, mostly automated)
Phase D   — Run Team Lead on EPIC 01        (~30–60 min, walkthrough of the full loop)
   → after D, you're ready for real EPIC 02+ business stories via BMad
```

### Phase A — Fork & clone

```bash
git clone git@github.com:<you>/kiat.git && cd kiat
```

### Phase A.5 — Install pinned Claude Code skills

Some agent skills are **not committed** to this repo — they live upstream (Trail of Bits, Clerk, etc.) and are pulled at the exact SHA pinned in `skills-lock.json`. This keeps Kiat clear of vendored third-party code while still guaranteeing reproducibility: the lock file records both the source SHA *and* a SHA-256 hash of the resulting directory, so any tampered upstream is caught at install time.

```bash
make install-claude-skills
```

**What it does**: reads `skills-lock.json`, fetches each declared skill at the pinned commit, copies the relevant subpath into `.claude/skills/<name>/`, and verifies the SHA-256 of the installed dir matches the lock. Idempotent — safe to re-run.

**Run it**:
- Once after every fresh clone (before launching any Kiat agent — coders and reviewers expect these skills to be present).
- After every `git pull` that bumps `skills-lock.json`.
- Before opening a PR locally — `make check-claude-skills` is the CI-equivalent gate that fails on missing or drifted skills.

**Currently pinned** (see `skills-lock.json` for the authoritative list): `differential-review` and `sharp-edges` from [trailofbits/skills](https://github.com/trailofbits/skills) — security-focused skills. `differential-review` is loaded conditionally by `kiat-backend-reviewer` at review time; `sharp-edges` is loaded by `kiat-backend-coder` at build time when the story's `## Skills` section lists it. The Clerk skills (`clerk-backend-api`, `clerk-custom-ui`, `clerk-nextjs-patterns`, `clerk-testing`) are still committed for now; their lock-file entries record an integrity hash but no `ref` — they will migrate to install-on-demand in a future change.

### Phase B — Credentials setup

Clerk dev instance + `playwright-ci` JWT template + test users + `.env` + (optionally) GCP project + GitHub Environment secrets. **This is the only part Kiat's agents cannot do for you** — third-party dashboards need human hands.

Full walkthrough: [`kiat-getting-started.md`](kiat-getting-started.md).

### Phase C — Ship EPIC 00 via Team Lead

In a fresh Claude Code session at the repo root:

```bash
claude --agent kiat-team-lead
```

Then, one story at a time:

```
Run the full pipeline on delivery/epics/epic-00/story-01-backend-skeleton.md
```

Repeat for `story-02` (frontend), `story-03` (Playwright harness), `story-04` (CI workflow). Team Lead spawns `kiat-tech-spec-writer` at Phase -1 for each story (technical sections are empty — they get filled), then backend and/or frontend coders in parallel, then reviewers, test gates, rollup event.

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

## The pipeline (Team Lead + sub-agents)

Tech lead humans only ever talk to **Team Lead**. Team Lead spawns everything else.

```
┌──────┐   ┌───────────────┐    Phase -1 (if informal or missing tech layer)
│ User ├──►│  Team Lead    ├──────────────────────────────────┐
└──────┘   └───────────────┘                                  │
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │ kiat-tech-spec-writer│
                                                   │ • enriches story     │
                                                   │ • runs kiat-validate │
                                                   │ • returns SPEC_HANDOFF│
                                                   └──────────┬───────────┘
                                                              │
              Phase 0a diff-check + 0b budget + 0c queue overlap
                                                              ▼
                           Phase 1 — launch coders in parallel
                             ┌───────────────┐     ┌───────────────┐
                             │backend-coder  │     │frontend-coder │
                             └───────┬───────┘     └───────┬───────┘
                                     │                     │
                              Phase 3 — tests + handoff     │
                                     ▼                     ▼
                             ┌───────────────┐     ┌───────────────┐
                             │backend-review │     │frontend-review│
                             └───────┬───────┘     └───────┬───────┘
                                     └──────────┬──────────┘
                                                ▼
                        Phase 4 — parse VERDICT (3-way: APPROVED / NEEDS_DISCUSSION / BLOCKED)
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
                  APPROVED                BLOCKED                 NEEDS_DISCUSSION
                       │                  back to coder           Team Lead arbitrates
                       ▼                                                  │
                  Phase 5 validation                                      │
                       │                                                  │
                       ▼                                                  ▼
               Phase 5b/c/d closeout                          Phase 6 rollup emission
```

The full procedure is split into 7 stage files under `.claude/agents/team-lead/` — each loaded on demand by Team Lead, not pre-loaded. The orchestrator entry point is [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md).

| Stage | What Team Lead does |
|---|---|
| **Intake** | Solo-mode eligibility, clean working tree gate, reconciliation pre-launch |
| **Spec authoring** | Spawn tech-spec-writer (if story lacks technical layer) under prompt-hygiene rules |
| **Validation** | Spec diff-check, queue scope-overlap, pre-flight context budget |
| **Delivery** | Scope story, launch coders in parallel, test feedback loop |
| **Review** | Parse 3-way verdicts (APPROVED / BLOCKED / NEEDS_DISCUSSION), arbitrate, append Review Log |
| **Closeout** | Pitfall capture, deviations companion file, reconciliation notification |
| **Ship** | Commit guard, integration test gate, rollup write+verify, final status, reconciliation guard |

### The 3-way verdict protocol (why it matters)

Reviewers emit exactly one verdict on line 1:

| Verdict | Meaning | Team Lead's action |
|---|---|---|
| `APPROVED` | Ship it | Move to Phase 5 |
| `BLOCKED` | Concrete issues a coder can fix | Batch issues, send back, start fix cycle |
| `NEEDS_DISCUSSION` | Judgment call a coder can't resolve alone | **Team Lead arbitrates** — override if pattern is documented, escalate to writer / user / designer if not. Never bounce to coder as "fix this". |

The BLOCKED vs NEEDS_DISCUSSION distinction is **load-bearing** — it's what prevents infinite review loops on judgment calls.

---

## Your first real feature — after EPIC 00 and EPIC 01

Once Phases A-D are done, every new feature follows this loop:

1. **Capture the domain with BMad** — in a Claude Code session at the repo root, run a BMad skill (`bmad-product-brief`, `bmad-create-epics-and-stories`, `bmad-create-story`…). BMad writes to `delivery/business/` (glossary, personas, rules) and creates stories in `delivery/epics/epic-NN/story-NN-slug.md`, populating only the `## Business Context` section.
2. **Hand off to Team Lead** — close the BMad session, relaunch with `claude --agent kiat-team-lead`, and point it at the new story file. Team Lead enters Phase -1 (spawns `kiat-tech-spec-writer` to enrich the story with technical sections), then launches backend + frontend coders in parallel, reviewers, test gates.
3. **Watch the pipeline run** — Team Lead streams its phase log. At the end you get either `story_rollup: passed` or an escalation for you to resolve.
4. **Run locally, verify, commit** — `make dev` to poke the feature in a browser, `make ci-local` to run the full gate, then push. CI green on GitHub → ready to ship.

This is the loop for every story from EPIC 02 onwards. EPIC 00 (infra) and EPIC 01 (learning walkthrough) were one-time events to prove the agents work in your environment.

---

## Linking a visual reference to a story

Stories that involve UI carry a `### Mockups` sub-section under `## Business Context`. **If a visual reference exists (a live Figma URL OR static screenshots), it's the binding reference.** Tech-spec-writer does NOT restate visual decisions in the spec — it links. Frontend-coder matches pixel-close. Deviations (rendering constraints, accessibility, existing primitives) are discussed, never decided unilaterally.

Two valid shapes, pick one per story:

**Shape A — Live Figma URL** (preferred when the designer maintains it actively)

```markdown
### Mockups

- [Navbar — collapsed](https://figma.com/file/XXX/...?node-id=1)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=2)
```

URLs only. **Never check in PNG/SVG exports alongside a live Figma** — they go stale silently when the designer updates, and they bloat the repo.

**Shape B — Static screenshots** (when there's no active Figma, or the client doesn't use Figma)

```markdown
### Mockups

- ![Navbar — collapsed](../../business/mockups/story-NN/navbar.png)
- ![Edit profile modal](../../business/mockups/story-NN/modal.png)
```

Files under `delivery/business/mockups/story-NN/` — the only place binary design assets belong in this repo.

**One shape per story, never both** (avoids drift between a live Figma and cached PNGs).

If no visual reference exists, write `No mockups — implementer uses the existing design system`. The frontend-coder will use Shadcn primitives with default Tailwind and not invent a visual direction.

**EPIC 00 scaffold is design-neutral by construction.** No custom layout, no palette, no typography decisions. This leaves the canvas blank so your first visual reference — whenever it arrives — doesn't have to fight an existing design. The design system spec [`delivery/specs/design-system.md`](delivery/specs/design-system.md) describes the **protocol** for defining tokens; values stay at Tailwind v4 defaults until a client brings their first design reference.

---

## Common questions

**Can I skip BMad and go straight to Team Lead?**
Yes — launch Team Lead with an informal request ("add feature X"), it'll enter Phase -1 and spawn tech-spec-writer which writes both layers. You lose the domain-knowledge capture in `delivery/business/`, so this is fine for refactors and infra stories, not ideal for net-new business features.

**Can I write stories by hand and skip tech-spec-writer?**
Yes — if a story has both `## Business Context` and the technical sections already populated, Team Lead skips Phase -1.

**What if a reviewer disagrees with a pattern documented in `delivery/specs/`?**
Team Lead overrides on `NEEDS_DISCUSSION` when the spec is authoritative. If the reviewer found a genuine gap, that's a spec bug — fix `delivery/specs/`, then the next story inherits the fix.

**What happens if the retry budget runs out?**
Team Lead escalates to the user (you) with the outstanding issues. You decide: accept the debt + merge, or allocate more time. No silent "retry forever" mode.

**Can I run two stories in parallel?**
In Kiat's current design, Team Lead runs one story at a time per session. Parallel stories need parallel Team Lead sessions on separate branches — possible but advanced.

---

## Where to dig deeper

| I want to understand… | Go to |
|---|---|
| The full agent pipeline (every phase, gate, audit line) | [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md) + the stage files under `.claude/agents/team-lead/` |
| BMad modes (Explore / Capture / Plan / Review) | [`delivery/business/README.md`](delivery/business/README.md) |
| Clean Architecture, API conventions, DB migrations, RLS | [`delivery/specs/README.md`](delivery/specs/README.md) |
| Clerk auth flows (real + test-auth bypass + JWT swap for Playwright) | [`delivery/specs/clerk-patterns.md`](delivery/specs/clerk-patterns.md) |
| Playwright canonical patterns | [`delivery/specs/testing-playwright.md`](delivery/specs/testing-playwright.md) |
| Smocker mock patterns | [`delivery/specs/smocker-patterns.md`](delivery/specs/smocker-patterns.md) |
| Meta-rules for any Claude session in this repo | [`CLAUDE.md`](CLAUDE.md) |
| `.claude/` framework internals (for framework contributors) | [`.claude/README.md`](.claude/README.md) |

---

## Philosophy (one sentence each)

- **Spec before code.** A vague request is a bug.
- **One source of truth per rule.** If it's in `delivery/specs/X.md`, don't restate it in another doc or a prompt — link.
- **Context budget is finite.** Agents load only what the current task requires. A link in a doc is NOT an instruction to Read that file.
- **Audit trail over trust.** Required skills are invoked; the audit line in the output is the proof.
- **Scaffold teaches patterns, not aesthetics.** EPIC 00 is design-neutral; your Figma drives everything visual from EPIC 01+.

---

## Contributing back to Kiat

If you improve a framework-level rule (agent behaviour, skill, spec that applies beyond your project), open a PR against `github.com/sopial42/kiat`. Project-specific changes stay in your fork.
