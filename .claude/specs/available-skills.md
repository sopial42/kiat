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

| Skill | Parent agent | Declared in |
|---|---|---|
| `kiat-validate-spec` | `kiat-tech-spec-writer` | frontmatter `skills:` — used at Step 6 (self-validation before handoff) |

All other Kiat skills are invoked **dynamically** by their parent agents (at a specific phase or step in the agent's protocol), not via frontmatter. This is intentional: dynamic invocation lets the agent control *when* the skill runs and keeps the ambient context small. The tech-spec-writer is the single exception because `kiat-validate-spec` is load-bearing — it gates every single handoff.

If a future skill proves it must run on every session (no conditional path), it can be promoted to this table. Until then, the default is dynamic invocation.

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

## Community skills installed at pinned versions

These skills are **not Kiat-owned and not committed** to the repo. They're pulled from upstream at the exact commit SHA pinned in [`/skills-lock.json`](../../skills-lock.json) by `make install-claude-skills` (see the README's Phase A.5). The install script verifies a SHA-256 directory hash against the lock file on every run, so a tampered upstream is detected immediately.

If a skill below shows status `PENDING`, its upstream source has not been identified yet — it cannot be added to a story's `## Skills` section until somebody fills the lock file's `source`/`ref`/`path` and runs `make install-claude-skills` to record the `computedHash`.

### differential-review

- **Status**: ✅ PINNED ([`skills-lock.json`](../../skills-lock.json))
- **Source**: [`trailofbits/skills`](https://github.com/trailofbits/skills) → `plugins/differential-review/skills/differential-review`
- **Size**: ~3k tokens
- **Purpose**: adversarial security analysis (attacker models, exploit scenarios, blast-radius from call-graphs, regression detection via git blame) that complements the standard review skills
- **When to use**: stories touching authentication, payments, user data with security implications, RLS changes, crypto, deserialization, file uploads, anything whose failure is exploitable
- **Loaded by**: `kiat-backend-reviewer` — dynamically invoked at Step 3.5 when the diff hits security-critical paths. Triggers and audit-line format are defined inline in the agent file.

### sharp-edges

- **Status**: ✅ PINNED ([`skills-lock.json`](../../skills-lock.json))
- **Source**: [`trailofbits/skills`](https://github.com/trailofbits/skills) → `plugins/sharp-edges/skills/sharp-edges`
- **Size**: ~6k tokens
- **Purpose**: cross-language security pitfalls — error-prone APIs, dangerous defaults, footgun designs, "secure-by-default" review
- **When to use**: stories evaluating new dependencies, configuration schemas, cryptographic library choices, production-environment guards, or reviewing whether existing code follows pit-of-success principles
- **Loaded by**: `kiat-backend-coder` (build-time, when story's `## Skills` lists it). The reviewer does not invoke it directly — `differential-review` covers the review-time security angle.

**How coders use it**: at Step 2, when the story's `## Skills` lists `sharp-edges`, read `.claude/skills/sharp-edges/SKILL.md` and the relevant `references/*.md` for the pattern at hand (e.g. config-schema design, dangerous-defaults review). Apply its checklist to the code being written, especially around error-prone API boundaries and security-sensitive guards. The skill is reference material — there is no protocol to "run" — you read it like a spec and let it shape your implementation.

**Audit line pattern**: `sharp-edges: applied <reference-file> for <concern>` (e.g. `sharp-edges: applied references/secure-defaults.md for production env guard`)

### react-best-practices

- **Status**: ✅ PINNED ([`skills-lock.json`](../../skills-lock.json))
- **Source**: [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) → `skills/react-best-practices` (Vercel Engineering, MIT)
- **Size**: ~10k tokens (SKILL.md + 45 rule files across 8 categories)
- **Purpose**: React/Next.js performance optimization — re-render avoidance, memoization, bundle splitting, async patterns, hydration, client-side caching, JS micro-optimizations
- **When to use**: stories with complex React features, performance-sensitive components, hot-path rendering, large list virtualization, async data flows
- **When to skip**: trivial UI changes (label edits, color swaps), backend-only stories, stories already passing performance review with no regression risk
- **Loaded by**: `kiat-frontend-reviewer` — dynamically invoked at Step 4 when the story's `## Skills` lists it.

**Audit line pattern**: `react-best-practices: applied <category>/<rule-name> from skills/react-best-practices/rules/`

### frontend-design

- **Status**: ✅ PINNED ([`skills-lock.json`](../../skills-lock.json)) — replaces the legacy placeholder `web-design-guidelines` from earlier drafts
- **Source**: [`anthropics/skills`](https://github.com/anthropics/skills) → `skills/frontend-design` (official Anthropic library)
- **Size**: ~5k tokens
- **Purpose**: production-grade frontend design language — bold aesthetic direction, anti-AI-slop guidance, accessibility, typography, layout, color, motion
- **When to use**: stories with significant visual/UX work where `kiat-ui-ux-search` would be overkill — landing pages, dashboards, marketing components, anything needing a clear aesthetic point-of-view
- **When to skip**: stories using existing design-system primitives without visual changes, backend-only stories, trivial label/copy updates
- **Loaded by**: `kiat-frontend-reviewer` — dynamically invoked at Step 4 when the story's `## Skills` lists it.

**Audit line pattern**: `frontend-design: applied <aesthetic-direction> per skills/frontend-design/SKILL.md`

### composition-patterns

- **Status**: ✅ PINNED ([`skills-lock.json`](../../skills-lock.json))
- **Source**: [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) → `skills/composition-patterns` (Vercel Engineering, MIT, same SHA as `react-best-practices`)
- **Size**: ~3k tokens (SKILL.md + 8 rule files: architecture, state, patterns, react19)
- **Purpose**: React component architecture — avoid boolean-prop proliferation, compound components, state lifting, render-props vs children, context interfaces, React 19 patterns (no forwardRef)
- **When to use**: stories that **create or refactor a reusable component** — going into the design system, used in 2+ places, or whose API will be consumed by other agents
- **When to skip**: one-off page implementations, trivial UI work, stories that consume Shadcn primitives unchanged (the primitives already follow these patterns), backend-only stories
- **Loaded by**: `kiat-frontend-reviewer` — dynamically invoked at Step 4 when the story's `## Skills` lists it.
- **Complements**: `react-best-practices` (perf) and `frontend-design` (visual) — these three together cover the major axes of frontend review without overlap.

**Audit line pattern**: `composition-patterns: applied <category>/<rule-name> from skills/composition-patterns/rules/`

### clerk-nextjs-patterns

- **Source**: [clerk/skills](https://github.com/clerk/skills) (official Clerk AI skill)
- **Size**: ~5k tokens (SKILL.md) + ~2k per reference file (5 references)
- **Location**: `.claude/skills/clerk-nextjs-patterns/`
- **Purpose**: Next.js App Router patterns for Clerk — `auth()` vs hooks, middleware strategies (public-first vs protected-first), Server Action protection, API route auth (401 vs 403), user-scoped caching
- **When to use**: stories that add or modify Clerk middleware, auth guards on pages/layouts, Server Actions with auth, API route handlers with auth, or caching of user-scoped data
- **When to skip**: pure backend stories, stories that don't touch Next.js auth integration, trivial UI changes behind existing auth guards
- **Loaded by**: `kiat-frontend-coder` (contextual, when story touches Clerk + Next.js)
- **Complements**: `kiat-clerk-auth-review` (review-time checks) — this skill is build-time guidance

**Audit line pattern**: `clerk-nextjs-patterns: applied <pattern> from references/<file>.md`

### clerk-testing

- **Source**: [clerk/skills](https://github.com/clerk/skills) (official Clerk AI skill)
- **Size**: ~1.5k tokens
- **Location**: `.claude/skills/clerk-testing/`
- **Purpose**: E2E testing patterns for Clerk apps — `clerkSetup()`, `setupClerkTestingToken()`, `storageState` for persistent auth, framework-specific setup (Playwright/Cypress)
- **When to use**: stories that add or modify E2E tests involving authenticated flows, stories that set up Playwright auth fixtures, stories that touch `clerkSetup` or storage state management
- **When to skip**: backend-only stories, stories with no E2E test component, stories where auth tests already exist and aren't being modified
- **Loaded by**: `kiat-frontend-coder` (contextual, when story involves E2E auth tests)
- **Complements**: `block-c-clerk` (test-patterns-check) and `kiat-clerk-auth-review` (review-time)

**Audit line pattern**: `clerk-testing: applied <pattern> for <Playwright|Cypress> auth setup`

### clerk-backend-api

- **Source**: [clerk/skills](https://github.com/clerk/skills) (official Clerk AI skill)
- **Size**: ~8k tokens
- **Location**: `.claude/skills/clerk-backend-api/`
- **Purpose**: Clerk Backend REST API explorer — user management, organization CRUD, invitations, metadata operations (public/private/unsafe), rate limit awareness, endpoint schema inspection
- **When to use**: stories that need to interact with Clerk's Backend API (user sync, org provisioning, metadata updates), stories that add webhook handlers for Clerk events, debugging auth issues that require API inspection
- **When to skip**: stories that only use Clerk client-side (hooks, components), stories with no server-to-Clerk communication
- **Loaded by**: `kiat-backend-coder` (contextual, when story involves Clerk API calls)
- **Caution**: requires `CLERK_SECRET_KEY` env var — never expose in frontend code

**Audit line pattern**: `clerk-backend-api: used <endpoint> for <purpose>`

### clerk-custom-ui

- **Source**: [clerk/skills](https://github.com/clerk/skills) (official Clerk AI skill)
- **Size**: ~4k tokens (SKILL.md) + ~2k per reference file (5 references across core-2/core-3)
- **Location**: `.claude/skills/clerk-custom-ui/`
- **Purpose**: Custom authentication flows (useSignIn/useSignUp hooks) and appearance customization (themes, variables, options) — covers both Core 2 and current SDK patterns, shadcn theme integration
- **When to use**: stories that build custom sign-in/sign-up pages (not using Clerk's pre-built components), stories that style or theme Clerk components, stories that integrate Clerk appearance with the project's design system (especially shadcn)
- **When to skip**: stories using Clerk's pre-built components without customization, backend-only stories, stories where auth UI is unchanged
- **Loaded by**: `kiat-frontend-coder` (contextual, when story involves custom auth UI or Clerk theming)

**Audit line pattern**: `clerk-custom-ui: applied <core-2|core-3> <custom-sign-in|custom-sign-up|appearance> pattern`

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
- **Escalates to `kiat-tech-spec-writer`** if it doesn't, asking to either trim skills or split the story

This enforcement is why the registry matters: the tech-spec-writer needs to know the approximate cost of each skill to make responsible decisions.

---

## Related

- [`context-budgets.md`](context-budgets.md) — the budget rules and pre-flight protocol (same directory)
- [`../agents/kiat-tech-spec-writer.md`](../agents/kiat-tech-spec-writer.md) — the agent that uses this registry
- [`../../delivery/specs/project-memory.md`](../../delivery/specs/project-memory.md) — emergent patterns that may supersede generic skill recommendations (project-owned, not framework)
