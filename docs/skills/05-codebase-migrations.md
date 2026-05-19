# Skill 05: Codebase Migrations

> **Discipline:** DevOps / Monorepo Restructuring
> **Applies to:** Directory renames, package moves, build script updates, path refactors
> **Source:** Restructure of `web/` → `web/admin/` + `marketing/` → `web/portal/` (254 files)

---

## Overview

RayCarWash is a monorepo without a monorepo tool. `concurrently` orchestrates 4 services. Renaming directories or moving packages requires updating: build scripts, import paths, type definitions, documentation, CI/CD config, and lockfiles.

This skill codifies the process from the April 2026 restructure.

---

## Prerequisites

- Read `AGENTS.md` — directory structure, command reference
- Read root `package.json` — understand `concurrently` scripts
- Read `docs/INDEX.md` — understand plan registry

---

## Checklist

### Phase 1: Audit (before any moves)

- [ ] `git status` — working tree must be clean before starting
- [ ] Enumerate all files in source directory: `ls -R {source}`
- [ ] Enumerate all imports of source paths across the repo: `rg "from 'source/"` + `rg "require\('source/"` + `rg "source/" package.json`
- [ ] Check if destination path already exists (collision detection)
- [ ] Check `.gitignore` for source path references
- [ ] Check CI/CD configs for source path references

### Phase 2: Git mv

```bash
# Move, not copy+delete (preserves git history)
git mv {source} {destination}
```

- [ ] Verify git detected the rename (shows as `R` in `git status --porcelain`)
- [ ] Verify no unexpected files outside source directory were affected

### Phase 3: Update Import Paths

- [ ] Update `tsconfig.json` / `jsconfig.json` path aliases
- [ ] Update `next.config.js` or `next.config.ts` path aliases if any
- [ ] Update shared type definitions (`web/shared/types/` if they reference paths)
- [ ] Update `package.json` workspace references

**Import path patterns to search:**
```
# Marketing → portal
import ".../marketing/..." → ".../portal/..."

# Web → admin
import ".../web/..." → ".../admin/..."
```

### Phase 4: Update Build Scripts (root package.json)

- [ ] Find and replace all source path references in `scripts` section
- [ ] Update `dev:`, `build:`, `lint:`, `typecheck:` script names if relevant
- [ ] Verify all 4 services still have corresponding scripts
- [ ] Update `concurrently` commands:
  ```json
  "dev:all": "concurrently -n backend,frontend,admin,portal -c blue,green,yellow,magenta \"npm run dev:backend\" \"npm run dev:frontend\" \"npm run dev:admin\" \"npm run dev:portal\""
  ```

### Phase 5: Update Documentation

- [ ] `AGENTS.md` — directory table, commands section
- [ ] `docs/INDEX.md` — plan paths, category descriptions
- [ ] Every plan doc that references the old path
- [ ] `README.md` (root + affected apps)
- [ ] `.github/` workflows if they reference the old path

### Phase 6: Verify

- [ ] `npm run dev:{app}` — app starts without import errors
- [ ] `npm run build` (if applicable) — no build errors
- [ ] `npm run lint` — no new lint errors from path changes
- [ ] `git status` — only expected files changed
- [ ] Run app and navigate to affected routes (smoke test)

### Phase 7: Commit

- [ ] `git add -A` (add all changes)
- [ ] `git status` — review everything is staged
- [ ] Write commit message: `refactor: {source} → {destination} ({N} files)`

---

## Common Pitfalls

| Pitfall | Impact | Prevention |
|---------|--------|------------|
| `copy` instead of `git mv` | Lose git history | Always use `git mv` |
| Missed import in deeply nested file | Build break in CI | Run full build + lint before commit |
| `package-lock.json` changes from workspace update | Accidental dep changes | Review lockfile diff carefully |
| Node modules cache with old paths | Phantom import success locally, failure in CI | `rm -rf node_modules && npm install` |
| `.env` files referencing old paths | App config breaks | Search for `.env*` file changes |
| Multiple lockfiles warning | Cosmetics but adds noise | `agreed:` in commit message |

---

## Examples from RayCarWash

### Git mv command (April 2026)
```bash
git mv web web/admin
git mv marketing web/portal
```

### Import path update (Next.js config)
```typescript
// web/admin/tsconfig.json
"paths": {
  "@/*": ["./src/*"],   // was: @/web/*
}
```

### Script rename pattern
```json
// Before
"dev:web": "npm --prefix web run dev",
"dev:marketing": "npm --prefix marketing run dev",

// After
"dev:admin": "npm --prefix web/admin run dev",
"dev:portal": "npm --prefix web/portal run dev",
```

### Doc update pattern
```markdown
<!-- Before -->
| `marketing/` | Next.js | :3001 |

<!-- After -->
| `web/portal/` | Next.js 16 + next-intl | :3001 |
```
