---
name: ai-planning
description: Task decomposition and planning for complex features. Use when starting a new sprint, a complex task, or a multi-step implementation. Breaks down work into traceable, verifiable steps.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - backend-api-design
  - backend-state-machine
  - backend-service-layer
preconditions:
  - Which lifecycle does this touch?
  - Which failure modes apply?
  - Which skills must be loaded?
outputs:
  - Feature planning document
  - Atomic task decomposition
  - Implementation order following bottom-up pattern
conflicts:
  - Never skip system_contracts review
  - Never implement without failure_modes analysis
execution_priority: 4
---

# Planning Complex Features

**Priority: CRITICAL**  
**Applies to:** New features, sprint planning, complex multi-step tasks

## Step-by-Step Process

### 1. Understand the Scope

Before writing code, answer:
1. What does this feature do from the user's perspective?
2. What API endpoints does it expose?
3. What domain(s) does it touch?
4. What are the edge cases?
5. What existing code does it extend?

### 2. Map the Architecture

```
Frontend → Router → Service → Repository → Model
              ↓
         Schema (request/response)
              ↓
         Audit log
              ↓
         Worker (async side effects)
              ↓
         WebSocket (real-time)
```

### 3. Break Into Atomic Tasks

Each task should be:
- Verifiable in under 5 minutes
- Testable with pytest
- Independent (doesn't depend on future tasks)

Example decomposition for "Multi-vehicle booking":

```
□ Add AppointmentVehicle model (snapshot vehicle at booking)
□ Add vehicle_id FK to AppointmentVehicle → Appointment
□ Update AppointmentRepository.find_by_client to include vehicles
□ Update fare calculation to sum all vehicle prices
□ Update BookingSummary schema to list vehicles
□ Update seed data to include multi-vehicle test cases
□ Write tests for multi-vehicle fare calculation
□ Add multi-vehicle to appointment creation endpoint
□ Write integration test for multi-vehicle booking flow
```

### 4. Identify Cross-Cutting Concerns

Every feature needs:

| Concern | What to check |
|---------|--------------|
| Auth | Which endpoints need auth? Which roles? |
| Schema | Request + response schemas defined? |
| Audit | Which mutations need audit logs? |
| Validation | Pydantic validators on schemas? |
| Errors | All error codes documented with `responses={}`? |
| Tests | Unit tests for service, integration tests for flow |

### 5. Check Existing Patterns

Before implementing:
1. Search `domains/{domain}/` for similar patterns
2. Check if a repository method already exists
3. Look at seed functions for test data
4. Check `VALID_TRANSITIONS` for state machine changes
5. Review existing endpoints for naming conventions

### 6. Verify Against Contract

After implementation:
1. Schema matches the model
2. Endpoint path follows conventions
3. Auth applied correctly
4. Audit logs emitted
5. Tests pass
6. Swagger shows correct response codes

## Feature Planning Template

```markdown
## Feature: [Name]

### User Story
As a [role], I can [action] so that [benefit].

### API Contract
- `POST /api/v1/resource` — create
- `GET /api/v1/resource/{id}` — read
- `PATCH /api/v1/resource/{id}` — update

### Domain Touched
- `domains/resource/` — models, repository, service, router, schemas

### Data Model Changes
```python
# domains/resource/models.py
class NewField(TimestampMixin, Base):
    ...
```

### Edge Cases
1. Duplicate creation → 409 Conflict
2. Not found → 404
3. Unauthorized → 401
4. Forbidden role → 403
5. Invalid input → 422

### Implementation Order
1. Model + schema
2. Repository method
3. Service method
4. Router endpoint
5. Audit log
6. Tests
```

## Anti-Patterns

```markdown
# ❌ BAD: Vague task
"Implement booking flow"

# ✅ GOOD: Traceable task
"Update AppointmentRepository.find_by_client to include AppointmentVehicle
with vehicle make/model/year in response schema"

# ❌ BAD: Skip schema design
"Start coding and figure out the schema as we go"

# ✅ GOOD: Schema-first
"Define AppointmentVehicleSchema before writing repository"

# ❌ BAD: No edge cases
"Just make it work for the happy path"

# ✅ GOOD: Edge cases upfront
"Handle duplicate email → 409, invalid role → 403"
```

## Success Criteria

- Every task has an owner (code path) and verification (test)
- Schema defined before service code
- Edge cases identified before implementation
- Cross-cutting concerns checked (auth, audit, errors)
- Implementation order follows Router → Service → Repository → Model bottom-up