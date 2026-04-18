# Kiat — How To

How the agents collaborate, how BMad captures domain knowledge, how the business/tech cycle flows, how to bring a visual reference. Read this once after `kiat-getting-started.md` — it's the rulebook for every feature you'll ship on top of Kiat.

---

## 1. The two personas (recap)

Two roles share this repo, each with its own entry point and its own folder:

```
┌──────────────────────────┐      ┌──────────────────────────┐
│  Client / Product owner  │      │       Tech Lead          │
│                          │      │                          │
│  Entry: Claude Code      │      │  Entry: Claude Code      │
│  running bmad-* skills   │      │  launched as             │
│                          │      │  `--agent kiat-team-lead`│
│                          │      │                          │
│  Writes:                 │      │  Orchestrates (but does  │
│   • delivery/business/   │      │   NOT directly touch):   │
│   • ## Business Context  │      │   • spec-writer          │
│     of stories           │      │   • backend + frontend   │
│                          │      │     coders               │
│  Never touches           │      │   • reviewers            │
│   delivery/specs/        │      │                          │
│   .claude/               │      │  Touches:                │
│   technical sections     │      │   • delivery/epics/ (tech │
│                          │      │     sections)            │
│                          │      │   • .claude/metrics/     │
└──────────────────────────┘      └──────────────────────────┘
```

**Why this split**: the business layer and the technical layer evolve on different clocks and with different authors. Collapsing them into one document turns every edit into a merge conflict between people who shouldn't be merging. Folder-level contracts ([`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md)) keep each persona in their lane.

---

## 2. BMad — the business-side agent

BMad is **external to Kiat** (any Claude Code session invoking `bmad-*` skills acts as BMad). It has no dedicated `.claude/agents/` file. Kiat provides folder-level contracts that govern exactly what BMad is allowed to write, where.

### BMad's 4 input modes

| Mode | Trigger phrase | Writes to |
|---|---|---|
| **Explore** | "help me think through X", "I'm not sure yet" | Nothing — think out loud, converge toward Capture or Plan |
| **Capture** | "note that personas are…", "the business rule is…" | `delivery/business/` — glossary, personas, business-rules, domain-model, user-journeys |
| **Plan** | "next story", "prochain epic", "we'll build X" | `delivery/epics/` — creates `_epic.md` / `story-NN-slug.md`, writes **only** the `## Business Context` section |
| **Review** | "does this spec make sense?", "check my work" | Nothing — audit-only, surface inconsistencies |

### Before writing anything

Every BMad session that may write to `delivery/business/` or a story's `## Business Context` **must first list `delivery/business/` and read every non-empty `.md` in it**. Prevents contradicting or duplicating facts captured earlier. See the BMad writing protocol in [`delivery/business/README.md`](delivery/business/README.md) for the full rules.

### What BMad never does

- Writes SQL schemas, API paths, React component names, test framework references
- Touches `delivery/specs/`, `.claude/`, or any technical section of a story
- Invokes `kiat-tech-spec-writer`, `kiat-team-lead`, or any coder / reviewer directly

If BMad finds itself typing `CREATE TABLE` or `POST /api/...`, that's a protocol violation — stop, undo, escalate.

---

## 3. The tech-side pipeline (Team Lead + sub-agents)

Tech lead humans only ever talk to **Team Lead**. Team Lead spawns everything else.

### The shape

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
              Phase 0a diff-check + Phase 0b budget           │
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
                             │ + clerk-auth  │     │ + clerk-auth  │
                             │   (conditional)│     │   (conditional)│
                             └───────┬───────┘     └───────┬───────┘
                                     └──────────┬──────────┘
                                                ▼
                        Phase 4 — parse VERDICT (3-way: APPROVED / NEEDS_DISCUSSION / BLOCKED)
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
                  APPROVED                BLOCKED                  NEEDS_DISCUSSION
                       │                 fix budget                 Team Lead
                       │                 45 min wall                arbitrates
                       ▼                     │                         │
                  Phase 5 validation          └──► back to coder ──┐    │
                       │                                          │    │
                       ▼                                          ▼    ▼
               Phase 5b pitfall capture       Phase 6 rollup emission
                       │
                       ▼
               Phase 7 prod smoke (for prod-affecting stories)
```

### The phases, one line each

| Phase | What Team Lead does |
|---|---|
| -1 | Spec authoring — spawn tech-spec-writer if the story lacks the technical layer |
| 0a | Spec validation / diff-check — trust writer's `CLEAR` verdict if file unchanged |
| 0b | Pre-flight context budget — hard gate, no coder starts oversized |
| 1 | Scope (backend / frontend / both) |
| 2 | Launch coders in parallel (single message, two Agent calls) |
| 3 | Test feedback loop — coders report back with `TEST_PATTERNS: ACKNOWLEDGED` |
| 4 | Reviewer verdict merge — BLOCKED > NEEDS_DISCUSSION > APPROVED |
| 5 | Validate story against acceptance criteria |
| 5b | Pitfall capture if >15min of fix budget was burned on tests |
| 6 | Rollup event written + verified (hard exit gate) |
| 7 | Prod smoke validation for prod-affecting stories (MANDATORY) |

Full details in [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md) — that file is the source of truth. Do not restate its rules here.

### The 3-way verdict protocol (why it matters)

Reviewers emit exactly one verdict on line 1:

| Verdict | Meaning | Team Lead's action |
|---|---|---|
| `APPROVED` | Ship it | Move to Phase 5 |
| `BLOCKED` | Concrete issues a coder can fix | Batch issues, send back, start fix budget |
| `NEEDS_DISCUSSION` | Judgment call a coder can't resolve alone | **Team Lead arbitrates** — override if pattern is documented, escalate to writer / user / designer if not. Never bounce to coder as "fix this". |

The BLOCKED vs NEEDS_DISCUSSION distinction is **load-bearing** — it's what prevents infinite review loops on judgment calls.

### Retry budget — time-based, not cycle-based

45 minutes of coder wall-clock time per story for addressing reviewer feedback. Cycle counting fails in practice (teams hit "cycle 3" over typos). Wall clock is stricter and fairer. See [`.claude/specs/metrics-events.md`](.claude/specs/metrics-events.md) for how Team Lead tracks it.

---

## 4. The business ↔ tech cycle

A feature typically goes through 4 beats:

### Beat 1 — Business capture (BMad session)

Client or product owner opens a Claude Code session at the repo root. They articulate the domain with BMad Capture mode — personas, rules, glossary, user journeys — writing to `delivery/business/`. This happens rarely (once at project start, then on major domain shifts).

### Beat 2 — Story planning (BMad session, Plan mode)

Same or different BMad session. Mode: Plan. Creates a new story file at `delivery/epics/epic-NN/story-NN-slug.md` and writes **only** the `## Business Context` section — user story, personas impacted, user-facing acceptance criteria, business rationale, `### Mockups` (visual reference, see section 5 below).

### Beat 3 — Technical execution (Team Lead session)

Tech lead closes the BMad session, relaunches with `claude --agent kiat-team-lead`, and points at the story:

> Run the full pipeline on `delivery/epics/epic-NN/story-NN-slug.md`

Team Lead enters Phase -1, spawns tech-spec-writer (who adds technical sections preserving the Business Context intact), runs Phase 0a/0b, launches coders, reviewers. Ends with a rollup event.

### Beat 4 — Local validation + merge

Tech lead runs `make dev` or `make dev-test`, pokes the feature, runs `make ci-local` end-to-end, pushes. CI on GitHub verifies the same gate. Merge.

### What crosses the boundary

**From business to tech**: the `## Business Context` section (user-facing acceptance criteria, persona links, mockups).
**From tech to business**: nothing in the story file itself. But a `NEEDS_DISCUSSION` verdict can re-open a question for the product owner — e.g., "reviewer flagged ambiguity in AC-3, need clarification on the error state".

### What never crosses

- BMad never writes a SQL schema, an API path, a React component name.
- Coders never rewrite the `## Business Context` to match what they built. If there's a drift, escalate via `NEEDS_DISCUSSION`, let BMad resolve.

---

## 5. Visual references — Figma URLs or static screenshots

**The rule**: if a visual reference exists for a UI story, it's the binding reference. Tech-spec-writer does NOT restate visual decisions — it links. Frontend-coder matches pixel-close. Deviations (rendering constraints, accessibility, existing primitives) are discussed in the review, never decided unilaterally.

### Two valid shapes, one per story

**Shape A — Live Figma URL** (use when the designer actively maintains Figma)

```markdown
### Mockups

- [Navbar — collapsed](https://figma.com/file/XXX/...?node-id=1)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=2)
```

The Figma is the live source. Never checkin PNG/SVG exports alongside — they'll go stale.

**Shape B — Static screenshots** (use when there's no active Figma, or the client doesn't use Figma)

```markdown
### Mockups

- ![Navbar — collapsed](../../business/mockups/story-NN/navbar.png)
- ![Edit profile modal](../../business/mockups/story-NN/modal.png)
```

Files under `delivery/business/mockups/story-NN/` (the only place binary design assets belong in this repo). When screenshots ARE the reference, they can't go stale — they're the truth.

**One shape per story**, never mixed. Trying to maintain "Figma is truth, PNG is cached copy" drifts silently the first time the designer updates.

### How the frontend-coder uses it

1. Step 1 of the coder's workflow: read the story's `### Mockups` sub-section under `## Business Context`.
2. If a Figma URL is present, WebFetch it (Claude can see Figma public frames) or — if private — the coder flags that it needs Figma access and the tech lead shares an exported screenshot for the story.
3. If screenshots are present, the coder Reads them directly (Claude is multimodal).
4. If `No mockups`, the coder uses Shadcn primitives with default Tailwind, introduces no visual decision of its own.

### How the frontend-reviewer enforces it

When `### Mockups` contains references, the reviewer runs the app locally (or reads a Playwright trace screenshot), compares to the visual reference, and flags divergence as `BLOCKED` unless the implementation notes document the trade-off (e.g., "mockup shows a shadow we can't achieve with Tailwind defaults without custom config — using `shadow-md` approximation").

---

## 6. Scaffold teaches patterns, not aesthetics

EPIC 00 ships with **intentionally skeletal** UI:

- Shadcn primitives only (`<Button>`, `<Input>`, `<Card>`)
- Default Tailwind v4 values (no custom palette, no custom typography)
- No dashboard, navbar, sidebar, or navigation shell beyond what auth-gating requires
- No marketing / landing page design

**Why**: visual decisions are the MOST project-specific thing in a SaaS. If EPIC 00 imposed a dashboard layout with specific colors, the first forker bringing their Figma would either fight it or demolish it. Kiat avoids this by **leaving the canvas blank** — the scaffold teaches the technical patterns (auth wrapper hook, RSC boundary, optimistic update, real-backend test) but defers every visual choice to the first EPIC 01+ story that ships with a visual reference.

The design system spec [`delivery/specs/design-system.md`](delivery/specs/design-system.md) describes the **protocol** for defining tokens (colors, spacing, typography) — not the specific values. Values stay at Tailwind v4 defaults until a client brings their first design reference.

---

## 7. When to dig deeper

| I need to know… | Read |
|---|---|
| How Team Lead tracks the fix budget internally | [`.claude/specs/metrics-events.md`](.claude/specs/metrics-events.md) |
| How coders verify context budget pre-flight | [`.claude/specs/context-budgets.md`](.claude/specs/context-budgets.md) |
| What skills exist and when they get invoked | [`.claude/specs/available-skills.md`](.claude/specs/available-skills.md) |
| The full backend coder workflow (Step 0 to 5) | [`.claude/agents/kiat-backend-coder.md`](.claude/agents/kiat-backend-coder.md) |
| Same for frontend coder | [`.claude/agents/kiat-frontend-coder.md`](.claude/agents/kiat-frontend-coder.md) |
| The review checklists | [`.claude/skills/kiat-review-backend/`](.claude/skills/kiat-review-backend/) and [`/kiat-review-frontend/`](.claude/skills/kiat-review-frontend/) |

---

## 8. Common questions

**Can I skip BMad and go straight to Team Lead?**
Yes — launch Team Lead with an informal request ("add feature X"), it'll enter Phase -1 and spawn tech-spec-writer which writes both layers. You lose the domain-knowledge capture in `delivery/business/`, so this is fine for refactors and infra stories, not ideal for net-new business features.

**Can I write stories by hand and skip tech-spec-writer?**
Yes — if a story has both `## Business Context` and the technical sections already populated, Team Lead skips Phase -1. Useful when you want tight control over the spec.

**What if a reviewer disagrees with a pattern that's documented in delivery/specs/?**
Team Lead overrides on `NEEDS_DISCUSSION` when the spec is authoritative. If the reviewer genuinely found a gap in the spec itself, that's a spec bug — fix `delivery/specs/`, then the next story inherits the fix.

**What happens if fix budget runs out?**
Team Lead escalates to the user (you) with the outstanding issues. You decide: accept the debt + merge, or allocate more time. No silent "retry forever" mode.

**Can I run two stories in parallel?**
In Kiat's current design, Team Lead runs one story at a time per session. Parallel stories need parallel Team Lead sessions on separate branches — possible but advanced.
