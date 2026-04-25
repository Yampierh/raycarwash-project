"""
api/router.py — Aggregates all domain routers into one FastAPI APIRouter.

main.py calls: application.include_router(api_router)
This file is the single source of truth for which routers are active.
"""
from fastapi import APIRouter

from app.routers.addon_router       import router as addon_router
from app.routers.appointment_router import router as appointment_router
from app.routers.auth_router        import router as auth_router
from app.routers.detailer_router    import router as detailer_router
from app.routers.fare_router        import router as fare_router
from app.routers.matching_router    import router as matching_router
from app.routers.payment_router     import router as payment_router
from app.routers.review_router      import router as review_router
from app.routers.rides_router       import router as rides_router
from app.routers.service_router     import router as service_router
from app.routers.vehicle_router     import router as vehicle_router
from app.routers.verification_router import router as verification_router
from app.routers.webhook_router     import router as webhook_router
from app.routers.wellknown_router   import router as wellknown_router
from app.ws.router                  import router as ws_router

api_router = APIRouter()

# WebAuthn domain verification (no prefix — must be at /.well-known/*)
api_router.include_router(wellknown_router)

# Stripe webhooks (no prefix — raw path /webhooks/*)
api_router.include_router(webhook_router)

# Auth domain — /auth/*
api_router.include_router(auth_router)

# Service catalogue — /api/v1/services/*
api_router.include_router(service_router)

# Addons — /api/v1/addons/*
api_router.include_router(addon_router)

# Matching — /api/v1/matching
api_router.include_router(matching_router)

# Vehicles — /api/v1/vehicles/*
api_router.include_router(vehicle_router)

# Appointments — /api/v1/appointments/*
api_router.include_router(appointment_router)

# Detailers — /api/v1/detailers/*
api_router.include_router(detailer_router)

# Stripe Identity — /api/v1/detailers/verification/*
api_router.include_router(verification_router)

# Fare estimation — /api/v1/fares/*
api_router.include_router(fare_router)

# Rides (v2) — /api/v1/rides/*
api_router.include_router(rides_router)

# WebSocket — /ws/appointments/{id}
api_router.include_router(ws_router)

# Payments — /api/v1/payments/*
api_router.include_router(payment_router)

# Reviews — /api/v1/reviews/*
api_router.include_router(review_router)
