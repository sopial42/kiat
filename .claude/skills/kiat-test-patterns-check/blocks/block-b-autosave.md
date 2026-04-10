# Block B — Auto-save

**Trigger:** any `useAutoSave` usage, any "saves as user types"

## Mandatory rules

From `delivery/specs/frontend-architecture.md` "useAutoSave Consumer Contract":

- `enabled` condition MUST be **stable** — it must NOT transition `false → true` in the same render as `data` changes.
- Do NOT use `enabled: !isLoading` with data that arrives after loading — create a stable flag like `const shouldSave = isReady && dataHydrated`.
- `flush()` is a no-op when `enabled` is false — don't rely on it to save during the loading-to-loaded transition.
- Debounce MUST be in the 500-1000ms range (500ms is the default).
- UI MUST show save status transitions (`Saving` → `Saved`).

## Required acknowledgment (paste verbatim)

> I will decouple the `enabled` flag from the `data` prop so it does not transition false→true in the same render. Debounce will be 500ms. I will show "Saving..." and "Saved" states to the user.

## Common drift caught by reviewers

- `enabled: !isLoading && data` pattern — reviewer flags: `data` transitioning from undefined→object is the exact contract violation described above
- No `Saving` / `Saved` UI — reviewer flags: acknowledged rule required visible save status
- Debounce set to 100ms or 3000ms — reviewer flags: outside 500-1000ms range
