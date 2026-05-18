# 05 — CI/CD Pipeline

> **Status:** Draft
> **Priority:** Critical
> **Dependencies:** 08-hardening.md Phase 0 (codigo estable + tests verdes)
> **Audit findings resolved:** L14 (no postinstall hook), L15 (dev omits web), L16 (venv path), L17 (no backend compose), L18 (Redis persistence)

## 1. Objective

Establecer un pipeline CI/CD automatizado que garantice calidad antes de cada merge y despliegue reproducible a produccion.

## 2. Scope

- CI: test gating, linting, type-check, migraciones round-trip, envelope compliance
- CD: deploy automatico a staging + manual gate a produccion
- Infra como soporte (no IaC — eso es plan 06)

## 3. Stack

| Herramienta | Uso |
|-------------|-----|
| GitHub Actions | Orquestador principal |
| pytest + mypy + ruff | CI quality gates |
| pytest-xdist | Tests en paralelo |
| Docker Buildx | Multi-arch image build |
| GitHub Container Registry | Almacenamiento de imagenes |
| Vercel | Deploy web + marketing (ya integrado) |

## 4. Pipeline Design

### CI (Push + PR a master)

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    - ruff check backend/
    - mypy backend/
  test:
    - docker compose up -d postgres redis
    - alembic upgrade head
    - pytest -n auto --maxfail=5
    - alembic downgrade base && alembic upgrade head  # round-trip
  envelope:
    - pytest tests/test_envelope_compliance.py -v
  api-contract:
    - openapi-diff HEAD~1 HEAD  # detect breaking changes
```

### CD (Push a master / tag)

```yaml
staging:
  - build & push Docker image
  - deploy to staging env
  - smoke tests (httpie suite)
  - notify #releases

production:
  - requires: staging OK
  - manual approval
  - deploy to production
  - run e2e smoke tests
  - notify #releases
```

## 5. Secrets Management

| Secret | Origin | Rotacion |
|--------|--------|----------|
| `JWT_PRIVATE_KEY` | GitHub Actions secret | Cada 90 dias |
| `STRIPE_SECRET_KEY` | GitHub Actions secret | Cada 180 dias |
| `ENCRYPTION_KEY` | GitHub Actions secret | Cada 90 dias |
| `DATABASE_URL` | GitHub Actions secret | Por deploy |
| `DOCKER_USERNAME` / `DOCKER_PASSWORD` | GitHub Actions secret | Cada 180 dias |

## 6. Implementation

| Step | Description | Effort |
|------|-------------|--------|
| 1 | Crear `.github/workflows/ci.yml` | 1 dia |
| 2 | Crear `.github/workflows/cd-staging.yml` | 1 dia |
| 3 | Crear `.github/workflows/cd-production.yml` | 1 dia |
| 4 | Configurar secrets en GitHub repo | 0.5 dia |
| 5 | Crear `Dockerfile` multi-stage optimizado | 0.5 dia |
| 6 | Smoke test suite script | 1 dia |
| 7 | Documentar runbook en `docs/plans/05-ci-cd-runbook.md` | 0.5 dia |

## 7. Definition of Done

- [ ] CI corre en cada push, <10 min
- [ ] Tests rotos -> PR bloqueado
- [ ] Deploy a staging automatico post-merge
- [ ] Deploy a produccion con approval manual
- [ ] Smoke tests pasan post-deploy
- [ ] Runbook documentado
