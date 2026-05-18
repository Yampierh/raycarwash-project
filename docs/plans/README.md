# Operational Plans

Planes de infraestructura, calidad y operaciones para RayCarWash.

## Index

| # | File | Area | Priority | Status |
|---|------|------|----------|--------|
| 05 | [05-ci-cd.md](./05-ci-cd.md) | CI/CD pipeline — GitHub Actions, test gating, deploy | Critical | Draft |
| 06 | [06-infrastructure.md](./06-infrastructure.md) | IaC, K8s/ECS, secrets, backup/DR | High | Draft |
| 07 | [07-observability.md](./07-observability.md) | OpenTelemetry, Sentry, Grafana, logging | Medium | Draft |
| 08 | [08-hardening.md](./08-hardening.md) | Fixes criticos P0/P1 del audit | Critical | Draft |

## Dependency Order

```
08-hardening.md  (arreglos inmediatos, sin dependencias)
  |-- 05-ci-cd.md  (requiere 08 Phase 0: codigo estable)
  |     `-- 06-infrastructure.md  (requiere CI/CD)
  |           `-- 07-observability.md  (requiere infra desplegada)
  |
  `-- Integration Plans E0-E4 (requieren 08 Phase 0-2)
        |-- 00-user.md -> 01-profiles.md
        |-- 04-vehicles.md (paralelo a 01)
        `-- 02-detailing.md -> 03-mechanic.md
```

## Cross-References

- **Master Index**: [`docs/INDEX.md`](../INDEX.md) — manifest central, estado, trazabilidad
- **Integration Plans**: [`docs/integration_plans/`](../integration_plans/) — planes de producto (E0-E4)
- **Technical Audit**: [`docs/audit/`](../audit/) — hallazgos referenciados por cada plan

## Convention

- One plan per cross-cutting operational concern
- Numbered by implementation order (continua desde integration_plans 00-04)
- Every plan references relevant audit findings
- Mark `Status: Done` only when all Definition of Done items are verified
