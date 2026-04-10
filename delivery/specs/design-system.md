# Design System: Colors, Spacing, Typography

Visual guidelines and Tailwind tokens for consistent UI.

---

## Colors

### Primary (Kotai Blue)
- **Base**: `#273D54` (dark blue, primary actions)
- **Light**: `#52ACD9` (sky blue, secondary, hover states)
- **Pale**: `#E8F1F6` (very light blue, backgrounds)

### Grayscale
- **Dark**: `#1F2937` (text, headings)
- **Mid**: `#6B7280` (secondary text, disabled)
- **Light**: `#F3F4F6` (backgrounds, borders)
- **White**: `#FFFFFF` (cards, main content)

### Semantic
- **Success**: `#10B981` (green, checkmarks, confirmations)
- **Warning**: `#F59E0B` (amber, caution, warnings)
- **Error**: `#EF4444` (red, errors, destructive actions)
- **Info**: `#3B82F6` (blue, information)

### Timeline Phases (Epic 24)
- **Phase 1**: `#7AB87A` (green, inactive: `#A0C9A0`)
- **Phase 2**: `#F49952` (orange, inactive: `#FEB078`)
- **Phase 3**: `#6AAFD4` (blue, inactive: `#9DC9E5`)

---

## Tailwind v4 Setup

**No `tailwind.config.ts`** — All tokens in `frontend/src/globals.css`:

```css
/* frontend/src/globals.css */

@theme {
  --color-primary: #273d54;
  --color-primary-light: #52acd9;
  --color-primary-pale: #e8f1f6;
  
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;
  
  --color-gray-dark: #1f2937;
  --color-gray-mid: #6b7280;
  --color-gray-light: #f3f4f6;
  
  --spacing-xs: 0.25rem;  /* 4px */
  --spacing-sm: 0.5rem;   /* 8px */
  --spacing-md: 1rem;     /* 16px */
  --spacing-lg: 1.5rem;   /* 24px */
  --spacing-xl: 2rem;     /* 32px */
  
  --radius-sm: 8px;
  --radius-md: 16px;
  --radius-full: 9999px;
}

@layer utilities {
  .text-heading { @apply font-nunito font-bold text-xl text-gray-dark; }
  .text-body { @apply font-inter text-base text-gray-dark; }
  .text-small { @apply font-inter text-sm text-gray-mid; }
}
```

---

## Using Colors in Components

```tsx
// Using Tailwind classes
<button className="bg-primary hover:bg-primary-light text-white">
  Create
</button>

<div className="bg-success/10 text-success">
  ✓ Success
</div>

<input 
  className="border border-gray-light focus:border-primary focus:ring-1 focus:ring-primary-light"
/>
```

---

## Spacing

**Scale**: 4px base unit

| Size | Value | Usage |
|---|---|---|
| `p-1` | 4px | Tight spacing, chip padding |
| `p-2` | 8px | Inputs, small elements |
| `p-3` | 12px | Form fields, compact |
| `p-4` | 16px | Cards, buttons, default |
| `p-6` | 24px | Sections, generous |
| `p-8` | 32px | Page sections, form card |

**Mobile-first responsive**:
```tsx
<div className="p-4 sm:p-6 lg:p-8">
  Content
</div>
```

---

## Border Radius

**Standard**:
- `rounded-[16px]` — Buttons, inputs, selects, cards, dialogs
- `rounded-full` — Circles only: radio dots, pills, avatars
- No `rounded-lg` (not in design system)

**Usage**:
```tsx
<button className="rounded-[16px] bg-primary">
  Click me
</button>

<div className="rounded-full w-10 h-10 bg-primary">
  Avatar
</div>
```

---

## Typography

### Fonts
- **Headings**: Nunito (Bold for prominence)
- **Body**: Inter (default, readable)

### Sizes & Weights

| Role | Font | Size | Weight | Example |
|---|---|---|---|---|
| Page Title | Nunito | 24px | Bold (700) | Wizard header |
| Section Title | Nunito | 20px | Bold (700) | Card titles |
| Button Text | Inter | 14px | Medium (500) | Button labels |
| Body Text | Inter | 16px | Regular (400) | Paragraphs, form text |
| Small Text | Inter | 14px | Regular (400) | Captions, hints |
| Tiny Text | Inter | 12px | Regular (400) | Labels, metadata |

**Tailwind classes**:
```tsx
<h1 className="font-nunito text-2xl font-bold">Page Title</h1>
<h2 className="font-nunito text-xl font-bold">Section Title</h2>
<p className="font-inter text-base">Body text</p>
<label className="font-inter text-sm">Label</label>
```

---

## Shadows & Elevation

**Cards & Modals**:
```tsx
<div className="shadow-md bg-white rounded-[16px]">
  Card
</div>
```

**Hover (subtle lift)**:
```tsx
<button className="hover:shadow-lg transition-shadow">
  Hover me
</button>
```

---

## Component Styles

### Button (Shadcn)
```tsx
<Button className="h-12 rounded-[16px] bg-primary text-white hover:bg-primary-light">
  Action
</Button>
```

### Input (Shadcn)
```tsx
<Input 
  className="rounded-[16px] border-gray-light focus:border-primary"
  placeholder="Enter text"
/>
```

### Card (Shadcn)
```tsx
<Card className="rounded-[16px] shadow-md">
  <CardContent className="p-8">
    Content
  </CardContent>
</Card>
```

### Radio Button
**Visual**: 16×16px dot  
**Hit area**: 44×44px (via label padding)
```tsx
<label className="flex items-center p-3">
  <input type="radio" className="w-4 h-4" />
  <span className="ml-3">Option</span>
</label>
```

---

## Responsive Design

**Mobile-first approach**:
```tsx
{/* Default (mobile): 1 column */}
<div className="grid grid-cols-1">
  {/* At sm: 2 columns */}
  <div className="sm:grid-cols-2">
    {/* At lg: 3 columns */}
    <div className="lg:grid-cols-3">
      Items
    </div>
  </div>
</div>
```

**Breakpoints**:
- `sm`: 640px (tablet portrait)
- `md`: 768px (tablet landscape)
- `lg`: 1024px (desktop)

**Padding responsive**:
```tsx
<div className="p-4 sm:p-6 lg:p-8">
  Content (gets larger on wider screens)
</div>
```

---

## Dark Mode

**If implementing dark mode** (not in current spec):
```css
@theme {
  --color-dark-bg: #1a1a1a;
  --color-dark-text: #ffffff;
}

@media (prefers-color-scheme: dark) {
  .dark { @apply bg-dark-bg text-dark-text; }
}
```

---

## Accessibility

**Color contrast**: All text must have WCAG AA contrast (4.5:1 for body, 3:1 for large)
```tsx
// ✅ Good: Dark text on light background
<p className="text-gray-dark bg-white">Readable</p>

// ❌ Bad: Gray text on light gray background (low contrast)
<p className="text-gray-mid bg-gray-light">Hard to read</p>
```

**Reduced motion**:
```tsx
<div className="transition-all motion-safe:duration-300 motion-reduce:duration-0">
  Animated element
</div>
```

---

## Figma Source of Truth

Design files reference: See project Figma design file for exact hex values and component library.

---

See also:
- [CLAUDE.md](../../.claude/docs/CLAUDE.md) — Tailwind v4 conventions
- [frontend-architecture.md](frontend-architecture.md) — Component patterns
