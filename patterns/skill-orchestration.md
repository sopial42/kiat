# Pattern: Skill Orchestration

**Goal**: Know when to use a skill vs agent, and how to load skills dynamically.

---

## What is a Skill?

A **skill** is reusable, vetted expertise from Anthropic or custom libraries.

Examples:
- `clerk-testing` → Clerk auth patterns
- `react-best-practices` → React performance tips
- `differential-review` → Code review checklist
- `sharp-edges` → Security pitfalls
- `bmad-editorial-review-prose` → Content quality review

**Benefits:**
- Versioned (can update once, all agents benefit)
- Focused (not cluttering main CLAUDE.md)
- Optional (only load when needed)

---

## When to Use a Skill

### Use a Skill When:
- Knowledge is **reusable across many projects** (Clerk patterns, React best practices)
- Knowledge is **maintained externally** (Anthropic, libraries)
- Knowledge is **large** (would bloat CLAUDE.md)
- Knowledge is **optional per-task** (not every story needs it)

### Don't Use a Skill When:
- Knowledge is **project-specific** (your database schema, your design system)
- Knowledge is **one-time** (a specific edge case in story 42)
- Knowledge is **in flux** (still figuring out best practices)

---

## Common Skills for SaaS Projects

### Authentication & Security
- `@skills: clerk` — Clerk auth flows, webhooks
- `@skills: clerk-testing` — E2E auth testing
- `@skills: sharp-edges` — Security pitfalls (RLS, secrets, injection)

### Frontend
- `@skills: react-best-practices` — Performance, hooks patterns
- `@skills: composition-patterns` — Component design
- `@skills: web-design-guidelines` — Accessibility, UX
- `@skills: next-best-practices` — App Router, RSC

### Backend
- `@skills: api-design` — REST conventions (if available)
- `@skills: database-optimization` — Query tuning (if available)

### Code Review
- `@skills: differential-review` — Code quality checklist
- `@skills: bmad-editorial-review-prose` — Content clarity

---

## How Skills Are Loaded

### Option 1: Baked into Agent Config (Always Available)

**For Base Coders:**
```yaml
# agents/kiat-backend-coder.md
System Prompt includes:
  "You have access to @skills: sharp-edges for security checks"
  
Result: Every session, coder can reference security pitfalls
```

### Option 2: Dynamic Loading per Story

**In Story Spec:**
```markdown
# Story 42: Add 2FA

**Recommended Skills**:
- Backend: @skills: clerk-testing (understand Clerk webhooks)
- Frontend: @skills: clerk-testing (understand token refresh)

---
```

**In Coder Prompt:**
```
"Use @skills: clerk-testing to understand Clerk auth patterns before implementing."
```

### Option 3: Conditional Loading (Runtime Check)

**Example**: If story mentions "performance", load performance skill:
```
If story.keywords.includes("optimize"):
  prompt += "\n@skills: react-best-practices"
```

---

## Decision Matrix: Skill vs Local Doc

| Scenario | Use | Why |
|----------|-----|-----|
| "How do I structure a React component?" | @skills: react-best-practices | Reusable, Anthropic-maintained |
| "What colors are in our design system?" | design-system.md (local) | Project-specific, changes rarely |
| "How do I handle Clerk webhooks?" | @skills: clerk-testing | Clerk's official patterns |
| "What's our API error code scheme?" | api-conventions.md (local) | Project-specific, consistent |
| "How do I prevent SQL injection?" | @skills: sharp-edges | Security best practices, reusable |
| "What's the current wizard UX flow?" | story-NN.md (local) | Epic-specific, read fresh |

---

## Example: When to Load Skills

### Story 1: Basic CRUD Feature
```
Skills needed: None (CLAUDE.md + architecture.md sufficient)
```

### Story 2: Clerk Integration (Webhook Handling)
```
Skills: @skills: clerk-testing

Coder loads Clerk skill to understand:
  - Webhook signature validation
  - Event types (user.created, user.updated)
  - Token refresh flows
```

### Story 3: Optimize React List (1000+ items)
```
Skills: @skills: react-best-practices, @skills: composition-patterns

Coder loads skills to understand:
  - useCallback, useMemo patterns
  - Component composition (small reusable pieces)
  - Virtualization approaches
```

### Story 4: Code Review (before submission)
```
Skills: @skills: differential-review, @skills: sharp-edges

Reviewer loads skills to check:
  - Code quality patterns
  - Security pitfalls (RLS, secrets, injection)
```

---

## Anti-Pattern: Skill Overload

### ❌ What NOT to do:

```
Backend-Coder session:
  @skills: clerk, clerk-testing, sharp-edges, 
  @skills: api-design, database-optimization, 
  @skills: performance, monitoring, logging
  
  "Use all these skills to build story 42"
```

**Result**: Context explosion, distracted thinking, slower.

### ✅ What to do instead:

```
Backend-Coder session (normal story):
  CLAUDE.md + backend-architecture.md (baked in)
  (No extra skills)

Backend-Coder session (Clerk webhook story):
  @skills: clerk-testing (just this one)

Backend-Coder session (before submission):
  @skills: sharp-edges (security check)
  @skills: differential-review (code quality)
```

---

## Checklist: Before Launching Coder Session

- [ ] Story spec is clear ✅
- [ ] Necessary context is available (docs, templates, conventions) ✅
- [ ] Only load skills that are needed for THIS story ✅
- [ ] Don't load unrelated skills (saves tokens) ✅
- [ ] Document recommended skills in story spec ✅

---

## Custom Skills (Optional)

If you build a custom skill (e.g., "our-auth-patterns"):

1. Document it in `.claude/skills/our-auth-patterns.md`
2. When to use it: [describe scenarios]
3. Reference: [link to key patterns]
4. Update MEMORY.md to track custom skills

Example:
```markdown
# Custom Skill: our-auth-patterns

**When to use**: Stories involving user authentication beyond basic Clerk

**Patterns**:
- Session management (JWT + refresh tokens)
- Role-based access (editor, viewer, admin)
- Org switching (multi-tenant)
- API key auth (for service-to-service)

**Reference**: delivery/specs/auth-patterns.md
```

---

## Summary

| Pattern | Example | When |
|---------|---------|------|
| **Baked skill** | @skills: sharp-edges in coder config | Always useful, general security |
| **Story-recommended** | @skills: clerk-testing in story spec | Specific to this story |
| **Reviewer skill** | @skills: differential-review before review | Every code review |
| **Optional custom** | @skills: our-auth-patterns if available | Advanced scenarios |

---

**Next**: Read `reviewer-spec-access.md` to understand how reviewers stay synchronized with specs.
