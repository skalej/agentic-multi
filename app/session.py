import uuid
from typing import Dict, Any

class SessionStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def create(self, payload: Dict[str, Any]) -> str:
        sid = str(uuid.uuid4())
        self._store[sid] = payload
        return sid

    def get(self, sid: str) -> Dict[str, Any] | None:
        return self._store.get(sid)

    def update(self, sid: str, patch: Dict[str, Any]):
        if sid in self._store:
            self._store[sid].update(patch)

    def delete(self, sid: str):
        if sid in self._store:
            del self._store[sid]

SESSIONS = SessionStore()
