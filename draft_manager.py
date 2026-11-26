import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DRAFT_FILE = "nexusvault_form_drafts.json"


def _make_key(form_type: str, scope_id: Optional[str] = None) -> str:
    clean_type = str(form_type).strip()
    if scope_id and str(scope_id).strip():
        return f"{str(scope_id).strip()}::{clean_type}"
    return clean_type


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    target = os.path.abspath(path)
    parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".draft_", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def get_all_drafts() -> Dict[str, Any]:
    """Fetches all saved form drafts safely."""
    if not os.path.exists(DRAFT_FILE):
        return {}
    try:
        with open(DRAFT_FILE, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_draft(
    form_type: str,
    data_dict: Dict[str, Any],
    scope_id: Optional[str] = None,
) -> bool:
    """Atomically saves form input progress to local persistent JSON file."""
    try:
        drafts = get_all_drafts()
        record = dict(data_dict or {})
        now_dt = datetime.now(timezone.utc).astimezone()
        record["last_saved"] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        record["last_saved_iso"] = now_dt.isoformat()
        if scope_id:
            record["scope_id"] = str(scope_id).strip()
        drafts[_make_key(form_type, scope_id)] = record
        _atomic_write_json(DRAFT_FILE, drafts)
        return True
    except Exception:
        return False


def get_draft(
    form_type: str,
    scope_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves draft for specific form category and optional scope."""
    drafts = get_all_drafts()
    scoped_key = _make_key(form_type, scope_id)
    if scoped_key in drafts:
        return drafts[scoped_key]
    if scope_id and form_type in drafts:
        return drafts[form_type]
    return None


def clear_draft(
    form_type: str,
    scope_id: Optional[str] = None,
) -> bool:
    """Clears saved draft after successful submission."""
    try:
        drafts = get_all_drafts()
        changed = False
        for key in (_make_key(form_type, scope_id), str(form_type).strip()):
            if key in drafts:
                del drafts[key]
                changed = True
        if changed:
            _atomic_write_json(DRAFT_FILE, drafts)
        return True
    except Exception:
        return False
