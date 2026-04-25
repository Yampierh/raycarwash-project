# CLAUDE CODE EXECUTION PROTOCOL (RayCarwash System)

## PURPOSE
This protocol defines the mandatory execution flow for ALL backend changes in this repository.

It transforms the skills system into an enforceable decision pipeline for code generation.

Claude Code MUST follow this protocol before writing or modifying any code.

---

# 1. CORE EXECUTION PRINCIPLE

All changes MUST follow this deterministic flow:

ARCHITECTURE → CONTRACTS → DOMAIN SKILL → IMPLEMENTATION → OBSERVABILITY → VALIDATION

No step can be skipped.

---

# 2. MANDATORY SKILL LOADING ORDER

Before any implementation:

### STEP 1 — SYSTEM FOUNDATION
- architecture_orchestrator (always first)
- system_contracts
- failure_modes

### STEP 2 — DOMAIN CONTEXT
Load ONLY relevant domain skills:
- backend-api-design
- backend-service-layer
- backend-repository-pattern
- backend-state-machine (if applicable)
- backend-async-workers (if background tasks exist)
- backend-websocket (if real-time is involved)
- backend-stripe (if payments involved)

### STEP 3 — INFRASTRUCTURE RULES
- infra-observability
- infra-deployment (if environment changes required)
- infra-database-migrations (if schema changes occur)

### STEP 4 — AI ASSIST SKILLS (ONLY IF NEEDED)
- ai-planning (feature decomposition)
- ai-debugging (fixing issues)
- ai-safe-execution (destructive operations)

---

# 3. IMPLEMENTATION FLOW (STRICT ORDER)

## STEP A — ARCHITECTURE VALIDATION
Check:
- Does this change violate system_contracts?
- Does it introduce new failure_modes?
- Does it break existing domain boundaries?

If YES → STOP and redesign.

---

## STEP B — API DESIGN (if endpoints are involved)
Rules:
- All endpoints must follow API versioning (/api/v1/)
- Pydantic schemas MUST be defined BEFORE endpoint implementation
- No raw dict responses allowed
- All mutations MUST be audited

---

## STEP C — SERVICE LAYER RULES
- Business logic ONLY
- NO SQL queries allowed
- NO HTTP calls inside services
- NO direct cross-service calls
- Must be transaction-safe (db.begin())
- Must return typed objects (not dicts)

---

## STEP D — REPOSITORY LAYER RULES
- All DB access goes through repositories
- Must use async SQLAlchemy (select())
- MUST enforce soft deletes
- MUST use proper indexing assumptions
- MUST return domain models or typed results

---

## STEP E — STATE MACHINE (if applicable)
If entity has lifecycle states:
- Validate transitions against VALID_TRANSITIONS
- Never bypass state rules
- Never modify immutable fields (e.g. estimated_price)
- Always log transitions in audit trail

---

## STEP F — WORKERS (if async/background logic exists)
- Must be idempotent
- Must handle retries safely
- Must not block event loop
- Must not contain business logic (only execution triggers)

---

## STEP G — OBSERVABILITY (MANDATORY)
Every execution MUST include:
- request_id propagation
- structured JSON logging
- audit logging for mutations
- error context enrichment

No exception.

---

# 4. FAILURE MODE HANDLING

Before finalizing implementation:

Check:
- What happens if DB fails?
- What happens if Stripe fails?
- What happens if worker crashes?
- What happens if WebSocket disconnects?
- What happens if state transition is invalid?

All failure modes MUST map to:
failure_modes skill

If not covered → STOP and define behavior.

---

# 5. OUTPUT VALIDATION CHECKLIST

Before returning any code:

- [ ] No SQL in services
- [ ] No missing repository layer
- [ ] No schema-less endpoints
- [ ] No missing audit logs on mutations
- [ ] No missing request_id logging
- [ ] No bypassed state machine rules
- [ ] No cross-domain imports violating boundaries
- [ ] All async operations are properly awaited
- [ ] All DB mutations are transactional

If ANY item fails → revision required.

---

# 6. EXECUTION RULE

Claude Code MUST treat this file as HARD CONSTRAINTS, not suggestions.

If a conflict exists between:
- speed vs correctness → correctness wins
- simplicity vs architecture → architecture contracts win
- convenience vs rules → rules win

---

# 7. FINAL PRINCIPLE

This system prioritizes:
- consistency
- predictability
- auditability
- production safety

Over:
- shortcuts
- ad-hoc implementation
- experimental structures

---

END OF PROTOCOL