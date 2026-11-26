import time
from typing import Any, Dict, Optional, Protocol

from persistence import clear_working_state, load_working_state, save_working_state


class StorageAdapter(Protocol):
    def upsert(self, key: str, value: Any) -> bool: ...
    def get(self, key: str) -> Optional[Any]: ...
    def delete(self, key: str) -> bool: ...


class SQLiteResumeAdapter:
    """Durable SQLite-backed adapter for resuming draft and workspace sessions."""

    def __init__(self, scope_id: str = "resume_session"):
        self.scope_id = scope_id

    def upsert(self, key: str, value: Any) -> bool:
        payload = value if isinstance(value, dict) else {"value": value}
        return save_working_state(f"resume::{key}", payload, scope_id=self.scope_id)

    def get(self, key: str) -> Optional[Any]:
        return load_working_state(f"resume::{key}")

    def delete(self, key: str) -> bool:
        return clear_working_state(f"resume::{key}")


class SessionResumeManager:
    def __init__(self, storage_adapter: Optional[StorageAdapter] = None):
        self.db: StorageAdapter = storage_adapter or SQLiteResumeAdapter()

    def save_draft_state(
        self,
        tracking_code: str,
        vendor_email: str,
        form_data: Dict[str, Any],
    ) -> bool:
        payload = {
            "tracking_code": tracking_code,
            "vendor_email": (vendor_email or "").strip().lower(),
            "form_data": form_data,
            "last_updated": time.time(),
            "status": "DRAFT_IN_PROGRESS",
        }
        return self.db.upsert(key=tracking_code, value=payload)

    def resume_session(
        self,
        tracking_code: str,
        vendor_email: str,
    ) -> Optional[Dict[str, Any]]:
        record = self.db.get(key=tracking_code)
        if not isinstance(record, dict):
            return None
        stored_email = str(record.get("vendor_email") or "").strip().lower()
        if stored_email != str(vendor_email or "").strip().lower():
            return None
        return record.get("form_data")
