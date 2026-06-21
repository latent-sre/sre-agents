# React craft

Pairs with the TypeScript conventions. Match the repo's
existing patterns first; the defaults below apply when none is set.

## Hooks rules (enforce)
- Call Hooks only at the **top level** of components/custom Hooks — never in loops, conditions, nested
  functions, or after early returns. Enforce with **`eslint-plugin-react-hooks`** (official).

## You probably don't need an Effect
- **Calculate during render** instead of syncing via `useEffect`; cache expensive work with `useMemo`.
- Reset component state by passing a different **`key`**, not an Effect.
- Logic from a **user interaction belongs in the event handler**, not an Effect.
- Use Effects only to **synchronize with an external system**.

## Server Components & directives (App Router)
- Components are Server Components by default; opt into the client with **`'use client'`** (needed for
  state/effects/event handlers/browser APIs).
- **`'use server'`** marks async Server Functions callable from the client — use for **mutations**, not
  data fetching. A Server Function passed to an `action` is a "Server Action."

## React 19
- **Actions** auto-manage pending/error state; `<form action={fn}>` submits via an Action.
- **`useActionState`** (state + dispatch + `isPending`; replaces `useFormState`), **`useFormStatus`**
  (parent form status — must be inside a `<form>`), **`useOptimistic`** (optimistic UI), and **`use()`**
  (read a Promise/context; may be called conditionally; integrates with Suspense).

## React Compiler (v1.x, stable — confirm the current release)
- Build-time auto-memoization — usually removes the need for manual `useMemo`/`useCallback`/`memo`. Keep
  manual memoization only as an escape hatch (e.g. to stabilize an Effect dependency).

## Lists, keys & performance
- Stable, unique **`key`** from your data — never the array index (reorder bugs) or `Math.random()`
  (recreates everything). Keys are scoped to siblings.
- **Virtualize** very large lists so only visible rows render.

## Tests (React Testing Library)
- "Tests should resemble how the software is used." Query by role/text; prefer
  **`@testing-library/user-event`** (`userEvent.setup()`) over `fireEvent`; don't assert implementation
  details. See `tdd-workflow`.

## Definition of done
Hooks-lint clean · no unnecessary Effects · accessible queries in tests · Vitest green.
