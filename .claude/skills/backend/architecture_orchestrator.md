---
name: system-architecture-orchestrator
description: SYSTEM ROOT — The central orchestrator that defines how all skills execute together. Load this skill FIRST for any backend task. Defines skill execution order, cross-skill dependencies, and system-wide governance rules.
depends_on: []
preconditions: []
outputs:
  - Skill execution order (priority 0-4)
  - Dependency graph
  - Governance rules
conflicts: []
execution_priority: 0
---

# Architecture Orchestrator

**Skill Priority: 0 (Load First)**  
**Applies to:** All backend tasks, all skill interactions

## Purpose

This is the **root skill** of the RayCarWash engineering OS. Every backend task must be evaluated through this orchestrator before any individual skill is loaded.

## Skill Execution Priority (Global Order)

```
Priority 0 → architecture_orchestrator     ← ALWAYS load first
Priority 1 → system_contracts              ← Define the system state machine
Priority 2 → backend/domain skills        ← Implement against contracts
Priority 3 → infra skills                 ← Operate and observe
Priority 4 → ai execution skills          ← Plan, debug, execute safely
```

## Skill Dependency Graph

```
                    ┌────────────────────────┐
                    │architecture_orchestrator│
                    └───────────┬────────────┘
                                │ loads
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
     ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
     │system_contracts│ │system_contracts│  │system_contracts│
     └───────┬───────┘  └───────┬───────┘  └──────┬──────┘
             │                  │                  │
    ┌────────┼────────┐  ┌──────┘  ┌────────┐  ┌──┘
    ▼        ▼        ▼  ▼         ▼        ▼  ▼
┌────────┐ ┌──────┐ ┌──┐ ┌──────┐ ┌─────┐ ┌──┐ ┌─────────┐
│refactor│ │api_dsg│ │api_dsg│ │stripe│ │state│ │repo││workers │
└───┬────┘ └──┬───┘ └─┬┘ └──┬───┘ └──┬──┘ └──┬┘ └─┬┘└────┬────┘
    │         │        │     │        │       │    │    │
    ▼         ▼        ▼     ▼        ▼       ▼    ▼    ▼
┌─────────┐ ┌──────┐ ┌────┐ ┌───────┐ ┌────────┐ ┌──────┐
│infra/obs│ │infra/│ │inf/│ │infra/ │ │failure_│ │infra/│
│         │ │deploy│ │db_ │ │deploy │ │ modes │ │obs   │
└────┬────┘ └──┬───┘ └─┬──┘ └───┬───┘ └────┬───┘ └──┬───┘
     │         │        │        │          │         │
     └─────────┴────────┴────────┴──────────┴────────┘
                          │
                     ai skills
              (planning, debugging, safe_execution)
```

## Cross-Skill Governance Rules

### Rule 1: No Skill Executes in Isolation

Every task must answer these **system governance questions** before touching code:

1. **Which lifecycle does this touch?** (appointment, payment, request, worker)
2. **What contract does this operate under?** (from `system_contracts.md`)
3. **What failure modes are possible?** (from `failure_modes.md`)
4. **What must be observable?** (from `infra/observability.md`)

### Rule 2: Bottom-Up Within Domain, Top-Down Across System

| Direction | Rule |
|-----------|------|
| Within a domain | Model → Repo → Service → Router (bottom-up) |
| Across domains | Contract → Implementation → Observation (top-down) |
| Across layers | Orchestrator → Contracts → Execution (top-down) |

### Rule 3: Conflict Resolution

When two skills conflict, the higher priority skill wins:

```
architecture_orchestrator > system_contracts > domain > infra > ai
```

### Rule 4: The Immutability Hierarchy

Financial fields CANNOT be overridden by any skill:

```
estimated_price   → NEVER modified after appointment creation
actual_price     → Set ONLY on COMPLETED status
ledger entries   → Append-only, never modified or deleted
```

### Rule 5: The No-Cross-Domain-Service Import Rule

Services MUST NOT import other domain services. Use events instead:

```
BAD:  from domains.payments.service import PaymentService
GOOD: from domains.realtime.service import RealtimeService
GOOD: from domains.audit.repository import AuditRepository
```

## Skill Execution Decision Tree

```
Task received → Load architecture_orchestrator
                    │
           ┌────────▼────────┐
           │  What domain?  │
           └───────┬────────┘
                   │
       ┌───────────┼───────────┬──────────┐
       ▼           ▼           ▼          ▼
   ┌────────┐ ┌────────┐ ┌───────┐ ┌───────┐
   │appoint-│ │payment-│ │auth/  │ │worker-│
   │ments   │ │ments   │ │users  │ │infra  │
   └────┬───┘ └───┬────┘ └───┬───┘ └───┬───┘
        │         │           │          │
        ▼         ▼           ▼          ▼
  state_machine  stripe_     api_design  async_workers
  + system_     integratn    + auth      + observability
  contracts     + system_    + safe_     + failure_modes
              contracts    execution
```

## System-Level Checks (Every Task)

Every backend task MUST pass these checks before code is written:

```
□ Which system contract does this touch? (system_contracts.md)
□ Which failure modes apply? (failure_modes.md)
□ What is the audit event? (audit_log required?)
□ What is the observable event? (structured log required?)
□ What is the worker event? (Redis pub/sub required?)
□ What rollback plan exists? (safe_execution.md)
□ Does this violate the immutability hierarchy? (Rule 4)
□ Does this cross domain services? (Rule 5)
□ What is the execution priority? (Priority 0-4)
```

## Failure Mode Priority

When failures occur, the resolution order is:

```
1. Check request_id → trace all layers
2. Check lifecycle state → is transition valid?
3. Check financial immutability → was a financial field violated?
4. Check idempotency → is this a duplicate?
5. Check worker health → is a worker in crash loop?
6. Escalate with full trace
```

## Skill Metadata Schema

Every skill file MUST declare these fields at the top:

```yaml
---
name: skill-name
description: ...
depends_on:           # List skill names this depends on
  - architecture_orchestrator
  - system_contracts
  - [domain skill name]
preconditions:        # What must be true before this skill runs
  - Domain model defined
  - Schema defined
outputs:             # What this skill produces
  - Router endpoint
  - Service method
conflicts:          # What this skill should NOT override
  - Never modify estimated_price
execution_priority:  # 0-4
  - 2
---
```

## Success Criteria

- This skill is loaded FIRST for every backend task
- All 15 skills reference this as the dependency root
- No skill violates the governance rules
- The dependency graph is a DAG (no cycles)
- Immutability hierarchy enforced by all domain skills