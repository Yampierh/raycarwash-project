"""
domains/public/ — Marketing public endpoints (Plan 19 — Track 1).

9 read-mostly endpoints serving testimonials, FAQ, coverage zones,
stats, contact form, and waitlist for the marketing portal at
`web/portal/`. All endpoints are anonymous (no auth) — aggressive
rate limiting + CDN caching mitigate scraping and abuse per
Plan 22 audit findings H2, H5, H6.

Layout:
  models.py      SQLAlchemy entities (6 tables + enums)
  schemas.py     Pydantic request/response shapes
  repository.py  Async DB access (soft-delete filtered)
  service.py     Business logic (no SQL)
  router.py      FastAPI endpoints (rate-limited)

Mount via `api/router.py` only after Paso 4 (migrations + seed) lands.
"""
