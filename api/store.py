from typing import Optional
from pathlib import Path
import threading

# Reuse the parser we already wrote and tested
try:
    from dsa.parse_xml import parse_sms_xml
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dsa.parse_xml import parse_sms_xml


class TransactionStore:
    """Holds all transactions and exposes CRUD operations."""

    def __init__(self):
        self._by_id: dict[int, dict] = {}
        self._next_id: int = 1
        self._lock = threading.Lock()

    def load_from_xml(self, xml_path: str | Path) -> int:
        """load data from xml"""
        transactions = parse_sms_xml(xml_path)
        with self._lock:
            self._by_id = {t["id"]: t for t in transactions}
            self._next_id = (max(self._by_id) + 1) if self._by_id else 1
        return len(self._by_id)

    def list_all(self) -> list[dict]:
        """GET /transactions"""
        # Return a list snapshot
        return list(self._by_id.values())

    def get(self, transaction_id: int) -> Optional[dict]:
        """GET /transactions/{id}  O(1) dict lookup"""
        return self._by_id.get(transaction_id)

    def create(self, payload: dict) -> dict:
        """POST /transactions"""
        with self._lock:
            new_id = self._next_id
            self._next_id += 1
        
            record = {
                "id": new_id,
                "address": payload.get("address", "M-Money"),
                "date": payload.get("date", 0),
                "readable_date": payload.get("readable_date", ""),
                "body": payload.get("body", ""),
                "category": payload.get("category", "UNCATEGORIZED"),
                "amount": payload.get("amount", 0),
            }
            self._by_id[new_id] = record
            return record

    def update(self, transaction_id: int, payload: dict) -> Optional[dict]:
        """PUT /transactions/{id}"""
        with self._lock:
            existing = self._by_id.get(transaction_id)
            if existing is None:
                return None
            # Don't let the client overwrite the id
            updated = {**existing, **{k: v for k, v in payload.items() if k != "id"}}
            self._by_id[transaction_id] = updated
            return updated

    def delete(self, transaction_id: int) -> bool:
        """DELETE /transactions/{id}"""
        with self._lock:
            return self._by_id.pop(transaction_id, None) is not None

    def count(self) -> int:
        """Handy for tests and the /health endpoint."""
        return len(self._by_id)
