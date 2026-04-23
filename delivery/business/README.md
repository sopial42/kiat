# Business / Domain Documentation

This directory holds the **stable business and domain documentation** for the project. It is separate from `delivery/specs/` (technical conventions) because it has a different cycle of life and a different author: BMAD (product/metier), not the tech-spec-writer.

## What goes here

Only evergreen, slowly-evolving documentation about **the business domain itself** — not about implementation. If the content would be equally valid whether the project were built in Go or TypeScript, it belongs here.

Suggested files (create them as the project grows — don't pre-create empty stubs):

| File | What it contains | When to create |
|---|---|---|
| `glossary.md` | Domain terms with precise definitions (terms that are ambiguous outside your domain — e.g. does "order" mean a purchase order or a sort order?) | As soon as the team uses any term that's ambiguous outside context |
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

Keep each file under ~5k tokens (~20 KB). If a file grows past that, split it by sub-domain (for example `business/orders/glossary.md`, `business/billing/glossary.md`). The tech-spec-writer's budget is not strictly capped, but feeding it 30k tokens of domain context on every story will drown the technical spec it's trying to write.

## Relationship with `project-memory.md`

[`delivery/specs/project-memory.md`](../specs/project-memory.md) is for **emergent cross-story patterns discovered during implementation** — things like "we decided to use `updated_at` for optimistic locking in story 7, so story 12 should follow the same pattern." It is project-owned but technical.

This directory is for **business knowledge that exists independently of any story** — things like "a customer can have at most one active subscription at a time, because our billing provider enforces it upstream." It is project-owned and business-level.

If you're not sure where a fact belongs: if removing the project and rebuilding it from scratch would still leave the fact valid, it's business (here). If the fact only exists because of how the code was written, it's project memory (specs/project-memory.md).

## Relationship with `delivery/epics/`

BMad writes the **business layer** of each epic and story directly into `delivery/epics/epic-X/`, specifically in the `## Business Context` section at the top of each `story-NN.md` file (and a parallel section in `_epic.md`). The `kiat-tech-spec-writer` agent then reads that Business Context and adds the technical layers below it, without modifying the Business Context itself.

The docs in this directory (`delivery/business/`) serve as the **stable reference** that the Business Context of each story can link to: instead of duplicating a persona description, a glossary term, or a business rule inside the story, BMad writes `[<persona>](../../business/personas.md#<anchor>)` and points at the evergreen version here. One source of truth per concept; the story file is the composition point.

In short:
- `delivery/business/*.md` — evergreen, slowly-evolving domain knowledge (referenced by many stories)
- `delivery/epics/epic-X/story-NN.md` → `## Business Context` — the business layer specific to one story, which points at the evergreen files above for shared concepts

## Language convention

The content of `delivery/business/` reflects the **project's business language**, which is a project-level choice. For projects whose domain, users, or regulations are expressed in a non-English language (French RGPD, Spanish commerce regulations, German engineering vocabulary, etc.), writing this content in that language preserves nuances that English translation would flatten. For international projects, English is the natural default.

The `kiat-tech-spec-writer` agent reads these files regardless of language. When it writes the technical sections of a story (everything below `## Business Context`), it uses **English** — aligned with the code, API payloads, commit messages, and the rest of the framework. This means a story file can legitimately be **bilingual**: a non-English Business Context at the top, English technical sections below.

To bridge the two languages cleanly, `glossary.md` should include a **code identifier** for each domain term that maps to how it's named in the codebase. Generic bilingual example (replace with your own domain's terms):

```markdown
## Commande

**Définition (FR)** : engagement d'achat confirmé par un client, avec ligne
d'articles, adresse de livraison figée, et prix total calculé hors TVA.

**Code identifier (EN)** : `order` / `Order` / `/api/orders`

**Règles associées** : voir `business-rules.md#immuabilite-commande`
```

This lets the tech-spec-writer read the non-English definition for understanding, then use the English code identifier in the technical sections without losing the link.

---

## BMad writing protocol (rules for Claude sessions acting as BMad)

This section governs what BMad writes **into `delivery/business/`**. Rules for writing in `delivery/epics/` live in [`../epics/README.md`](../epics/README.md). The two files are siblings by design — each folder owns the contract that governs it.

### BMad's 4 input modes

| Mode | When you use it | Lands in this folder? |
|---|---|---|
| **Explore** | Your idea is still fuzzy, you want to think out loud | Only if the exploration converges on a stable business fact |
| **Capture** | You want to record a domain fact (term, persona, rule…) | **Yes — primary destination for this folder** |
| **Plan** | You want to turn ideas into backlog (epic, story) | No — lands in `delivery/epics/` instead |
| **Review** | You want BMad to audit what's already here, or reconcile post-delivery deviations | Writes only when reconciling `## Post-Delivery Notes` from delivered stories |

You don't have to name the mode explicitly — BMad detects it from your phrasing. But the four modes are the vocabulary of the contract; if you're unsure what BMad is about to do, ask which mode it thinks it's in.

### Capture-mode decision tree

When BMad is in Capture mode, it routes the fact you gave it to exactly one of the five canonical files:

| You tell BMad… | BMad writes to… |
|---|---|
| A vocabulary term that matters in the domain | `glossary.md` |
| A user profile / archetype | `personas.md` |
| An invariant rule (compliance, quota, constraint) | `business-rules.md` |
| An entity + its relations at the business level (not SQL) | `domain-model.md` |
| An end-to-end user flow from the user's POV | `user-journeys.md` |

If the target file doesn't exist yet, BMad creates it the first time — always proposing the path before writing.

### Rules BMad respects when writing here

1. **Propose before writing.** Before any write, BMad announces the exact file and the exact section it intends to touch, and waits for green light. Say `direct` in your message to skip the green light for that specific capture.
2. **Read before writing.** BMad re-reads the target file first, to avoid duplicates or contradictions with existing content.
3. **No duplication** — cf. "Relationship with `delivery/epics/`" above. A business fact lives in one place in this folder; stories link to it, they do not recopy it.
4. **Size discipline** — cf. "Sizing discipline" above. If a file approaches ~5k tokens, BMad proposes a split before writing more.
5. **Zones BMad never touches.** `delivery/specs/` (technical conventions) and `.claude/` (Kiat framework machinery) are off-limits. If a capture is actually about code structure, API design, or framework behavior, BMad refuses and redirects.
6. **Slicing discipline (when writing in `delivery/epics/`).** Stories BMad produces in Plan mode must follow the vertical-slice discipline defined in [`../epics/README.md#slicing-discipline`](../epics/README.md) — every story delivers a user-observable increment end-to-end, exceptions (`backend-infra`, `frontend-chrome`, `infra`) require a one-line justification. This rule does not apply to captures in this folder (glossary, personas, rules…) — only to Plan-mode writes that land in `delivery/epics/`.

### What BMad does NOT write here

Everything already listed in "What does NOT go here" above still holds — in particular, **no story specs and no epic briefs in this folder**. The business layer of every story (its `## Business Context` section) lives inside the story file itself, in `delivery/epics/epic-X/`. This folder is only for evergreen domain knowledge that outlives any single story.

---

### Review mode — Post-Delivery Reconciliation

When the PO/PM invokes BMad in **Review mode** on a delivered story (status `✅ Done`), BMad performs a **reconciliation check** — reading the story's `## Post-Delivery Notes` section to discover any deviations between what the spec planned and what the coders actually shipped.

#### When to trigger

- **Periodically**: the PO/PM can ask BMad to scan all `✅ Done` stories in an epic for unreconciled `## Post-Delivery Notes`. BMad lists the stories that have non-placeholder content.
- **Per-story**: the PO/PM points BMad at a specific delivered story file.
- **In `/loop`**: BMad can be set up via `/loop` to periodically scan for unreconciled stories across all epics.

#### Reconciliation protocol

1. **Read** the story's `## Post-Delivery Notes`. If the placeholder `_(no deviations)_` is present, the story shipped as specified — report "no reconciliation needed" and stop.

2. **For each deviation**, classify the business impact:

   | Deviation prefix | BMad action |
   |---|---|
   | `AC-N` (acceptance criterion changed) | Read the original AC in `## Business Context`. Assess whether the difference is cosmetic (e.g., toast instead of modal — same UX outcome) or material (e.g., async instead of sync — different user experience). If material: propose an update to the `## Business Context` acceptance criterion and, if applicable, to the relevant `delivery/business/` file. |
   | `SPEC_GAP` (new concept introduced) | Check if the concept exists in `delivery/business/glossary.md` or `domain-model.md`. If not: switch to **Capture mode** and propose adding it. If it exists but the definition doesn't match: propose an update. |
   | `DECISION` (judgment call on silence) | Assess whether the decision should become a **business rule** (e.g., "rate limit is 100 req/min" → belongs in `business-rules.md` if it's a product decision, not just a technical default). If yes: switch to **Capture mode** and propose. If it's purely technical: note it and move on — it belongs in `delivery/specs/project-memory.md`, not here. |

3. **Propose before writing** — same rule as Capture mode. BMad announces each update it intends to make and waits for green light before writing.

4. **Mark as reconciled**. After all deviations in a story are processed, BMad appends a line to the story's `## Post-Delivery Notes`:

   ```markdown
   _Reconciled by BMad on 2026-04-22 — 2 items updated in delivery/business/, 1 noted as technical-only._
   ```

   This line is the signal that the story's deviations have been reviewed by the PO/PM and the business layer is up to date.

#### What BMad does NOT do during reconciliation

- **No technical changes.** BMad never edits `delivery/specs/`, code, or `.claude/` files. If a deviation is purely technical (e.g., "used async job queue" with no business impact), BMad notes it and moves on.
- **No retroactive story edits.** BMad does not modify the `## Business Context` of a `✅ Done` story to pretend the spec was always right. The `## Post-Delivery Notes` section is the historical record of what changed. If BMad updates an acceptance criterion, it adds a note explaining the update was post-delivery.
- **No new stories from deviations alone.** If a deviation reveals a bigger gap (e.g., "we introduced soft delete but have no GDPR retention policy"), BMad flags it to the PO/PM as a potential future story — it does not create the story unilaterally.
