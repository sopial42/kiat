# Frontend Architecture: Next.js + React + Shadcn/UI

Comprehensive guide to building scalable, accessible frontend features.

---

## Stack

- **Framework**: Next.js 16 with App Router
- **Language**: TypeScript (strict mode)
- **UI Library**: Shadcn/UI (Radix + Tailwind)
- **Styling**: Tailwind v4 (CSS variables, no config)
- **Data Fetching**: TanStack Query (React Query)
- **Auth**: Clerk (real or test mode)

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                       # Next.js App Router pages
│   │   ├── layout.tsx            # Root layout
│   │   ├── page.tsx              # Home page
│   │   ├── (auth)/               # Auth group layout
│   │   │   ├── sign-in/page.tsx
│   │   │   └── sign-up/page.tsx
│   │   ├── dashboard/            # Authenticated pages
│   │   │   ├── layout.tsx        # Dashboard layout
│   │   │   └── page.tsx
│   │   └── api/                  # API routes (if needed)
│   ├── components/               # Reusable components
│   │   ├── ui/                   # Shadcn components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   └── features/             # Feature-specific components
│   │       ├── ItemForm.tsx
│   │       └── ItemCard.tsx
│   ├── hooks/                    # Custom hooks
│   │   ├── useQuery.ts           # Data fetching (wrapped)
│   │   ├── useMutation.ts        # Mutations (wrapped)
│   │   └── useAutoSave.ts        # Auto-save pattern
│   ├── lib/                      # Utilities
│   │   ├── api.ts                # API client
│   │   ├── utils.ts              # General utilities
│   │   └── constants.ts          # App constants
│   ├── types/                    # TypeScript types
│   │   └── index.ts
│   ├── providers/                # Context providers
│   │   ├── QueryProvider.tsx
│   │   └── AuthProvider.tsx
│   └── globals.css              # Tailwind setup
├── e2e/                          # Playwright tests
├── public/                       # Static assets
└── playwright.config.ts          # Playwright config
```

---

## API Integration

Frontend calls the backend through **relative URLs** (`fetch('/api/items')`). `next.config.ts` rewrites `/api/*` to the backend service:

```ts
// frontend/next.config.ts
const backend = process.env.BACKEND_URL ?? 'http://localhost:8080';
export default {
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${backend}/:path*` }];
  },
};
```

`BACKEND_URL` is a server-side env var (NO `NEXT_PUBLIC_` prefix) — change at deploy time without rebuilding the image, no CORS to configure (same-origin), no `NEXT_PUBLIC_API_URL` baked into the client bundle. Dev default is `http://localhost:8080`; in prod set to the backend service's internal URL (Cloud Run service, K8s service name, etc.).

Do **not** ship a `NEXT_PUBLIC_API_URL` for the frontend to read directly — that path puts the backend hostname into the client bundle, requires explicit CORS, and forces a per-env image rebuild. Use the rewrite.

---

## Server vs Client Components

### Server Components (Default)

**When**: Page layout, data fetching, metadata, server-only operations

```tsx
// app/page.tsx (Server Component by default)
import { getUserData } from '@/lib/api';

export default async function DashboardPage() {
  const data = await getUserData();  // ← Server-side fetch, no waterfall
  
  return (
    <div>
      <h1>{data.title}</h1>
      <ItemForm initialData={data} />  {/* ← Client component for interaction */}
    </div>
  );
}
```

**Benefits**:
- Direct database access (no API call)
- Secrets safe (never sent to browser)
- Smaller JS bundle
- Better SEO (server renders HTML)

### Client Components

**When**: Forms, interactive state, hooks (useState, useEffect, useQuery)

```tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';

interface ItemFormProps {
  initialData?: ItemData;
}

export function ItemForm({ initialData }: ItemFormProps) {
  const [name, setName] = useState(initialData?.name || '');
  const { mutate, isPending } = useMutation({
    mutationFn: (data) => api.createItem(data),
    onSuccess: () => {
      // Refresh, navigate, etc.
    },
  });

  return (
    <form onSubmit={() => mutate({ name })}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <Button disabled={isPending}>Create</Button>
    </form>
  );
}
```

**Key rule**: Pass data from Server → Client via props. Never fetch same data twice.

```tsx
// ✅ GOOD: Server fetches, passes to client
async function Page() {
  const data = await fetch(...);  // Server-side
  return <ClientComponent data={data} />;
}

// ❌ BAD: Both server and client fetch (double request)
async function Page() {
  const data = await fetch(...);  // Server fetch
  return <ClientComponent />;  // Client also fetches (N+1)
}
```

---

## Hooks Patterns

### useQuery (Data Fetching)

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function ItemList() {
  const { data: items, isLoading, error } = useQuery({
    queryKey: ['items'],  // Cache key
    queryFn: () => api.getItems(),
  });

  if (isLoading) return <Skeleton />;
  if (error) return <ErrorBoundary error={error} />;

  return (
    <div>
      {items?.map((item) => (
        <ItemCard key={item.id} item={item} />
      ))}
    </div>
  );
}
```

**Key rules**:
- Cache key should match your data structure
- Queries don't fire in loops (see N+1 pitfall)
- Don't use `enabled` with constantly changing dependencies

### useMutation (Create/Update/Delete)

```tsx
'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function CreateItemButton() {
  const queryClient = useQueryClient();

  const { mutate, isPending, error } = useMutation({
    mutationFn: (data) => api.createItem(data),
    onSuccess: () => {
      // Invalidate cached data to refetch
      queryClient.invalidateQueries({ queryKey: ['items'] });
      // Or: queryClient.refetchQueries({ queryKey: ['items'] });
    },
    onError: (err) => {
      // Handle error (show toast, etc.)
      console.error('Failed to create item:', err);
    },
  });

  return (
    <Button
      onClick={() => mutate({ title: 'First item' })}
      disabled={isPending}
    >
      {isPending ? 'Creating...' : 'Create Item'}
    </Button>
  );
}
```

### useAutoSave (Forms with Auto-Persistence)

```tsx
'use client';

import { useCallback, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface UseAutoSaveOptions<T> {
  initialData: T;
  onSave: (data: T) => Promise<void>;
  debounceMs?: number;
  enabled?: boolean;
}

export function useAutoSave<T>({
  initialData,
  onSave,
  debounceMs = 500,
  enabled = true,
}: UseAutoSaveOptions<T>) {
  const [data, setData] = useState<T>(initialData);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const debounceRef = useRef<NodeJS.Timeout>();

  const { mutate: save } = useMutation({
    mutationFn: () => onSave(data),
    onMutate: () => setSaveStatus('saving'),
    onSuccess: () => setSaveStatus('saved'),
    onError: () => setSaveStatus('error'),
  });

  const handleChange = useCallback((newData: T) => {
    setData(newData);
    
    // Only auto-save if enabled
    if (!enabled) return;

    // Debounce save
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      save();
    }, debounceMs);
  }, [enabled, save]);

  return { data, saveStatus, handleChange };
}

// Usage
export function ItemForm({ initialData }) {
  const { data, saveStatus, handleChange } = useAutoSave({
    initialData,
    onSave: (data) => api.updateItem(data),
    enabled: true,  // ← Must be stable (not `!isLoading`)
  });

  return (
    <form>
      <input 
        value={data.name}
        onChange={(e) => handleChange({ ...data, name: e.target.value })}
      />
      {saveStatus === 'saving' && <span>Saving...</span>}
      {saveStatus === 'saved' && <span>Saved ✓</span>}
      {saveStatus === 'error' && <span>Error saving</span>}
    </form>
  );
}
```

---

## Component Patterns

### Shadcn/UI Components

**Always use Shadcn, never build from scratch:**

```tsx
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Title</CardTitle>
      </CardHeader>
      <CardContent>
        <Input placeholder="Enter text" />
        <Button>Submit</Button>
      </CardContent>
    </Card>
  );
}
```

### Form Handling (React Hook Form + Shadcn)

```tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Form, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
});

type FormData = z.infer<typeof formSchema>;

export function ItemForm() {
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      email: '',
    },
  });

  const onSubmit = async (data: FormData) => {
    try {
      await api.createItem(data);
      // Success handling
    } catch (error) {
      form.setError('root', { message: 'Failed to create' });
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <Input {...field} />
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Create</Button>
      </form>
    </Form>
  );
}
```

---

## Styling

### Tailwind v4 (No Config)

All tokens in `frontend/src/globals.css`. The full token set + naming protocol lives in [`design-system.md`](design-system.md); this is just an excerpt to show the wiring.

```css
@import 'tailwindcss';

/* Shadcn/UI vocabulary — every primitive added via `npx shadcn@latest add`
   references these names. Defaults are neutral (slate grayscale) until a
   visual reference arrives. See design-system.md for the full block. */
@theme {
  --color-background:           #ffffff;
  --color-foreground:           #0f172a;  /* slate-900 */

  --color-primary:              #0f172a;
  --color-primary-foreground:   #f8fafc;  /* slate-50 */

  --color-muted:                #f1f5f9;  /* slate-100 */
  --color-muted-foreground:     #64748b;  /* slate-500 */

  --color-destructive:          #ef4444;  /* red-500 */
  --color-destructive-foreground: #f8fafc;

  --color-border:               #e2e8f0;  /* slate-200 */
  --color-ring:                 #0f172a;

  --spacing-md: 1rem;
  --radius:     0.5rem;          /* 8px base — derived sizes in design-system.md */
}

@layer base {
  body {
    @apply bg-background text-foreground;
  }
}

@layer components {
  .card {
    @apply bg-card text-card-foreground rounded-lg border shadow-sm p-6;
  }

  .btn-primary {
    @apply px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90;
  }
}
```

### Responsive Breakpoints

```tsx
{/* Mobile-first (default is mobile width) */}
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 1 column on mobile, 2 on tablet (640px+), 3 on desktop (1024px+) */}
</div>

{/* Padding responsive */}
<div className="p-4 sm:p-6 lg:p-8">
  Content
</div>

{/* Hide on mobile */}
<div className="hidden lg:block">
  Desktop-only content
</div>
```

---

## Accessibility

### Labels (CRITICAL)

Every input must have a label (visible or `aria-label`):

```tsx
// ✅ GOOD: Visible label
<label htmlFor="email">Email:</label>
<input id="email" type="email" />

// ✅ GOOD: Aria label (hidden visually)
<input aria-label="Search" type="text" placeholder="Search..." />

// ❌ BAD: No label at all
<input type="email" />
```

### ARIA Attributes

```tsx
// Button with aria-label
<button aria-label="Close dialog" onClick={onClose}>
  ✕
</button>

// Dialog with aria-labelledby
<div role="dialog" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Delete</h2>
</div>

// List with aria-label
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/">Home</a></li>
  </ul>
</nav>
```

### Keyboard Navigation

```tsx
// Form with Tab-able elements
<form>
  <input tabIndex={0} />
  <button type="submit" tabIndex={0}>Submit</button>
  {/* Escape closes dialog */}
  {isOpen && <Dialog onKeyDown={(e) => e.key === 'Escape' && onClose()} />}
</form>
```

### Reduced Motion

```tsx
<div className="transition-all motion-safe:duration-300 motion-reduce:duration-0">
  Animated element (no animation if user prefers reduced motion)
</div>
```

---

## Common Pitfalls

### Pitfall 1: Stale Closure

```tsx
// ❌ BAD
useEffect(() => {
  const interval = setInterval(() => {
    console.log(count);  // Always 0
  }, 1000);
}, []);  // Missing dependency

// ✅ GOOD
useEffect(() => {
  const interval = setInterval(() => {
    console.log(count);  // Current count
  }, 1000);
}, [count]);  // Include dependency
```

### Pitfall 2: Multiple mutations on same data

```tsx
// ❌ BAD: Race condition
const handleChange = async () => {
  await selectZone.mutate('zone1');
  await clearOther.mutate(...);  // Stale updated_at
};

// ✅ GOOD: Chain within one mutation
const { mutate } = useMutation(async (zone) => {
  await selectZone.mutate(zone);
  const latest = await getLatest();  // Fresh data
  await clearOther.mutate(latest);
});
```

### Pitfall 3: useAutoSave enabled contract

```tsx
// ❌ BAD: enabled changes when data loads (triggers double-save)
const { data, useAutoSave } = useForm();
const { handleSave } = useAutoSave({
  enabled: !isLoading,  // ← Transitions false→true
});

// ✅ GOOD: Stable condition
const shouldSave = !isLoading && isReady;  // Decoupled from data
const { handleSave } = useAutoSave({
  enabled: shouldSave,
});
```

---

## Testing (Playwright)

See `delivery/specs/testing.md` for full testing guide. Key points:

- ✅ Wait for elements: `waitForSelector()`, `waitForURL()`
- ✅ Use roles: `getByRole('button', { name: 'Save' })`
- ❌ Never: `waitForTimeout()`, `serial` mode
- ❌ Never: Assert transient UI ('Saving...')

---

See also:
- [CLAUDE.md](CLAUDE.md) — General conventions
- [design-system.md](../delivery/specs/design-system.md) — Colors, spacing, typography
- [testing.md](../delivery/specs/testing.md) — Playwright anti-flakiness
