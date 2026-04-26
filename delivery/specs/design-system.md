# Design System — Protocol, Not Specific System

How this project defines and uses visual tokens (colors, spacing, typography, radius). **The values shipped in this file are neutral defaults** — they exist so EPIC 00 renders something usable, not to impose a visual direction.

> **Principle: Scaffold teaches patterns, not aesthetics.**
> EPIC 00 is design-neutral by construction. Values here stay at Shadcn/UI's neutral defaults (slate grayscale, single `destructive` semantic color) until your first visual reference arrives. **When a Figma URL or screenshot lands in a story's `### Mockups` section, customize the values in this file in the same commit as the feature implementation.** Don't bulk-customize upfront.

---

## What this file is

A **protocol**: where tokens live, how they're named, how components consume them. The *specific values* matter less than the *consistency of the contract*.

What belongs here:
- The token categories your project uses (surfaces / primary / semantic destructive / borders & inputs / spacing / radius / typography)
- The `@theme` block in `frontend/src/globals.css` with the current values
- Component-level patterns (button, input, card) that read from tokens
- Dark mode strategy when it arrives

What does NOT belong here:
- Visual decisions without a visual reference driving them (no "I think we should use blue-600") — drive from Figma / screenshots, document the result
- Component-specific implementations (those live in `frontend/src/components/`)

## Why Shadcn/UI vocabulary (and not a custom palette)

This project bootstraps with the **exact token names Shadcn/UI primitives expect** — `--color-background`, `--color-foreground`, `--color-card`, `--color-popover`, `--color-primary`, `--color-secondary`, `--color-muted`, `--color-accent`, `--color-destructive`, `--color-border`, `--color-input`, `--color-ring`, plus a `-foreground` companion for each surface — rather than inventing custom names like `--color-primary-pale` or `--color-gray-dark`.

**Reasoning**: at bootstrap, Kiat has no design value to protect — every color is a placeholder until brand direction arrives. Inventing custom names that diverge from the Shadcn vocabulary buys nothing and costs ongoing maintenance: every `npx shadcn@latest add <primitive>` generates code that references the standard names, and a custom palette silently breaks those primitives (transparent backgrounds, invisible text, missing borders) without any test catching it — the breakage is purely visual.

Adopting Shadcn vocabulary directly means: (1) Shadcn primitives drop in and work; (2) when a brand identity arrives, only the *values* change, not the *contract*; (3) any frontend developer who has touched a Shadcn project in the last two years recognises the names instantly.

---

## Tailwind v4 setup

**No `tailwind.config.ts`** — Tailwind v4 uses CSS `@theme` directives. All tokens in `frontend/src/globals.css`:

```css
/* frontend/src/globals.css */

@import "tailwindcss";

@theme {
  /* ─── Surfaces (page-level) ───
     Defaults = white background, slate-900 foreground. Replace with
     your brand palette when the first visual reference arrives. */
  --color-background:           #ffffff;
  --color-foreground:           #0f172a;  /* slate-900 */

  /* ─── Cards & popovers ───
     Same as surfaces by default. Override when the visual reference
     calls for elevated surfaces (subtle gray, off-white, etc.). */
  --color-card:                 #ffffff;
  --color-card-foreground:      #0f172a;
  --color-popover:              #ffffff;
  --color-popover-foreground:   #0f172a;

  /* ─── Primary action ───
     Slate-900 on slate-50 — neutral, accessible default. Replace with
     your brand color in the same commit as the first visual reference. */
  --color-primary:              #0f172a;  /* slate-900 */
  --color-primary-foreground:   #f8fafc;  /* slate-50 */

  /* ─── Secondary action ─── */
  --color-secondary:            #f1f5f9;  /* slate-100 */
  --color-secondary-foreground: #0f172a;

  /* ─── Muted (subtle backgrounds, secondary text) ─── */
  --color-muted:                #f1f5f9;
  --color-muted-foreground:     #64748b;  /* slate-500 */

  /* ─── Accent (hover highlights, subtle emphasis) ─── */
  --color-accent:               #f1f5f9;
  --color-accent-foreground:    #0f172a;

  /* ─── Destructive (error / delete) ─── */
  --color-destructive:          #ef4444;  /* red-500 */
  --color-destructive-foreground: #f8fafc;

  /* ─── Borders, inputs, focus ring ─── */
  --color-border:               #e2e8f0;  /* slate-200 */
  --color-input:                #e2e8f0;
  --color-ring:                 #0f172a;

  /* ─── Spacing scale (4px base) ───
     Matches Tailwind's default p-1..p-8. Rarely customized. */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* ─── Radius ───
     Single base + Shadcn-style derived steps. Customize the base if
     your brand is particularly rounded (pill-heavy) or particularly
     sharp (brutalist) — the derived sizes follow automatically. */
  --radius:    0.5rem;                       /* 8px base */
  --radius-sm: calc(var(--radius) - 4px);    /* 4px */
  --radius-md: calc(var(--radius) - 2px);    /* 6px */
  --radius-lg: var(--radius);                /* 8px */
  --radius-xl: calc(var(--radius) + 4px);    /* 12px */
  --radius-full: 9999px;

  /* ─── Typography ───
     Defaults to Tailwind's font-sans stack. Pair with a display font
     (e.g. Inter, Outfit, Geist) when your brand calls for it. */
  --font-sans:    ui-sans-serif, system-ui, sans-serif;
  --font-display: ui-sans-serif, system-ui, sans-serif;
}

@layer base {
  body {
    @apply bg-background text-foreground;
  }
}

@layer utilities {
  .text-heading { @apply font-display font-bold text-xl text-foreground; }
  .text-body    { @apply font-sans text-base text-foreground; }
  .text-small   { @apply font-sans text-sm text-muted-foreground; }
}
```

> **Adding semantic colors (success / warning / info)**: Shadcn's bootstrap vocabulary intentionally ships only `destructive` — projects layer their own semantic variants on top when brand direction arrives. When that happens, add them following the same `--color-<role>` + `--color-<role>-foreground` pairing pattern (e.g. `--color-success` + `--color-success-foreground`) so they slot in next to the Shadcn defaults without inventing a new naming convention.

---

## Token naming protocol

Follow these patterns consistently:

| Category | Naming | Example |
|---|---|---|
| Color (surface) | `--color-<role>` paired with `--color-<role>-foreground` | `--color-card` + `--color-card-foreground` |
| Color (action) | `--color-<role>` paired with `--color-<role>-foreground` | `--color-primary` + `--color-primary-foreground` |
| Color (single-purpose) | `--color-<role>` | `--color-border`, `--color-input`, `--color-ring` |
| Spacing | `--spacing-<size>` | `--spacing-md` |
| Radius | `--radius` (base) + `--radius-<size>` (derived) | `--radius-lg` |
| Font | `--font-<role>` | `--font-display` |

**Do NOT invent custom names that diverge from Shadcn.** The vocabulary above is what `shadcn@latest add <primitive>` references. Names like `--color-primary-light`, `--color-primary-pale`, `--color-gray-dark` may feel descriptive, but they break every Shadcn primitive that expects `--color-muted` / `--color-muted-foreground` / `--color-border`. If the visual reference demands more granularity than the Shadcn vocabulary covers (e.g. a distinct hover shade for primary), add a new role-named token (`--color-primary-hover`) — never an arbitrary Tailwind-like number (`--color-primary-600`).

**Do NOT skip the `@theme` layer.** Inline hex values in components (`className="bg-[#273d54]"`) bypass the token system and break any future rebrand. Reviewer rule: any hex code in a component's Tailwind class is a `NEEDS_DISCUSSION` — does it belong in `@theme`?

**Pair every surface/action with its `-foreground`.** A surface token without its foreground companion is incomplete by construction — it forces the consumer to guess which text color is legible on top, which is exactly the contract Shadcn primitives rely on to stay accessible.

---

## Using tokens in components

```tsx
// ✅ Token-based — each surface/action paired with its foreground
<button className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg">
  Create
</button>

<div className="bg-card text-card-foreground rounded-lg border p-6">
  Card content
</div>

<input className="border border-input bg-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />

<button className="bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90">
  Delete
</button>

<p className="text-muted-foreground text-sm">Secondary text</p>
```

Tailwind v4 auto-generates utility classes from the `@theme` block — `bg-background`, `text-foreground`, `bg-primary`, `text-primary-foreground`, `border`, `rounded-lg`, etc. No config file needed.

**Hover / opacity variants** use Tailwind's slash syntax (`bg-primary/90`) instead of a separate `--color-primary-hover` token, mirroring the Shadcn primitive convention. Add a dedicated hover token only when the visual reference specifies a hue shift, not just a tint change.

```tsx
// ❌ Inline hex — bypasses the system
<button className="bg-[#273d54] text-white">Create</button>

// ❌ Foreground guessed from `text-white` instead of paired token
<button className="bg-primary text-white">Create</button>
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

Default strategy: derive from a single `--radius` base (8px). Shadcn primitives reference `rounded-sm` / `rounded-md` / `rounded-lg` directly, so changing the base shifts every primitive consistently.

| Class | Value (default) | Use |
|---|---|---|
| `rounded-sm` | 4px (`--radius - 4px`) | Small elements — chips, badges, small inputs |
| `rounded-md` | 6px (`--radius - 2px`) | Buttons, inputs — the Shadcn primitive default |
| `rounded-lg` | 8px (`var(--radius)`) | Cards, dialogs, popovers |
| `rounded-xl` | 12px (`--radius + 4px`) | Larger surfaces — feature cards, hero panels |
| `rounded-full` | — | Circles only: avatars, radio dots, pill tags |

**If your visual reference calls for a different default** (e.g. sharp "brutalist" design uses `rounded-none`, or ultra-rounded uses larger radii), change the `--radius` base in `@theme` — the derived sizes follow automatically. Don't override per-component.

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
