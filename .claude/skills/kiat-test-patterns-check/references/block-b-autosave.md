# Block B — Auto-save

**Trigger:** any `useAutoSave` usage, any "saves as user types" behavior.

## Rules and reasons

**The `enabled` flag is stable — it must not transition `false → true` in the same render as the `data` prop changes.** Derive it from something like `const shouldSave = isReady && dataHydrated`, not from `!isLoading`.

> *Why*: if `enabled` flips from false to true at the same moment the hook receives fresh data, the hook's debounce fires immediately with that data — and the first save submits whatever the hook saw before the data fully loaded. The user's first few keystrokes get dropped, and worse, the race is timing-dependent so it only reproduces on slow devices.

**`flush()` is a no-op when `enabled` is false.** Don't rely on it to save during the loading-to-loaded transition.

> *Why*: consumers sometimes try to "force save" at an important moment (before navigation, on blur). If the hook is disabled, the flush silently does nothing. Check the hook state before calling flush, or restructure so the save isn't needed at that moment.

**Debounce is 500-1000ms (500ms is the typical default).**

> *Why*: below 500ms, saves happen faster than the user's typing rhythm and create excessive network chatter. Above 1000ms, users notice the "Saved" indicator lagging behind their edits and lose confidence. The project's hook contract enforces this range.

**The UI shows `Saving…` and `Saved` state transitions.**

> *Why*: without feedback, users don't know whether their work is safe. Auto-save is supposed to remove the anxiety of "did I save?" — skipping the UI defeats the point.

Full hook contract lives in `delivery/specs/frontend-architecture.md` under "useAutoSave consumer contract".

## Required acknowledgment (paste verbatim)

> I will decouple the `enabled` flag from the `data` prop so it does not transition false→true in the same render. Debounce will be 500ms. I will show "Saving..." and "Saved" states to the user.

## Common drift caught by reviewers

- `enabled: !isLoading && data` pattern — reviewer flags: `data` transitioning from undefined to object is the exact contract violation above.
- No `Saving` / `Saved` UI — reviewer flags: acknowledged rule required visible save status.
- Debounce set to 100ms or 3000ms — reviewer flags: outside the 500-1000ms range.
