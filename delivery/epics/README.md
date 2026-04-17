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

Stories that touch UI carry a `### Mockups` sub-section under `## Business Context`, holding **Figma URLs** — never checked-in PNG/SVG exports.

**Why URLs only:**
- **Source of truth stays live.** A Figma frame updated by the designer remains in sync; a PNG checked in three weeks ago rots silently.
- **Repo stays lean.** Design assets can weigh dozens of MB; git is not an art server.
- **Tech-spec-writer and frontend coder read the URL.** Claude can WebFetch a public Figma URL (or the designer shares a password-protected link via a dev-only channel); the coder doesn't need a local copy.

**If a client absolutely needs archived snapshots** (audit trail, contractual deliverable), those exports go under `delivery/business/mockups/story-NN/` — not in `delivery/epics/`, not in `delivery/specs/`. Client-archival assets belong with client-archival knowledge in `delivery/business/` (which is markdown-only by default, but a binary sub-folder is acceptable when the contract demands it). The story file still carries the Figma URL in `### Mockups`; the archive is parallel, not a replacement.

**What the template says:** see [`epic-template/story-NN-slug.md`](epic-template/story-NN-slug.md#mockups) for the canonical `### Mockups` block. Stories with no UI change write `No mockups — implementer uses the existing design system`.

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

## What does NOT go here

- ❌ **Evergreen domain knowledge** — glossary, personas, business rules, domain model, user journeys live in `../business/`, not here. The epic/story files link to them.
- ❌ **Technical conventions** — architecture, API design, database patterns, design system, testing rules, etc. live in `../specs/`. Stories link to the relevant convention rather than restating it.
- ❌ **Framework machinery** — agent definitions, skills, context budgets, and other Kiat framework internals live in `../../.claude/`. Never edited from a story.
- ❌ **Runtime metrics** — `../metrics/events.jsonl` is written by Team Lead only; never by hand, never from a story.
