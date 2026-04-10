# Epic [NN]: [Title]

**Objective**: [1-2 sentences. What problem does this epic solve?]

**Scope**: [What's IN this epic? What's OUT for future epics?]

**Timeline**: [When should this be done? E.g., "2 weeks"]

**Team**: [Who's building it? E.g., "1 backend, 1 frontend, 1 QA"]

**T-Shirt Size**: S / M / L / XL

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

_(populate as needed — e.g., "all hypothesis endpoints use `hypothesis_id` path param, not `id`")_

### Shared components introduced by this epic

_(populate as components are created — e.g., "story 02 introduced `<HypothesisCard>` at `frontend/src/features/hypotheses/HypothesisCard.tsx` — reuse in story 03+ instead of recreating")_

### API contracts baseline for this epic

_(populate as the first backend story lands — e.g., "response envelope for this epic: `{data, meta}`, error envelope: `{error: {code, message}}` — enforced from story 01")_

### Epic-specific gotchas

_(populate as stories discover surprises — e.g., "the S3 bucket policy requires `x-amz-meta-patient-id` header on every upload — missed at story 02, fixed in review")_

---

## Notes

[Any additional context? Background? Prior discussions?]
