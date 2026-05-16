# Project Memory

> Living document of **emergent patterns, conventions, and architectural decisions** specific to *this project* that aren't captured in the static convention docs. The only cross-story coherence mechanism in Kiat — everything else is scoped to a single story.

---

## Why this file exists

The other docs in `delivery/specs/` are **static** and **generic across Kiat projects**. This file is the opposite: **dynamic** (grows with the project) and **specific** (your codebase's emergent decisions).

**Problem it solves**: Kiat agents are deliberately isolated — each agent only sees what it needs for the current story, to keep context budgets tight. Cost of that isolation = **coherence drift**: story 5 invents a new pattern without knowing story 3 solved the same problem differently. Over time, the project becomes a salad of inconsistent patterns.

This file is the one place where cross-story patterns accumulate — the project's memory outside of any single agent's context.

---

## How to use it

- **`kiat-tech-spec-writer`** reads this file at the start of every new story, before writing the technical spec. If emergent patterns apply, the spec must align or justify divergence.
- **Humans onboarding** read it to understand the unwritten rules that emerged during development.
- **Reviewers** may read it when flagging `NEEDS_DISCUSSION` items to check if an existing pattern applies.

**Who writes**: you (the human), manually, after each PASSED story. Ask yourself: *did we establish a pattern the next story should follow?* If yes, add an entry. If no, skip. Manual because automating it would add fragility to the Team Lead exit gate.

**Greenfield bootstrap (optional)**: if you arrive at story 1 with an architecture document already produced (typically by BMad's `bmad-create-architecture`), the file does not have to start empty. Run the `kiat-seed-project-memory` skill once to extract cross-story technical decisions from the architecture document and seed them here as a single "pre-implementation seed" section. This bridges the BMad→Kiat handoff so the tech-spec-writer and coders do not have to rediscover decisions already documented upstream. The skill proposes entries; you approve before they are written. Skip this for brownfield projects where the file is already populated from real story patterns.

---

## Organize as your project grows

No pre-defined sections. Create `##` sections as emergent patterns call for them — typical categories that show up in most projects:

- Component patterns (shared React components other stories must reuse)
- API patterns by domain (URL/payload/error shapes per resource family)
- Architectural decisions (non-obvious choices affecting multiple stories)
- Data model emergent rules (invariants, relationships not in the initial schema)
- Testing patterns (project-specific test setups beyond `testing.md`)

But only create a section when you have a real entry for it. Empty structure is noise; fill-as-you-go keeps the file honest.

---

## Entry template

Keep entries short (5–10 lines). The point is to be **findable by the next story**, not to write architecture documents.

```markdown
### PM-NNN — <Pattern name>

**Status**: active | superseded | promoted
**Established**: story-NN-<slug> (YYYY-MM-DD) | pre-implementation seed (YYYY-MM-DD)
**Last verified**: YYYY-MM-DD
**Touches**: <topic-1, topic-2, ...>
**Rule**: <one sentence — what must hold true>
**Canonical example**: `<path/to/file>` (when an implementation exists)
**Canonical ref**: `<path:line>` (when the source is a planning artifact, e.g. architecture.md)
**Rationale**: <why this and not the obvious alternative — one sentence>
**Deviations allowed when**: <if any — otherwise "never, escalate to arbitration">
**Amends / Supersedes / Superseded by / Promoted to**: <PM-XXX or path/to/topic.md, when applicable>
```

**Field rules**:

- **`PM-NNN` ID**: monotonic, never renumbered, never reused. The ID is the durable handle for amendments. Assign the next free integer.
- **`Status`**: `active` (current rule), `superseded` (replaced by a later entry — keep for audit trail), `promoted` (moved to a topical file in `delivery/specs/<topic>.md` — keep as a redirect stub).
- **`Touches`**: the canonical topic vocabulary — `backend`, `frontend`, `database`, `auth`, `clerk`, `api`, `testing`, `deployment`, `security`, `design-system`, `share-tokens`, `pdf-generation`, `calc-engine`, `external-integrations`, `observability`, `ci-cd`. Add a new topic only when an architectural amendment introduces one. Grepping `Touches:` is the cheap topic index — a coder asking "what decisions affect auth?" can find them in <1s.
- **`Canonical example` vs `Canonical ref`**: use `example` when a real file path proves the pattern; use `ref` when the source is a planning document (architecture.md). Both are acceptable. An entry with neither is suspect.

---

## Cap and promotion mechanics

The file must stay short to remain findable. The framework enforces a soft cap and a promotion path.

### Cap

- **Hard cap**: 25 single-topic entries OR 400 lines, whichever is hit first. Cross-topic entries (`Touches:` lists ≥2 topics) are exempt from the count — they have nowhere else to live.
- **What happens at the cap**: the `kiat-validate-project-memory` CI check (planned follow-up) fails the build. The human must promote single-topic clusters or justify the cap exception in the file's frontmatter.

### Promotion to a topical file

When ≥3 entries share a single `Touches:` topic, the cluster is **promotion-eligible**. The human runs `kiat-promote-project-memory` (planned follow-up skill) which:

1. Proposes a new project-owned file `delivery/specs/<topic>.md` (e.g., `share-tokens.md`, `pdf-generation.md`, `calc-engine.md`).
2. Moves the clustered entries into the new file, preserving their `PM-NNN` IDs.
3. Replaces each entry in `project-memory.md` with a redirect stub:
   ```markdown
   ### PM-008 — Share token TTL — PROMOTED

   **Status**: promoted
   **Promoted to**: [`delivery/specs/share-tokens.md#pm-008`](share-tokens.md#pm-008)
   ```

**Why a new project-owned file, not edits to a framework-owned file**: framework-owned `delivery/specs/<topic>.md` files (e.g., `clerk-patterns.md`) ship with Kiat upstream. Adding project-specific overrides to them creates merge friction on every Kiat upgrade and dissolves the framework/project ownership boundary. New project-owned files keep the boundary clean — they're entirely project-owned, they live next to the framework files, and the coders load them when their story touches that topic (the existing routing logic in `kiat-tech-spec-writer.md` already handles "load files relevant to the story").

### Cross-topic decisions stay here forever

A decision that touches ≥2 topics (e.g., "three-regime data isolation" touches `database` + `security` + `backend`) is structurally non-promotable: splitting it across topical files would fragment the rule and let coders implement inconsistent halves. Cross-topic entries remain in `project-memory.md` indefinitely. They are exempt from the cap because they have no alternative home.

---

## Promotion to framework conventions (upstream Kiat)

If a pattern here starts to look universal (applies to every story, every epic, arguably every Kiat project), consider promoting it upstream:

- Upstream to `github.com/sopial42/kiat` if it's Kiat-framework-level (agent protocol, workflow rule).

Promotion to a project-local topical file (above) and promotion upstream are distinct: the former keeps the rule in this project, the latter generalizes it for all Kiat projects. Upstream promotion is a high bar and a separate PR — when in doubt, keep the rule local.
