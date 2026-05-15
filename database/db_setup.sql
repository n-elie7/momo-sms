DROP DATABASE IF EXISTS momo_sms;
CREATE DATABASE momo_sms
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE momo_sms;

CREATE TABLE users (
    user_id         INT             AUTO_INCREMENT PRIMARY KEY      COMMENT 'Surrogate key',
    full_name       VARCHAR(100)    NOT NULL                        COMMENT 'Person or business name parsed from SMS body',
    phone_number    VARCHAR(15)     NULL                            COMMENT 'MSISDN where available, e.g. 250788...',
    account_number  VARCHAR(20)     NULL                            COMMENT 'MoMo account number when present',
    user_type       ENUM('customer','agent','business','self')
                    NOT NULL        DEFAULT 'customer'              COMMENT 'self = the SMS account holder',
    is_anonymized   BOOLEAN         NOT NULL DEFAULT FALSE          COMMENT 'TRUE when phone is masked (e.g. *********013)',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_phone     UNIQUE (phone_number),
    CONSTRAINT chk_users_name_len CHECK (CHAR_LENGTH(full_name) >= 1)
) ENGINE=InnoDB COMMENT='Distinct parties involved in MoMo transactions';

CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_name ON users(full_name);


CREATE TABLE transaction_categories (
    category_id     INT             AUTO_INCREMENT PRIMARY KEY,
    category_code   VARCHAR(40)     NOT NULL                        COMMENT 'Machine code, e.g. PAYMENT_CODE',
    category_name   VARCHAR(80)     NOT NULL                        COMMENT 'Human label',
    direction       ENUM('credit','debit','info')
                    NOT NULL                                        COMMENT 'credit = money in, debit = money out, info = non-financial (OTP)',
    description     TEXT            NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_cat_code UNIQUE (category_code)
) ENGINE=InnoDB COMMENT='Catalog of MoMo transaction types';

CREATE TABLE raw_sms (
    raw_sms_id      INT             AUTO_INCREMENT PRIMARY KEY,
    sms_address     VARCHAR(40)     NULL                            COMMENT 'XML address attr, typically M-Money',
    sms_date_ms     BIGINT          NOT NULL                        COMMENT 'Epoch ms from XML date attr',
    readable_date   VARCHAR(50)     NULL                            COMMENT 'Human date from XML',
    body            TEXT            NOT NULL                        COMMENT 'Full SMS body verbatim',
    body_hash       CHAR(64)        NOT NULL                        COMMENT 'SHA-256 of body, deduplication key',
    parse_status    ENUM('pending','parsed','failed','ignored')
                    NOT NULL        DEFAULT 'pending',
    ingested_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_raw_hash UNIQUE (body_hash),
    CONSTRAINT chk_raw_date CHECK (sms_date_ms > 0)
) ENGINE=InnoDB COMMENT='Verbatim SMS records (audit trail)';

CREATE INDEX idx_raw_status ON raw_sms(parse_status);
CREATE INDEX idx_raw_date   ON raw_sms(sms_date_ms);


CREATE TABLE transactions (
    transaction_id      INT             AUTO_INCREMENT PRIMARY KEY,
    external_tx_ref     VARCHAR(40)     NULL                        COMMENT 'TxId from SMS body, e.g. 76662021700',
    financial_tx_id     VARCHAR(40)     NULL                        COMMENT 'Financial Transaction Id when present',
    category_id         INT             NOT NULL,
    amount              DECIMAL(15,2)   NOT NULL                    COMMENT 'Transaction amount, in currency',
    fee                 DECIMAL(15,2)   NOT NULL DEFAULT 0.00       COMMENT 'Fee charged',
    currency            CHAR(3)         NOT NULL DEFAULT 'RWF',
    new_balance         DECIMAL(15,2)   NULL                        COMMENT 'Account balance reported after the tx',
    tx_timestamp        DATETIME        NOT NULL                    COMMENT 'When the transaction itself occurred',
    status              ENUM('completed','failed','reversed')
                        NOT NULL        DEFAULT 'completed',
    token               VARCHAR(50)     NULL                        COMMENT 'Vendor token (cash power, airtime)',
    message_note        TEXT            NULL                        COMMENT 'Free-text message from sender/agent',
    raw_sms_id          INT             NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_tx_external      UNIQUE (external_tx_ref),
    CONSTRAINT chk_tx_amount       CHECK (amount >= 0),
    CONSTRAINT chk_tx_fee          CHECK (fee >= 0),
    CONSTRAINT chk_tx_currency     CHECK (CHAR_LENGTH(currency) = 3),
    CONSTRAINT fk_tx_category
        FOREIGN KEY (category_id) REFERENCES transaction_categories(category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_tx_rawsms
        FOREIGN KEY (raw_sms_id) REFERENCES raw_sms(raw_sms_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Parsed MoMo transactions (fact table)';

CREATE INDEX idx_tx_timestamp ON transactions(tx_timestamp);
CREATE INDEX idx_tx_category  ON transactions(category_id);
CREATE INDEX idx_tx_status    ON transactions(status);
CREATE INDEX idx_tx_finid     ON transactions(financial_tx_id);

CREATE TABLE transaction_participants (
    participant_id  INT             AUTO_INCREMENT PRIMARY KEY,
    transaction_id  INT             NOT NULL,
    user_id         INT             NOT NULL,
    role            ENUM('sender','receiver','agent','merchant')
                    NOT NULL                                        COMMENT 'Role of this user in this transaction',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tp_combo UNIQUE (transaction_id, user_id, role),
    CONSTRAINT fk_tp_tx
        FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tp_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='M:N junction — who participated in which transaction and how';

CREATE INDEX idx_tp_tx   ON transaction_participants(transaction_id);
CREATE INDEX idx_tp_user ON transaction_participants(user_id);


CREATE TABLE system_logs (
    log_id          INT             AUTO_INCREMENT PRIMARY KEY,
    raw_sms_id      INT             NULL,
    transaction_id  INT             NULL,
    log_level       ENUM('INFO','WARN','ERROR','DEBUG')
                    NOT NULL,
    stage           VARCHAR(40)     NOT NULL                        COMMENT 'e.g. ingest, parse, categorize, persist',
    message         TEXT            NOT NULL,
    details_json    JSON            NULL                            COMMENT 'Structured context (regex match, fields, etc.)',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_rawsms
        FOREIGN KEY (raw_sms_id) REFERENCES raw_sms(raw_sms_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_log_tx
        FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Pipeline event log for data processing observability';

CREATE INDEX idx_log_level ON system_logs(log_level);
CREATE INDEX idx_log_stage ON system_logs(stage);
CREATE INDEX idx_log_time  ON system_logs(created_at);


INSERT INTO transaction_categories (category_code, category_name, direction, description) VALUES
('INCOMING_RECEIVE','Incoming money received','credit','Money received from another MoMo customer'),
('PAYMENT_CODE','Payment to merchant code','debit','Payment completed to a numeric merchant code'),
('TRANSFER_PHONE','Transfer to phone','debit','Funds transferred to another MoMo number'),
('BANK_DEPOSIT','Bank deposit','credit','Cash/bank deposit added to MoMo account'),
('WITHDRAWAL_AGENT','Agent withdrawal','debit','Cash withdrawn via a MoMo agent'),
('AIRTIME','Airtime purchase','debit','MTN airtime top-up'),
('CASH_POWER','MTN Cash Power','debit','Electricity token purchase'),
('DIRECT_PAYMENT','Direct payment (external)','debit','External vendor charge on MoMo account'),
('OTP','One-time password','info','MoMo OTP delivered via SMS (non-financial)');

INSERT INTO users (full_name, phone_number, account_number, user_type, is_anonymized) VALUES
('Account Holder',     NULL,            '36521838',     'self',     FALSE),
('Jane Smith',         '250791666666',  NULL,           'customer', FALSE),
('Samuel Carter',      '250790777777',  NULL,           'customer', FALSE),
('Alex Doe',           '250788999999',  NULL,           'customer', FALSE),
('Robert Brown',       '250789888888',  NULL,           'customer', FALSE),
('Linda Green',        NULL,            NULL,           'customer', TRUE),
('Agent Sophia',       '250795963036',  NULL,           'agent',    FALSE),
('DIRECT PAYMENT LTD', NULL,            NULL,           'business', FALSE);

INSERT INTO raw_sms (sms_address, sms_date_ms, readable_date, body, body_hash, parse_status) VALUES
('M-Money', 1715351458724, '10 May 2024 4:30:58 PM',
 'You have received 2000 RWF from Jane Smith (*********013) on your mobile money account at 2024-05-10 16:30:51. Your new balance:2000 RWF. Financial Transaction Id: 76662021700.',
 SHA2('raw1',256), 'parsed'),
('M-Money', 1715351506754, '10 May 2024 4:31:46 PM',
 'TxId: 73214484437. Your payment of 1,000 RWF to Jane Smith 12845 has been completed at 2024-05-10 16:31:39. Your new balance: 1,000 RWF. Fee was 0 RWF.',
 SHA2('raw2',256), 'parsed'),
('M-Money', 1715445936412, '11 May 2024 6:45:36 PM',
 '*113*R*A bank deposit of 40000 RWF has been added to your mobile money account at 2024-05-11 18:43:49. Your NEW BALANCE :40400 RWF.',
 SHA2('raw3',256), 'parsed'),
('M-Money', 1715452495316, '11 May 2024 8:34:55 PM',
 '*165*S*10000 RWF transferred to Samuel Carter (250791666666) from 36521838 at 2024-05-11 20:34:47 . Fee was: 100 RWF. New balance: 28300 RWF.',
 SHA2('raw4',256), 'parsed'),
('M-Money', 1716682234219, '26 May 2024 2:10:34 AM',
 'You Abebe Chala CHEBUDIE have via agent: Agent Sophia (250790777777), withdrawn 20000 RWF from your mobile money account: 36521838 at 2024-05-26 02:10:27. Your new balance: 6400 RWF. Fee paid: 350 RWF. Financial Transaction Id: 14098463509.',
 SHA2('raw5',256), 'parsed'),
('M-Money', 1716723067339, '26 May 2024 1:31:07 PM',
 '*162*TxId:14103506143*S*Your payment of 4000 RWF to MTN Cash Power with token 72962-79980-44699-06073 has been completed at 2024-05-26 13:31:00. Your new balance: 800 RWF.',
 SHA2('raw6',256), 'parsed');


INSERT INTO transactions
  (external_tx_ref, financial_tx_id, category_id, amount, fee, new_balance, tx_timestamp, status, token, message_note, raw_sms_id)
VALUES
  (NULL,           '76662021700',  (SELECT category_id FROM transaction_categories WHERE category_code='INCOMING_RECEIVE'),
   2000.00,   0.00,  2000.00,  '2024-05-10 16:30:51', 'completed', NULL, NULL,
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw1',256))),

  ('73214484437',  NULL,           (SELECT category_id FROM transaction_categories WHERE category_code='PAYMENT_CODE'),
   1000.00,   0.00,  1000.00,  '2024-05-10 16:31:39', 'completed', NULL, 'Payment to merchant code 12845',
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw2',256))),

  (NULL,           NULL,           (SELECT category_id FROM transaction_categories WHERE category_code='BANK_DEPOSIT'),
   40000.00,  0.00,  40400.00, '2024-05-11 18:43:49', 'completed', NULL, 'Cash deposit at agent',
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw3',256))),

  (NULL,           NULL,           (SELECT category_id FROM transaction_categories WHERE category_code='TRANSFER_PHONE'),
   10000.00,  100.00, 28300.00, '2024-05-11 20:34:47', 'completed', NULL, NULL,
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw4',256))),

  (NULL,           '14098463509',  (SELECT category_id FROM transaction_categories WHERE category_code='WITHDRAWAL_AGENT'),
   20000.00,  350.00, 6400.00,  '2024-05-26 02:10:27', 'completed', NULL, 'Agent withdrawal',
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw5',256))),

  ('14103506143',  NULL,           (SELECT category_id FROM transaction_categories WHERE category_code='CASH_POWER'),
   4000.00,   0.00,  800.00,   '2024-05-26 13:31:00', 'completed',
   '72962-79980-44699-06073', 'MTN Cash Power token purchase',
   (SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw6',256)));


INSERT INTO transaction_participants (transaction_id, user_id, role) VALUES
-- Tx 1: incoming receive — Jane Smith is sender, Account Holder is receiver
((SELECT transaction_id FROM transactions WHERE financial_tx_id='76662021700'),
 (SELECT user_id FROM users WHERE full_name='Jane Smith'), 'sender'),
((SELECT transaction_id FROM transactions WHERE financial_tx_id='76662021700'),
 (SELECT user_id FROM users WHERE full_name='Account Holder'), 'receiver'),
-- Tx 2: payment to code — Account Holder is sender, Jane Smith is receiver
((SELECT transaction_id FROM transactions WHERE external_tx_ref='73214484437'),
 (SELECT user_id FROM users WHERE full_name='Account Holder'), 'sender'),
((SELECT transaction_id FROM transactions WHERE external_tx_ref='73214484437'),
 (SELECT user_id FROM users WHERE full_name='Jane Smith'), 'receiver'),
-- Tx 4: transfer to phone — Account Holder → Samuel Carter
((SELECT transaction_id FROM transactions WHERE amount=10000.00 AND new_balance=28300.00),
 (SELECT user_id FROM users WHERE full_name='Account Holder'), 'sender'),
((SELECT transaction_id FROM transactions WHERE amount=10000.00 AND new_balance=28300.00),
 (SELECT user_id FROM users WHERE full_name='Samuel Carter'), 'receiver'),
-- Tx 5: agent withdrawal — Account Holder withdrew, Agent Sophia facilitated
((SELECT transaction_id FROM transactions WHERE financial_tx_id='14098463509'),
 (SELECT user_id FROM users WHERE full_name='Account Holder'), 'sender'),
((SELECT transaction_id FROM transactions WHERE financial_tx_id='14098463509'),
 (SELECT user_id FROM users WHERE full_name='Agent Sophia'), 'agent'),
-- Tx 6: cash power
((SELECT transaction_id FROM transactions WHERE external_tx_ref='14103506143'),
 (SELECT user_id FROM users WHERE full_name='Account Holder'), 'sender');

INSERT INTO system_logs (raw_sms_id, transaction_id, log_level, stage, message, details_json) VALUES
((SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw1',256)),
 (SELECT transaction_id FROM transactions WHERE financial_tx_id='76662021700'),
 'INFO', 'parse', 'Parsed INCOMING_RECEIVE successfully',
 JSON_OBJECT('regex','incoming_v1','fields_extracted',4)),

((SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw2',256)),
 (SELECT transaction_id FROM transactions WHERE external_tx_ref='73214484437'),
 'INFO', 'categorize', 'Matched PAYMENT_CODE pattern', NULL),

((SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw3',256)),
 (SELECT transaction_id FROM transactions WHERE amount=40000.00 AND new_balance=40400.00),
 'INFO', 'persist', 'Transaction inserted', NULL),

(NULL, NULL, 'WARN', 'ingest', 'Duplicate body_hash skipped',
 JSON_OBJECT('body_hash','abc123','source','xml_batch_2024_05_30')),

((SELECT raw_sms_id FROM raw_sms WHERE body_hash=SHA2('raw5',256)),
 (SELECT transaction_id FROM transactions WHERE financial_tx_id='14098463509'),
 'INFO', 'parse', 'Withdrawal parsed: 2 participants linked',
 JSON_OBJECT('participants',JSON_ARRAY('self','agent'))),

(NULL, NULL, 'ERROR', 'parse', 'Unrecognised body pattern',
 JSON_OBJECT('sample','Yello!Umaze kugura 2000Rwf','action','queued_for_review'));


SELECT t.transaction_id,
       t.tx_timestamp,
       c.category_name,
       t.amount,
       t.fee,
       t.new_balance,
       GROUP_CONCAT(CONCAT(u.full_name, ' (', tp.role, ')') SEPARATOR ', ') AS participants
FROM   transactions t
JOIN   transaction_categories c   ON c.category_id = t.category_id
LEFT JOIN transaction_participants tp ON tp.transaction_id = t.transaction_id
LEFT JOIN users u                     ON u.user_id = tp.user_id
GROUP BY t.transaction_id
ORDER BY t.tx_timestamp;


SELECT DATE_FORMAT(t.tx_timestamp,'%Y-%m') AS month,
       c.category_name,
       COUNT(*)                            AS tx_count,
       SUM(t.amount)                       AS total_amount,
       SUM(t.fee)                          AS total_fees
FROM   transactions t
JOIN   transaction_categories c ON c.category_id = t.category_id
WHERE  c.direction = 'debit'
GROUP  BY month, c.category_name
ORDER  BY month, total_amount DESC;


SELECT u.full_name,
       COUNT(*)         AS num_transactions,
       SUM(t.amount)    AS total_received
FROM   users u
JOIN   transaction_participants tp ON tp.user_id = u.user_id AND tp.role = 'receiver'
JOIN   transactions t              ON t.transaction_id = tp.transaction_id
WHERE  u.user_type = 'customer'
GROUP  BY u.user_id
ORDER  BY total_received DESC
LIMIT  10;

UPDATE transactions
SET    status = 'reversed'
WHERE  external_tx_ref = '14103506143';

DELETE FROM system_logs
WHERE  log_level = 'DEBUG' AND created_at < (NOW() - INTERVAL 90 DAY);

SELECT 'users' AS tbl, COUNT(*) AS n FROM users UNION ALL
SELECT 'transaction_categories',   COUNT(*) FROM transaction_categories UNION ALL
SELECT 'raw_sms',                  COUNT(*) FROM raw_sms UNION ALL
SELECT 'transactions',             COUNT(*) FROM transactions UNION ALL
SELECT 'transaction_participants', COUNT(*) FROM transaction_participants UNION ALL
SELECT 'system_logs',              COUNT(*) FROM system_logs;
