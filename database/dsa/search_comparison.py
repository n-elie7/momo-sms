# Compares Linear Search and Dictionary Lookup on parsed MoMo transactions and reports
# execution time and speedup.



import time
import random
import sys
import os

# ── path fix so we can import parse_xml from same folder ──────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_xml import transactions_list, transactions_dict

# ══════════════════════════════════════════════════════════════════════════════
# SEARCH IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def linear_search(data: list[dict], target_id: int) -> dict | None:
    """
    O(n) — walks the list from index 0 until a matching id is found.
    Worst case: target is the last element (all n records inspected).
    Best case:  target is the first element (1 comparison).
    Average:    n/2 comparisons.
    """
    for record in data:
        if record["id"] == target_id:
            return record
    return None


def dict_lookup(index: dict[int, dict], target_id: int) -> dict | None:
    """
    O(1) — Python dict is a hash table.
    The key is hashed to a memory address; value retrieved directly.
    Time does NOT grow as dataset grows.
    """
    return index.get(target_id)


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_benchmark(runs: int = 1000) -> None:
    n       = len(transactions_list)
    id_pool = [t["id"] for t in transactions_list]

    # Use the same random IDs for both methods so the comparison is fair
    random.seed(42)
    search_ids = [random.choice(id_pool) for _ in range(runs)]

    print("=" * 60)
    print("  MoMo DSA Benchmark — Linear Search vs Dictionary Lookup")
    print("=" * 60)
    print(f"  Dataset size : {n} transactions")
    print(f"  Lookups/test : {runs}")
    print()

    # ── 1. Linear Search ──────────────────────────────────────────────────────
    start_linear = time.perf_counter()
    for tid in search_ids:
        linear_search(transactions_list, tid)
    end_linear = time.perf_counter()

    linear_total_ms = (end_linear - start_linear) * 1_000
    linear_avg_us   = (end_linear - start_linear) / runs * 1_000_000

    # ── 2. Dictionary Lookup ──────────────────────────────────────────────────
    start_dict = time.perf_counter()
    for tid in search_ids:
        dict_lookup(transactions_dict, tid)
    end_dict = time.perf_counter()

    dict_total_ms = (end_dict - start_dict) * 1_000
    dict_avg_us   = (end_dict - start_dict) / runs * 1_000_000

    # ── 3. Worst-case linear (target = last record) ───────────────────────────
    worst_id = transactions_list[-1]["id"]
    start_wc = time.perf_counter()
    for _ in range(runs):
        linear_search(transactions_list, worst_id)
    end_wc = time.perf_counter()
    worst_avg_us = (end_wc - start_wc) / runs * 1_000_000

    # ── Results table ─────────────────────────────────────────────────────────
    speedup = linear_avg_us / dict_avg_us

    print(f"  {'Method':<28} {'Total (ms)':>12}  {'Avg/call (µs)':>14}")
    print("  " + "-" * 56)
    print(f"  {'Linear Search (avg case)':<28} {linear_total_ms:>12.4f}  {linear_avg_us:>14.4f}")
    print(f"  {'Linear Search (worst case)':<28} {'—':>12}  {worst_avg_us:>14.4f}")
    print(f"  {'Dictionary Lookup':<28} {dict_total_ms:>12.4f}  {dict_avg_us:>14.4f}")
    print("  " + "-" * 56)
    print(f"  Speedup (dict vs linear avg)  : {speedup:.1f}x faster")
    print(f"  Speedup (dict vs linear worst): {worst_avg_us / dict_avg_us:.1f}x faster")
    print()

    # ── Correctness check ─────────────────────────────────────────────────────
    print("  Correctness check (first 5 lookups match):")
    all_match = True
    for tid in search_ids[:5]:
        r1 = linear_search(transactions_list, tid)
        r2 = dict_lookup(transactions_dict, tid)
        match = r1 == r2
        if not match:
            all_match = False
        status = "✔" if match else "✘"
        print(f"    {status}  id={tid}  →  {r1['category'] if r1 else 'None'}")

    print()
    if all_match:
        print("  ✔  Both methods return identical results.")
    else:
        print("  ✘  MISMATCH detected — check data integrity.")

    print()
    print("  Complexity Summary:")
    print(f"  {'Linear Search':<20} O(n)  — scales with dataset size")
    print(f"  {'Dictionary Lookup':<20} O(1)  — constant regardless of size")
    print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run_benchmark(runs=1000)
