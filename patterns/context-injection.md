# Pattern: Context Injection for Agents

**Problem**: Agents need to know about specs, architecture, testing patterns, etc. But if we dump the entire codebase into every prompt, we waste tokens and agents get distracted.

**Solution**: Smart context injection — agents load only what they need, when they need it.

---

## The Strategy: Layered Context

### Layer 1: Static Context (Baked into agent config)

**What**: Stable docs that don't change per-story

**Included in**:
- Backend-Coder: `CLAUDE.md`, `backend-architecture.md`, `testing-patterns.md`
- Frontend-Coder: `CLAUDE.md`, `frontend-architecture.md`, `testing-patterns.md`, `clerk-patterns.md`
- Reviewers: `CLAUDE.md`, checklist, architecture docs

**Why**: These docs are read-heavy. Agents benefit from having them available, but they don't change per-story.

**How to use**:
```yaml
# .claude/agents/kiat-backend-coder.md
# Agent system prompt includes:
# "You have access to these files:"
# - backend-architecture.md (routing, handlers, ORM patterns)
# - testing-patterns.md (Venom test structure)
```

---

### Layer 2: Story-Specific Context (Injected fresh per session)

**What**: Spec + design system + conventions (changes per-story)

**Injected into**:
- Backend-Coder: `delivery/epic-X/story-NN.md` + `delivery/specs/api-conventions.md` + `delivery/specs/database-conventions.md`
- Frontend-Coder: `delivery/epic-X/story-NN.md` + `delivery/specs/design-system.md`
- Reviewers: `delivery/epic-X/story-NN.md` + code diff + checklist

**Why**: Each story is different. New context per session keeps agents focused.

**How to use**:
```
Frontend-Coder session:
  "Here's the spec for this story: @file-context: delivery/epic-25/story-03-hypothesis-photos.md
   
   You also have access to the design system: @file-context: delivery/specs/design-system.md
   
   Read the spec first, understand acceptance criteria, then implement."
```

---

### Layer 3: On-Demand Context (Load when needed)

**What**: Specialized docs loaded via `@skills` only when relevant

**Skills examples**:
- `@skills: clerk-testing` — For auth-related features (if story involves signup/login)
- `@skills: react-best-practices` — For performance-heavy components
- `@skills: sharp-edges` — Before code submission (check for security pitfalls)
- `@skills: bmad-editorial-review-prose` — BMAD before finalizing specs

**Why**: Not every story needs every skill. Only load expertise when you'll use it.

**How to use**:
```
Backend-Coder session (normal story):
  No special skills needed. Build the handler.

Backend-Coder session (Clerk-related feature):
  "Before building the auth handler, load @skills: clerk-testing
   to understand Clerk webhook patterns."

Reviewer session (code review):
  "Use @skills: differential-review to check code quality.
   Use @skills: sharp-edges to check for security pitfalls."
```

---

## What NOT to Include (Context Bloat)

### ❌ Don't include:
- Entire codebase (just the changed files + tests)
- All prior epics (only relevant ones via summary)
- Full git history (maybe 1-2 recent commits for context)
- All testing pitfalls (summary in testing-patterns.md, not all 26)
- Design mockups as images (link to Figma, describe in text)

### ✅ Do include:
- Acceptance criteria (what's "done"?)
- API contracts (exact request/response shapes)
- Database schema changes (what fields? what types?)
- Design specs (colors, spacing, components)
- Edge cases (what can go wrong?)

---

## Pattern: How Coders Access Specs

### For Backend-Coder:

**Session start:**
```
User: "Story 42 is ready to code: https://github.com/...tree/story-42"

Backend-Coder:
  1. Read spec: @file-context: delivery/epic-25/story-42-webhook-handler.md
  2. Extract: POST /webhooks/clerk → authenticate → process event → save to DB
  3. Check API contract: "What fields in request? What response?"
  4. Plan: Migration? Handler? Service method? Tests?
  5. Ask: "Any clarifications before I start?" (chat)
  6. Code: Follow plan
  7. Test: Run Venom, ensure all pass
  8. Handoff: "Backend ready at branch story-42"
```

**If spec is unclear:**
```
Backend-Coder: "Spec says 'handle webhook events' but doesn't specify which Clerk event types (user.created? user.updated?). Clarify?"

BMAD Master (in same chat): "Oh, it's user.created and user.updated. I'll update the spec."

Backend-Coder: "Thanks, proceeding with those two events."
```

### For Frontend-Coder:

**Session start:**
```
Frontend-Coder:
  1. Read spec: @file-context: delivery/epic-25/story-42-photo-upload.md
  2. Read design: @file-context: delivery/specs/design-system.md
  3. Extract: Button to upload photo → validate file size → show progress → display preview
  4. Check: Component library? Hook patterns? Error handling?
  5. Plan: Component? Hook? Tests?
  6. Code: Follow plan
  7. Test: Run Playwright, ensure all pass
  8. Handoff: "Frontend ready at branch story-42"
```

### For Reviewers:

**Review session:**
```
Reviewer:
  1. Read spec: @file-context: delivery/epic-25/story-42-webhook-handler.md
  2. Read checklist: @file-context: checklists/kiat-backend-reviewer.md
  3. Read code diff: [coder provides git show output or links to diff]
  4. Audit:
     - Does code match spec?
     - Does migration exist?
     - Are tests comprehensive?
     - Any security issues?
  5. Report: List of issues (or "Approved")
```

---

## Pattern: Reviewer Spec Access

**Key principle**: Reviewer sees spec via file-context, not copied into prompt.

**Why**:
- If spec is updated by BMAD, reviewer immediately sees new version
- No duplication (one source of truth)
- Smaller prompt (file-context is cheaper than copying)

**How it works**:
```
Reviewer prompt template:
  "Here's the spec you're reviewing against: @file-context: delivery/epic-X/story-NN.md
   
   Here's the code diff: [git diff output]
   
   Here's your checklist: @file-context: checklists/kiat-backend-reviewer.md
   
   Does the code implement the spec correctly?"
```

**If spec is updated mid-review:**
```
BMAD Master: "Updated story-42.md to clarify webhook event types."

Backend-Reviewer (next review session): Automatically sees updated spec via file-context.

No re-review needed. Coder sees update in next session.
```

---

## Pattern: Skill Loading per Agent

**Decision**: Some skills are per-agent, some are per-story.

### Always-included skills (per-agent):
- Backend-Coder: None (base Go knowledge in training)
- Frontend-Coder: `react-best-practices` (loaded by default)
- Reviewers: `differential-review` (loaded by default)

### Story-specific skills (dynamic):
- If story is: "Add 2FA" → Load `@skills: clerk-testing`
- If story is: "Optimize React list" → Load `@skills: react-best-practices` + `composition-patterns`
- If story is: "Add payment integration" → Load `@skills: stripe` (if available)
- Before review: Always load `@skills: sharp-edges` (security check)

**How to document**:
```markdown
# Story 42: Add Webhook Handler

...acceptance criteria...

## Implementation Notes
- Backend-Coder should load: `@skills: clerk` (for webhook validation)
- Consider loading: `@skills: sharp-edges` (security review before submitting)
```

---

## Anti-Pattern: Context Explosion

### ❌ What NOT to do:

```
Backend-Coder prompt:
  [Entire CLAUDE.md copied]
  [Entire backend-architecture.md copied]
  [Entire testing-patterns.md copied]
  [All prior 10 epics as summary]
  [Full codebase tree]
  [Spec for story 42]
  [Specs for stories 41, 43, 44 (nearby stories)]
  
  "Go build story 42"
```

**Result**: 50k+ tokens of context, coder is distracted, slow thinking.

### ✅ What to do instead:

```
Backend-Coder prompt:
  "Your context includes: CLAUDE.md, backend-architecture.md, testing-patterns.md (baked in).
   
   Here's the spec for THIS story: @file-context: story-42.md
   
   Here's the API convention doc (for reference): @file-context: delivery/specs/api-conventions.md
   
   Go build story 42. Ask if anything is unclear."
```

**Result**: 12-15k tokens focused on the task at hand, faster thinking, better code.

---

## Checklist: Before Launching an Agent Session

- [ ] Agent has static context (CLAUDE.md, architecture.md)
- [ ] Agent has story-specific context (story-NN.md)
- [ ] Agent has design system context (if frontend)
- [ ] Agent has the right skills loaded (@skills: correct for this task)
- [ ] Agent doesn't have: full codebase, all prior epics, unrelated docs
- [ ] Spec is clear enough for agent to start (or agent will ask for clarification)

---

## Summary

| What | Where | When | Why |
|------|-------|------|-----|
| **CLAUDE.md** | Baked into agent | Always available | Rules of the road, stable |
| **Architecture.md** | Baked into agent | Always available | Patterns, stable |
| **Testing-patterns.md** | Baked into agent | Always available | Pitfalls, stable |
| **Story-NN.md** | Injected fresh | Per-session | Spec, story-specific |
| **Design-system.md** | Injected (frontend) | Per-session | Colors/spacing, reference |
| **API-conventions.md** | Injected (backend) | Per-session | REST design, reference |
| **@skills: X** | Loaded on-demand | Per-task | Specialized expertise |
| **Code diff** | Provided to reviewer | Review session | Code to check |
| **Checklist.md** | Injected to reviewer | Review session | What to check |

---

**Next**: Read `infinite-loop-prevention.md` to understand how agents avoid reviewer ping-pong.
