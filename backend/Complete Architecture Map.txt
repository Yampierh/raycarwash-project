POST /auth/token          → login, returns access + refresh JWT pair
POST /auth/refresh        → rotate refresh → new access + refresh pair
GET  /auth/me             → current user profile

POST /api/v1/users        → register
POST /api/v1/vehicles     → register vehicle (JWT owner_id)
GET  /api/v1/vehicles     → list own vehicles

POST /api/v1/appointments          → book (advisory lock → no double-booking)
GET  /api/v1/appointments/mine     → paginated list (client or detailer)
GET  /api/v1/appointments/{id}     → single (participant or admin only)
PATCH /api/v1/appointments/{id}/status → state machine transition

GET  /api/v1/detailers/{id}/availability → 30-min slot grid
GET  /api/v1/detailers/{id}/profile      → public profile + ratings
POST /api/v1/detailers/location          → GPS ping (detailer only)

POST /api/v1/payments/create-intent → Stripe PaymentIntent (idempotent)

POST /api/v1/reviews               → post-COMPLETED review
GET  /api/v1/reviews/detailer/{id} → paginated detailer reviews

GET  /health → liveness probe