import xml.etree.ElementTree as ET
import re
import os
import json
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_XML_PATH = os.path.join(_ROOT, "data", "modified_sms_v2.xml")

# category rules
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


# amount regex extraction
AMOUNT_PATTERNS = [
    # "RWF 5,000" / "RWF5000"
    r'RWF\s?([\d,]+(?:\.\d{1,2})?)',
    # "5,000 RWF"
    r'([\d,]+(?:\.\d{1,2})?)\s?RWF',
    # "amount of 5000" / "amount: 5,000"
    r'amount(?:\s+of)?[:\s]+([\d,]+(?:\.\d{1,2})?)',
    r'\b(\d{4,}(?:,\d{3})*(?:\.\d{1,2})?)\b',
]

def extract_amount(body: str) -> float | None:
    """extract amount function return the amount"""
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(',', '')
            try:
                return float(raw)
            except ValueError:
                continue
    return None

def parse_sms_xml(filepath: str) -> list[dict]:
    """parse sms in xml file"""
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

    sms_elements = root.findall('sms')
    if not sms_elements:
        # some exports nest under a different tag try finding anywhere
        sms_elements = root.iter('sms')

    transactions = []

    for idx, sms in enumerate(sms_elements, start=1):
        body = sms.get('body', '').strip()

        record = {
            "id": idx,
            "address": sms.get('address', '').strip(),
            "date": sms.get('date', '').strip(),
            "readable_date": sms.get('readable_date', '').strip(),
            "body": body,
            "category": detect_category(body),
            "amount": extract_amount(body),
        }
        transactions.append(record)

    return transactions

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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path = os.path.join(base_dir, 'data', 'modified_sms_v2.xml')

    transactions = parse_sms_xml(xml_path)

    print_summary(transactions)

    out_path = os.path.join(base_dir, 'data', 'transactions.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)

transactions_list = parse_sms_xml(_XML_PATH)
transactions_dict = {t["id"]: t for t in transactions_list}

def get_next_id(transactions_dict=transactions_dict, _counter=[None]):
    if _counter[0] is None:
        _counter[0] = max(transactions_dict.keys(), default=0) + 1
    nid = _counter[0]
    _counter[0] += 1
    return nid

if __name__ == '__main__':
    main()
