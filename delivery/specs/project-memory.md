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
### <Pattern name>

**Established at**: story-NN-<slug> (YYYY-MM-DD)
**Rule**: <one sentence — what must hold true>
**Canonical example**: `<path/to/file>`
**Rationale**: <why this and not the obvious alternative>
**Deviations allowed when**: <if any — otherwise "never, escalate to arbitration">
```

---

## Promotion to framework conventions

If a pattern here starts to look universal (applies to every story, every epic, arguably every Kiat project), consider promoting it:

- To a `delivery/specs/<topic>.md` if it's stack-locked but project-agnostic.
- Upstream to `github.com/sopial42/kiat` if it's Kiat-framework-level (agent protocol, workflow rule).

Promotion is a judgment call — when in doubt, leave it here; premature promotion pollutes the framework.
