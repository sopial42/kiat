# Project Memory

> Living document of **emergent patterns, conventions, and architectural decisions** that are *specific to this project* and aren't captured in the static convention docs. This is the only cross-story coherence mechanism in Kiat — everything else is scoped to a single story.

---

## Why this file exists

The other convention docs in `delivery/specs/` are **static** (they describe conventions that apply broadly) and **global** (they're generic across Kiat projects). This file is the opposite: **dynamic** (it grows with the project) and **specific** (it captures decisions unique to your codebase).

**The problem it solves:** Kiat agents are deliberately isolated — each agent only sees what it needs for the current story, to keep context budgets tight. The cost of that isolation is **coherence drift**: story 5 invents a new pattern without knowing story 3 already solved the same problem differently. Over time, the project becomes a salad of inconsistent patterns.

This file is the **only place** where cross-story patterns accumulate. It's the project's memory outside of any single agent's context.

---

## How this file is used

### Who reads it

1. **`kiat-tech-spec-writer`** (when it exists) reads this file at the start of every new story, *before* writing the technical spec. If emergent patterns apply to the new story, the spec must align with them. If divergence is necessary, it must be justified in the spec.
2. **Humans onboarding to the project** read this file to understand the "unwritten rules" that emerged during development.
3. **Reviewers** *may* read this file when they flag something as `NEEDS_DISCUSSION` and want to check if an existing pattern applies (optional, not mandatory).

### Who updates it

**You (the human) maintain this file manually for now.** After each PASSED story, ask yourself: *"did we establish a new pattern that the next story should follow?"* If yes, add an entry. If no, skip.

**Why manual?** Automating the maintenance would require a new agent obligation (write to this file at every story completion), which adds fragility. Kiat already has multiple mandatory writes per story (rollup event, audit lines) and piling on a fourth is risky. Manual maintenance is slow but reliable.

**Future :** once the project has run 10+ stories and we know what patterns actually emerge, we can consider automating part of the maintenance (e.g., `kiat-tech-spec-writer` proposes a PR-like diff to this file that the human reviews).

### When NOT to update

- **Don't dump every story's decisions here.** Only patterns that the next story should respect.
- **Don't duplicate content from the static conventions** (`backend-conventions.md`, `design-system.md`, etc.). If a rule belongs in a global convention, put it there instead.
- **Don't freeze bad decisions.** If a pattern here turns out to be wrong, remove it or mark it deprecated. This file is mutable — history lives in git, not in this file.

---

## Table of contents

- [Naming conventions (emergent)](#naming-conventions-emergent)
- [Shared UI components](#shared-ui-components)
- [API patterns by domain](#api-patterns-by-domain)
- [Architectural decisions](#architectural-decisions)
- [Data model emergent rules](#data-model-emergent-rules)
- [Testing patterns (project-specific)](#testing-patterns-project-specific)
- [Known gotchas (project-specific)](#known-gotchas-project-specific)
- [Deprecated / removed patterns](#deprecated--removed-patterns)

---

## Naming conventions (emergent)

> _Patterns that emerged from actual story implementations and should be followed by subsequent stories. Not to be confused with the global naming rules in `backend-conventions.md`._

_(empty — will populate as stories reveal emergent naming patterns)_

**Template for new entries:**

```markdown
### <pattern name>
**Established at:** story-NN-<slug> (YYYY-MM-DD)
**Rule:** <one-sentence description>
**Example:** `<concrete example from code>`
**Rationale:** <why this pattern was chosen, what alternative was rejected>
```

---

## Shared UI components

> _Components that have emerged as reusable across multiple stories. The next story should **import from the shared location**, not recreate._

_(empty — will populate as reusable components emerge)_

**Template for new entries:**

```markdown
### <ComponentName>
**Location:** `frontend/src/shared/components/<ComponentName>.tsx`
**Used by:** story-XX, story-YY, story-ZZ (3 stories so far)
**API:** `<props signature>`
**Do:** import from the shared location
**Don't:** recreate a variant — extend via props instead
**Owner story (canonical example):** story-XX-<slug>
```

---

## API patterns by domain

> _Emergent patterns in how endpoints are structured per domain (auth, patients, care plans, etc.). The next story in the same domain should follow the established pattern._

_(empty — will populate as API families get established)_

**Template for new entries:**

```markdown
### <domain>
**Established at:** story-NN-<slug>
**Pattern:** <describe the URL structure, payload shape, error handling, etc.>
**Canonical example:** `POST /<domain>/<resource>` — see `backend/internal/interface/<handler>.go`
**Cross-layer contract:** backend returns `<type>`, frontend expects `<type>`
**Deviations allowed when:** <conditions under which a new story can diverge>
```

---

## Architectural decisions

> _Non-obvious architectural choices that affect multiple stories. These should be reflected in `architecture-clean.md` eventually, but start here as emergent decisions._

_(empty — will populate with real decisions as the project evolves)_

**Template for new entries:**

```markdown
### <decision name>
**Decided at:** story-NN-<slug> (YYYY-MM-DD)
**Decision:** <what was chosen>
**Rejected alternatives:** <what was considered and why rejected>
**Affects:** <which parts of the codebase>
**Who should know:** <backend-coder | frontend-coder | reviewers | all>
**Promoted to convention?:** <no | yes, in `architecture-clean.md` since YYYY-MM-DD>
```

---

## Data model emergent rules

> _Relationships, invariants, or constraints between tables that emerged during implementation and weren't in the original schema design._

_(empty — will populate as data model decisions accumulate)_

**Template for new entries:**

```markdown
### <relationship or invariant name>
**Tables involved:** <table_a>, <table_b>
**Rule:** <what must hold true>
**Enforced at:** <DB constraint | RLS policy | application layer | all of the above>
**Discovered at:** story-NN-<slug>
**Why not in migrations directly:** <reason — usually "emerged after initial schema was frozen">
```

---

## Testing patterns (project-specific)

> _Testing patterns specific to this project that aren't in `testing.md` (the global testing spec). For example: how to mock a specific third-party service, how to seed data for a particular domain, etc._

_(empty — will populate as project-specific testing patterns emerge)_

**Template for new entries:**

```markdown
### <pattern name>
**Scope:** <which kind of tests this applies to — Venom, Playwright, both>
**Pattern:** <describe>
**Canonical example:** `backend/venom/<file>` or `frontend/e2e/<file>`
**Why this and not the default testing.md approach:** <rationale>
```

---

## Known gotchas (project-specific)

> _Lessons learned that are specific to this project (not general Kiat gotchas, which live in the static docs). Populate when a story hits a surprising bug that the next story should avoid._

_(empty — will populate as real gotchas are discovered)_

**Template for new entries:**

```markdown
### <gotcha name>
**Discovered at:** story-NN-<slug> (YYYY-MM-DD)
**Symptom:** <what went wrong>
**Root cause:** <what actually broke>
**Workaround or fix:** <what resolved it>
**Prevention for future stories:** <what to check before coding in this area>
```

---

## Deprecated / removed patterns

> _Patterns that were once established but have been removed or superseded. Kept here so agents reading the file don't accidentally revive them._

_(empty — will populate if any pattern gets deprecated)_

**Template for new entries:**

```markdown
### <pattern name> (DEPRECATED YYYY-MM-DD)
**Was established at:** story-NN-<slug>
**Why deprecated:** <reason>
**Replaced by:** <new pattern, or "nothing — direct removal">
**Still references in code?:** <yes, need refactor / no, already cleaned up>
```

---

## File size and audit

This file is scanned by `kiat/.claude/tools/doc-audit.py` alongside the other project convention docs. Target: ≤ 8k tokens (same budget as other convention docs). If this file grows past that, split by category (e.g., `project-memory-naming.md`, `project-memory-components.md`) rather than letting it sprawl.

**Rule of thumb:** if an entry is > 10 lines, it probably belongs in a real convention doc, not here. This file captures patterns *emerging*; stable patterns get promoted to the static docs.

---

## Related

- [`backend-conventions.md`](backend-conventions.md) — Static backend conventions (naming, errors, logging)
- [`architecture-clean.md`](architecture-clean.md) — Static architectural patterns (Clean Arch 4 layers)
- [`frontend-architecture.md`](frontend-architecture.md) — Static frontend patterns (RSC, hooks, accessibility)
- [`design-system.md`](design-system.md) — Static design tokens and component library
- [`../../.claude/specs/failure-patterns.md`](../../.claude/specs/failure-patterns.md) — Reactive failure pattern registry (framework-side cousin of this file, but for escalations, not patterns)
