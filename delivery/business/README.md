# Business / Domain Documentation

This directory holds the **stable business and domain documentation** for the project. It is separate from `delivery/specs/` (technical conventions) because it has a different cycle of life and a different author: BMAD (product/metier), not the tech-spec-writer.

## What goes here

Only evergreen, slowly-evolving documentation about **the business domain itself** — not about implementation. If the content would be equally valid whether the project were built in Go or TypeScript, it belongs here.

Suggested files (create them as the project grows — don't pre-create empty stubs):

| File | What it contains | When to create |
|---|---|---|
| `glossary.md` | Domain terms with precise definitions (what is a "patient", a "care plan", a "hypothesis"?) | As soon as the team uses any term that's ambiguous outside context |
| `personas.md` | User personas with goals, pain points, and constraints | Before building the first user-facing feature |
| `business-rules.md` | Invariant business rules (compliance, GDPR, audit, quotas) | As soon as any rule is non-obvious or could be forgotten |
| `domain-model.md` | Entities and their relations, at the **business** level (not the SQL schema) | Before the data model stabilizes |
| `user-journeys.md` | End-to-end flows from the user's perspective | Before building features that cross multiple pages/screens |

## What does NOT go here

- ❌ **Technical conventions** — those live in `delivery/specs/` (architecture, API design, design system, etc.)
- ❌ **Story specs** — those live in `delivery/epics/epic-X/story-NN.md` (written by the tech-spec-writer, one per story)
- ❌ **BMAD story briefs** — those live in the BMAD working directory (configure BMAD to write its per-story outputs into `delivery/epics/epic-X/` or a dedicated `delivery/bmad/` path, whichever your BMAD setup prefers)
- ❌ **Implementation details** — if the content only makes sense because of how the code is structured, it's technical, not business

## How the Kiat pipeline uses these files

`kiat-tech-spec-writer` reads the relevant file(s) from this directory **on demand** when a new story touches the corresponding domain. It does NOT load them ambiently — budget is finite, and most stories only need one or two of these.

Routing rules (same "load only what you need" principle as `delivery/specs/`):

- **New domain-touching feature** → read `glossary.md` + `domain-model.md`
- **New user-facing feature** → read `personas.md` + the relevant section of `user-journeys.md`
- **Compliance-sensitive work** → read `business-rules.md`
- **Refactor with no business impact** → read nothing from here

## Sizing discipline

Keep each file under ~5k tokens (~20 KB). If a file grows past that, split it by sub-domain (for example `business/patients/glossary.md`, `business/billing/glossary.md`). The tech-spec-writer's budget is not strictly capped, but feeding it 30k tokens of domain context on every story will drown the technical spec it's trying to write.

## Relationship with `project-memory.md`

[`delivery/specs/project-memory.md`](../specs/project-memory.md) is for **emergent cross-story patterns discovered during implementation** — things like "we decided to use `updated_at` for optimistic locking in story 7, so story 12 should follow the same pattern." It is project-owned but technical.

This directory is for **business knowledge that exists independently of any story** — things like "a patient can only be enrolled in one active care plan at a time, because French healthcare regulations require a single responsible provider." It is project-owned and business-level.

If you're not sure where a fact belongs: if removing the project and rebuilding it from scratch would still leave the fact valid, it's business (here). If the fact only exists because of how the code was written, it's project memory (specs/project-memory.md).
