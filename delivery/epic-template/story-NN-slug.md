# Story NN: [Title]

**Epic**: [Epic X](../_epic.md)

**Objective**: [What does this story deliver? 1-2 sentences]

**T-Shirt Size**: S / M / L

---

## Acceptance Criteria

- [ ] Criterion 1 (testable, specific)
- [ ] Criterion 2
- [ ] Criterion 3

[Example: "User can upload a photo ≤20MB and see it displayed in the UI within 3 seconds"]

---

## Technical Specification

### Database Changes

[If any schema changes needed]

```sql
-- File: backend/migrations/NNN_description.sql
CREATE TABLE IF NOT EXISTS feature_x (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS policy
ALTER TABLE feature_x ENABLE ROW LEVEL SECURITY;

CREATE POLICY feature_x_user_isolation ON feature_x
  USING (user_id = auth.uid());
```

### API Contracts

[If backend changes needed]

**Endpoint 1: Create Feature**

```
POST /api/features

Request:
  {
    "name": "Feature Name",
    "description": "Description"
  }

Response (201 Created):
  {
    "id": "uuid",
    "name": "Feature Name",
    "created_at": "2026-04-09T10:00:00Z"
  }

Error (400 Bad Request):
  {
    "code": "INVALID_INPUT",
    "message": "name is required (max 255 characters)"
  }

Error (409 Conflict):
  {
    "code": "CONFLICT",
    "message": "Feature name already exists"
  }
```

### Frontend Changes

[If UI/component changes needed]

**New Component**: `FeatureForm`
- Props: `onSuccess` callback, optional `initial` data
- State: Form values, save status
- Behavior: Auto-save after 500ms of inactivity

**New Hook**: `useFeatureCreate`
- Returns: `{ mutate, isPending, error }`
- Auto-invalidates query cache on success

**Styling**: 
- Use Shadcn `<Form>`, `<Input>`, `<Textarea>`, `<Button>`
- Border radius: `rounded-[16px]` for button
- Responsive: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`

### Edge Cases & Error Handling

- [ ] Network timeout → Show error toast with retry button
- [ ] Duplicate name → Show 409 error, suggest rename
- [ ] Large text in description → Truncate at 1000 chars, show warning
- [ ] File too large (if upload) → Show clear error with size limit
- [ ] Offline → Queue mutation, show "offline" banner, retry when online
- [ ] Double-click submit → Prevent duplicate submission (disable button)

---

## Testing Plan

### Backend (Venom Tests)

```
backend/venom/feature_test.go

- TestCreateFeature_Happy: Create feature, verify ID returned, name stored
- TestCreateFeature_Validation: Empty name → INVALID_INPUT error
- TestCreateFeature_Duplicate: Same name twice → CONFLICT error
- TestCreateFeature_RLS: User B cannot read User A's feature (via RLS)
```

### Frontend (Playwright E2E Tests)

```
frontend/e2e/feature.spec.ts

- Test: Happy path - fill form, save, verify in UI
- Test: Validation - empty name shows error message
- Test: Auto-save - changes automatically saved after 500ms
- Test: Error recovery - network error shown, retry works
- Test: Offline - mutation queued, retried when online
```

### Manual Testing (if needed)

- [ ] Browser: Chrome, Firefox, Safari
- [ ] Mobile: iOS Safari, Android Chrome
- [ ] Network: Throttled to 3G (slow save)

---

## Acceptance Criteria Mapping

| Acceptance Criterion | Test Coverage |
|---------------------|---------------|
| User can create feature | E2E: Happy path |
| User sees validation errors | E2E: Validation test |
| Feature persists after reload | E2E: Reload after save |
| User cannot see other users' features | Venom: RLS test |

---

## Notes

[Any additional context?]

- Design reference: [Link to Figma]
- Related story: [Story N](./story-NN-other.md)
- Known constraints: [e.g., "Must work offline"]
- Future enhancement: [e.g., "Batch upload (story 5)"]

---

## Implementation Notes for Coder

[Optional: hints for the coder to avoid common mistakes]

- Backend: Don't forget to wire handler in `main.go`
- Frontend: Use `useAutoSave` hook, not manual `useEffect` debounce
- Testing: Include RLS test (User B can't read User A's data)
- Logging: Include feature_id in logs for debugging

---

**Status**: 🟡 In Progress / 🟢 Done / 🔴 Blocked
