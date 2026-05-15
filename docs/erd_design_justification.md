# ERD Design Justification

## Entities at a glance

The schema has six tables: `users`, `transaction_categories`, `transactions`, `transaction_participants`, `raw_sms`, and `system_logs`. Together they cover every distinct transaction pattern observed in `modified_sms_v2.xml` — incoming receives, payments to merchant codes, transfers to phone numbers, bank deposits, agent withdrawals, airtime, MTN Cash Power, direct payments, and OTP messages.

## Why this shape

**`transactions` is the central fact table** — one row per parsed SMS that represents an actual financial event. It carries the universal attributes (`amount`, `fee`, `new_balance`, `tx_timestamp`, `status`) so reporting queries (monthly spend, fee totals, balance trends) hit a single table.

**`transaction_categories` is a lookup, not an enum**, because category metadata is real data — each category has a `direction` (credit/debit/info), a human label, and a description. Storing it relationally lets us add new MoMo product types without altering tables.

**`transaction_participants` is the junction that resolves the M:N**. A single transaction often involves multiple parties in different roles — for example, an agent withdrawal has the account holder as `sender` and the agent as `agent`. A bare sender/receiver FK pair on `transactions` would not capture this, and would leave us nowhere to record agent fees or facilitator roles. The junction uses `(transaction_id, user_id, role)` as a unique key so the same user can't be assigned the same role twice on one transaction.

**`raw_sms` preserves the original payload** with a SHA-256 `body_hash` for deduplication. Keeping the source separate from parsed data lets the team re-parse historical SMS if regexes are improved, without touching cleaned `transactions` rows.

**`system_logs` ties processing events back to both the source SMS and the resulting transaction** (both FKs nullable) so failed parses, duplicate ingests, and reversal warnings are queryable.

## Integrity guarantees

`FOREIGN KEY` constraints enforce referential integrity with deliberate `ON DELETE` policies (`CASCADE` from transactions to participants; `RESTRICT` from categories to transactions). `CHECK` constraints prevent negative amounts and fees. Indexes on `tx_timestamp`, `category_id`, `status`, and `external_tx_ref` cover the most frequent query patterns.
