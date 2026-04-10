---
name: kiat-ui-ux-search
description: >
  Use this skill whenever a story involves visual design decisions — new UI
  components, color palette choices, typography pairing, spacing systems,
  accessibility-critical interfaces, responsive layouts, animations, chart or
  data visualization, or navigation patterns. Even if the user doesn't
  explicitly ask for "design recommendations", reach for it when the work
  touches how things look or feel. This is a lightweight router around the
  external ui-ux-pro-max skill (50+ styles, 161 palettes, 57 font pairings, 99
  UX guidelines) — the underlying content is ~85k tokens and must not be loaded
  eagerly. Query it on-demand via its bundled `search.py` script and apply only
  the rules that match the current task.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Kiat UI/UX Search

A lightweight router around the [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) community skill. Its job is to let coders query a rich UI/UX knowledge base without loading the full 85k-token content into their context window — that would blow the Kiat coder context budget by more than 3×.

## When to reach for this skill

A story benefits from this skill when it introduces or modifies something users see or interact with, and the design decision is not already dictated by `delivery/specs/design-system.md` or an existing pattern. Concretely:

- A new visual component being designed from scratch
- Color palette or theme decisions beyond the project's existing tokens
- Typography pairing choices (font families, weights, sizes)
- Spacing and layout system decisions
- Accessibility-critical interfaces where WCAG AA is sensitive
- Responsive behavior decisions (mobile, tablet, desktop breakpoints)
- Animation or interaction patterns
- Chart or data visualization design
- Navigation pattern choices (menus, tabs, breadcrumbs)
- Form design and validation feedback

Skip this skill on pure backend stories, trivial UI tweaks (label change, copy edit), or refactors that don't change user-visible behavior. The underlying content is expensive — querying it for a story that already has a clear design direction wastes tokens and may suggest patterns that contradict existing ones.

## Why this skill is a router, not the full content

The real skill at `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill` is ~85k tokens. Loading it eagerly would break the framework's context budget enforcement (Layer 5). Instead, the upstream skill ships with a searchable database and a `search.py` script that returns only the relevant rules per query (typically 500–2000 tokens). This skill's whole job is to teach the caller how to run those queries effectively and how to reconcile the results with the project's own design authorities.

## Prerequisites (one-time setup per project)

The underlying skill must be cloned into `.claude/skills/ui-ux-pro-max/` for the search script to work. Before your first query, verify that the installation exists. If it doesn't, stop and surface the instructions to the user — don't try to guess at paths or skip the query.

Preflight check:

```bash
test -f .claude/skills/ui-ux-pro-max/scripts/search.py && echo OK || echo MISSING
```

If the preflight returns `MISSING`, tell the user the skill isn't installed and provide the setup block below. The clone is cheap and one-time — don't attempt to work around it.

```bash
cd .claude/skills
git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git ui-ux-pro-max
python3 ui-ux-pro-max/scripts/search.py --help  # verify it runs
```

If the script fails after cloning (missing Python dependencies, missing CSV files), surface the error to the user verbatim. The upstream skill has its own README for setup troubleshooting, and guessing at fixes tends to make the skill quietly incorrect rather than loudly broken.

## How to query

The workflow is:

1. **Read the references below to understand the shape of the knowledge base.** You probably only need `categories.md` + `invoke-patterns.md` for a typical task.
2. **Decide which categories and keywords apply.** Start narrow — 1-2 categories is usually enough. Adding more only if the first results miss the target.
3. **Run the search script** from the repo root:
   ```bash
   python3 .claude/skills/ui-ux-pro-max/scripts/search.py --category <name> --query "<keywords>"
   ```
4. **Cross-reference the results with the project's own design authorities** before applying them. Generic UX rules can contradict project-specific conventions, and project-specific wins.

### Reference files

- [`references/categories.md`](references/categories.md) — The 10 priority categories of the underlying skill with short descriptions. Read this first to pick which category matches your task.
- [`references/invoke-patterns.md`](references/invoke-patterns.md) — Concrete examples of `search.py` invocations for common scenarios. Read this when you're ready to query.
- [`references/when-to-use.md`](references/when-to-use.md) — Extended trigger criteria with real examples. Read this only if you're on the fence about whether the skill applies.

## Reconciling with project-specific authorities

Query results from the underlying skill are generic best practices. The project has its own design authorities that take precedence when there's a conflict:

1. **`delivery/specs/design-system.md`** — The project's own design tokens, spacing, and typography. If an upstream recommendation contradicts a token defined here, the project wins.
2. **`delivery/specs/project-memory.md`** — Emergent patterns established by previous stories. Consistency across stories beats fresh recommendations — introducing a new pattern per story costs refactoring later.

If a query returns a recommendation that contradicts one of these, note it in your handoff so the reviewer understands why you diverged. Don't silently follow the generic rule.

## Audit line

When you query this skill, include a one-line audit trail in your handoff so the reviewer can verify the query actually happened and what you applied:

```
UI/UX search: category=<name> query="<terms>" → <N> recommendations applied
```

This matches the Kiat audit-line pattern used elsewhere in the framework. Skipping the audit line isn't fatal, but it forces the reviewer to guess which parts of your design came from the query versus your own judgment — adding it takes 10 seconds and saves that ambiguity.

## Tips for effective queries

- **Be specific in the query terms.** "button" alone returns noise; "button hover primary" gets the rule you need.
- **Match the query to the category.** Querying "color palette" in `layout-responsive` wastes a call; use `typography-color`.
- **Use 2-4 keywords.** One keyword is too broad, five+ is too narrow — the matcher runs on semantic similarity and over-specifying misses results.
- **Run multiple small queries rather than one giant one.** Each query costs ~500-2000 tokens of output; three focused queries stay within budget, one sprawling query overflows it.
- **Iterate if the first query misses.** The knowledge base is searchable by semantic similarity, so rewording "data grid" to "table dense layout" can surface different rules.

## When to skip even though the story is visual

- **The story uses an existing pattern.** If the spec says "reuse PatientCard" or "follow the dashboard layout", project consistency beats fresh generic advice. Query `project-memory.md` and existing code instead.
- **A designer has provided explicit direction.** Figma files, brand colors, or a hand-off document — follow them. Querying this skill would produce conflicting recommendations.
- **The story is tiny.** Label changes, copy edits, small padding tweaks. The query overhead isn't worth it.
- **Adding this skill pushes the coder's context budget over the 25k limit.** Budget is a hard constraint; a missed UX recommendation is a soft quality issue. Budget wins.

## Related

- [`delivery/specs/design-system.md`](../../../delivery/specs/design-system.md) — The project's own design system (colors, spacing, typography). Always consult this **first**.
- [`delivery/specs/project-memory.md`](../../../delivery/specs/project-memory.md) — Emergent UI patterns from previous stories. Consult this **second**.
- The [ui-ux-pro-max GitHub repo](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — The underlying skill. Visit if you want to understand the full scope of the knowledge base.
