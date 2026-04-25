# COMPATIBILITY SHIM — actual code lives in domains/appointments/service.py
from domains.appointments.service import (  # noqa: F401
    AppointmentService,
    AppointmentCalculation,
    TimeSlot,
    SLOT_GRANULARITY_MINUTES,
    MIN_ADVANCE_BOOKING_MINUTES,
)
