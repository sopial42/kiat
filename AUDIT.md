# Kiat Context Audit

> One-shot snapshot of what Claude actually loads into context when working in a Kiat repo. Generated as a baseline for the `refactor/dx-context-trim` work. Numbers use a 4-bytes/token approximation.

---

## TL;DR

- **Cold session** (no agent): **~3.4k tokens** ambient (CLAUDE.md only). Good.
- **Team Lead session** (`claude --agent kiat-team-lead`): **~25k tokens before any work** (CLAUDE.md + kiat-team-lead.md). The team-lead file alone is **86 KB / 1 132 lines / ~21.5k tokens** — the single biggest item in the ambient pool.
- **Sub-agent invocation** (coder/reviewer): **10-15k tokens** baseline + on-demand specs per story.
- **No file is auto-loaded that shouldn't be.** EVOLUTION.md, `.claude/specs/*.md`, `delivery/specs/*.md`, the queue files are all on-demand — verified by grep against the agent frontmatters and CLAUDE.md.

The bottleneck is **agent-level**, not ambient-level. CLAUDE.md is already trim. The win is in **shrinking what Team Lead loads up-front**.

---

## 1. What is auto-loaded at cold start

Auto-loaded by Claude Code from project root, every session:

| File | Lines | Bytes | Tokens (≈) |
|---|---:|---:|---:|
| `CLAUDE.md` | 123 | 13 833 | 3 460 |
| **Total ambient** | **123** | **13 833** | **3 460** |

Nothing else is ambient. `README.md`, `kiat-getting-started.md`, `kiat-how-to.md`, `.claude/README.md`, `.claude/EVOLUTION.md` are documentation read by humans, not by Claude Code.

---

## 2. What is loaded when an agent is invoked

Per the frontmatter `name:` + `tools:` + `skills:` blocks of each agent file:

| Agent | File lines | File bytes | Skill auto-load | Total tokens (≈) |
|---|---:|---:|---|---:|
| `kiat-team-lead` | 1 132 | 88 069 | `kiat-validate-spec` (3.5 KB) | **~22 700** |
| `kiat-tech-spec-writer` | 491 | 40 960 | `kiat-validate-spec` | ~11 100 |
| `kiat-backend-coder` | 354 | 28 467 | `kiat-test-patterns-check` (variable, router + 9 blocks) | ~7 500 + skill |
| `kiat-frontend-coder` | 337 | 27 136 | `kiat-test-patterns-check` | ~7 200 + skill |
| `kiat-backend-reviewer` | (TBC) | 14 848 | none auto, `kiat-review-backend` runtime | ~3 700 |
| `kiat-frontend-reviewer` | 222 | 14 234 | none auto, `kiat-review-frontend` runtime | ~3 550 |

**Effective Team Lead boot**: `CLAUDE.md` + `kiat-team-lead.md` + `kiat-validate-spec/SKILL.md` ≈ **~26 200 tokens** before any user instruction is processed.

---

## 3. What is loaded on-demand during Team Lead flow

These files are referenced by `kiat-team-lead.md` and Read at specific phases. They are **not** auto-loaded; Team Lead must Read them explicitly via the `Read` tool.

| File | Bytes | Tokens (≈) | Loaded when |
|---|---:|---:|---|
| `.claude/specs/context-budgets.md` | 10 957 | 2 740 | Phase 0b |
| `.claude/specs/metrics-events.md` | 37 171 | 9 290 | Phase 5c, 5d, 6 (rollup write) |
| `.claude/specs/failure-patterns.md` | 6 963 | 1 740 | Pre-escalation only |
| `.claude/specs/reconciliation-protocol.md` | 43 314 | 10 830 | Phase 0.2, 0c, 5c, 5d |
| `.claude/specs/bmad-reconcile-contract.md` | 20 275 | 5 070 | Phase 5d |
| `.claude/specs/parallel-worktree-protocol.md` | 35 430 | 8 860 | Multi-session work only |
| `delivery/specs/cross-cutting-files.md` | (varies) | ~500 | Phase 0c, Phase 3 |
| `delivery/_queue/needs-human-review.md` | (varies) | ~200 | Phase 0c |
| `delivery/metrics/events.jsonl` | (varies, append-only) | tail-only | Phase 0.2, 6 |

**Realistic mid-flow Team Lead context** (story with deviations, real reconciliation): ~26k boot + ~22k on-demand specs = **~48k tokens before the story file itself**.

---

## 4. What is loaded on-demand by coders / reviewers

Per the `## Skills` section of each story + the coder's own frontmatter:

- Coder always loads: `kiat-test-patterns-check`, `delivery/specs/<layer>-conventions.md`, the story file
- Coder may load: any contextual skill the writer listed (`sharp-edges`, `differential-review`, etc.), per-domain pitfall doc, `clerk-patterns.md` if auth touched
- Reviewer always loads: `kiat-review-<layer>`, the story file, the coder's diff
- Reviewer may load: `kiat-clerk-auth-review` (hard trigger), `differential-review`

Typical coder context: 12-20k tokens. Typical reviewer context: 8-15k tokens. Within the documented budget (35k / 20k).

---

## 5. What is NOT auto-loaded (good)

Verified by grep against agent frontmatters and `CLAUDE.md`:

- `.claude/EVOLUTION.md` (696 lines, 41 KB) — referenced as a memo, never auto-loaded. Team Lead writes to it post-rollup but does not Read it during normal flow.
- `kiat-getting-started.md`, `kiat-how-to.md`, `.claude/README.md`, `README.md` — human-facing docs, not in any agent frontmatter.
- `delivery/business/`, `delivery/epics/` (other stories) — only the active story is loaded.
- `.claude/skills/bmad-*` — Bmad skills are invoked when a BMad session runs them; Kiat agents never auto-load them.

This part is well-designed. The "links are not Read-instructions" rule in `CLAUDE.md` is respected by every agent file inspected.

---

## 6. Cross-reference debt: phase numbering

`Phase -2 / -1 / 0a / 0b / 0c / 5b / 5c / 5d` are referenced 100+ times across 25 files:

```
./.claude/agents/kiat-team-lead.md            69 refs
./.claude/specs/reconciliation-protocol.md    31
./.claude/specs/bmad-reconcile-contract.md    19
./.claude/specs/metrics-events.md             15
./.claude/EVOLUTION.md                        13
./.claude/agents/kiat-tech-spec-writer.md     12
./delivery/epics/README.md                     7
./kiat-how-to.md                               6
./README.md                                    3
./CLAUDE.md                                    3
./.claude/README.md                            3
./.claude/agents/kiat-{back,front}end-coder.md  3 each
./delivery/business/README.md                  4
./delivery/epics/epic-00/story-01-*.md         4
./delivery/epics/epic-01/story-01-*.md         4
./delivery/epics/epic-template/story-NN-slug.md  3
./delivery/epics/epic-template/story-NN-slug.reconcile.md  2
./delivery/README.md                           3
./kiat-getting-started.md                      2
```

**Verdict**: a full rename of `-2/-1/0a/0b/0c/5b/5c/5d` to semantic names (`intake`, `spec-authoring`, `validation`, `closeout`, …) is a cross-cutting refactor touching 25 files including EVOLUTION.md (which is append-only history). Out of scope for the context-trim PR. Left as follow-up.

What this PR does instead: groups phases under **semantic stages** in the Team Lead orchestrator and the new modular files (`team-lead/intake.md`, `team-lead/spec-authoring.md`, etc.). The negative-phase numbers (`-2`, `-1`) are now flagged as historical accidents in the orchestrator's preamble.

---

## 7. Recommendations (executed in this PR vs. follow-up)

| Item | Action | This PR? |
|---|---|:---:|
| Split `kiat-team-lead.md` (1132 → ≤300 line orchestrator + 7 stage files) | Refactor | ✅ |
| Group phases under semantic stages (`intake`, `spec-authoring`, `validation`, `delivery`, `review`, `closeout`, `ship`) | Refactor | ✅ |
| Merge `kiat-how-to.md` content into README, delete the file | Refactor | ✅ |
| Keep `kiat-getting-started.md` as Phase B credentials detail | Status quo | ✅ |
| Keep `.claude/README.md` (framework contributor doc, different audience) | Status quo | ✅ |
| Trim `.claude/specs/metrics-events.md` (37 KB → ?) — Team Lead only needs the rollup schema, not the full v2 changelog | Refactor | ❌ follow-up |
| Trim `.claude/specs/reconciliation-protocol.md` (43 KB) | Refactor | ❌ follow-up |
| Full rename of phase numbers across 25 files | Refactor | ❌ follow-up |
| Add `triggers:` frontmatter to skills (gstack pattern) | Feature | ❌ follow-up |
| Slash commands (`/kiat-review`, `/kiat-ship`) for one-shot ops | Feature | ❌ follow-up |

---

## 8. Methodology

- Line counts: `wc -l` on each tracked file.
- Byte counts: `wc -c` on each tracked file.
- Token estimate: `bytes / 4` (a coarse but standard heuristic for English text + markdown).
- Load-mode classification: grep on agent frontmatters (`tools:`, `skills:`) + grep on `CLAUDE.md` for ambient pointers + reading each agent file body for explicit `Read(...)` references during flow.
- No actual session instrumentation was used — these are static-analysis estimates. The real number will vary with the model's tokenizer and tool-call overhead.
