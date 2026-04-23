# Epics — The Backlog

This directory is the project's **Jira-equivalent**: every epic and every story lives here. It is the single source of truth for "what are we going to build next" and "what did we build".

Sibling folder: [`../business/`](../business/) holds the evergreen business knowledge (glossary, personas, domain model, etc.) that stories reference. If an epic or story mentions a persona, a domain term, or a business rule, the definition of that concept lives in `../business/` — the epic/story only links to it.

---

## The two-layer story model

Every epic and every story file has **two layers written by two different authors**:

| Layer | Author | What's in it | When it's written |
|---|---|---|---|
| **Business Context** (top of the file) | **BMad** | User story, personas impacted, user-facing acceptance criteria, links to `../business/`, business rationale | When the product direction is being shaped |
| **Technical sections** (below) | **`kiat-tech-spec-writer`** | Skills, Backend / API contracts, Frontend / Components, Database, Edge cases, Test scenarios, Out of scope | When the team is ready to turn the story into code |

**One file per artifact, two layers, two authors.** The file evolves from "raw business need" → "ready to code" without ever being split. The tech-spec-writer reads the Business Context as its input and preserves it intact while appending the technical layers.

See the canonical templates in [`epic-template/`](epic-template/):
- [`_epic.md`](epic-template/_epic.md) — epic-level skeleton (both layers)
- [`story-NN-slug.md`](epic-template/story-NN-slug.md) — story-level skeleton (both layers)

Naming conventions (`epic-NN-slug`, `story-NN-slug.md`) and review file conventions are documented in [`../README.md`](../README.md#conventions). This README does **not** restate them — one source of truth per rule.

---

## BMad writing protocol (rules for Claude sessions acting as BMad)

This section governs what BMad writes **into `delivery/epics/`**. Rules for writing in `delivery/business/` live in [`../business/README.md`](../business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad). The two files are siblings — each folder owns the contract that governs it.

### The only mode that lands here

Of BMad's 4 input modes (Explore / Capture / Plan / Review — defined in the sibling README), **only `Plan` produces writes in this folder**.

- **Plan** — user says "on va construire X", "prochain epic", "prépare la prochaine story", "next story". BMad reads the relevant `../business/` docs (personas, glossary, business-rules) **before** proposing anything, then proposes an epic structure or a story placement inside an existing epic, and writes the `## Business Context` section only after green light.

Explore converges *into* Capture or Plan. Capture lands in `../business/`. Review writes nothing. See the sibling README for the full mode vocabulary.

### Slicing discipline

**Vertical slices by default.** Every story delivers a **user-observable increment end-to-end** (DB → API → UI → test when all three layers are involved), however thin. Not "all the backend, then all the frontend". Horizontal-by-layer decomposition is the most common LEAN anti-pattern and is disallowed unless the story explicitly fits one of the exceptions listed below.

**Why**: stacking a pure-backend story then a pure-frontend story on the same feature means hours or days elapse before anyone sees a working slice. Misinterpretations of the API contract surface at integration time — after the code is written — and trigger rework on both sides. Thin vertical slices invert this: each story is demoable, the feedback loop closes in hours not days, and each slice teaches the next one what to adjust.

#### Walking skeleton principle

In an epic with multiple stories on the same feature, **story 01 is the walking skeleton**: it carries a single data point from the user's click down to the database and back, with the minimum vital (one field, one happy path). Subsequent stories add **depth** (validation, edge cases, empty states, performance) — not **breadth** (other features). A user-visible demo exists at the end of story 01, however crude.

#### Demo check — the anti-horizontal gate

Every story's `### Acceptance criteria (user-facing)` must contain **at least one criterion observable by a non-technical viewer**. A criterion like "the user sees the updated name in the navbar" passes. A criterion like "`GET /users/me` returns the new name in the response body" does **not** pass — it's a technical contract, not a user observation.

If every user-facing AC reads like a technical assertion, the story is a horizontal slice in disguise and must be reshaped before coding begins. `kiat-validate-spec` Category 6 enforces this mechanically.

#### Two metadata fields on every story

Every story carries two header fields that make its slicing shape explicit:

| Field | Values | Meaning |
|---|---|---|
| `**Scope**` | `vertical-slice` *(default)* \| `backend-infra` \| `frontend-chrome` \| `infra` | Architectural shape of the slice |
| `**User signal**` | `direct` \| `indirect` \| `none` *(justify)* | Observable symptom the story produces |

The two are **orthogonal**: `Scope` describes the architectural shape, `User signal` describes the observable symptom. A `backend-infra` story that speeds up existing search is `User signal: indirect` (the user feels the change via existing UI). A `vertical-slice` story with `User signal: none` is a contradiction caught at spec validation.

- **`direct`** — the user sees, clicks, types, or receives something new
- **`indirect`** — effect observable in existing behavior (faster, more accurate, an edge case now handled gracefully) — requires a scenario to verify
- **`none`** — infra with no user-facing signal; landing verified via logs, metrics, or a downstream story

#### Legitimate exceptions — `Scope ≠ vertical-slice`

Non-default `Scope` values exist and are legitimate **when the work truly has no product-feature shape**. Any story that chooses a non-default `Scope` **must carry a one-line `**Scope justification**` next to the field** — unjustified exceptions are blocked at spec validation.

| Non-default `Scope` | Legitimate when… | Typical `User signal` |
|---|---|---|
| `backend-infra` | Background job, webhook receiver, service-to-service wiring, async pipeline without a UI counterpart in this story | `indirect` or `none` |
| `frontend-chrome` | Design system token, layout shell, shared navigation primitive without a new backend contract | `indirect` or `none` |
| `infra` | Bootstrap scaffolding (e.g., epic-00 skeleton stories), CI pipeline, migration script, DevOps tooling | `none` |

If you find yourself reaching for `backend-infra` because "the UI will come in the next story", **stop** — that's exactly the horizontal-by-layer pattern the rule forbids. Reshape as a vertical slice with one tiny UI touch, or split differently.

#### Anti-pattern gallery

| Anti-pattern | Why it fails LEAN | Prefer |
|---|---|---|
| "Implement the backend for feature X" (then story 02: "Build the UI for feature X") | Hours before any demo; integration bugs surface late | Thin slice DB→API→UI with one field; enrich in story 02 |
| "Wire the Playwright E2E suite" as a standalone story (outside bootstrap) | Tests are not a feature; they ship with each slice | Tests embedded in every vertical slice from story 01 onward |
| "Refactor before building the feature" | No user feedback, no signal the refactor was needed | Build the first slice; refactor when the second slice reveals the pattern |
| "Land the migration, land the API, land the UI" as 3 stories | Same horizontal anti-pattern, three stories deep | One vertical slice with minimum migration + minimum API + minimum UI |

#### Relationship with `### Target architecture`

`### Target architecture` below describes the **final state** of a shared artifact after all its stories land. The slicing discipline here describes **how we get there, slice by slice**. They cooperate: when an epic has ≥2 stories on the same feature, the `_epic.md` should carry both — `### Target architecture` for the destination, `#### Slicing plan` inside it for the step-by-step path. Neither replaces the other.

### The one section BMad writes

BMad writes **exclusively** the `## Business Context` section, in two places:

1. **`_epic.md`** → `## Business Context` — epic-level framing
2. **`story-NN-slug.md`** → `## Business Context` — story-level framing

Everything else in these files — `## Skills`, `## Acceptance Criteria (technical)`, Backend, Frontend, Database, API contracts, Edge cases, Testing Plan, Out of scope — is the **tech-spec-writer's territory**. If BMad finds itself typing a SQL schema, an HTTP path, a React component name, a test framework reference, or a file path under `backend/` or `frontend/`, **that is a protocol violation**. BMad stops, undoes, and escalates to the user.

### What goes inside `## Business Context`

**At the epic level** (`_epic.md`):

```markdown
## Business Context

> Section written by BMad. The tech-spec-writer MUST NOT modify this section.

### Outcome
[What user-visible change this epic aims to produce. One short paragraph.]

### Impacted personas
- [Persona 1] — see [`../../business/personas.md#<anchor>`](../../business/personas.md)

### Business hypotheses & risks
- [Hypothesis we're assuming — and how we'd know if it's wrong]
- [Risk that could make this epic fail to deliver its outcome]
```

**At the story level** (`story-NN-slug.md`):

```markdown
## Business Context

> Section written by BMad. The tech-spec-writer MUST NOT modify this section.

### User story
As [persona], I want [goal], so that [value].

### Acceptance criteria (user-facing)
- [ ] [User-observable criterion — no API paths, no SQL, no component names]
- [ ] [...]

### Linked business knowledge
- Persona: [`../../business/personas.md#<anchor>`](../../business/personas.md)
- Glossary terms: [`../../business/glossary.md#<term>`](../../business/glossary.md)
- Business rules: [`../../business/business-rules.md#<rule>`](../../business/business-rules.md)

### Business rationale
[1–3 sentences: why this need exists, what user pain it relieves, why now.]
```

The **user-facing acceptance criteria** that BMad writes are different from the **technical acceptance criteria** that the tech-spec-writer may add lower in the file. The user-facing ones are observable by the user ("I can see my items sorted by priority"); the technical ones are implementation-bound ("`GET /items?sort=priority` returns 200 with pagination headers").

**Exact section headers (do not rename):**

| Layer | Header in the file | Author |
|---|---|---|
| User-facing (inside `## Business Context`) | `### Acceptance criteria (user-facing)` | BMad |
| Technical (top-level, below `## Business Context`) | `## Acceptance Criteria (technical)` | tech-spec-writer |

Two different heading levels on purpose: the user-facing list is a sub-section of `## Business Context` (BMad's only sandbox), while the technical list is a peer of `## Backend`, `## Frontend`, etc. A story that drops the `(user-facing)` / `(technical)` suffix, or merges the two lists into one, is a two-layer boundary violation — stop and fix the structure before proceeding.

### Target architecture

**Rule in one line**: whenever **2 or more stories in the same epic touch the same artifact** (page, endpoint, shared component, table, service), the `_epic.md` MUST include a dedicated sub-section in `## Business Context` titled `### Target architecture` that describes the artifact's final state and its per-story evolution.

Backend work naturally decomposes into independent units: each endpoint, each fetcher, each migration lives in its own file with its own test suite, and stories can be written in isolation without losing context. **Frontend work does not decompose that way.** A page is built incrementally: story 01 creates the skeleton, story 02 adds multi-select, story 03 activates an export button — all on the same page, sharing the same state shape, the same layout, the same composable result sections. The writer who attacks story 01 without seeing where stories 02 and 03 will land makes architectural choices (state shape, layout, data flow) that have to be redone 1-2 stories later.

The same pattern applies to any artifact touched by multiple stories: a shared endpoint progressively enriched, a table extended across migrations, a shared component whose props grow story by story. Each affected story then carries a short `⚠️ Required reading before this story` pointer in its own Business Context, linking back to the epic's `### Target architecture`.

**What goes in `### Target architecture`** (user-facing / information architecture only — no code):

- **Final state of the shared artifact** — what zones, what links, what navigation, what composable blocks the user sees when all its stories have landed
- **Per-story evolution** — a one-liner per story: what each story adds or activates on the artifact (e.g., "story 01 establishes the skeleton with N inactive buttons; story 02 activates button X; story 03 activates button Y")
- **Primitives reused** from other parts of the codebase — point at the existing patterns the artifact will inherit (design system, shared layout chrome, shared endpoint envelope) so the tech-spec-writer does not reinvent
- **Implicit architectural constraints** — decisions story 01 must make to avoid rework, phrased in user-facing / structural terms (e.g., "the result zone must be a repeatable unit because story 02 will duplicate it N times", "the export button must be rendered from story 01 even if inactive, to avoid a visual re-layout in story 03")

**What does NOT go in this section** — still BMad's sandbox, still user-facing:

- No component names, no route paths, no framework-specific terms (Next.js App Router, React Context, Shadcn), no file paths
- No state-management library choice, no caching strategy — those are the tech-spec-writer's territory

**Per-story cross-reference** — every story belonging to the series carries, as the first line of its `## Business Context` blockquote, a pointer like:

```markdown
> ⚠️ Required reading before this story: [_epic.md — Target architecture](./_epic.md#target-architecture) — this story [creates | extends | activates] the shared artifact described there. Follow the per-story evolution to avoid architecture choices that will be redone in a later story.
```

BMad writes both sides — the epic section **and** the per-story pointers — as a single coherent act. A story whose epic has a `### Target architecture` but which lacks the cross-reference pointer is a contract violation.

**When to skip this section**: when every story in the epic touches a **different** artifact (e.g., 4 independent backend fetchers, each in its own package + test suite, plus 1 aggregation story). The rule is "2+ stories on the **same** artifact", not "any epic with 2+ stories". If in doubt, add it — the cost of writing it is minutes, the cost of not writing it is one or two stories of backtracked architecture.

#### Slicing plan

**Complement to `### Target architecture`.** When `### Target architecture` is populated, it describes the destination; the slicing plan describes the path — one line per story, calling out the user-observable value that slice adds. Keep the prose tight (title-case fragment or short sentence, no implementation detail).

```markdown
#### Slicing plan

- **Story 01 (walking skeleton)**: <smallest end-to-end slice that proves the data flows — e.g., "User sees an empty list at `/items`, backed by a seeded row">
- **Story 02**: <next user-observable increment — e.g., "User can add an item via inline form; list updates immediately">
- **Story 03**: <...>
```

Write the slicing plan with the same user-facing voice as `### Target architecture` — no routes, no component names, no framework terms. Its purpose is to make the per-slice demo explicit at epic-authoring time, so BMad catches horizontal-by-layer decomposition before any story file is written. See [`#slicing-discipline`](#slicing-discipline) for the underlying rule.

**When to skip**: the same rule as `### Target architecture` above — skip when every story in the epic targets a different feature. When kept, each story carrying the `⚠️ Required reading` pointer in its `## Business Context` covers both the target-architecture constraints and the slicing plan in one read.

### Mockups — how UI designs flow into stories

Stories that touch UI carry a `### Mockups` sub-section under `## Business Context`. **Two valid shapes, one per story, never mixed.**

#### Shape A — Live Figma URL (preferred when the designer actively maintains Figma)

```markdown
### Mockups

- [Navbar — signed-in state](https://figma.com/file/XXX/...?node-id=1)
- [User menu — open](https://figma.com/file/XXX/...?node-id=2)
- [Edit profile modal](https://figma.com/file/XXX/...?node-id=3)
```

The live Figma is the source of truth — never check in PNG/SVG exports alongside a live Figma (they go stale silently when the designer updates the frames).

#### Shape B — Static screenshots (when there's no active Figma, or the client doesn't use Figma)

```markdown
### Mockups

- ![Navbar](../../business/mockups/story-NN/navbar.png)
- ![User menu](../../business/mockups/story-NN/user-menu.png)
- ![Edit profile modal](../../business/mockups/story-NN/edit-modal.png)
```

Files live under `delivery/business/mockups/story-NN/` — the only place binary design assets belong in this repo. When screenshots ARE the reference, they can't go stale because they ARE the source of truth.

#### When no visual reference exists

Write `No mockups — implementer uses the existing design system`. The frontend-coder will use Shadcn primitives with default Tailwind and not invent a visual direction.

#### Why these rules

- **Source of truth stays in one place.** Mixing a live Figma with a checked-in PNG drifts the first time the designer updates.
- **Tech-spec-writer does NOT restate visual decisions** in the technical sections — it links. The frontend-coder fills the gap by reading the reference (WebFetch for Figma URLs, Read for screenshots — Claude is multimodal).
- **The rule applies identically to both shapes**: whichever one carries the reference, it IS binding. Deviations during implementation are discussed in the review, never decided unilaterally.

**What the template says:** see [`epic-template/story-NN-slug.md`](epic-template/story-NN-slug.md) for the canonical `### Mockups` block. The repo-root doc [`../../kiat-how-to.md`](../../kiat-how-to.md) section 5 has the human-oriented overview.

### Rules BMad respects when writing here

1. **Propose before writing.** Before creating or modifying any file under `delivery/epics/`, BMad announces the exact path (`epic-NN-slug/_epic.md` or `epic-NN-slug/story-NN-slug.md`) and what it intends to put in the Business Context. It waits for green light. Say `direct` in your message to skip the green light for that specific write.
2. **Read before writing.** Before creating a new story, BMad lists the existing `epic-NN-slug/` directory to avoid story-number collisions and to discover any epic patterns already established in prior stories of the same epic.
3. **Respect the two-layer boundary.** BMad writes only `## Business Context`. If technical sections already exist (written by the tech-spec-writer on a prior pass), BMad leaves them **completely untouched**, even if they seem wrong or outdated — raising the issue with the user instead of editing across the boundary.
4. **No duplication from `../business/`.** BMad never copies persona descriptions, glossary definitions, or business rules into a story. It links to the canonical version in `../business/` and trusts the reader (human or tech-spec-writer) to follow the link when needed.
5. **No speculative epic creation.** BMad never invents a new epic number unilaterally. It proposes `Epic NN: <name>` with a rationale and waits for the user's explicit go-ahead before creating the directory.
6. **Language.** The `## Business Context` section is written in the **project's business language** (see the Language convention section in [`../business/README.md`](../business/README.md#language-convention)). Technical sections below remain in English, aligned with the code.

### Handoff to Team Lead (which orchestrates the tech-spec-writer)

Once BMad has written a story's `## Business Context` and the user is ready to turn it into code, the user invokes **Team Lead** (`kiat-team-lead`) on the story file. Team Lead detects that the technical sections are missing and enters **Phase -1**, where it spawns `kiat-tech-spec-writer` as a sub-agent. The writer runs in **enrichment mode**: it preserves the pre-existing `## Business Context` intact, reads any `../business/` docs linked from it, and appends the technical sections below.

The user never invokes `kiat-tech-spec-writer` directly — Team Lead is the single entry point for all technical work. See [`../../.claude/agents/kiat-team-lead.md`](../../.claude/agents/kiat-team-lead.md) for Phase -1 and [`../../.claude/agents/kiat-tech-spec-writer.md`](../../.claude/agents/kiat-tech-spec-writer.md) for the enrichment-mode protocol on the writer side.

---

## Status lifecycle

Every `_epic.md` and `story-NN-slug.md` carries a `**Status**:` line at the **top** of the file (right after the `# Title` heading), using one of these five values:

| Emoji | Status | Meaning | Who sets it |
|---|---|---|---|
| 📥 | `Backlog` | Known work, not planned for the current cycle | BMad (when placing a story in a future epic without a schedule) |
| 📝 | `Drafted` | File exists with `## Business Context` populated; technical sections are empty or stubbed | BMad on creation, or tech-spec-writer during Phase -1 enrichment |
| 🚧 | `In Progress` | Technical sections complete, Team Lead has started or is running the pipeline | Team Lead at Phase 0b transition |
| ✅ | `Done` | Reviewers both APPROVED, rollup event written, (if applicable) Phase 7 prod validation passed | Team Lead at Phase 6 completion |
| 🛑 | `Blocked` | Pipeline escalated — spec gap, security finding, fix budget exhausted, prod validation failed | Team Lead on escalation |

**Format in the file** (first line after the title):

```markdown
# Story 01: Add editable display name with navbar

**Status**: 📝 Drafted
```

**Transitions** (agents MUST respect these — no skipping states):

```
📥 Backlog  → 📝 Drafted        (BMad or writer adds content)
📝 Drafted  → 🚧 In Progress    (Team Lead starts Phase 0b)
🚧 In Progress → ✅ Done         (Phase 6 rollup success + Phase 7 if applicable)
🚧 In Progress → 🛑 Blocked     (any escalation)
🛑 Blocked → 🚧 In Progress     (unblock — human resumed the pipeline)
✅ Done → (terminal; no further edits except retrospective notes)
```

**Epic-level aggregation rule**: an `_epic.md` carries its own `**Status**:`. Rule of thumb for Team Lead to update it:
- All child stories `✅ Done` → epic `✅ Done`
- Any child `🛑 Blocked` → epic `🛑 Blocked`
- Otherwise → epic `🚧 In Progress`
- All children `📥 Backlog` or file is fresh → epic `📝 Drafted`

**Footer placeholders** (`**Status**: 🟡 In Progress / 🟢 Done / 🔴 Blocked` at the bottom of old-style templates) are deprecated. The top-of-file line is the single source of truth; no duplicate footer.

---

## Review Log

Every story that goes through the pipeline accumulates a `## Review Log` section **at the bottom of the file** (below `## Testing Plan` / `## Implementation Notes for Coder`, above the final `---` if any). Team Lead appends one **cycle block** per review round. Append-only — never rewrite history.

### Template pre-scaffold

Every story file ships with this section pre-created:

```markdown
## Review Log

_(no cycles run yet)_
```

On the first cycle, Team Lead replaces `_(no cycles run yet)_` with the first cycle block. On subsequent cycles, Team Lead appends a new block below the previous one.

### Cycle block schema

Each block follows this exact shape (reviewers emit it wrapped in markers, Team Lead appends verbatim):

```markdown
<!-- REVIEW_LOG_BLOCK_BEGIN -->
### Cycle <N> — <ISO-8601 UTC timestamp>

**Reviewer**: `kiat-backend-reviewer` | `kiat-frontend-reviewer`
**Verdict**: `APPROVED` | `NEEDS_DISCUSSION` | `BLOCKED`

**Audit lines**:
- Skill invocations: `kiat-review-backend` / `kiat-review-frontend` PASSED
- Clerk-auth skill: <verbatim audit line emitted by reviewer>
- TEST_PATTERNS: <PASSED | DRIFT — file:line>

**Issues raised** (empty if APPROVED):
- [CATEGORY] file:line — <one-line summary>
- ...

**Arbitration** (only on NEEDS_DISCUSSION):
- Team Lead decision: <override with rationale | escalated to writer / user / designer>

**Cycle outcome**:
- Files changed in fix: <list> (empty if APPROVED or escalated)
- Fix budget consumed this cycle: <minutes>
- Cumulative fix budget: <total minutes> / 45
<!-- REVIEW_LOG_BLOCK_END -->
```

The `<!-- REVIEW_LOG_BLOCK_BEGIN -->` and `<!-- REVIEW_LOG_BLOCK_END -->` HTML comments are **contract markers** — they let Team Lead and tooling extract individual cycles without ambiguity. Do not remove them.

### Who writes what

| Field | Source |
|---|---|
| Reviewer, Verdict, Audit lines, Issues raised | Reviewer emits the block at the end of its review output |
| Arbitration | Team Lead fills this field when handling a `NEEDS_DISCUSSION` |
| Cycle outcome | Team Lead fills after the fix cycle (or marks "APPROVED — no fix needed") |

The reviewer's full review body (prose explanation of each issue) lives **above** the block in the Team Lead response log, not in the story file. The `## Review Log` section keeps only the structured block per cycle — prose stays in the conversation.

### Idempotent append

On every cycle, Team Lead:
1. Locates `## Review Log` in the story file
2. If it still contains the `_(no cycles run yet)_` placeholder → replace with the new cycle block
3. Otherwise → append the new cycle block after the last `<!-- REVIEW_LOG_BLOCK_END -->`

Never rewrite previous cycles. Corrections go in a new cycle block with a note; history is append-only.

---

## Prod Validation (Phase 7 artifact)

Production-affecting stories carry a `## Prod Validation` section **below `## Review Log`**. Template scaffolds it as:

```markdown
## Prod Validation

_(not yet validated)_
```

Team Lead replaces this placeholder after executing Phase 7, per the protocol in [`../../.claude/agents/kiat-team-lead.md`](../../.claude/agents/kiat-team-lead.md) Phase 7.

---

## Post-Delivery Notes

Stories that go through the pipeline may accumulate a `## Post-Delivery Notes` section **below `## Review Log` and above `## Prod Validation`**. Team Lead writes it at Phase 5c by aggregating the `Business Deviations:` sections from each coder's handoff. Append-only — once written, the section is never rewritten.

### Why this section exists

During implementation, coders regularly make decisions that deviate from the spec: an acceptance criterion is implemented differently due to technical constraints, a new domain concept is introduced that isn't in the glossary, a judgment call is made on something the spec was silent about. Without a structured place to capture these deviations, the business layer (`delivery/business/`) silently diverges from what was actually shipped — and the PO/PM never knows.

### Template pre-scaffold

Every story file ships with this section pre-created:

```markdown
## Post-Delivery Notes

> Aggregated by Team Lead at Phase 5c from coder handoffs. Consumed by BMad in
> Review mode to reconcile `delivery/business/` with what was actually shipped.

_(no deviations)_
```

If all coders reported `Business Deviations: NONE`, Team Lead leaves the placeholder untouched. If any coder reported deviations, Team Lead replaces `_(no deviations)_` with the aggregated content.

### Populated format

```markdown
## Post-Delivery Notes

> Aggregated by Team Lead at Phase 5c from coder handoffs. Consumed by BMad in
> Review mode to reconcile `delivery/business/` with what was actually shipped.

### Backend deviations
- AC-3: "User can delete in bulk" → async job queue, not synchronous. Reason: timeout above 50 items.
- SPEC_GAP: "soft delete" concept introduced for GDPR compliance — not in glossary.

### Frontend deviations
- DECISION: Mobile breakpoint set to 480px (spec said "mobile-friendly" without a number).
```

### Deviation categories

| Prefix | Meaning |
|---|---|
| `AC-N` | Acceptance criterion N implemented differently than specified |
| `SPEC_GAP` | New concept/behavior introduced that the spec and `delivery/business/` don't mention |
| `DECISION` | Judgment call on something the spec was silent about |

### How BMad consumes this section

When the PO/PM invokes BMad in **Review mode** on a delivered story (status `✅ Done`), BMad reads `## Post-Delivery Notes`. If deviations exist:

1. BMad switches to **Capture mode** to update `delivery/business/` — adding missing glossary terms (`SPEC_GAP`), adjusting business rules, updating domain model entries.
2. If a deviation changes the meaning of an acceptance criterion (`AC-N`), BMad may also switch to **Plan mode** to annotate the `## Business Context` of the current story or related future stories.
3. Once all deviations are reconciled, BMad notes it in the story file (append a line: `_Reconciled by BMad on <date>_` below the deviations).

This keeps `delivery/business/` as a faithful record of what was **actually built**, not what was **originally planned**. The full BMad reconciliation protocol is documented in [`../business/README.md#review-mode--post-delivery-reconciliation`](../business/README.md#review-mode--post-delivery-reconciliation).

---

## What does NOT go here

- ❌ **Evergreen domain knowledge** — glossary, personas, business rules, domain model, user journeys live in `../business/`, not here. The epic/story files link to them.
- ❌ **Technical conventions** — architecture, API design, database patterns, design system, testing rules, etc. live in `../specs/`. Stories link to the relevant convention rather than restating it.
- ❌ **Framework machinery** — agent definitions, skills, context budgets, and other Kiat framework internals live in `../../.claude/`. Never edited from a story.
- ❌ **Runtime metrics** — `../metrics/events.jsonl` is written by Team Lead only; never by hand, never from a story.
