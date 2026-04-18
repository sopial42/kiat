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

The **user-facing acceptance criteria** that BMad writes are different from the **technical acceptance criteria** that the tech-spec-writer may add lower in the file. The user-facing ones are observable by the user ("I can see my patients sorted by risk"); the technical ones are implementation-bound ("`GET /patients?sort=risk` returns 200 with pagination headers").

**Exact section headers (do not rename):**

| Layer | Header in the file | Author |
|---|---|---|
| User-facing (inside `## Business Context`) | `### Acceptance criteria (user-facing)` | BMad |
| Technical (top-level, below `## Business Context`) | `## Acceptance Criteria (technical)` | tech-spec-writer |

Two different heading levels on purpose: the user-facing list is a sub-section of `## Business Context` (BMad's only sandbox), while the technical list is a peer of `## Backend`, `## Frontend`, etc. A story that drops the `(user-facing)` / `(technical)` suffix, or merges the two lists into one, is a two-layer boundary violation — stop and fix the structure before proceeding.

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

## What does NOT go here

- ❌ **Evergreen domain knowledge** — glossary, personas, business rules, domain model, user journeys live in `../business/`, not here. The epic/story files link to them.
- ❌ **Technical conventions** — architecture, API design, database patterns, design system, testing rules, etc. live in `../specs/`. Stories link to the relevant convention rather than restating it.
- ❌ **Framework machinery** — agent definitions, skills, context budgets, and other Kiat framework internals live in `../../.claude/`. Never edited from a story.
- ❌ **Runtime metrics** — `../metrics/events.jsonl` is written by Team Lead only; never by hand, never from a story.
