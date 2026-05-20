"""Static regression checks for DB hardening changes.

These tests intentionally avoid importing app modules so they can document the
expected source-level invariants even when local DB dependencies are not
installed.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _find_role_permissions_node(module: ast.Module):
    """Find ROLE_PERMISSIONS assignment regardless of type-hint syntax."""
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "ROLE_PERMISSIONS":
            return node
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROLE_PERMISSIONS":
                    return node
    msg = "ROLE_PERMISSIONS not found"
    raise AssertionError(msg)


def test_client_role_does_not_receive_permission_write_access() -> None:
    source = _read("app/db/seed_rbac.py")
    module = ast.parse(source)
    rp_node = _find_role_permissions_node(module)

    dict_node = rp_node.value
    client_node = next(
        value for key, value in zip(dict_node.keys, dict_node.values)
        if isinstance(key, ast.Constant) and key.value == "client"
    )
    client_permissions = ast.literal_eval(client_node)

    assert "write:permissions" not in client_permissions


def test_marketplace_operational_tables_are_registered() -> None:
    registry = _read("infrastructure/db/registry.py")
    assert "AppointmentStatusHistory" in registry
    assert "AppointmentCancellation" in registry
    assert "ProviderAvailabilityException" in registry
    assert "ProviderPayout" in registry
    assert "Refund" in registry


def test_appointment_assignment_has_dedupe_constraint() -> None:
    appointments = _read("domains/appointments/models.py")
    assert "uq_assignment_appointment_detailer" in appointments


def test_payment_ledger_mutation_guard_exists_in_migration() -> None:
    migration = _read("alembic/versions/m_025_db_hardening_marketplace_records.py")
    assert "prevent_payment_ledger_mutation" in migration
    assert "BEFORE UPDATE OR DELETE ON payment_ledger" in migration
    assert "BEFORE TRUNCATE ON payment_ledger" in migration


def test_payment_ledger_amount_cents_constraint() -> None:
    payments = _read("domains/payments/models.py")
    assert "ck_payment_ledger_amount_nonnegative" in payments


def test_appointment_model_price_aliases() -> None:
    models = _read("domains/appointments/models.py")
    assert "estimated_price_cents" in models
    assert "actual_price_cents" in models


if __name__ == "__main__":
    for _test in (
        test_client_role_does_not_receive_permission_write_access,
        test_marketplace_operational_tables_are_registered,
        test_appointment_assignment_has_dedupe_constraint,
        test_payment_ledger_mutation_guard_exists_in_migration,
        test_payment_ledger_amount_cents_constraint,
        test_appointment_model_price_aliases,
    ):
        _test()
