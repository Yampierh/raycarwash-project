# 06 — Infrastructure & Deployment

> **Status:** Draft
> **Priority:** High
> **Dependencies:** 05-ci-cd.md (CI/CD debe existir primero), 08-hardening.md Phase 0 (infra segura)
> **Audit findings resolved:** L17 (no backend compose), L18 (Redis persistence), M5 (S3/Twilio adapters), M11 (server-side auth web), M12 (empty next.config), L13 (STORAGE_ADAPTER RuntimeError)

## 1. Objective

Definir la infraestructura como codigo (IaC) para entornos staging y produccion, con despliegue reproducible, escalable y seguro.

## 2. Scope

- IaC con Terraform o Pulumi
- Orquestacion: ECS Fargate o EKS
- Base de datos: RDS PostgreSQL con Multi-AZ
- Redis: ElastiCache o Memorystore
- Storage: S3 + CloudFront
- Secrets: AWS Secrets Manager
- Backup/DR: Estrategia de backups y recovery

## 3. Architecture Decision

**Propuesta**: AWS ECS Fargate + Terraform

Razones:
- Sin sobrecarga de gestion de nodos (vs EKS)
- Costo predecible para la escala actual
- Terraform -> estado remoto en S3 + DynamoDB locking

## 4. Componentes

| Componente | Prod | Staging | Dev |
|------------|------|---------|-----|
| Compute | ECS Fargate (2x1 vCPU) | ECS Fargate (1x0.5 vCPU) | docker-compose |
| DB | RDS PostgreSQL 16 (db.t3.medium, Multi-AZ) | RDS PostgreSQL 16 (db.t3.small) | PostgreSQL local |
| Cache | ElastiCache Redis 7 (1 node) | ElastiCache Redis 7 (1 node) | Redis Docker |
| Storage | S3 + CloudFront + presigned URLs | S3 (same bucket, prefix/staging/) | LocalStorageAdapter |
| CDN | CloudFront | — | — |
| Secrets | AWS Secrets Manager | AWS Secrets Manager | .env file |
| Email | SendGrid API | SendGrid API (sandbox) | MailHog |
| SMS | Twilio | Twilio (test) | Log |

## 5. Implementation

| Step | Description | Effort |
|------|-------------|--------|
| 1 | Terraform: VPC + subnets + security groups | 1 dia |
| 2 | Terraform: RDS PostgreSQL | 1 dia |
| 3 | Terraform: ElastiCache Redis | 0.5 dia |
| 4 | Terraform: ECS cluster + Fargate service | 2 dias |
| 5 | Terraform: S3 + CloudFront | 0.5 dia |
| 6 | Secrets Manager: schema + automatic rotation | 1 dia |
| 7 | Backup plan: RDS snapshots + S3 lifecycle | 0.5 dia |
| 8 | Document runbook: deploy, rollback, incident response | 1 dia |

## 6. DR Strategy

| Escenario | RTO | RPO | Estrategia |
|-----------|-----|-----|------------|
| DB failure | 15 min | 5 min | RDS Multi-AZ failover |
| AZ outage | 30 min | 5 min | ECS Fargate multi-AZ |
| App crash | 5 min | N/A | ECS auto-restart + health checks |
| Data corruption | 4 hr | 24 hr | Point-in-time recovery RDS |
| Full region | 4 hr | 1 hr | Cross-region backup + secondary infra |
