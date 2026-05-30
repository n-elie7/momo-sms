"""
dsa/parse_xml.py
----------------
Parses modified_sms_v2.xml (Android SMS backup format) into a list of
transaction dictionaries. Each record is enriched with a 'category' and
'amount' field extracted from the SMS body text.

Usage:
    python3 dsa/parse_xml.py
"""

import xml.etree.ElementTree as ET
import re
import os
import json
from collections import Counter

# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY DETECTION
# Each tuple is (keyword_list, category_label).
# The first matching rule wins, so order matters — put specific rules first.
# ──────────────────────────────────────────────────────────────────────────────
CATEGORY_RULES = [
    (["received",   "you have received"],          "Incoming Money"),
    (["payment",    "you have made a payment",
      "paid to"],                                  "Payment"),
    (["transferred","you have transferred",
      "sent to"],                                  "Transfer Sent"),
    (["bank deposit","deposit to your"],            "Bank Deposit"),
    (["airtime",    "air time"],                    "Airtime Bill Payment"),
    (["cash power", "caspower", "electricity"],     "Cash Power Bill Payment"),
    (["withdrawn",  "agent withdrawal",
      "cash out"],                                  "Withdrawal"),
    (["bundle",     "internet", "data package"],    "Bundle Purchase"),
    (["third party","3rd party"],                   "Third Party Transaction"),
    (["reverse",    "reversal"],                    "Reversal"),
    (["fee",        "charge"],                      "Fee"),
]

def detect_category(body: str) -> str:
    """Return a category label based on keywords found in the SMS body."""
    lower = body.lower()
    for keywords, label in CATEGORY_RULES:
        if any(kw in lower for kw in keywords):
            return label
    return "Other"


# ──────────────────────────────────────────────────────────────────────────────
# AMOUNT EXTRACTION
# Tries several common MoMo SMS patterns in order of specificity.
# ──────────────────────────────────────────────────────────────────────────────
AMOUNT_PATTERNS = [
    # "RWF 5,000" / "RWF5000"
    r'RWF\s?([\d,]+(?:\.\d{1,2})?)',
    # "5,000 RWF"
    r'([\d,]+(?:\.\d{1,2})?)\s?RWF',
    # "amount of 5000" / "amount: 5,000"
    r'amount(?:\s+of)?[:\s]+([\d,]+(?:\.\d{1,2})?)',
    # Generic standalone number (last resort, only if long enough to be money)
    r'\b(\d{4,}(?:,\d{3})*(?:\.\d{1,2})?)\b',
]

def extract_amount(body: str) -> float | None:
    """
    Return the transaction amount as a float, or None if not found.
    Removes commas before converting (e.g. '5,000' → 5000.0).
    """
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(',', '')
            try:
                return float(raw)
            except ValueError:
                continue
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CORE PARSER
# ──────────────────────────────────────────────────────────────────────────────
def parse_sms_xml(filepath: str) -> list[dict]:
    """
    Parse an Android SMS backup XML file and return a list of enriched
    transaction dictionaries.

    Expected XML structure:
        <smses count="N">
            <sms address="..." date="..." readable_date="..." body="..." .../>
            ...
        </smses>

    Returns:
        List of dicts, each with keys:
            id, address, date, readable_date, body, category, amount
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"XML file not found: {filepath}\n"
            "Make sure 'modified_sms_v2.xml' is inside the 'data/' folder."
        )

    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        raise ValueError(f"XML is malformed and could not be parsed: {e}")

    root = tree.getroot()

    # Support both <smses> and <sms-backup> as root tags
    sms_elements = root.findall('sms')
    if not sms_elements:
        # Some exports nest under a different tag; try finding anywhere
        sms_elements = root.iter('sms')

    transactions = []

    for idx, sms in enumerate(sms_elements, start=1):
        body = sms.get('body', '').strip()

        record = {
            "id":            idx,
            # Sender / receiver phone number
            "address":       sms.get('address', '').strip(),
            # Unix timestamp in milliseconds
            "date":          sms.get('date', '').strip(),
            # Human-readable date string from the XML
            "readable_date": sms.get('readable_date', '').strip(),
            # Full SMS text
            "body":          body,
            # Derived fields
            "category":      detect_category(body),
            "amount":        extract_amount(body),
        }
        transactions.append(record)

    return transactions


# ──────────────────────────────────────────────────────────────────────────────
# CLI OUTPUT
# ──────────────────────────────────────────────────────────────────────────────
def print_summary(transactions: list[dict]) -> None:
    """Print a summary table: total records + category breakdown."""
    total = len(transactions)
    category_counts = Counter(t['category'] for t in transactions)

    print("=" * 55)
    print(f"  MoMo SMS Parser — {total} records parsed")
    print("=" * 55)
    print(f"{'Category':<35} {'Count':>6}  {'%':>5}")
    print("-" * 55)

    for category, count in sorted(category_counts.items(),
                                   key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {category:<33} {count:>6}  {pct:>4.1f}%")

    print("-" * 55)
    print(f"  {'TOTAL':<33} {total:>6}  100.0%")
    print("=" * 55)


def main():
    # Resolve path relative to this file so the script works from any directory
    base_dir    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path    = os.path.join(base_dir, 'data', 'modified_sms_v2.xml')

    print(f"\nParsing: {xml_path}\n")
    transactions = parse_sms_xml(xml_path)

    # ── Print every record ──────────────────────────────────────────────────
    for t in transactions:
        amount_str = f"RWF {t['amount']:,.2f}" if t['amount'] else "N/A"
        print(
            f"[{t['id']:>4}] {t['readable_date']:<28} "
            f"{t['category']:<30} {amount_str:>16}  "
            f"FROM: {t['address']}"
        )

    print()
    print_summary(transactions)

    # ── Optionally dump to JSON for the API layer to consume ────────────────
    out_path = os.path.join(base_dir, 'data', 'transactions.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)
    print(f"\n✔  JSON snapshot saved → {out_path}")


if __name__ == '__main__':
    main()
