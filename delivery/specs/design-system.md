# Design System — Protocol, Not Specific System

How this project defines and uses visual tokens (colors, spacing, typography, radius). **The values shipped in this file are neutral defaults** — they exist so EPIC 00 renders something usable, not to impose a visual direction.

> **Principle: Scaffold teaches patterns, not aesthetics.**
> EPIC 00 is design-neutral by construction. Values here stay at Tailwind v4 defaults (slate grayscale, semantic colors from `tailwindcss/colors`) until your first visual reference arrives. **When a Figma URL or screenshot lands in a story's `## Mockups` section, customize the values in this file in the same commit as the feature implementation.** Don't bulk-customize upfront.

---

## What this file is

A **protocol**: where tokens live, how they're named, how components consume them. The *specific values* matter less than the *consistency of the contract*.

What belongs here:
- The token categories your project uses (primary / semantic / grayscale / spacing / radius / typography)
- The `@theme` block in `frontend/src/globals.css` with the current values
- Component-level patterns (button, input, card) that read from tokens
- Dark mode strategy when it arrives

What does NOT belong here:
- Visual decisions without a visual reference driving them (no "I think we should use blue-600") — drive from Figma / screenshots, document the result
- Component-specific implementations (those live in `frontend/src/components/`)

---

## Tailwind v4 setup

**No `tailwind.config.ts`** — Tailwind v4 uses CSS `@theme` directives. All tokens in `frontend/src/globals.css`:

```css
/* frontend/src/globals.css */

@import "tailwindcss";

@theme {
  /* ─── Primary palette ───
     Defaults = Tailwind slate 700 / 500 / 100. Replace with your
     brand palette when the first visual reference arrives. */
  --color-primary:        #334155;  /* slate-700 */
  --color-primary-light:  #64748b;  /* slate-500 */
  --color-primary-pale:   #f1f5f9;  /* slate-100 */

  /* ─── Semantic colors ───
     Neutral defaults from tailwindcss/colors. Safe to keep as-is
     unless your brand overrides them explicitly. */
  --color-success: #10b981;  /* emerald-500 */
  --color-warning: #f59e0b;  /* amber-500 */
  --color-error:   #ef4444;  /* red-500 */
  --color-info:    #3b82f6;  /* blue-500 */

  /* ─── Grayscale ─── */
  --color-gray-dark:  #1f2937;  /* gray-800 — text */
  --color-gray-mid:   #6b7280;  /* gray-500 — secondary text */
  --color-gray-light: #f3f4f6;  /* gray-100 — surfaces */

  /* ─── Spacing scale (4px base) ───
     Matches Tailwind's default p-1..p-8. Rarely customized. */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* ─── Radius ───
     Defaults to Tailwind's rounded-md / rounded-lg. Customize if
     your brand is particularly rounded (pill-heavy) or particularly
     sharp (brutalist). */
  --radius-sm:   0.375rem;  /* 6px */
  --radius-md:   0.5rem;    /* 8px */
  --radius-lg:   1rem;      /* 16px */
  --radius-full: 9999px;

  /* ─── Typography ───
     Defaults to Tailwind's font-sans stack. Pair with a display font
     (e.g. Inter, Outfit, Geist) when your brand calls for it. */
  --font-sans:    ui-sans-serif, system-ui, sans-serif;
  --font-display: ui-sans-serif, system-ui, sans-serif;
}

@layer utilities {
  .text-heading { @apply font-display font-bold text-xl text-gray-dark; }
  .text-body    { @apply font-sans text-base text-gray-dark; }
  .text-small   { @apply font-sans text-sm text-gray-mid; }
}
```

---

## Token naming protocol

Follow these patterns consistently:

| Category | Naming | Example |
|---|---|---|
| Color | `--color-<role>` or `--color-<role>-<shade>` | `--color-primary`, `--color-primary-light` |
| Spacing | `--spacing-<size>` | `--spacing-md` |
| Radius | `--radius-<size>` | `--radius-lg` |
| Font | `--font-<role>` | `--font-display` |

**Do NOT invent ad-hoc shade counts.** Primary + primary-light + primary-pale is enough for 95% of use cases. If a visual reference demands more shades, add them — but name them by ROLE (`--color-primary-hover`, `--color-primary-pressed`) not by arbitrary Tailwind-like numbers (`--color-primary-600`).

**Do NOT skip the `@theme` layer.** Inline hex values in components (`className="bg-[#273d54]"`) bypass the token system and break any future rebrand. Reviewer rule: any hex code in a component's Tailwind class is a `NEEDS_DISCUSSION` — does it belong in `@theme`?

---

## Using tokens in components

```tsx
// ✅ Token-based
<button className="bg-primary hover:bg-primary-light text-white rounded-lg">
  Create
</button>

<div className="bg-success/10 text-success px-3 py-1 rounded-md">
  ✓ Success
</div>

<input className="border border-gray-light focus:border-primary focus:ring-2 focus:ring-primary-light/30" />
```

Tailwind v4 auto-generates utility classes from the `@theme` block — `bg-primary`, `text-gray-dark`, `rounded-lg`, `p-md`, etc. No config file needed.

```tsx
// ❌ Inline hex — bypasses the system
<button className="bg-[#273d54] text-white">Create</button>
```

---

## Spacing scale

4px base. Mobile-first responsive:

```tsx
<div className="p-4 sm:p-6 lg:p-8">
  Content
</div>
```

| Class | Value | Typical use |
|---|---|---|
| `p-1` / `p-2` | 4px / 8px | Tight element padding (chip, icon) |
| `p-3` / `p-4` | 12px / 16px | Form fields, buttons, cards |
| `p-6` | 24px | Section padding |
| `p-8` / `p-10` / `p-12` | 32px+ | Page sections, landing-page heroes |

---

## Border radius

Default strategy: medium rounding (`rounded-lg` = 16px) for interactive elements, sharp corners for structural elements.

| Class | Use |
|---|---|
| `rounded-md` (8px) | Small elements — chips, badges, small inputs |
| `rounded-lg` (16px) | Buttons, inputs, cards, dialogs — the default |
| `rounded-full` | Circles only — avatars, radio dots, pill tags |

**If your visual reference calls for a different default** (e.g. sharp "brutalist" design uses `rounded-none`, or ultra-rounded uses `rounded-2xl`), change the `--radius-lg` value in `@theme` globally — don't override per-component.

---

## Typography

Default: `font-sans` (system stack) for everything. Scaffold-acceptable for EPIC 00. When a visual reference specifies fonts:

```css
@theme {
  --font-display: "Outfit", ui-sans-serif, sans-serif;  /* headings */
  --font-sans:    "Inter",  ui-sans-serif, sans-serif;  /* body */
}
```

Then import the font in `frontend/src/app/layout.tsx`:

```tsx
import { Inter, Outfit } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-display" });

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
```

**Rule**: pair max, not trio. A display font + a body font is enough; a third font almost always means the system is unclear.

---

## Accessibility floor (WCAG AA)

Regardless of the visual reference, these checks are non-negotiable:

- **Contrast**: foreground ↔ background ≥ 4.5:1 for body text, ≥ 3:1 for large text (≥ 18px or 14px bold). See [testing-pitfalls-frontend.md:UA01](testing-pitfalls-frontend.md).
- **Focus states**: every interactive element must have a visible focus ring. Tailwind's `focus:ring-2` + `focus:ring-offset-2` is the minimum.
- **Disabled state**: never convey by color alone. Add `aria-disabled="true"` + `opacity-50 cursor-not-allowed`.
- **Touch targets**: minimum 44×44px on mobile (iOS HIG standard).

Reviewer rule: if the mockup shows a contrast-failing combination, flag as `NEEDS_DISCUSSION` — the mockup might be decorative, but shipping an inaccessible component is not OK.

---

## Dark mode

**Not shipped in EPIC 00.** Add when a visual reference includes a dark-mode variant. The protocol:

- Dual token blocks in `@theme`: base (light) + `@media (prefers-color-scheme: dark)` override
- Tailwind v4 handles the switch automatically
- Test every component in both modes; contrast floor applies to both

---

## When to customize — checklist

Before touching values in this file:

- [ ] The story that drove the change has a visual reference (Figma URL or screenshot)
- [ ] The customization is extracted from the reference, not invented
- [ ] Every new token name follows the protocol above (role-based, not arbitrary numbers)
- [ ] The component that consumes the new token doesn't inline hex values
- [ ] The change ships in the same commit as the feature that needs it

When in doubt, leave the default. The scaffold stays neutral until a visual reference forces a decision.

---

See also:
- [frontend-architecture.md](frontend-architecture.md) — RSC boundary, hook patterns
- [testing-pitfalls-frontend.md](testing-pitfalls-frontend.md) — UA01 (contrast), UA02 (auto-save timing)
- `kiat-how-to.md` (repo root) — the two visual-reference shapes (Figma URL / static screenshots)
