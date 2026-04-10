# 🏗️ Architecture Decision Log

Why did we structure Kiat the way we did? This doc explains the reasoning.

---

## Doc Organization: "Who needs what?"

### Decision: Layered docs by specificity, not by tool

**What we did:**
- `CLAUDE.md` → general rules (read once, stable for weeks)
- `backend-architecture.md` → architectural patterns (read once, stable)
- `testing-patterns.md` → Playwright pitfalls (reference, updated as we discover issues)
- `story-NN.md` → THIS epic spec (read fresh, changes per story)

**Why NOT a single monolithic CLAUDE.md:**
- Agents have limited context windows. Baking everything into one prompt = bloat
- Different agents need different subsets (kiat-frontend-coder doesn't need database conventions)
- Separation of concerns: "rules of the road" ≠ "API conventions" ≠ "testing pitfalls"

**Why NOT docs in Linear/Wiki:**
- Single source of truth in version control (git blame tells you who changed what, when)
- No extra auth/API calls needed
- Agents can `@file-context` markdown files directly
- Specs tied to git history (spec version = commit hash)

---

## Agent Orchestration: "One master, parallel workers"

### Decision: BMAD Master as the orchestrator

**What we did:**
- Single `bmad-master.md` agent that challenges, writes specs, launches other agents
- No separate "challenge" agent or "spec writer" agent

**Why:**
- **Continuity**: Same agent understands full context (prior feedback → updated spec → knows what coders should do)
- **Client-facing**: You expose BMAD to clients (in a chat), they give feedback, BMAD updates specs → agents code new version
- **Simplicity**: One conversation thread per epic (not: challenge thread + spec thread + code thread = confusion)

**Alternative we rejected:**
- Separate agents for challenge/writing → agent A writes spec, agent B can't see why → duplicated thinking
- Multiple agents discussing → token waste, no convergence

---

## Context Injection: "Load only what you need"

### Decision: `@file-context` + `@skills` for focused agent sessions

**What we did:**
```
Backend-Coder receives:
  @file-context: story-NN.md (spec)
  @file-context: CLAUDE.md (rules)
  @file-context: backend-architecture.md (patterns)
  @skills: clerk, sharp-edges (dynamic)
```

NOT:
```
Backend-Coder receives:
  [Entire kotai codebase]
  [All 18 prior epics]
  [All docs concatenated]
```

**Why:**
- **Token efficiency**: 12-15k tokens per session vs 50k+ if we dumped everything
- **Faster thinking**: Agent focuses on task, not distracted by unrelated code
- **Easier to update**: If we change backend-architecture.md, new sessions pick it up automatically (no re-training)
- **Parallel scale**: 5 agents can run simultaneously without context explosion

**How it works:**
1. Coder needs to know: "How do I structure an API error?"
2. Coder reads `backend-architecture.md` (baked into their config)
3. If coder needs "How do I test Clerk token flow?" → `@skills: clerk-testing`
4. No need to include full Playwright docs unless coder is writing E2E tests

---

## Skill Orchestration: "Use skills for refactored knowledge"

### Decision: Skills are reusable, agent-loaded expertise

**What we did:**
- Coders load `@skills: clerk-testing` when writing auth tests (reuses Anthropic's Clerk expertise)
- Reviewers load `@skills: differential-review` when analyzing code diffs
- BMAD loads `@skills: bmad-editorial-review-prose` for content quality

**Why:**
- **Expertise reuse**: Clerk wrote the `clerk-testing` skill; we don't rewrite Clerk auth docs
- **Versioned expertise**: If Clerk updates patterns, we update the skill once → all agents benefit
- **Reduce custom docs**: Instead of writing 5k words on "how Clerk works", link to `@skills: clerk`

**When NOT to use skills:**
- Your custom business logic (go in CLAUDE.md or architecture.md)
- One-off patterns (write in story.md, not a skill)
- Extremely opinionated patterns (maybe document locally first, promote to skill later)

---

## Specs Ownership: "BMAD writes, reviewers read, coders code"

### Decision: `story-NN.md` is the single source of truth

**What we did:**
- BMAD Master writes: `delivery/epics/epic-X/story-NN-feature-name.md`
- Contains: objectives | acceptance criteria | API contracts | UI mockups | edge cases | migration steps
- Reviewers read the spec to check "Does code match this?"
- Coders read the spec to understand "What do I build?"

**Why NOT specs in Linear:**
- No version control (if we change the spec mid-sprint, no audit trail)
- Agents can't easily `@file-context` Linear issues (API complexity)
- Can't blame who wrote/updated what

**Why NOT specs in Figma/Confluence:**
- Same issue: no version control
- Harder for agents to parse (not plaintext)

**Why NOT specs scattered across CLAUDE.md + PRs + Slack:**
- Half the team doesn't see half the requirements
- Agents have to re-discover requirements each session

---

## Reviewer Access to Specs: "Direct file reference, not duplication"

### Decision: Reviewers get `@file-context: story-NN.md` directly

**What we did:**
```
Reviewer prompt:
  "Review this code against acceptance criteria: @file-context: delivery/epics/epic-X/story-NN.md"
  + actual code diff
  + checklist
```

NOT:
```
Reviewer prompt:
  "Here's the spec again: [entire story.md copied into prompt]
   Here's the acceptance criteria again: [copied]
   Here's the API contract again: [copied]"
```

**Why:**
- **No duplication**: Spec lives in ONE place
- **Freshness**: If BMAD updates spec, reviewer immediately sees new version
- **Token efficiency**: File-context is cheaper than copying
- **Audit trail**: Reviewer can see git history of spec changes

---

## Preventing Infinite Loops: "Convergence rules, not hope"

### Decision: Max 1 coder loop, max 1 reviewer loop, then escalate

**What we did:**
1. **Coder writes** → passes to reviewer
2. **Reviewer finds issues** → lists all issues in one message
3. **Coder reads issues** → **fixes ALL in one session** → passes back to reviewer
4. **Reviewer checks again**:
   - ✅ Issues resolved → unblock tests
   - ❌ Still issues → **human escalation** (spec was bad, or story is too big)

NOT:
```
Coder writes → Reviewer finds issue 1 → Coder fixes → Reviewer finds issue 2 → Coder fixes → ... [loop]
```

**Why:**
- **Convergence guarantee**: After 1 iteration, we either succeed or admit the spec needs re-work
- **Token efficiency**: Coder reads full feedback once, fixes everything once
- **Human judgment gate**: If loop breaks down → human decides: "Do we split story? Re-write spec?"

**Documented in**: `patterns/infinite-loop-prevention.md`

---

## Test Gate Automation: "CI blocks merge, agents fix failures"

### Decision: Playwright tests run in agent sessions + CI; CI is final gate

**What we did:**
1. **During development**: Coder runs tests locally/in agent session
2. **If fail**: Coder debugs + fixes + reruns (max 3 iterations)
3. **Before merge**: CI runs Playwright + backend Venom tests
4. **If CI fails**: Coder gets notified → fixes (no merge until ✅)
5. **If CI passes**: Human can merge

**Why NOT**: "Coder runs tests once, if pass → merge"
- Tests might have race conditions that only appear in CI
- Need CI as the "source of truth" (is this production-safe?)

**Why NOT**: "Human runs tests before merge"
- Slow, error-prone
- Better to automate

---

## Skill Loading Strategy: "Dynamic, not static"

### Decision: Skills loaded per-agent via @skills tag, not pre-baked

**What we did:**
```yaml
# agents/kiat-backend-coder.md
@skills: clerk, sharp-edges, api-conventions-from-local-docs
```

Agent loads Clerk skill automatically when initialized.

NOT:
```
Load ALL 50 Anthropic skills every time
```

**Why:**
- **Context efficiency**: Only load what the agent will use
- **Flexibility**: Can add `@skills: new-skill` mid-project without rewriting agent config
- **Discovery**: Can test new skills by adding to config

**How to decide "skill vs local doc":**
- **Skill**: Reusable, multi-project knowledge (Clerk auth, React patterns, n8n workflows)
- **Local doc**: Project-specific (your database schema, your design system colors, your API versioning)

---

## Monorepo vs Multi-repo: "One repo, clear boundaries"

### Decision: Monorepo with isolated agent contexts

**What we did:**
```
mono-repo/
├── backend/          (Go, agents see this)
├── frontend/         (Next.js, agents see this)
├── infra/            (Terraform, TBD)
├── kiat/             (This starter kit)
└── delivery/         (Specs, epics, shared by all agents)
```

**Why monorepo:**
- Easy to share context (kiat-backend-reviewer can check if schema matches frontend expectations)
- Single git history (one source of truth)
- Easier CI/CD (deploy backend + frontend together)

**Why isolated contexts:**
- Backend-Coder doesn't load entire frontend codebase (token waste)
- Frontend-Coder doesn't load backend Go code (can't read Go well)
- But both can read `delivery/specs/api-conventions.md` (API contract)

**If scale demanded multi-repo later:**
- Same pattern still works (specs in shared wiki, agents point to it via URLs)
- Increase test-integration scope (make sure services talk correctly)

---

## Clerk Auth: "Real auth in dev, test bypass available"

### Decision: Two modes, selected by environment variables

**What we did:**
- `make dev` → Real Clerk (internet required, production-like)
- `make dev-test` → Test auth bypass (offline OK, super-fast iteration)

**Why:**
- **Dev flexibility**: Sometimes you want real auth (test webhooks, test Clerk UI), sometimes you just want to code (offline, fast)
- **Test isolation**: Playwright tests use test auth (no Clerk rate limits, fast)
- **Production safety**: Backend rejects test auth in production (os.Exit(1))

---

## Checklist per Role: "Done" is unambiguous

### Decision: Each agent has explicit checklist

**What we did:**
```
checklists/kiat-backend-coder.md:
  - [ ] Migration written + reviewed by schema reviewer
  - [ ] Handler implemented (request → response contract matches spec)
  - [ ] Middleware added (if auth required)
  - [ ] Logging added (trace_id, structured)
  - [ ] Error handling (AppError pattern, not generic panic)
  - [ ] Tests passing (Venom)
  - [ ] No secrets in code
```

NOT:
```
Coder: "Is this done?"
Reviewer: "Eh, looks ok?"
```

**Why:**
- **No ambiguity**: Coder knows exactly what "done" means
- **Reviewer can audit**: "Did coder follow checklist?"
- **Easy to evolve**: If we discover new requirement, add to checklist

---

## Memory Management: "Shared across sessions, not per-agent"

### Decision: One `MEMORY.md` per project, all agents read/write

**What we did:**
```
kiat/.claude/MEMORY.md
  - [Key decisions](decisions.md)
  - [Common pitfalls](pitfalls-found.md)
  - [Client feedback patterns](client-feedback.md)
```

Each memory file has:
```yaml
---
name: When to use Clerk webhooks vs polling
description: Auth pattern decision for user sync
type: feedback
---

We originally polled every 5min → switched to webhooks after race condition.
**Why**: Polling missed updates during peak load
**How to apply**: Always use webhooks for user state sync, poll for read-heavy queries only
```

**Why:**
- **Cross-session learning**: Agent A discovers pitfall in session 1; Agent B (in session 2) reads it
- **Client feedback**: BMAD discovers client pain point → saves to MEMORY → coders avoid that UX pattern
- **Shared "aha!" moments**: Don't re-discover the same gotcha 5 times

---

## Summary: Decisions at a Glance

| Decision | What | Why |
|----------|------|-----|
| **Docs structure** | Layered by specificity, not concatenated | Smaller context, easier updates |
| **Agent orchestration** | One BMAD Master, parallel coders | Continuity, client-facing, simple |
| **Context injection** | `@file-context` + `@skills` | Token efficiency, focused thinking |
| **Skills** | Reusable, agent-loaded expertise | Leverage Anthropic libraries, versioned |
| **Specs** | Single `story-NN.md` per story | One source of truth, version-controlled |
| **Reviewer access** | Direct file-context, no duplication | Freshness, efficiency |
| **Loop prevention** | Max 1 coder loop, escalate after | Convergence guarantee |
| **Test gate** | CI final arbiter, agents debug failures | Automation + safety |
| **Skill loading** | Dynamic per-agent, not pre-baked | Context efficiency |
| **Repo structure** | Monorepo with isolated contexts | Easy sharing, clear boundaries |
| **Auth** | Real + test mode, toggle via env | Dev flexibility + safety |
| **Checklists** | Per-role explicit lists | No ambiguity |
| **Memory** | One shared MEMORY.md | Cross-session learning |

---

**Next**: Read `CLAUDE.md` for day-to-day coding rules.
