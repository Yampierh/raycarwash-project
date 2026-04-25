---
name: infra-database-migrations
description: Alembic migration patterns for PostgreSQL. Use when creating migrations, modifying schema, or rolling back changes.
depends_on:
  - architecture_orchestrator
  - infra-deployment
preconditions:
  - Alembic configured
  - Model defined before migration
outputs:
  - Migration file
  - Tested upgrade and downgrade
conflicts:
  - Never modify production schema without migration
  - Never drop columns referenced by other code
execution_priority: 3
---

# Database Migrations

**Priority: HIGH**  
**Applies to:** Alembic migrations, schema changes, migration testing

## Migration Workflow

```bash
# 1. Create a new migration
cd backend
alembic revision --autogenerate -m "add appointments estimated_price"

# 2. Review the generated file in alembic/versions/
# 3. Apply in dev
alembic upgrade head

# 4. Test rollback
alembic downgrade -1

# 5. Re-apply
alembic upgrade head

# 6. In CI/CD — apply before deploy
alembic upgrade head
```

## Migration Template

```python
# alembic/versions/2026xxxx_add_appointments_estimated_price.py
"""add appointments estimated_price

Revision ID: xxxxxx
Revises: xxxxxx
Create Date: 2026-04-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = 'xxxxxx'
down_revision = 'xxxxxx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'appointments',
        sa.Column('estimated_price', sa.Integer(), nullable=True),
    )
    # Add index
    op.create_index(
        'ix_appointments_estimated_price',
        'appointments',
        ['estimated_price'],
        unique=False,
        postgresql_where=(sa.text('is_deleted = false')),
    )


def downgrade() -> None:
    op.drop_index('ix_appointments_estimated_price', table_name='appointments')
    op.drop_column('appointments', 'estimated_price')
```

## Column Type Rules

| Data | Python type | DB type |
|------|-------------|---------|
| UUID | `uuid.UUID` | `UUID(as_uuid=True)` |
| Money | `int` | `Integer` (cents) |
| Timestamp | `datetime` | `DateTime(timezone=True)` |
| JSON | `dict` | `JSONB` |
| Boolean | `bool` | `Boolean` |
| Enum | `str, enum.Enum` | `Enum(name)` |

## Index Rules

Always create indexes on:
- FK columns: `ix_{table}_{column}`
- Filter columns: `is_deleted`, `status`
- Composite indexes for common queries

```python
__table_args__ = (
    Index("ix_appointments_detailer_scheduled", "detailer_id", "scheduled_time"),
    Index("ix_appointments_status_deleted", "status", "is_deleted"),
)
```

## Soft Delete Column Convention

Every table must have soft delete columns:

```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

## Rollback Rules

- Every migration must have a working `downgrade()`
- Test downgrade before merging
- Never drop columns that are still referenced
- Never remove indexes that are still needed

## Anti-Patterns

```python
# ❌ BAD: Dropping a column with CASCADE
op.drop_column('appointments', 'client_id', cascade=True)

# ✅ GOOD: No cascade — check FK first
# FK should have ONDELETE RESTRICT

# ❌ BAD: Renaming columns without backward compat
op.alter_column('appointments', 'old_name', new_name='new_name')
# Breaks in-flight deployments

# ✅ GOOD: Add new column, migrate data, drop old in separate migration
# Migration 1: add new column
# Migration 2: backfill data
# Migration 3: drop old column

# ❌ BAD: create_all() in production
# Alembic is the source of truth for schema

# ✅ GOOD: create_all() only in DEBUG mode
if settings.DEBUG:
    await conn.run_sync(Base.metadata.create_all)
```

## Success Criteria

- Every schema change goes through a migration
- `downgrade()` tested and working
- `create_all()` only runs in DEBUG mode
- All FK columns have indexes
- Soft delete columns on every table