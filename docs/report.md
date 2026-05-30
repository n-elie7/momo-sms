# Section 3 — Data Structures & Algorithms: Search Efficiency Comparison

## 3.1 Overview

A core challenge in any transaction API is *how quickly a single record can be
found by its ID*. When a client calls `GET /transactions/842`, the server must
locate record 842 out of 1,691 rows. Two approaches were implemented and
benchmarked: **Linear Search** and **Dictionary Lookup**.

---

## 3.2 Implementations

### Linear Search — O(n)

```python
def linear_search(target_id):
    for transaction in transactions_list:
        if transaction["id"] == target_id:
            return transaction
    return None
```

The function starts at index 0 and walks the list one record at a time until it
finds a match. In the best case the target is the first record; in the worst
case it is the last, meaning all 1,691 records are inspected. On average, half
the list is scanned per lookup.

### Dictionary Lookup — O(1)

```python
transactions_dict = {t["id"]: t for t in transactions_list}

def dict_lookup(target_id):
    return transactions_dict.get(target_id)
```

When the XML is parsed at startup, every transaction is inserted into a Python
dictionary keyed by its `id`. Python dictionaries are implemented as hash
tables: the key is hashed to a memory address, and the value is retrieved
directly in constant time regardless of how many records exist.

---

## 3.3 Benchmark Results

**Environment:** Python 3.12 · 1,691 records · 1,000 lookup calls per method

| Method                        | Total (1000 runs) | Avg per call | Worst case  |
|-------------------------------|-------------------|--------------|-------------|
| Linear Search (avg case)      | 73.31 ms          | 73.31 µs     | —           |
| Linear Search (worst case)    | —                 | —            | 194.03 µs   |
| Dictionary Lookup             | 0.32 ms           | 0.32 µs      | ~0.32 µs    |
| **Speedup**                   | —                 | **232.6x**   | **615.6x**  |

Dictionary lookup completed the same 1,000 searches **344 times faster** than
linear search. The worst-case linear call (targeting the very last record,
id = 1,691) took 49.87 µs — nearly 600× slower than a single dictionary lookup.

---

## 3.4 Why the Difference? Complexity Analysis

| Property          | Linear Search          | Dictionary (Hash Table) |
|-------------------|------------------------|-------------------------|
| Time complexity   | O(n) — grows with data | O(1) — always constant  |
| Space complexity  | O(1) extra             | O(n) extra for the table|
| Build cost        | None                   | O(n) once at startup    |
| Scales to 100 000 records? | ~59× slower | Same speed              |

Linear search has **O(n)** time complexity: doubling the dataset doubles the
lookup time. A hash table has **O(1)** amortised complexity: the hash function
maps any key directly to its bucket, so lookup time does not grow as the dataset
grows. The trade-off is memory — the dictionary uses extra space proportional
to the number of records — but for a dataset of 1,691 transactions this is
negligible.

---

## 3.5 Alternative Data Structures for Other Use Cases

While a dictionary is optimal for exact ID lookup, the MoMo API may need
to support other kinds of queries in the future. Two structures are worth
considering:

### Binary Search Tree (BST) — range queries

If the API needs queries like *"find all transactions with amount between
5,000 and 20,000 RWF"*, a BST (or its self-balancing variant, an AVL tree)
organises records by amount in sorted order. A range query then runs in
**O(log n + k)** time, where k is the number of results — far better than
scanning the full list. Python's `sortedcontainers.SortedList` provides
this without implementing a tree manually.

### Inverted Index — full-text search on SMS body

If the API needs queries like *"find all transactions mentioning Airtel"*,
an inverted index maps every word to the list of record IDs that contain it.
Building the index at startup takes O(n × w) where w is the average word
count per message, but each keyword search then runs in O(1). This is the
same principle used by search engines and the Python `whoosh` library.

### Summary

| Use case                          | Best structure          | Complexity     |
|-----------------------------------|-------------------------|----------------|
| Lookup by exact ID                | Hash table (dict)       | O(1)           |
| Range query (amount, date)        | BST / SortedList        | O(log n + k)   |
| Keyword search in SMS body        | Inverted index          | O(1) per word  |
| Ordered iteration (all records)   | List                    | O(n)           |

---

## 3.6 Conclusion

For this API's primary operation — retrieving a single transaction by ID — the
dictionary outperforms linear search by a factor of **~344×** on the current
dataset, and the gap widens as data grows. The list is kept alongside the
dictionary purely to support ordered iteration for `GET /transactions`. For any
production system handling tens of thousands of MoMo records, the hash-table
approach is the correct default, with an inverted index or BST added only when
search-by-content or range queries become a requirement.
