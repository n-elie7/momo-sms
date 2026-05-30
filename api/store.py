# Loads MoMo SMS records into memory for fast O(1) lookups and CRUD operations.
# Supports multiple transaction categories and thread safe updates.
# Each record stores transaction details, parties involved, balances, and timestamps.
from __future__ import annotations

import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET



# Regex patterns  compiled once at import time


# Amounts like  2000 / 1,000 / 38,400
_AMT  = r"([\d,]+(?:\.\d+)?)\s*RWF"

# ── per-category patterns ────────────────────────────────────────────────────
_RE = {
    # TxId: 123. Your payment of 1,000 RWF to Jane Smith 12345 has been…
    "payment_sent_txid": re.compile(
        r"TxId:\s*(?P<fin_id>\d+)\.\s*Your payment of\s*" + _AMT +
        r"\s*to\s*(?P<receiver>[A-Za-z][A-Za-z\s]+?)\s+\d+\s+has been"
        r".*?new balance:\s*" + _AMT, re.S),

    # *165*S* 1000 RWF transferred to Jane Smith (250788…) from 36521838 …Fee was: 20 RWF. New balance: 27280 RWF.
    "transfer_sent": re.compile(
        r"\*165\*S\*\s*" + _AMT +
        r"\s*transferred to\s*(?P<receiver>[A-Za-z][A-Za-z\s]+?)\s*\((?P<receiver_phone>\d+)\)"
        r".*?Fee was:\s*" + _AMT +
        r".*?New balance:\s*" + _AMT, re.S),

    # *113*R* A bank deposit of 40000 RWF has been added…NEW BALANCE :40400 RWF.
    "bank_deposit": re.compile(
        r"\*113\*R\*\s*A bank deposit of\s*" + _AMT +
        r".*?NEW BALANCE\s*:\s*" + _AMT, re.S),

    # You have received 2000 RWF from Jane Smith (*…013) …Financial Transaction Id: 76662021700.
    "received": re.compile(
        r"You have received\s*" + _AMT +
        r"\s*from\s*(?P<sender>[A-Za-z][A-Za-z\s]+?)\s*\("
        r".*?Financial Transaction Id:\s*(?P<fin_id>\d+)", re.S),

    # *162*TxId:13913173274*S*Your payment of 2000 RWF to Airtime …
    "airtime": re.compile(
        r"\*162\*TxId:(?P<fin_id>\d+)\*S\*Your payment of\s*" + _AMT +
        r"\s*to Airtime"
        r".*?new balance:\s*" + _AMT, re.S),

    # *164*S* … transaction of 25000 RWF by DIRECT PAYMENT LTD … new balance:4060 RWF.
    "direct_payment_debit": re.compile(
        r"\*164\*S\*.*?transaction of\s*" + _AMT +
        r"\s*by\s*(?P<sender>[A-Z][A-Z\s]+?)\s+on"
        r".*?new balance:\s*" + _AMT, re.S),

    # You have transferred 50000 RWF to Linda Green (250795963036) from your mobile money account…
    "bank_transfer_out": re.compile(
        r"You have transferred\s*" + _AMT +
        r"\s*to\s*(?P<receiver>[A-Za-z][A-Za-z\s]+?)\s*\((?P<receiver_phone>\d+)\)", re.S),

    # A reversal has been initiated / *143*S* reversed
    "reversal": re.compile(
        r"(?:reversal has been initiated|has been reversed)"
        r".*?" + _AMT, re.S),

    # *143*R* … transaction … failed
    "failed_txn": re.compile(
        r"\*143\*R\*.*?amount\s*" + _AMT, re.S),

    # Yello!Umaze kugura … (bundle purchase – amount in local description)
    "bundle": re.compile(
        r"Yello!Umaze kugura.*?igura\s*" + _AMT, re.S),

    # Withdrawal – generic
    "withdrawal": re.compile(
        r"withdraw.*?" + _AMT, re.S | re.I),

    # Your payment of X RWF to <Name> (<phone>) has been completed … (bare, no TxId prefix)
    "payment_sent_bare": re.compile(
        r"Your payment of\s*" + _AMT +
        r"\s*to\s*(?P<receiver>[A-Za-z][A-Za-z\s]+?)\s*\((?P<receiver_phone>\d+)\)"
        r".*?new balance:\s*" + _AMT, re.S),

    # Fee: generic fallback
    "_fee": re.compile(r"[Ff]ee was[:\s]*" + _AMT),
    "_balance_generic": re.compile(r"[Nn]ew balance[:\s]*" + _AMT),
    "_amount_generic": re.compile(_AMT),
}


# Parsing helpers


def _f(s: str | None) -> float | None:
    """Parse a comma-formatted number string to float, or return None."""
    if s is None:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _classify_and_extract(body: str) -> dict[str, Any]:
    """
    Classify an SMS body into a tx_category and extract structured fields.
    Returns a dict with keys: tx_category, amount, fee, balance, sender,
    receiver, financial_tx_id.
    """
    out: dict[str, Any] = {
        "tx_category":    "other",
        "amount":         None,
        "fee":            None,
        "balance":        None,
        "sender":         None,
        "receiver":       None,
        "financial_tx_id": None,
    }

    # --- OTP (no financial data) ---
    if "<#> Dear Customer, your MTN MoMo application one-time password" in body:
        out["tx_category"] = "otp"
        return out

    # --- payment_sent_txid ---
    m = _RE["payment_sent_txid"].search(body)
    if m:
        out.update(tx_category="payment_sent", financial_tx_id=m.group("fin_id"),
                   amount=_f(m.group(2)), receiver=m.group("receiver").strip(),
                   balance=_f(m.group(3)))
        if fee := _RE["_fee"].search(body):
            out["fee"] = _f(fee.group(1))
        return out

    # --- transfer_sent (*165*S*) ---
    m = _RE["transfer_sent"].search(body)
    if m:
        out.update(tx_category="transfer_sent", amount=_f(m.group(1)),
                   receiver=m.group("receiver").strip(),
                   fee=_f(m.group(2)), balance=_f(m.group(3)))
        return out

    # --- bank_deposit (*113*R*) ---
    m = _RE["bank_deposit"].search(body)
    if m:
        out.update(tx_category="bank_deposit", amount=_f(m.group(1)),
                   balance=_f(m.group(2)))
        return out

    # --- received ---
    m = _RE["received"].search(body)
    if m:
        out.update(tx_category="received", amount=_f(m.group(1)),
                   sender=m.group("sender").strip(),
                   financial_tx_id=m.group("fin_id"))
        if bal := _RE["_balance_generic"].search(body):
            out["balance"] = _f(bal.group(1))
        return out

    # --- airtime (*162*) ---
    m = _RE["airtime"].search(body)
    if m:
        out.update(tx_category="airtime", financial_tx_id=m.group("fin_id"),
                   amount=_f(m.group(1)), receiver="Airtime",
                   balance=_f(m.group(2)))
        if fee := _RE["_fee"].search(body):
            out["fee"] = _f(fee.group(1))
        return out

    # --- direct_payment_debit (*164*S*) ---
    m = _RE["direct_payment_debit"].search(body)
    if m:
        out.update(tx_category="direct_payment_debit", amount=_f(m.group(1)),
                   sender=m.group("sender").strip(), balance=_f(m.group(2)))
        if fin := re.search(r"Financial Transaction Id:\s*(\d+)", body):
            out["financial_tx_id"] = fin.group(1)
        return out

    # --- bank_transfer_out ---
    m = _RE["bank_transfer_out"].search(body)
    if m:
        out.update(tx_category="bank_transfer_out", amount=_f(m.group(1)),
                   receiver=m.group("receiver").strip())
        return out

    # --- reversal ---
    m = _RE["reversal"].search(body)
    if m:
        out.update(tx_category="reversal", amount=_f(m.group(1)))
        return out

    # --- failed transaction ---
    m = _RE["failed_txn"].search(body)
    if m:
        out.update(tx_category="failed_txn", amount=_f(m.group(1)))
        return out

    # --- bundle purchase ---
    m = _RE["bundle"].search(body)
    if m:
        out.update(tx_category="bundle", amount=_f(m.group(1)))
        return out

    # --- withdrawal ---
    if "withdraw" in body.lower():
        out["tx_category"] = "withdrawal"
        m = _RE["withdrawal"].search(body)
        if m:
            out["amount"] = _f(m.group(1))
        return out

    # --- bare payment (no TxId prefix) ---
    m = _RE["payment_sent_bare"].search(body)
    if m:
        out.update(tx_category="payment_sent", amount=_f(m.group(1)),
                   receiver=m.group("receiver").strip(), balance=_f(m.group(2)))
        return out

    # --- generic fallback: at least grab the first RWF amount ---
    m = _RE["_amount_generic"].search(body)
    if m:
        out["amount"] = _f(m.group(1))
    return out


def _epoch_ms_to_iso(epoch_ms: int | str) -> str:
    try:
        ts = int(epoch_ms) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return str(epoch_ms)


def _build_record(elem: ET.Element, record_id: str) -> dict[str, Any]:
    body     = elem.get("body", "")
    raw_date = elem.get("date", "0")

    extracted = _classify_and_extract(body)

    return {
        "id":              record_id,
        "tx_category":     extracted["tx_category"],
        "amount":          extracted["amount"],
        "fee":             extracted["fee"],
        "balance":         extracted["balance"],
        "sender":          extracted["sender"],
        "receiver":        extracted["receiver"],
        "financial_tx_id": extracted["financial_tx_id"],
        "timestamp":       _epoch_ms_to_iso(raw_date),
        "readable_date":   elem.get("readable_date", ""),
        "body":            body,
        "raw_date":        int(raw_date) if raw_date.isdigit() else 0,
    }



# TransactionStore


class TransactionStore:
 # Thread-safe store for MoMo SMS transactions.
# Uses a dictionary for fast O(1) lookups.
# Loads data from XML or starts empty for testing.

    def __init__(self, xml_path: str | Path | None = None) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()
        if xml_path is not None:
            self._load_xml(Path(xml_path))

    
    # Loading
   

    def _load_xml(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"XML file not found: {path}")

        tree = ET.parse(path)
        root = tree.getroot()
        elements = root.findall("sms") if root.tag != "sms" else [root]

        loaded: dict[str, dict] = {}
        for i, elem in enumerate(elements):
            record_id = elem.get("id") or f"txn-{i+1:07d}"
            loaded[record_id] = _build_record(elem, record_id)

        with self._lock:
            self._data = loaded

        print(f"[Store] Loaded {len(loaded)} transactions from {path}")

    
    # CRUD
   

    def list_all(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        tx_category: str | None = None,
    ) -> dict[str, Any]:
        # Returns paginated MoMo records sorted by newest first, with optional category filtering.
        # Output includes data, total count, current page, page size, and total pages.
        page_size = min(max(1, page_size), 500)
        page      = max(1, page)

        with self._lock:
            records = list(self._data.values())

        if tx_category:
            records = [r for r in records if r["tx_category"] == tx_category.lower()]

        records.sort(key=lambda r: r["raw_date"], reverse=True)

        total  = len(records)
        pages  = max(1, (total + page_size - 1) // page_size)
        start  = (page - 1) * page_size
        window = records[start : start + page_size]

        return {"data": window, "total": total,
                "page": page, "page_size": page_size, "pages": pages}

    def get(self, record_id: str) -> dict[str, Any] | None:
        """O(1) dict lookup. Returns the record or None."""
        with self._lock:
            return self._data.get(record_id)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Inserts a new transaction record.
        # Requires a body string and accepts optional record fields.
        # Raises ValueError if body is empty or transaction ID already exists.
        body = payload.get("body", "")
        if not isinstance(body, str) or not body.strip():
            raise ValueError("Field 'body' is required and must be a non-empty string.")

        record_id = payload.get("id") or str(uuid.uuid4())
        now_iso   = datetime.now(tz=timezone.utc).isoformat()
        now_ms    = int(datetime.now(tz=timezone.utc).timestamp() * 1000)

        # Auto-extract if caller didn't provide structured fields
        extracted = _classify_and_extract(body)

        record: dict[str, Any] = {
            "id":              record_id,
            "tx_category":     payload.get("tx_category",    extracted["tx_category"]),
            "amount":          payload.get("amount",          extracted["amount"]),
            "fee":             payload.get("fee",             extracted["fee"]),
            "balance":         payload.get("balance",         extracted["balance"]),
            "sender":          payload.get("sender",          extracted["sender"]),
            "receiver":        payload.get("receiver",        extracted["receiver"]),
            "financial_tx_id": payload.get("financial_tx_id",extracted["financial_tx_id"]),
            "timestamp":       payload.get("timestamp",       now_iso),
            "readable_date":   payload.get("readable_date",   ""),
            "body":            body.strip(),
            "raw_date":        now_ms,
        }

        with self._lock:
            if record_id in self._data:
                raise ValueError(f"Transaction '{record_id}' already exists.")
            self._data[record_id] = record

        return record

    def update(self, record_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
       # Partially updates a transaction record (PATCH-style update).
        # Ignores immutable fields like id and raw_date.
        # Returns the updated record or None if the record is not found.
        IMMUTABLE = {"id", "raw_date"}
        ALLOWED   = {"tx_category", "amount", "fee", "balance", "sender",
                     "receiver", "financial_tx_id", "timestamp",
                     "readable_date", "body"}

        with self._lock:
            record = self._data.get(record_id)
            if record is None:
                return None
            updated = record.copy()
            for key, value in patch.items():
                if key in IMMUTABLE or key not in ALLOWED:
                    continue
                updated[key] = value

            # Re-parse body if it changed and caller didn't override fields
            if "body" in patch:
                re_extracted = _classify_and_extract(updated["body"])
                for field in ("tx_category","amount","fee","balance",
                              "sender","receiver","financial_tx_id"):
                    if field not in patch:          # don't overwrite explicit caller values
                        updated[field] = re_extracted[field]

            self._data[record_id] = updated

        return updated

    def delete(self, record_id: str) -> bool:
        """Remove a record. Returns True if deleted, False if not found."""
        with self._lock:
            if record_id not in self._data:
                return False
            del self._data[record_id]
        return True

    
    # DSA comparison helpers
   

    def linear_search(self, record_id: str) -> dict[str, Any] | None:
        """O(n) sequential scan — for DSA demonstration only."""
        with self._lock:
            for record in self._data.values():
                if record["id"] == record_id:
                    return record
        return None

    def dict_lookup(self, record_id: str) -> dict[str, Any] | None:
        """O(1) hash-table lookup — production path."""
        return self.get(record_id)

   
    # Convenience
   
    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __repr__(self) -> str:
        return f"<TransactionStore records={len(self)}>"
