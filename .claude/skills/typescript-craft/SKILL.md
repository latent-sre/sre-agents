---
name: typescript-craft
description: >-
  Idiomatic, modern (2025–2026) TypeScript conventions for this team — strict tsconfig, linting,
  testing, and type-safety idioms. Use whenever writing, reviewing, or refactoring TypeScript. Covers
  strict + verbatimModuleSyntax + noUncheckedIndexedAccess, typescript-eslint vs Biome, Vitest, unknown
  over any, satisfies, discriminated unions, and import type.
metadata:
  domain: language
  language: typescript
---

# TypeScript craft

Match the repo's existing tooling first; the
defaults below apply when none is set.

## tsconfig (modern core)
- **`strict: true`** (enables `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, …). Add
  **`verbatimModuleSyntax`**, **`isolatedModules`**, and for extra safety **`noUncheckedIndexedAccess`**
  + **`noImplicitOverride`**.
- **Module resolution:** `"bundler"` for bundled apps (`module: "esnext"`); `"nodenext"` for libraries
  that ship `tsc` output (so Node-correctness is verified).

## Lint & format
- **typescript-eslint flat config** for plugin-rich / type-aware projects: `recommended` → `strict` +
  `stylistic`; enable type-checked rules via `strictTypeChecked`/`stylisticTypeChecked` with
  `parserOptions.projectService` (typed linting runs ≈at type-check speed — worth it).
- **Biome** is the fast all-in-one (single Rust binary, lint+format, ~97% Prettier-compatible) — good
  for new/speed-sensitive projects; keep ESLint when you need its plugins or type-aware rules.

## Idioms
- Prefer **`unknown` over `any`** — it forces narrowing (catch clauses are `unknown` under strict).
- **`satisfies`** to validate a value against a type *without widening* (config objects, unions);
  reserve `as` for the last resort.
- Model variants as **discriminated unions** + a `never` default for exhaustiveness.
- Use **`import type`** for type-only imports (enforced by `verbatimModuleSyntax`); enable
  `consistent-type-imports`.

## Pitfalls
- `as`-casting away type errors; `any` leaks; non-null `!` to silence `strictNullChecks`; assuming
  index access is defined (use `noUncheckedIndexedAccess`); enums where unions/`as const` are clearer.

## Tests
- **Vitest** is the modern default (native ESM/TS, Jest-compatible API, fast watch). Jest is fine for
  large legacy suites. Test behavior, not internals. See `tdd-workflow`.

## Definition of done
`tsc --noEmit` clean under strict · ESLint/Biome clean · Vitest green.
