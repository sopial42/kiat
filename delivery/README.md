# Delivery: Specs, Stories, Reviews

This directory contains the product roadmap, user stories, acceptance criteria, and code reviews.

---

## Structure

```
delivery/
├── README.md                         # This file
├── specs/                            # Project conventions (user-editable per project)
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
├── metrics/                          # Runtime data (written by Team Lead)
│   └── events.jsonl                  # JSONL event log
├── epic-N-name/                      # Per-epic folders
│   ├── _epic.md                      # Epic summary
│   └── story-NN-slug.md              # Story specs (written by BMAD)
└── epic-template/                    # Templates for new epics
    ├── _epic.md
    └── story-NN-slug.md
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

### 1. Create Epic Folder

```bash
mkdir delivery/epic-25-my-feature
cd delivery/epic-25-my-feature
```

### 2. Write Epic Header (`_epic.md`)

See `epic-template/_epic.md` for template.

```markdown
# Epic 25: My Big Feature

**Objective**: What problem does this solve?

**Scope**: What's IN? What's OUT?

**Timeline**: When should this be done?

**Team**: Who's building it?

**T-Shirt Size**: S / M / L / XL

---

## Stories

- Story 01: Feature component
- Story 02: API handler
- Story 03: Integration test
```

### 3. Write Stories (`story-NN-slug.md`)

See `epic-template/story-NN-slug.md` for template.

Each story has:
- **Objective**: What does this story deliver?
- **Acceptance Criteria**: How do we know it's done?
- **Technical Spec**:
  - Database changes (migration)
  - API contracts (request/response)
  - Frontend changes (components, hooks)
  - Edge cases (what can go wrong?)
- **Testing Plan**: E2E scenarios

### 4. Code Phase

- BMAD Master has written the spec ✅
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

Before code starts, human verifies spec is complete:

- [ ] Objective clear (1-2 sentences, problem statement)
- [ ] Acceptance criteria testable (each criterion = one test scenario)
- [ ] Database schema specified (if any DB changes)
- [ ] API contracts specified (request/response/errors)
- [ ] Frontend changes specified (components, hooks, styling)
- [ ] Edge cases called out (network fail, double-click, offline, etc.)
- [ ] Testing strategy outlined (what E2E scenarios?)
- [ ] Acceptance criteria match API contracts (no gaps)
- [ ] No obvious implementation gaps

**If any unchecked**: BMAD refines spec before code starts.

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

```
User/Client: "I want X"
    ↓
BMAD Master: Challenge + write spec
    ↓
Human: Review spec → "Looks good?"
    ↓
Backend-Coder + Frontend-Coder: Build in parallel
    ↓
Reviewers: Review code
    ↓
Tests: Pass ✅
    ↓
Human: Merge
```

---

**Let's build systematically. Specs → Code → Review → Merge. 🚀**
