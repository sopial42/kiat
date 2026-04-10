# Available Skills Registry

Living registry of skills available to Kiat agents in this project. Maintained manually.

Read by `kiat-tech-spec-writer` when writing a new story, to decide which contextual skills the coders should load. Read by humans when onboarding a new skill or debugging why a skill wasn't triggered.

---

## Why this file exists

Kiat has two kinds of skills:

- **Always-loaded skills** — declared in the `skills:` frontmatter of an agent, loaded automatically at agent startup. Fiability: 100%. Cost: always paid, even when not needed.
- **Contextual skills** — loaded on-demand per story based on what that story needs. Fiability: depends on discipline. Cost: zero when not needed.

This file is the **single source of truth for contextual skills**. If a skill is only listed in one agent's prompt, it's invisible to other agents. If a skill is listed here, the tech-spec-writer knows it exists and can route it to the right story.

**Always-loaded skills are listed here too, for reference**, but they don't need to be declared in story `## Skills` sections — they load themselves.

---

## Always-loaded skills (via agent frontmatter)

These are loaded automatically by their parent agents at session startup. **Do not list them in story `## Skills` sections** — that would be redundant and confusing.

*(None yet — this is a future migration target. See `.claude/specs/context-budgets.md` for the tradeoff discussion on eager-loading vs on-demand.)*

Currently, Kiat skills are invoked dynamically by their parent agents rather than declared in frontmatter. This may change after the first few real stories reveal which skills are worth eager-loading.

---

## Contextual skills (load on-demand per story)

These skills must be **explicitly listed** in a story's `## Skills` section to be used by the coders. The tech-spec-writer decides which apply based on story scope, following each skill's "When to use" criteria.

### kiat-ui-ux-search

- **Type**: Kiat wrapper around external skill
- **Wrapper size**: ~1k tokens (lightweight router)
- **Underlying skill**: [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (~85k tokens, queried on-demand via `search.py`)
- **Setup required**: clone the underlying skill into `.claude/skills/ui-ux-pro-max/` before first use
- **Location**: `.claude/skills/kiat-ui-ux-search/SKILL.md`

**When to use** (tech-spec-writer adds this to stories matching any of these):
- New visual component being designed from scratch
- Color palette, typography, or spacing decisions beyond what `design-system.md` already covers
- Accessibility-critical interface (forms, navigation, data tables)
- Chart or data visualization design
- Responsive or interaction behavior decisions
- Animation or micro-interaction patterns

**When to skip** (do NOT add to stories that match any of these):
- Pure backend story (no frontend)
- Uses an existing pattern already in `project-memory.md`
- Designer has provided explicit design direction (Figma, etc.)
- Trivial UI tweak (label change, color swap, text edit)

**How coders use it**: the coder reads `kiat-ui-ux-search/SKILL.md`, picks relevant references (`categories.md`, `invoke-patterns.md`), then runs `python3 .claude/skills/ui-ux-pro-max/scripts/search.py --category <X> --query <Y>` to fetch specific recommendations.

**Audit line pattern**: coders should emit `UI/UX search: category=<X> query="<Y>" → N recommendations applied` in their handoff.

---

## Community skills available in the wider Claude Code ecosystem

These skills are not Kiat-owned — they're part of the broader Claude Code skill community. Kiat agents can invoke them but Kiat does not guarantee their behavior. Listed here as a reference so the tech-spec-writer knows what's available.

### differential-review

- **Source**: community
- **Size**: ~3k tokens
- **Purpose**: adversarial security analysis (attacker models, exploit scenarios) that complements the standard review skills
- **When to use**: stories touching authentication, payments, user data with security implications, RLS changes, crypto
- **Loaded by**: `kiat-backend-reviewer` (optional, conditionally)

### react-best-practices

- **Source**: community
- **Size**: ~10k tokens
- **Purpose**: performance-oriented React patterns (memoization, re-render avoidance, bundle optimization, hydration)
- **When to use**: stories with complex React features, performance-sensitive components, hot-path rendering
- **Loaded by**: `kiat-frontend-reviewer` (optional, conditionally)
- **Caution**: 10k tokens is significant — don't use on trivial React stories

### composition-patterns

- **Source**: community
- **Size**: ~5k tokens
- **Purpose**: React component architecture best practices (compound components, children over render props, avoiding boolean props)
- **When to use**: stories that build reusable component library pieces or make architecture decisions
- **Loaded by**: `kiat-frontend-reviewer` (optional)

### web-design-guidelines

- **Source**: community
- **Size**: ~4k tokens
- **Purpose**: design language consistency, visual hierarchy, UX patterns
- **When to use**: stories with significant visual/UX work, when `kiat-ui-ux-search` is overkill
- **Loaded by**: `kiat-frontend-reviewer` (optional)

### sharp-edges

- **Source**: community
- **Size**: ~6k tokens
- **Purpose**: security pitfalls and sharp edges across multiple languages
- **When to use**: stories touching security-sensitive code paths
- **Loaded by**: `kiat-backend-coder` or `kiat-backend-reviewer` (optional)

---

## How to add a new skill to this registry

When you discover a new skill worth tracking (community or custom), add a new subsection with this structure:

```markdown
### <skill-name>

- **Type**: <Kiat-owned | community | external wrapper>
- **Size**: ~X tokens
- **Source**: <file path or URL>
- **Setup required**: <any prerequisites>

**When to use** (tech-spec-writer's trigger criteria):
- <concrete criterion 1>
- <concrete criterion 2>
- <at least 3 criteria total>

**When to skip**:
- <at least 2 anti-criteria>

**How to use**: <invocation instructions>

**Audit line pattern**: `<skill-name>: <what to log>`
```

Commit the registry update in the same PR as the skill itself (or the decision to use a community skill).

---

## How the tech-spec-writer uses this registry

When writing a story, the tech-spec-writer:

1. **Reads this file** (always — it's small and mandatory)
2. **Skims the "Contextual skills" section** for each skill
3. **Checks "When to use" criteria** against the story scope
4. **Adds matching skills** to the story's `## Skills` section with a one-line justification
5. **Skips non-matching skills** — the default is "no additional skills required"

**Rule of thumb**: the tech-spec-writer is **stingy** by default. Every contextual skill added to a story costs tokens and risks blowing the coder's context budget. Only add a skill when the match is clear. If in doubt, skip it — the coder can escalate later if they really need it.

---

## Relationship with context budgets

Contextual skills declared in a story's `## Skills` section count against the coder's 25k context budget during the Phase 0b pre-flight check. Team Lead reads the `## Skills` section, estimates the total cost, and either:

- **Proceeds** if the sum (ambient docs + story spec + contextual skills) fits the budget
- **Escalates to BMAD / tech-spec-writer** if it doesn't, asking to either trim skills or split the story

This enforcement is why the registry matters: the tech-spec-writer needs to know the approximate cost of each skill to make responsible decisions.

---

## Related

- [`context-budgets.md`](context-budgets.md) — the budget rules and pre-flight protocol (same directory)
- [`../agents/kiat-tech-spec-writer.md`](../agents/kiat-tech-spec-writer.md) — the agent that uses this registry
- [`../../delivery/specs/project-memory.md`](../../delivery/specs/project-memory.md) — emergent patterns that may supersede generic skill recommendations (project-owned, not framework)
