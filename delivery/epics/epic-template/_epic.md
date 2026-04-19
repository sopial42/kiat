# Epic [NN]: [Title]

**Status**: 📝 Drafted

> Epic-level status aggregates from child stories — see [`../README.md#status-lifecycle`](../README.md#status-lifecycle). Team Lead flips this automatically as stories progress.

**Objective**: [1-2 sentences. What problem does this epic solve?]

**Scope**: [What's IN this epic? What's OUT for future epics?]

**Timeline**: [When should this be done? E.g., "2 weeks"]

**Team**: [Who's building it? E.g., "1 backend, 1 frontend, 1 QA"]

**T-Shirt Size**: S / M / L / XL

---

## Business Context

> Section written by BMad (or by the user). The tech-spec-writer NEVER
> modifies this section.
>
> Write in the project's business language (French for French-domain
> projects, English by default). The tech-spec-writer reads it regardless
> of language.

### Outcome attendu / Expected outcome

[What user-side or business-side change is this epic trying to produce? Describe the outcome in user terms, not technical terms.]

### Personas impactés / Personas affected

- [Persona 1 — link to `delivery/business/personas.md#<persona>`]
- [Persona 2 — link to `delivery/business/personas.md#<persona>`]

### Hypothèses & risques métier / Business hypotheses & risks

- [What we assume and that could turn out to be wrong]
- [Dependencies on external stakeholders, regulations, or timing]

### Target architecture

> **Keep this sub-section when ≥ 2 stories in this epic touch the same artifact** (page, endpoint, shared component, table, service). **Delete it** when every story touches a different artifact. Rule and rationale: [`../README.md#target-architecture`](../README.md#target-architecture).
>
> When kept, each story in the series MUST open its `## Business Context` with a `⚠️ Required reading before this story` pointer to this section — BMad writes both sides as a single coherent act.

[Describe the **final state** of the shared artifact after all its stories land — zones, navigation, composable blocks, primitives reused. Then a **per-story evolution** table (one line per story: what each adds or activates). Then the **implicit architectural constraints** each story must anticipate (e.g., "state must be listeable from story 01 because story 02 will introduce N items", "button X must render from story 01 even if inactive, to avoid re-layout in story 03"). User-facing / information architecture only — no component names, no routes, no framework terms.]

#### Slicing plan

> Populate when this epic has ≥ 2 stories on the same feature. One line per story describing the **user-observable value** each slice adds — walking skeleton first, then depth (validation / edge cases / UX), never breadth (other features). Rule and rationale: [`../README.md#slicing-discipline`](../README.md).

- **Story 01 (walking skeleton)**: [smallest end-to-end slice that proves the data flows — the user sees something, however crude]
- **Story 02**: [next user-observable increment on top of story 01]
- **Story 03**: [...]

### Linked business knowledge

_Point at the evergreen docs in `delivery/business/` that frame this epic. Link only the sections that actually matter for this epic — don't list the whole folder._

- Glossary terms involved: [`../../business/glossary.md`](../../business/glossary.md)
- Business rules at play: [`../../business/business-rules.md`](../../business/business-rules.md)
- User journey(s) touched: [`../../business/user-journeys.md`](../../business/user-journeys.md)
- Domain model entities: [`../../business/domain-model.md`](../../business/domain-model.md)

---

## Stories

- **Story 01**: [Brief title]
- **Story 02**: [Brief title]
- **Story 03**: [Brief title]

---

## Risks & Considerations

- [Any architectural challenges?]
- [Any integration concerns?]
- [Any timeline risks?]

---

## Acceptance Criteria (Epic-level)

- [ ] All stories completed
- [ ] All tests passing (Venom + Playwright)
- [ ] Code reviewed and approved
- [ ] Design spec matched
- [ ] No regressions in prior epics

---

## Epic Patterns (populated as stories are implemented)

> _This section is **maintained by the tech-spec-writer** (when it exists) or manually after each PASSED story in this epic. It captures patterns specific to THIS epic that subsequent stories of the same epic should follow. Patterns that apply cross-epic get promoted to [`delivery/specs/project-memory.md`](../specs/project-memory.md)._
>
> **Scope:** this section exists to catch "epic-local" drift — the risk that story 3 of this epic invents a new pattern without knowing story 1 already solved the same problem. It's a cheaper version of `project-memory.md`, bounded to the lifetime of this epic.

### Naming conventions (epic-local)

_(populate as needed — e.g., "all item endpoints use `item_id` path param, not `id`")_

### Shared components introduced by this epic

_(populate as components are created — e.g., "story 02 introduced `<ItemCard>` at `frontend/src/features/items/ItemCard.tsx` — reuse in story 03+ instead of recreating")_

### API contracts baseline for this epic

_(populate as the first backend story lands — e.g., "response envelope for this epic: `{data, meta}`, error envelope: `{error: {code, message}}` — enforced from story 01")_

### Epic-specific gotchas

_(populate as stories discover surprises — e.g., "the S3 bucket policy requires `x-amz-meta-item-id` header on every upload — missed at story 02, fixed in review")_

---

## Notes

[Any additional context? Background? Prior discussions?]
