import time
from typing import Dict, Any, Optional, Protocol

class StorageAdapter(Protocol):
    def upsert(self, key: str, value: Any) -> bool: ...
    def get(self, key: str) -> Optional[Any]: ...

class SessionResumeManager:
    def __init__(self, storage_adapter: StorageAdapter):
        self.db = storage_adapter
    def save_draft_state(self, tracking_code: str, vendor_email: str, form_data: Dict[str, Any]) -> bool:
        payload = {'tracking_code': tracking_code, 'vendor_email': vendor_email, 'form_data': form_data, 'last_updated': time.time(), 'status': 'DRAFT_IN_PROGRESS'}
        return self.db.upsert(key=tracking_code, value=payload)
    def resume_session(self, tracking_code: str, vendor_email: str) -> Optional[Dict[str, Any]]:
        record = self.db.get(key=tracking_code)
        if not record: return None
        if record.get('vendor_email').strip().lower() != vendor_email.strip().lower(): return None
        return record.get('form_data')
