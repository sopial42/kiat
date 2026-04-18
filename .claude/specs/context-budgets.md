# Context Budgets: Per-Agent Token Limits

> **Why this exists:** Long context windows don't mean unlimited effective reasoning. Claude's reasoning quality degrades when the working set exceeds a sweet spot, and XL stories silently push agents past that point. A coder that starts with 80k tokens of context has fewer tokens *and fewer clear thoughts* left to do the actual coding. We enforce budgets **pre-flight** so oversized stories are split before they become silent failures.

This doc defines:
1. **Hard budgets per agent role** (input-side context, before the agent starts working)
2. **A simple counting heuristic** agents can apply without a tokenizer
3. **The overflow protocol** — what Team Lead does when a budget would be exceeded
4. **Budget anatomy** — how the budget is allocated across inputs

---

## Hard Budgets (Input Context Only)

These are caps on **injected input context** before an agent starts its own work. They do NOT count the agent's own reasoning, tool-call outputs, or written code — those belong to a separate "working budget."

| Agent | Max input context | Rationale |
|---|---|---|
| **Tech Spec Writer** | unrestricted | Writes story specs — reads business + project specs on demand; no downstream budget pressure on its own session. |
| **Team Lead** | **10k tokens** | Pure orchestration — spec + story metadata + recent review outputs. No codebase. |
| **Backend-Coder** | **25k tokens** | Spec + architecture-clean.md + backend-conventions.md + relevant specs + a few existing files for patterns. |
| **Frontend-Coder** | **25k tokens** | Spec + frontend-architecture.md + design-system.md + a few existing components. |
| **Backend-Reviewer** | **20k tokens** | Spec + kiat-review-backend skill + kiat-clerk-auth-review (if triggered) + code diff. |
| **Frontend-Reviewer** | **20k tokens** | Spec + kiat-review-frontend skill + kiat-clerk-auth-review (if triggered) + code diff. |

**Why not bigger?** Not because the model can't handle more, but because:
1. **Reasoning quality degrades** well before the 1M hard limit (observable around 60-100k of dense technical context)
2. **Agent output quality** correlates with how much "thinking budget" is left after the input context
3. **Cost** — every token injected is paid for on every turn of the conversation
4. **Retry cost** — when an agent fails, you're paying for the same context again

**Why these specific numbers?** Starting heuristic, **not calibrated**. The numbers above are initial guesses based on typical doc sizes for a mid-sized SaaS project (3-5k per convention doc, 2-4k per medium story spec, 3k per skill file, 3-8k per code diff). They MUST be re-calibrated per project.

**Calibration step for your project** (run this once before launching the first story):
```bash
# Measure all files a typical coder would load
wc -c CLAUDE.md \
      delivery/specs/<your-architecture-doc>.md \
      delivery/specs/testing.md \
      delivery/specs/<your-convention-docs>.md \
      delivery/epics/epic-1/story-01-<slug>.md \
  | tail -1
# Divide total bytes by 4 → token estimate
# If > 25k, either trim conventions or raise the budget
```

The 25k ceiling is a **working hypothesis**, not a measured truth. If your first few stories consistently run at ~18k, you have headroom and the budget is right. If they consistently hit 30k+, either your conventions are too verbose (trim them) or your stories are genuinely too large (`kiat-tech-spec-writer` splits them) or the budget itself needs adjustment — that's a calibration decision based on real data.

---

## Counting Heuristic (No Tokenizer Required)

Agents don't have a tokenizer at hand. Use this cheap approximation, accurate to ±20% which is fine for gating:

**Rule of thumb: `tokens ≈ bytes / 4`**

For English + code, 1 token averages ~3.5-4.5 bytes. Dividing bytes by 4 gives a slight over-estimate, which is the safe direction for a budget.

**How to count without reading the file contents:**
```bash
wc -c <file>        # bytes
# divide by 4 for token estimate
```

For multiple files:
```bash
wc -c file1 file2 file3 | tail -1
# "total" line, divide by 4
```

**Budget check pseudo-algorithm:**
```
total_bytes = sum of wc -c for all files that will be injected
estimated_tokens = total_bytes / 4
if estimated_tokens > budget:
    ABORT → overflow protocol
```

**Important exclusions:**
- Don't count the agent's *own* system prompt (that's ambient)
- Don't count files the agent can read *on demand* — only files injected at session start
- Do count the code diff for reviewers (it's injected, not read on demand)
- Do count skills if they're listed as REQUIRED in the agent definition

---

## Budget Anatomy: Where Does It Go?

A Backend-Coder's 25k budget generally splits into **two buckets**:

| Bucket | Typical share | What's in it |
|---|---|---|
| **Ambient context** (always loaded) | ~40-60% of budget | CLAUDE.md + backend architecture/conventions docs + testing rules |
| **Per-story context** (injected fresh) | ~30-50% of budget | The story spec, story-specific conventions (api/database/security), existing code references |
| **Headroom** | ~5-15% of budget | Reserve for reasoning, tool calls, small on-demand reads |

**The ambient context should never dominate.** If your CLAUDE.md + conventions sum to more than ~60% of the budget, you've built conventions that are too heavy for the budget to hold. Trim the conventions first, don't raise the budget.

**Measuring your actual anatomy:** run this on your project after a few stories have been executed. The values will tell you whether you need to trim docs or raise the budget.

```bash
# Ambient (always loaded by backend-coder)
wc -c CLAUDE.md \
      delivery/specs/backend-conventions.md \
      delivery/specs/architecture-clean.md \
      delivery/specs/testing.md

# Per-story (typical)
wc -c delivery/epics/epic-*/story-01.md \
      delivery/specs/api-conventions.md \
      delivery/specs/database-conventions.md
```

**Red flags in measurement:**
- Ambient > 15k tokens → conventions are bloated; trim ruthlessly
- Per-story > 10k tokens → either story specs are too ambitious (ask `kiat-tech-spec-writer` to split them) or conventions are being double-loaded
- Ambient + per-story > 22k with zero headroom → you'll hit overflow on any above-average story; reduce one or the other

---

## Overflow Protocol (When Budget Is Exceeded)

**Team Lead runs the pre-flight check before launching ANY coder.** If the estimated input context exceeds the agent's budget, the protocol is:

### Step 1 — Identify the overflow culprit
Show the breakdown:
```
Story: story-27-item-bulk-import
Target: Backend-Coder (budget: 25k)
Estimated: 34k tokens

Breakdown:
- CLAUDE.md:                    ~3k
- architecture-clean.md:        ~5k
- testing.md:                   ~4k
- story-27-item-bulk-import:    ~11k ← SPEC IS OVERSIZED
- api-conventions.md:           ~3k
- database-conventions.md:      ~2k
- Existing item code refs:      ~6k ← TOO MANY REFS
Total:                          ~34k (BUDGET: 25k, OVER BY 9k)
```

### Step 2 — Decide: split or trim?

| Culprit | Action |
|---|---|
| **Spec > 6k tokens** | Escalate to `kiat-tech-spec-writer`: *"Story is too large for one coder session. Split into N sub-stories with distinct acceptance criteria."* |
| **Too many code references** | Trim to the 2-3 most representative; coder can read more on demand |
| **Ambient docs dominant, story small** | Budget is calibrated wrong — adjust this file, not the story |
| **Mixed (spec slightly too big + code refs slightly too big)** | Try trimming refs first; if still > budget, escalate to `kiat-tech-spec-writer` |

### Step 3 — Escalate to the tech-spec-writer with a concrete ask
When the spec itself is the overflow culprit, Team Lead escalates **before** launching any coder:

```
To kiat-tech-spec-writer:
Story story-27-item-bulk-import exceeds the Backend-Coder context budget
(34k estimated vs 25k hard limit). The spec is ~11k tokens.

Request: split this story into smaller sub-stories with distinct acceptance
criteria. Suggested split axes:
  - story-27a: bulk CSV upload + parsing (validation only)
  - story-27b: bulk insert with dedup + RLS
  - story-27c: error reporting UI

Each sub-story should land at ≤ 5k tokens of spec.
```

**Rule**: Team Lead NEVER launches a coder with an overflowing context "to see if it works." That's how silent failures ship. The budget is a hard gate.

---

## Coder Self-Check (Defense In Depth)

Even with Team Lead's pre-flight check, coders should self-verify on startup:

1. At session start, estimate the total bytes of injected files
2. Divide by 4 for token estimate
3. If estimate exceeds your budget (25k for coders, 20k for reviewers):
   - **STOP** — do not start coding
   - Report to Team Lead: *"Context budget exceeded: estimated Xk tokens vs budget Yk. Breakdown: [...]"*
   - Wait for Team Lead to escalate to `kiat-tech-spec-writer`

This is defense in depth — if Team Lead mis-counts or a file grows between pre-flight and launch, the coder catches it.

---

## Working Budget (Output + Reasoning)

Separate from the input budget, every agent gets an implicit **working budget** for its own reasoning, tool calls, and output. This is NOT enforced directly — it's a guideline:

| Agent | Suggested working budget | What it buys |
|---|---|---|
| Backend-Coder | 30-50k | Code generation, test generation, tool calls to read files |
| Frontend-Coder | 30-50k | Component code, E2E tests, design iteration |
| Reviewers | 10-20k | Reading + checklist + output |

If a coder runs out of working budget mid-session, they should **commit what they have, report status, and escalate** rather than write degraded code in the last few thousand tokens.

---

## Counter-Indications & Gotchas

- **Don't count skill files twice.** If a skill is listed in the agent definition, it's counted once at session start — not every time it's invoked.
- **Don't count files read via Bash/Read tools mid-session.** Those land in the *working* budget, not the input budget.
- **Do count the code diff for reviewers.** The diff is injected context, not on-demand.
- **Story specs grow over time.** A story that was 3k tokens when written may be 7k after clarifications. Always re-check before launch, not just once.
- **The budget is for the INITIAL context, not the full conversation.** Long conversations naturally exceed budgets; that's fine because the model prioritizes recent turns. The budget prevents *starting* overloaded.

---

## Future Hardening

If drift is observed in practice:
1. Add a pre-commit hook that computes the story spec's byte size and warns if > 20k bytes (5k tokens)
2. Add a CI step that rejects PRs introducing story specs > 6k tokens
3. Instrument Team Lead to log pre-flight estimates vs actual turn counts, calibrate budgets empirically over time
