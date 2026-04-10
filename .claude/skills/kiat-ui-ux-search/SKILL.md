---
name: kiat-ui-ux-search
description: Use this skill whenever a story involves visual design decisions — new UI components, color palette choices, typography pairing, spacing systems, accessibility-critical interfaces, responsive layouts, animations, chart or data visualization, or navigation patterns. Even if the user doesn't explicitly ask for "design recommendations", trigger this skill when the work touches how things look or feel to the user. This is a lightweight wrapper around the external ui-ux-pro-max skill (50+ styles, 161 palettes, 57 font pairings, 99 UX guidelines) — the underlying content is 85k tokens and must NOT be loaded eagerly. Instead, query it on-demand via its bundled search script.
---

# Kiat UI/UX Search

Lightweight Kiat wrapper around the [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) community skill. Lets agents query a rich UI/UX knowledge base without loading its 85k-token content into their context window.

## When to reach for this skill

Any story that introduces or modifies something users see or interact with. Concretely:

- New visual components being designed from scratch
- Color palette or theme decisions
- Typography pairing choices (font families, weights, sizes)
- Spacing and layout system decisions
- Accessibility-critical interfaces (WCAG AA sensitive areas)
- Responsive behavior decisions (mobile, tablet, desktop breakpoints)
- Animation or interaction patterns
- Chart or data visualization design
- Navigation pattern choices (menus, tabs, breadcrumbs)
- Form design and validation feedback

**Do not reach for this skill** when the story is pure backend, a trivial UI tweak (changing a label), or a refactor that doesn't change user-visible behavior. The underlying content is expensive — only query it when the decision actually benefits from structured UX knowledge.

## Why this skill is a wrapper, not the full content

The real skill at `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill` is ~85k tokens. That's 3.4× the entire context budget of a Kiat coder agent. Loading it eagerly would break the framework's Layer 5 (context budgets).

Instead, the real skill ships with a searchable database and a `search.py` script. You query specific categories + keywords, and the script returns only the relevant rules (typically 500-2000 tokens per query). This skill teaches you how to run those queries effectively.

## How to use

The workflow is:

1. **Read the references to understand the shape of the knowledge base.** The references below describe the 10 categories and give query examples.
2. **Decide which categories and keywords apply to the current task.**
3. **Run the search script** with `python3 .claude/skills/ui-ux-pro-max/scripts/search.py --category <name> --query <keywords>`.
4. **Apply the returned recommendations** when writing your spec or code.

### Reference files (load only what you need)

- [`references/categories.md`](references/categories.md) — The 10 priority categories of the underlying skill, with short descriptions. Read this first to pick which category matches your task.
- [`references/invoke-patterns.md`](references/invoke-patterns.md) — Concrete examples of `search.py` invocations for common scenarios. Read this when you're ready to query.
- [`references/when-to-use.md`](references/when-to-use.md) — Extended trigger criteria with real examples. Read this if you're unsure whether the skill applies to your current task.

You don't need to read all three. For a typical query, `categories.md` + `invoke-patterns.md` is enough.

## Prerequisites (one-time setup per project)

The underlying skill must be cloned into `.claude/skills/ui-ux-pro-max/` for the search script to work. If the directory doesn't exist, tell the user to run:

```bash
cd .claude/skills
git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git ui-ux-pro-max
```

Then verify the script is runnable:

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py --help
```

If the script fails (missing Python dependencies, missing CSV files), surface the error to the user — don't guess at how to fix it. The underlying skill has its own README for setup troubleshooting.

## Output pattern — leave an audit line

When you query this skill, include in your handoff a one-line audit trail so reviewers can verify the query happened:

```
UI/UX search: ran category=<name> query="<terms>" → <N> recommendations applied
```

This is consistent with the Kiat "audit lines" pattern (Layer 4 of the enforcement model). It lets reviewers confirm that the skill was actually consulted, not skipped.

## When to skip this skill even if a story is visual

Three situations where reaching for this skill is overkill:

- **The story uses an existing pattern.** If the spec says "reuse the existing PatientCard component", don't query UI/UX — follow the pattern already in place. Project consistency beats fresh recommendations.
- **The design is already provided by the user or a designer.** If there's a Figma file or explicit design direction, follow it. Don't overrule the designer with generic recommendations.
- **The story is tiny.** A label change, a color tweak on an existing button, a one-line copy edit — these don't need a structured UX query. Use judgment.

## Related

- [`delivery/specs/design-system.md`](../../../delivery/specs/design-system.md) — The project's own design system (colors, spacing, typography). Always consult this **first**, before this skill. The project design system wins when there's a conflict.
- [`delivery/specs/project-memory.md`](../../../delivery/specs/project-memory.md) — Emergent UI patterns that have been established by previous stories. Consult this **second**. Consistency across stories wins over generic recommendations.
- The [ui-ux-pro-max GitHub repo](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — The underlying skill. Visit if you want to understand the full scope of the knowledge base.
