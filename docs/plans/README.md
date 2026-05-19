# Operational Plans

Planes de infraestructura, calidad y operaciones para RayCarWash.

## Index

| # | File | Area | Priority | Status |
|---|------|------|----------|--------|
| 05 | [05-ci-cd.md](./05-ci-cd.md) | CI/CD pipeline — GitHub Actions, test gating, deploy | Critical | Draft |
| 06 | [06-infrastructure.md](./06-infrastructure.md) | IaC, K8s/ECS, secrets, backup/DR | High | Draft |
| 07 | [07-observability.md](./07-observability.md) | OpenTelemetry, Sentry, Grafana, logging | Medium | Draft |
| 08 | [08-hardening.md](./08-hardening.md) | Fixes críticos P0/P1 del audit | Critical | Draft |
| 09 | [09-provider-services-integration.md](./09-provider-services-integration.md) | Services catalog + per-provider link table | High | Planning |
| 10 | [10-authorization-layer.md](./10-authorization-layer.md) | Active-role + scope guards across API | High | Planning |
| 11 | [11-provider-dashboard.md](./11-provider-dashboard.md) | Provider dashboard — 12 views + 30+ endpoints | High | Planning |
| 12 | [12-marketing-redesign.md](./12-marketing-redesign.md) | Marketing site redesign (frontend done; backend gaps tracked) | High | Phases 1-4 frontend complete |
| 13 | [13-customer-dashboard.md](./13-customer-dashboard.md) | Customer "My Garage" dashboard (6 views + loyalty + subscriptions) | High | Planning |
| 14 | [14-mechanic-vertical.md](./14-mechanic-vertical.md) | Mechanic service vertical (parts, ASE, warranty, OBD-II) | Medium | Planning |
| 15 | [15-marketing-content-cms.md](./15-marketing-content-cms.md) | Admin CMS for testimonials/FAQ/coverage/templates | Medium | Planning |
| 16 | [16-coverage-zip-service.md](./16-coverage-zip-service.md) | Service zones + ZIP lookup + provider opt-in | Medium-High | Planning |
| 17 | [17-waitlist-system.md](./17-waitlist-system.md) | Generalized waitlist (mechanic, coverage, future verticals) | Medium | Planning |

## Dependency order

```
08-hardening.md  (arreglos inmediatos, sin dependencias)
  ├── 05-ci-cd.md  (requiere 08 Phase 0: código estable)
  │     └── 06-infrastructure.md  (requiere CI/CD)
  │           └── 07-observability.md  (requiere infra desplegada)
  │
  └── Integration Plans E0-E4 (requieren 08 Phase 0-2)
        ├── 00-user.md → 01-profiles.md
        ├── 04-vehicles.md (paralelo a 01)
        └── 02-detailing.md → 03-mechanic.md
              ↓
              09-provider-services-integration.md
                ↓
                10-authorization-layer.md
                  ├── 11-provider-dashboard.md (depende también de 09, 15)
                  ├── 13-customer-dashboard.md (depende de 04 vehicles)
                  ├── 14-mechanic-vertical.md (depende de 03, 09, 11, 15, 17)
                  ├── 15-marketing-content-cms.md (depende de 12)
                  ├── 16-coverage-zip-service.md (depende de h3 infra)
                  └── 17-waitlist-system.md (depende de email infra)
```

### Plans by surface

| Surface | Plans |
|---|---|
| **Portal public site** (`web/portal/(marketing)/`) | 12 (redesign), 15 (CMS), 16 (coverage), 17 (waitlist) |
| **Provider dashboard** (`web/portal/(app)/detailer/dashboard/`) | 11 (full dashboard), 09 (services), 10 (auth), 14 (mechanic ext.) |
| **Customer dashboard** (`web/portal/(app)/client/dashboard/`) | 13 (full dashboard) |
| **Mobile app** (`frontend/`) | Largely covered by existing screens; updates in 11, 13, 14 |
| **Backend cross-cutting** | 08 (hardening), 10 (auth), 15 (CMS), 16 (coverage), 17 (waitlist) |
| **Ops/infra** | 05, 06, 07 |

## Cross-references

- **Master Index**: [`docs/INDEX.md`](../INDEX.md) — manifiesto central, estado, trazabilidad
- **Integration Plans**: [`docs/integration_plans/`](../integration_plans/) — planes de producto (E0-E4)
- **Technical Audit**: [`docs/audit/`](../audit/) — hallazgos referenciados por cada plan
- **Design source**: [`raycarwash/project/`](../../raycarwash/project/) — prototipos HTML/JSX/CSS

## Convention

- One plan per cross-cutting operational or product concern
- Numbered by approximate implementation order (continúa desde integration_plans 00-04)
- Every plan references relevant audit findings
- Plans 11-17 are **design-driven** — they map the Claude Design bundle (`raycarwash/project/`) to backend requirements
- Mark `Status: Done` only when all Definition of Done items are verified
