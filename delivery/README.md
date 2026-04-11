# Delivery: Specs, Stories, Reviews

This directory contains the product roadmap, user stories, acceptance criteria, and code reviews.

---

## Structure

```
delivery/
├── README.md                         # This file
├── specs/                            # Technical conventions (architecture, design system, etc.)
│   ├── api-conventions.md            # REST design, error codes, status codes
│   ├── architecture-clean.md         # Clean Architecture 4 layers
│   ├── backend-conventions.md        # Project structure, naming, logging
│   ├── clerk-patterns.md             # Clerk auth flows
│   ├── database-conventions.md       # Migrations, RLS, timestamps
│   ├── deployment.md                 # Env vars, modes, production guards
│   ├── design-system.md              # Colors, spacing, typography, Tailwind
│   ├── frontend-architecture.md      # React patterns, hooks, accessibility
│   ├── git-conventions.md            # Branches, commits, PR discipline
│   ├── project-memory.md             # Emergent cross-story patterns (coherence)
│   ├── security-checklist.md         # OWASP, RLS testing
│   ├── service-communication.md      # DI patterns
│   └── testing.md                    # Anti-flakiness rules (+ CI gate)
├── business/                         # Business / domain documentation (written by BMad)
│   ├── README.md                     # What goes here + BMad writing protocol (business/)
│   ├── glossary.md                   # Domain terms (create on demand)
│   ├── personas.md                   # User personas (create on demand)
│   ├── business-rules.md             # Compliance / invariants (create on demand)
│   ├── domain-model.md               # Entities + relations at business level (create on demand)
│   └── user-journeys.md              # End-to-end flows (create on demand)
├── epics/                            # The backlog (Jira-equivalent)
│   ├── README.md                     # Two-layer story model + BMad writing protocol (epics/)
│   ├── epic-template/                # Templates for new epics
│   │   ├── _epic.md                  # Both layers: Business Context (BMad) + technical
│   │   └── story-NN-slug.md          # Both layers: Business Context (BMad) + technical
│   └── epic-N-name/                  # Per-epic folders (two authors, two layers)
│       ├── _epic.md                  # BMad writes Business Context; tech-spec-writer enriches
│       └── story-NN-slug.md          # BMad writes Business Context; tech-spec-writer enriches
└── metrics/                          # Runtime data (written by Team Lead only)
    └── events.jsonl                  # JSONL rollup event log
```

---

## Common Commands

### Local Development

| Command | What it does |
|---|---|
| `make dev` | Real Clerk auth (internet required). Use for Playwright E2E and manual QA. |
| `make dev-test` | Test auth bypass (offline-capable). Use for Venom tests and rapid iteration. |
| `make stop` | Stop all dev processes. |
| `make wipe` | Full cleanup (containers, volumes, state). |

### Backend

| Command | What it does |
|---|---|
| `make test-back` | Run all Venom tests. |
| `go test ./backend/...` | Run a specific subset of Go tests. |
| `grep trace_id logs/` | Find a request in structured logs by trace ID. |

### Frontend

| Command | What it does |
|---|---|
| `npm run test:e2e` | Run Playwright E2E tests locally. |
| `npm run build` | Check for TypeScript / build errors (prerequisite for CI). |
| `npm run dev` | Local dev (real Clerk). |
| `npm run dev-test` | Local dev (test auth bypass). |

### Kiat framework

| Command | What it does |
|---|---|
| `python3 kiat/.claude/tools/report.py` | Generate weekly health report from `delivery/metrics/events.jsonl`. |
| `python3 kiat/.claude/tools/report.py --since 2026-04-01` | Filter report by date. |
| `python3 kiat/.claude/tools/report.py --epic epic-3` | Filter report by epic. |
| `python3 kiat/.claude/tools/report.py --validate` | Schema-check the events file (CI-friendly). |
| `python3 kiat/.claude/tools/doc-audit.py` | Audit `delivery/specs/` against M1 (tokens) + M2 (structure ratio). |
| `python3 kiat/.claude/tools/doc-audit.py --strict` | Exit 1 if any doc fails (use in pre-commit or CI). |

**Note:** environment variables, production safety guards, and deployment details live in [specs/deployment.md](specs/deployment.md).

---

## Epic Workflow

> **Full contract lives in [`epics/README.md`](epics/README.md) and [`business/README.md`](business/README.md).** This section is a high-level summary. Read the two folder READMEs for the authoritative rules on what BMad and the tech-spec-writer each write.

### 1. Create Epic Folder (BMad, Plan mode)

BMad copies [`epics/epic-template/`](epics/epic-template/) into a new `epics/epic-NN-my-feature/` folder and fills in the `## Business Context` section of `_epic.md`. It proposes the epic number + name before writing — always wait for the user's green light before BMad creates the directory.

### 2. Draft stories (BMad, Plan mode)

For each story that belongs to the epic, BMad copies `story-NN-slug.md` from the template and fills in **only** the `## Business Context` section (user story, personas, user-facing acceptance criteria, links to `delivery/business/`, business rationale). The technical sections remain templated. BMad never writes below the `## Business Context` boundary.

### 3. Enrich stories with the technical layer (tech-spec-writer, enrichment mode)

The user invokes `kiat-tech-spec-writer` on the story file. The writer detects the pre-existing `## Business Context`, preserves it intact, reads the linked `delivery/business/` files + relevant `delivery/specs/` conventions, and appends `## Skills` + `## Acceptance Criteria (technical)` + Backend / API / Frontend / Database / Edge cases / Tests. It self-validates via `kiat-validate-spec` before reporting back.

**Fast path** — for pure technical work (refactors, bug fixes), skip steps 1-2 and go straight to the tech-spec-writer in greenfield mode. It writes both layers itself from the user's informal request.

### 4. Code Phase

- Both story layers are populated ✅ (`kiat-validate-spec` reports `SPEC_VERDICT: CLEAR`)
- `kiat-team-lead` runs Phase 0a (re-validate) + Phase 0b (pre-flight budget) ✅
- Backend-Coder builds `story-NN.md` backend code
- Frontend-Coder builds `story-NN.md` frontend code (parallel)

### 5. Review Phase

**After coding:**
- Backend-Reviewer reviews backend code → writes `story-NN-slug.review-back.md`
- Frontend-Reviewer reviews frontend code → writes `story-NN-slug.review-front.md`

**Review file format:**
```markdown
# Review: Story NN - [Slug]

**Reviewer**: [name]
**Date**: [date]
**Status**: ✅ Approved / ❌ Changes Requested

## Summary
[Brief overview of what was reviewed]

## Findings

### Blockers (must fix)
- [ ] Issue 1
- [ ] Issue 2

### Majors (should fix)
- [ ] Issue 3

### Minors (nice to have)
- [ ] Issue 4

---

[Detailed feedback]
```

### 6. Merge Phase

- Tests passing ✅
- Code reviewed ✅
- Human approves → Merge

---

## Conventions

### Epic Naming
- `epic-NN-description` (number sequentially: 1, 2, 3...)
- Hyphenated, lowercase
- Examples: `epic-1-landing`, `epic-25-wizard-step-1`

### Story Naming
- `story-NN-slug.md` (NN = 01, 02, 03... within epic)
- Story title in slug form
- Examples: `story-01-patient-form.md`, `story-03-e2e-tests.md`

### Review Naming
- `story-NN-slug.review-front.md` (frontend review)
- `story-NN-slug.review-back.md` (backend review)
- One per story per domain (if both frontend and backend changed)

### Dates
- ISO 8601 format: `2026-04-09`
- Always use absolute dates, not relative ("2026-04-09", not "today")

---

## Spec Completeness Checklist

Before code starts, the human verifies that **both story layers** are complete. `kiat-validate-spec` runs this mechanically at Phase 0a, but the human can sanity-check it too.

**Business layer** (written by BMad — check against [`epics/README.md`](epics/README.md) and [`business/README.md`](business/README.md) for the full contract):
- [ ] `## Business Context` exists with user story, personas, user-facing acceptance criteria, business rationale
- [ ] Linked `delivery/business/` entries are real (no broken anchors)
- [ ] User-facing acceptance criteria are observable ("user can see X") — not technical ("API returns 200 with X")

**Technical layer** (written by `kiat-tech-spec-writer`):
- [ ] `## Skills` section lists the contextual skills the story needs (or "No additional skills required")
- [ ] Every user-facing acceptance criterion maps to a technical check (HTTP / DB / UI assertion)
- [ ] Database schema specified (if any DB changes)
- [ ] API contracts specified (request / response / errors)
- [ ] Frontend changes specified (components, hooks, styling)
- [ ] Edge cases called out (network fail, double-click, offline, etc.)
- [ ] Testing strategy outlined (what E2E scenarios? Venom cases?)
- [ ] No obvious implementation gaps

**If the business layer is incomplete**: ask BMad to refine it (in Plan mode). **If the technical layer is incomplete**: re-run `kiat-tech-spec-writer` in enrichment mode. Do not proceed to code until both layers pass.

---

## Review Completeness Checklist

After code review, human verifies review is thorough:

- [ ] Spec compliance checked (code matches acceptance criteria)
- [ ] Tests verified (E2E passing, coverage OK)
- [ ] Security checked (RLS, secrets, input validation)
- [ ] Code quality checked (naming, patterns, error handling)
- [ ] Accessibility checked (labels, ARIA, keyboard nav)
- [ ] Performance checked (no N+1, no unnecessary renders)
- [ ] All issues listed (not hiding problems)
- [ ] Issues grouped and prioritized (blockers vs majors vs minors)

---

## Example: Complete Story

### Epic 25: Hypothesis Photos

**`_epic.md`:**
```markdown
# Epic 25: Hypothesis Photos

**Objective**: Allow users to photograph hypothesis areas for visual reference.

**Scope**: 
- IN: Capture, compress, upload, display in lightbox
- OUT: Batch upload, AI tagging

**Timeline**: 2 weeks
**Team**: 1 backend, 1 frontend
**T-Shirt Size**: M
```

**`story-01-photo-upload.md`:**
```markdown
# Story 01: Photo Upload & Compression

### Acceptance Criteria
- [ ] User can click "Upload Photo" button
- [ ] File picker opens (image files only, max 20MB)
- [ ] Image compressed to 1280px max width
- [ ] Progress shown during upload
- [ ] Success: photo appears in UI
- [ ] Error: clear error message shown

### Technical Spec

#### Database
- Migration: Create `hypothesis_photos` table
  - photo_id UUID
  - hypothesis_id UUID (FK)
  - file_url VARCHAR (S3 URL)
  - file_size INT
  - created_at TIMESTAMPTZ
  - user_id UUID (for RLS)

#### API
- POST /hypotheses/:id/photos (multipart/form-data)
  - Request: file (image)
  - Response 201: { photo_id, file_url }
  - Error 400: "File too large (max 20MB)"
  - Error 413: Payload Too Large

#### Frontend
- Component: PhotoUploadButton
- Hook: usePhotoUpload (compression, S3 upload)
- UI: File picker, progress bar, error display

#### E2E Tests
- Upload 5MB JPEG → stored ✅
- Upload 25MB file → error 413 ✅
- Network error → retry ✅

---
```

**After code:**
- `story-01-photo-upload.review-back.md` (backend review)
- `story-01-photo-upload.review-front.md` (frontend review)

---

## Tips

1. **Write specs BEFORE coding** — Agents need clarity
2. **Be specific** — "Add photo upload" vs "Create POST /hypotheses/:id/photos with compression"
3. **Include edge cases** — Network fail, double-click, offline, file type mismatch
4. **Link to conventions** — Don't re-explain REST design, link to `specs/api-conventions.md`
5. **Use checklists** — Reviewers can verify completeness systematically

---

## Feedback Loop

Two-layer pipeline: **BMad** shapes the business layer, **kiat-tech-spec-writer** enriches it with the technical layer, then the Kiat pipeline executes the story. See [`business/README.md`](business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad) and [`epics/README.md`](epics/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad) for the BMad writing protocol (4 modes, decision trees, rules).

```
User: informal product thinking ("I want X", "users struggle with Y")
    ↓
BMad (product / business layer)
    • Capture mode → evergreen facts land in delivery/business/
    • Plan mode    → epic + story Business Context land in delivery/epics/
    ↓
kiat-tech-spec-writer (technical layer — enrichment mode)
    • reads the ## Business Context (preserves it intact)
    • reads linked delivery/business/ and delivery/specs/ docs
    • appends Skills, Backend, Frontend, Database, Edge cases, Tests
    • self-validates with kiat-validate-spec
    ↓
Human: launches kiat-team-lead on the story
    ↓
Team Lead: Phase 0a (re-validate) + 0b (pre-flight budget)
    ↓
Backend-Coder + Frontend-Coder: Build in parallel
    ↓
Reviewers: 3-way verdict (APPROVED / NEEDS_DISCUSSION / BLOCKED)
    ↓
Tests: Pass ✅
    ↓
Team Lead: emit rollup event → events.jsonl
    ↓
Human: Merge
```

**Boundary**: BMad writes only inside `delivery/business/` and the `## Business Context` sections of `delivery/epics/`. It never touches `delivery/specs/` (technical conventions), `.claude/` (framework machinery), or the technical sections of story files. The tech-spec-writer writes only the technical layer of story files and never modifies a `## Business Context` section written by BMad. Each folder's README enforces its own half of the contract.

---

**Let's build systematically. Specs → Code → Review → Merge. 🚀**
