# app/models/ledger.py
# COMPATIBILITY SHIM — re-exports ledger models from domains/payments.
from domains.payments.models import PaymentLedger, LedgerSeal, LedgerRevision  # noqa: F401
