USE momo_sms;

-- Quick row counts proves data is there
SELECT 'users' AS tbl, COUNT(*) AS n FROM users UNION ALL
SELECT 'transaction_categories', COUNT(*) FROM transaction_categories UNION ALL
SELECT 'raw_sms', COUNT(*) FROM raw_sms UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions UNION ALL
SELECT 'transaction_participants', COUNT(*) FROM transaction_participants UNION ALL
SELECT 'system_logs', COUNT(*) FROM system_logs;

-- create: Insert a new airtime purchase
INSERT INTO transactions
  (external_tx_ref, financial_tx_id, category_id, amount, fee, new_balance, tx_timestamp, status, message_note)
VALUES
  ('99999000111', NULL,
   (SELECT category_id FROM transaction_categories WHERE category_code='AIRTIME'),
   500.00, 0.00, 300.00, '2024-06-01 09:15:00', 'completed', 'Airtime test purchase');

-- Confirm it was inserted
SELECT * FROM transactions WHERE external_tx_ref = '99999000111';

-- Read: All transactions joined with category and participants
SELECT t.transaction_id,
       t.tx_timestamp,
       c.category_name,
       t.amount,
       t.fee,
       t.new_balance,
       GROUP_CONCAT(CONCAT(u.full_name, ' (', tp.role, ')') SEPARATOR ', ') AS participants
FROM transactions t
JOIN transaction_categories c   ON c.category_id = t.category_id
LEFT JOIN transaction_participants tp ON tp.transaction_id = t.transaction_id
LEFT JOIN users u                     ON u.user_id = tp.user_id
GROUP BY t.transaction_id
ORDER BY t.tx_timestamp;

-- Update: Mark the cash power transaction as reversed
UPDATE transactions
SET status = 'reversed'
WHERE external_tx_ref = '14103506143';

-- Confirm the change
SELECT transaction_id, external_tx_ref, status, message_note
FROM transactions
WHERE external_tx_ref = '14103506143';

-- Delete: Delete the test airtime transaction we created
DELETE FROM transactions WHERE external_tx_ref = '99999000111';

-- Confirm it's gone (should return zero rows)
SELECT * FROM transactions WHERE external_tx_ref = '99999000111';
