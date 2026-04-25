---
name: ai-safe-execution
description: Guardrails for destructive and irreversible operations. Use before running migrations, deleting data, dropping tables, or modifying production code.
depends_on:
  - architecture_orchestrator
  - infra-database-migrations
preconditions:
  - Backup taken before destructive operation
  - Rollback plan documented
outputs:
  - Verified rollback capability
  - Documented pre-flight checklist
conflicts:
  - Never hard-delete data
  - Never modify financial fields
  - Never bypass backup verification
execution_priority: 4
---

# Safe Execution Guardrails

**Priority: CRITICAL**  
**Applies to:** Destructive operations, migrations, rollbacks, production changes

## When to Use

Apply this skill before executing:
- `alembic downgrade`
- `DROP TABLE`, `DROP COLUMN`
- `DELETE FROM` (not soft delete)
- Bulk data deletion
- Modifying `estimated_price` or `actual_price`
- Production schema changes
- Deploying breaking changes

## Pre-Execution Checklist

### 1. Identify the Operation Type

| Operation | Risk Level | Guard |
|-----------|-----------|-------|
| Read-only query | Low | No guard needed |
| INSERT / UPDATE single row | Medium | Verify test passes first |
| ALTER TABLE (add column) | Medium | Check downgrrade path |
| alembic downgrade | **HIGH** | Check current head, test upgrade first |
| DROP TABLE / DROP COLUMN | **CRITICAL** | Full rollback plan + backup |
| Bulk DELETE | **CRITICAL** | Verify WHERE clause + soft delete first |
| Modifying financial fields | **CRITICAL** | Verify no production data depends on it |

### 2. Create a Rollback Plan

Before ANY destructive operation:

```markdown
## Rollback Plan: Drop column estimated_price

### Risk Assessment
- **HIGH** — This column is referenced in financial calculations
- **If deployed**: All appointments lose their estimated price
- **Rollback**: alembic upgrade head (re-adds column)

### Pre-flight
- [ ] Backup: `pg_dump raycarwash > backup.sql`
- [ ] Test downgrade locally
- [ ] Verify no production data references column directly
- [ ] Notify team of maintenance window

### Execution
1. Create migration to drop column
2. Test downgrade locally
3. Test upgrade locally
4. Apply migration in CI/CD pipeline
```

### 3. Verify Backup

Before dropping anything:

```bash
# Backup before destructive migration
pg_dump -h localhost -U postgres -d raycarwash > backup_$(date +%Y%m%d).sql

# Verify backup
wc -l backup_*.sql  # Should have content
```

## Destructive Operation Rules

| Operation | Rule |
|-----------|------|
| Hard DELETE | **Never** — always soft delete |
| DROP TABLE | Backup first, test restore, check FK cascades |
| DROP COLUMN | Check if any application code uses it |
| Bulk UPDATE on financial data | Verify `estimated_price` / `actual_price` |
| Modifying appointment status | Check `VALID_TRANSITIONS` — don't bypass |
| Modifying ledger entries | **Never** — append-only |

## Confirmation Protocol

For CRITICAL operations (DROP TABLE, hard DELETE, financial field changes):

1. **Describe the operation** — what will change, what will be lost
2. **Verify the current state** — `alembic current`, DB backup
3. **Confirm rollback plan** — how to restore if wrong
4. **Check team notification** — maintenance window if production

Example confirmation check:

```
OPERATION: alembic downgrade -1
TARGET: Drop last migration (add_estimated_price)
RISK: Loses estimated_price column from appointments table

CURRENT HEAD: abc123 (add_estimated_price)
BACKUP: pg_dump taken ✓
ROLLBACK PLAN: alembic upgrade head (re-creates column)
TESTED LOCALLY: Yes ✓

Confirm? [Y/N]
```

## Anti-Patterns

```bash
# ❌ BAD: Run downgrade without checking current head
alembic downgrade -1
# You might be undoing the wrong migration

# ✅ GOOD: Verify first
alembic current
alembic history -- indicate  # shows full lineage

# ❌ BAD: Hard delete for debugging
DELETE FROM appointments WHERE id = '...'
# Bypasses audit trail

# ✅ GOOD: Soft delete
UPDATE appointments SET is_deleted=True, deleted_at=NOW()
WHERE id = '...'

# ❌ BAD: Modify estimated_price to fix a bug
appointment.estimated_price = 1000  # Financial corruption

# ✅ GOOD: Recalculate based on formula
appointment.estimated_price = calculate_fare(service, vehicles, addons)
```

## Production Change Rules

- [ ] Migration tested locally (upgrade + downgrade)
- [ ] Backup taken
- [ ] Rollback plan documented
- [ ] CI/CD pipeline used (not manual `alembic upgrade head`)
- [ ] Team notified of maintenance window
- [ ] Smoke test after deploy

## Success Criteria

- No hard deletes in codebase
- All destructive operations have rollback plans
- Backup verified before any DROP
- Financial fields never modified manually
- Production changes go through CI/CD