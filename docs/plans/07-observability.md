# 07 — Observability & Monitoring

> **Status:** Draft
> **Priority:** Medium
> **Dependencies:** 06-infrastructure.md (infra debe existir), 08-hardening.md Phase 2 (service layer estable)
> **Audit findings resolved:** H15 (SMTP retry), L09 (NHTSA retry), L10 (Stripe retry), L08 (NHTSA shared client), M17 (warnings.warn -> logger.warning)

## 1. Objective

Implementar observabilidad de tres pilares (logs, metricas, tracing) para detectar, diagnosticar y resolver incidentes en produccion.

## 2. Scope

- OpenTelemetry SDK para tracing distribuido
- Logs estructurados (ya existe JSON logger)
- Metricas de negocio y sistema
- Alertas proactivas
- Dashboards operativos

## 3. Stack

| Herramienta | Uso |
|-------------|-----|
| OpenTelemetry Python SDK | Tracing automatico FastAPI + SQLAlchemy + Redis |
| Sentry | Error tracking + performance monitoring |
| Grafana + Prometheus | Metricas personalizadas y dashboards |
| AWS CloudWatch | Logs centralizados (si AWS) |
| PagerDuty / OpsGenie | Alerting on-call |

## 4. Implementation

| Step | Description | Effort |
|------|-------------|--------|
| 1 | OpenTelemetry: instrumentar FastAPI, SQLAlchemy, Redis, httpx | 2 dias |
| 2 | Sentry: setup + release tracking + performance | 1 dia |
| 3 | Metricas: Prometheus + /metrics endpoint en FastAPI | 1 dia |
| 4 | Dashboards: Grafana (API latency, error rate, DB pool, Redis) | 1 dia |
| 5 | Alertas: PagerDuty rules (5xx spike, p99 latency, DB deadlocks) | 1 dia |
| 6 | Logs: CloudWatch Logs Insights queries + dashboard | 0.5 dia |
| 7 | Runbook: incident response document | 1 dia |

## 5. Critical Metrics

| Metric | Target | Alert if |
|--------|--------|----------|
| p99 API latency | <500ms | >2s for 5 min |
| Error rate (5xx) | <0.1% | >1% for 5 min |
| DB connection pool usage | <80% | >90% for 5 min |
| Redis command latency | <10ms | >50ms for 5 min |
| Active users (business) | varies | drop >50% from baseline |
| Appointment completion rate | >90% | <80% |
