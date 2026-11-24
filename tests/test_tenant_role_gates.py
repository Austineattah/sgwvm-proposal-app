"""Tests for tenant_role_gates wired to database.py and app.py."""

from __future__ import annotations

import ast
import sqlite3
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

import database as db_mod


def _load_app_route_resolver() -> object:
    """Extract _resolve_role_gate_route from app.py without executing top-level UI."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(app_path))
    target_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_resolve_role_gate_route"
    )
    namespace: dict[str, object] = {"db": db_mod}
    exec(compile(ast.Module(body=[target_fn], type_ignores=[]), str(app_path), "exec"), namespace)
    return namespace["_resolve_role_gate_route"]


_resolve_role_gate_route = _load_app_route_resolver()


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point database.DB_FILE at a temporary SQLite database and initialize schema."""
    db_path = tmp_path / "tenant_role_gates_wired.db"
    monkeypatch.setattr(db_mod, "DB_FILE", db_path)
    db_mod.init_db()
    return db_path


def _insert_tenant(
    db_path: Path,
    tenant_slug: str,
    corp_name: str,
    status: str = "ACTIVE",
    is_deleted: int = 0,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO tenants (
                tenant_slug, full_corporation_name, status, is_deleted
            )
            VALUES (?, ?, ?, ?)
            """,
            (tenant_slug, corp_name, status, is_deleted),
        )
        conn.commit()
    finally:
        conn.close()


def test_provision_default_role_gates_and_lookup(isolated_db: Path) -> None:
    _insert_tenant(isolated_db, "gombe-south", "Gombe South Holdings Ltd", status="ACTIVE")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with db_mod.get_connection() as connection:
        slugs = db_mod._provision_default_role_gates(connection, "gombe-south", now)

    assert slugs == {
        "desk_slug": "gombe-south-desk",
        "admin_slug": "gombe-south-admin",
        "vendor_slug": "gombe-south",
    }

    gates = db_mod.get_tenant_role_gates("gombe-south")
    assert set(gates.keys()) == {"desk_operator", "admin"}
    assert gates["desk_operator"]["role_slug"] == "gombe-south-desk"
    assert gates["desk_operator"]["developer_access_revoked"] is False
    assert gates["admin"]["role_slug"] == "gombe-south-admin"
    assert gates["admin"]["developer_access_revoked"] is False

    resolved_desk = db_mod.resolve_role_gate_by_slug("gombe-south-desk")
    assert resolved_desk is not None
    assert resolved_desk["tenant_slug"] == "gombe-south"
    assert resolved_desk["role_key"] == "desk_operator"
    assert resolved_desk["status"] == "ACTIVE"


def test_verify_tenant_role_gate_enforces_credentials_and_active_tenant(isolated_db: Path) -> None:
    _insert_tenant(isolated_db, "bayelsa-west", "Bayelsa West Ventures", status="ACTIVE")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "bayelsa-west", now)

    valid = db_mod.verify_tenant_role_gate(
        "bayelsa-west-desk",
        db_mod._DEFAULT_DESK_GATE_PASSWORD,
    )
    assert valid is not None
    assert valid["tenant_slug"] == "bayelsa-west"
    assert valid["role_key"] == "desk_operator"

    assert (
        db_mod.verify_tenant_role_gate("bayelsa-west-desk", "WrongPassword#2026")
        is None
    )
    assert db_mod.verify_tenant_role_gate("bayelsa-west-desk", "") is None

    conn = sqlite3.connect(isolated_db)
    try:
        conn.execute(
            "UPDATE tenants SET status = 'SUSPENDED' WHERE tenant_slug = ?",
            ("bayelsa-west",),
        )
        conn.commit()
    finally:
        conn.close()

    assert (
        db_mod.verify_tenant_role_gate(
            "bayelsa-west-desk",
            db_mod._DEFAULT_DESK_GATE_PASSWORD,
        )
        is None
    )


def test_route_resolver_rejects_cross_role_slugs(isolated_db: Path) -> None:
    _insert_tenant(isolated_db, "boki-ikom", "Boki Ikom Corp", status="ACTIVE")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "boki-ikom", now)

    tenant_slug, effective_slug, err = _resolve_role_gate_route("boki-ikom-admin", "front_desk")
    assert tenant_slug is None
    assert effective_slug == "boki-ikom-admin"
    assert err is not None and "not authorized" in err

    desk_tenant, desk_effective, desk_err = _resolve_role_gate_route(
        "boki-ikom-desk",
        "front_desk",
    )
    assert desk_err is None
    assert desk_tenant == "boki-ikom"
    assert desk_effective == "boki-ikom-desk"

    assert (
        db_mod.verify_tenant_role_gate(
            "boki-ikom-admin",
            db_mod._DEFAULT_DESK_GATE_PASSWORD,
        )
        is None
    )


def test_rotate_admin_role_gate_password_revokes_initial_and_records_activity(
    isolated_db: Path,
) -> None:
    _insert_tenant(isolated_db, "sgwvm-corp", "SGWVM Corp", status="ACTIVE")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "sgwvm-corp", now)

    initial_secret = db_mod._DEFAULT_ADMIN_GATE_PASSWORD
    rotated_secret = "NewAdminGateSecret#2026"

    ok, msg = db_mod.rotate_admin_role_gate_password(
        "sgwvm-corp",
        initial_secret,
        rotated_secret,
        rotated_by="lead_architect",
    )
    assert ok is True, msg

    assert db_mod.verify_tenant_role_gate("sgwvm-corp-admin", initial_secret) is None
    verified = db_mod.verify_tenant_role_gate("sgwvm-corp-admin", rotated_secret)
    assert verified is not None
    assert verified["developer_access_revoked"] is True

    gates = db_mod.get_tenant_role_gates("sgwvm-corp")
    assert gates["admin"]["developer_access_revoked"] is True
    assert gates["admin"]["rotated_by"] == "lead_architect"
    assert gates["admin"]["rotated_at"] is not None

    activities = db_mod.get_tenant_activities("sgwvm-corp")
    rotation_events = [
        entry
        for entry in activities
        if entry.get("action_type") == "admin_gate_password_rotated"
    ]
    assert rotation_events
    assert rotation_events[0]["actor"] == "lead_architect"
    assert "rotated" in rotation_events[0]["details"].lower()


def test_deleted_tenant_blocks_gate_and_rotation(isolated_db: Path) -> None:
    _insert_tenant(isolated_db, "deleted-corp", "Deleted Corp Ltd", status="ACTIVE", is_deleted=1)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "deleted-corp", now)

    assert db_mod.resolve_role_gate_by_slug("deleted-corp-admin") is None
    assert (
        db_mod.verify_tenant_role_gate(
            "deleted-corp-admin",
            db_mod._DEFAULT_ADMIN_GATE_PASSWORD,
        )
        is None
    )

    ok, msg = db_mod.rotate_admin_role_gate_password(
        "deleted-corp",
        db_mod._DEFAULT_ADMIN_GATE_PASSWORD,
        "ValidRotatedPass#2026",
        rotated_by="lead_architect",
    )
    assert ok is False
    assert "unavailable" in msg.lower()


def test_admin_rotation_rejects_invalid_inputs(isolated_db: Path) -> None:
    _insert_tenant(isolated_db, "guardrail-corp", "Guardrail Corp", status="ACTIVE")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "guardrail-corp", now)

    current_secret = db_mod._DEFAULT_ADMIN_GATE_PASSWORD

    # Wrong current password
    ok_wrong, _ = db_mod.rotate_admin_role_gate_password(
        "guardrail-corp",
        "WrongCurrentPass#2026",
        "NewValidPass#2026",
    )
    assert ok_wrong is False

    # Short new password (< 10 chars)
    ok_short, _ = db_mod.rotate_admin_role_gate_password(
        "guardrail-corp",
        current_secret,
        "Short#9",
    )
    assert ok_short is False

    # Duplicate new password (same as current)
    ok_same, _ = db_mod.rotate_admin_role_gate_password(
        "guardrail-corp",
        current_secret,
        current_secret,
    )
    assert ok_same is False

    # Original credential remains valid after failed rotations
    assert (
        db_mod.verify_tenant_role_gate("guardrail-corp-admin", current_secret) is not None
    )

def test_route_resolver_handles_unprovisioned_fallback_and_missing_suffix(
    isolated_db: Path,
) -> None:
    _ = isolated_db
    base_slug, effective_slug, err = _resolve_role_gate_route(
        "gombe-south-desk",
        "front_desk",
    )
    assert err is None
    assert base_slug == "gombe-south"
    assert effective_slug == "gombe-south-desk"

    bad_base, bad_effective, bad_err = _resolve_role_gate_route(
        "gombe-south",
        "admin",
    )
    assert bad_base is None
    assert bad_effective == "gombe-south-admin"
    assert bad_err is not None and "Invalid role slug" in bad_err


def test_suspended_tenant_blocks_admin_gate_rotation(isolated_db: Path) -> None:
    _insert_tenant(
        isolated_db,
        "suspended-corp",
        "Suspended Corp Ltd",
        status="SUSPENDED",
        is_deleted=0,
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_connection() as connection:
        db_mod._provision_default_role_gates(connection, "suspended-corp", now)

    ok, msg = db_mod.rotate_admin_role_gate_password(
        "suspended-corp",
        db_mod._DEFAULT_ADMIN_GATE_PASSWORD,
        "ValidRotatedPass#2026",
        rotated_by="lead_architect",
    )
    assert ok is False
    assert "unavailable" in msg.lower()

def _load_terminal_role_login(
    session_state: dict[str, object],
    errors: list[str],
    successes: list[str],
) -> object:
    """Extract _render_terminal_role_login with stubbed Streamlit UI/session primitives."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    raw = app_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(raw, filename=str(app_path))
    target_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_render_terminal_role_login"
    )

    st_stub = types.SimpleNamespace(
        session_state=session_state,
        error=lambda msg: errors.append(str(msg)),
        success=lambda msg: successes.append(str(msg)),
    )

    namespace: dict[str, object] = {
        "sqlite3": sqlite3,
        "logging": __import__("logging"),
        "Mapping": __import__("collections.abc", fromlist=["Mapping"]).Mapping,
        "st": st_stub,
        "db": db_mod,
        "_tenant_key": lambda slug, role, suffix: f"{slug}:{role}:{suffix}",
        "_configured_staff_users": lambda: {},
        "_TERMINAL_LOCKOUT_MESSAGE": "Terminal locked out.",
    }
    exec(compile(ast.Module(body=[target_fn], type_ignores=[]), str(app_path), "exec"), namespace)
    return namespace["_render_terminal_role_login"]


def test_mid_session_guard_revokes_session_when_tenant_inactive_or_deleted(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_slug = "mid-session-corp"
    role = "admin"
    _insert_tenant(isolated_db, tenant_slug, "Mid Session Corp", status="ACTIVE", is_deleted=0)

    monkeypatch.setattr(db_mod, "get_tenant_role_lockout", lambda slug, r: {"is_locked_out": False})

    session_state: dict[str, object] = {}
    errors: list[str] = []
    successes: list[str] = []
    render_login = _load_terminal_role_login(session_state, errors, successes)

    identity_key = f"{tenant_slug}:{role}:identity"
    gate_verified_key = f"{tenant_slug}:{role}:gate_verified"
    active_gate_key = f"{tenant_slug}:{role}:active_gate_slug"

    # Active tenant preserves session identity
    session_state[identity_key] = {
        "tenant_slug": tenant_slug,
        "role": role,
        "user_role": role,
        "username": "admin_user",
    }
    session_state[gate_verified_key] = True
    session_state[active_gate_key] = f"{tenant_slug}-{role}"

    active_result = render_login(tenant_slug, role)
    assert active_result is not None
    assert active_result["username"] == "admin_user"
    assert identity_key in session_state

    # Suspended tenant revokes active session and clears gate keys
    errors.clear()
    with sqlite3.connect(isolated_db) as conn:
        conn.execute(
            "UPDATE tenants SET status = 'SUSPENDED' WHERE tenant_slug = ?",
            (tenant_slug,),
        )
        conn.commit()

    suspended_result = render_login(tenant_slug, role)
    assert suspended_result is None
    assert identity_key not in session_state
    assert gate_verified_key not in session_state
    assert active_gate_key not in session_state
    assert any("SUSPENDED" in msg for msg in errors)

    # Deleted tenant revokes active session even if status is ACTIVE
    errors.clear()
    session_state[identity_key] = {
        "tenant_slug": tenant_slug,
        "role": role,
        "user_role": role,
        "username": "admin_user",
    }
    session_state[gate_verified_key] = True
    session_state[active_gate_key] = f"{tenant_slug}-{role}"
    with sqlite3.connect(isolated_db) as conn:
        conn.execute(
            "UPDATE tenants SET status = 'ACTIVE', is_deleted = 1 WHERE tenant_slug = ?",
            (tenant_slug,),
        )
        conn.commit()

    deleted_result = render_login(tenant_slug, role)
    assert deleted_result is None
    assert identity_key not in session_state
    assert gate_verified_key not in session_state
    assert active_gate_key not in session_state
    assert any(tenant_slug in msg for msg in errors)
