
import time
import random
from pathlib import Path

from parse_xml import transactions_list, transactions_dict

try:
    from parse_xml import parse_sms_xml
except ImportError:
    from parse_xml import parse_sms_xml


def linear_search(data: list[dict], target_id: int) -> dict | None:
    """O(n) walks the list from index 0 until a matching id is found."""
    for record in data:
        if record["id"] == target_id:
            return record
    return None


def dict_lookup(index: dict[int, dict], target_id: int) -> dict | None:
    """O(1) Python dict is a hash table."""
    return index.get(target_id)


def run_benchmark(runs: int = 1000) -> dict:
    id_pool = [transaction["id"] for transaction in transactions_list]

    # Use the same random IDs for both methods so the comparison is fair
    search_ids = [random.choice(id_pool) for _ in range(runs)]

    # Linear Search
    start_linear = time.perf_counter()
    for tid in search_ids:
        linear_search(transactions_list, tid)
    end_linear = time.perf_counter()

    linear_total = end_linear - start_linear

    # Dictionary Lookup
    start_dict = time.perf_counter()
    for tid in search_ids:
        dict_lookup(transactions_dict, tid)
    end_dict = time.perf_counter()

    dict_total = end_dict - start_dict

    return {
        "records_in_dataset": len(transactions_list),
        "num_lookups": runs,
        "linear_total_seconds": linear_total,
        "dict_total_seconds":   dict_total,
        "linear_avg_microseconds": (linear_total / runs) * 1_000_000,
        "dict_avg_microseconds":   (dict_total   / runs) * 1_000_000,
        # Avoid divide by zero
        "speedup_factor": linear_total / dict_total if dict_total > 0 else float("inf"),
    }

def print_report(results: dict) -> None:
    """Pretty-print the benchmark results."""
    print("=" * 60)
    print("Linear Search vs Dictionary Lookup")
    print("=" * 60)
    print(f"Records in dataset: {results['records_in_dataset']:,}")
    print(f"Lookups performed: {results['num_lookups']:,}")
    print()
    print(f"Linear search total: {results['linear_total_seconds']:.6f} s")
    print(f"Dict lookup total: {results['dict_total_seconds']:.6f} s")
    print()
    print(f"Linear avg per lookup: {results['linear_avg_microseconds']:.3f} µs")
    print(f"Dict avg per lookup: {results['dict_avg_microseconds']:.3f} µs")
    print()
    print(f"Dict lookup was {results['speedup_factor']:.1f}x faster")
    print("=" * 60)
 
 
def print_scaling_table(transactions: list[dict]) -> None:
    """Run the same benchmark at multiple dataset sizes and print a comparison table."""
    sizes = [20, 100, 500, 1000, len(transactions)]
    # Drop duplicates and sort so the table reads cleanly even when the
    # dataset is exactly one of the canonical sizes.
    sizes = sorted(set(s for s in sizes if s <= len(transactions)))
 
    print("\n" + "=" * 78)
    print("Scaling comparison — same lookups, varying dataset size")
    print("=" * 78)
    print(f"{'Dataset size':>14} | {'Linear (µs/op)':>16} | {'Dict (µs/op)':>14} | {'Speedup':>10}")
    print("-" * 78)
 
    for size in sizes:
        subset = transactions[:size]
    
        results = run_benchmark(subset, num_lookups=1000)
        print(
            f"{size:>14,} | "
            f"{results['linear_avg_microseconds']:>16.3f} | "
            f"{results['dict_avg_microseconds']:>14.3f} | "
            f"{results['speedup_factor']:>9.1f}x"
        )
    print("=" * 78)

if __name__ == "__main__":
    xml_path = Path(__file__).parent.parent / "data" / "modified_sms_v2.xml"
    if not xml_path.exists():
        # Fall back to the path used in development
        xml_path = Path("/mnt/user-data/uploads/modified_sms_v2.xml")
 
    print(f"Loading transactions from {xml_path}...")
    transactions = parse_sms_xml(xml_path)
    print(f"Loaded {len(transactions)} records\n")
 
    # Fix the seed so the random ids are reproducible
    random.seed(42)
 
    # Headline benchmark against the full dataset
    results = run_benchmark(transactions, num_lookups=1000)
    print_report(results)
 
    # Scaling table shows O(n) vs O(1) and explicitly covers the 20-record
    # minimum required by the assignment brief.
    print_scaling_table(transactions)
