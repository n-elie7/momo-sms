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
) COMMENT='Distinct parties involved in MoMo transactions';

CREATE TABLE transaction_categories (
    category_id     INT             AUTO_INCREMENT PRIMARY KEY,
    category_code   VARCHAR(40)     NOT NULL                        COMMENT 'Machine code, e.g. PAYMENT_CODE',
    category_name   VARCHAR(80)     NOT NULL                        COMMENT 'Human label',
    direction       ENUM('credit','debit','info')
                    NOT NULL                                        COMMENT 'credit = money in, debit = money out, info = non-financial (OTP)',
    description     TEXT            NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_cat_code UNIQUE (category_code)
) COMMENT='Catalog of MoMo transaction types';

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
) COMMENT='Verbatim SMS records (audit trail)';

    user_id         INT             AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100)    NOT NULL,
    phone_number    VARCHAR(15)     NULL UNIQUE,
    account_number  VARCHAR(20)     NULL,
    user_type       ENUM('customer','agent','business','self')
                    NOT NULL        DEFAULT 'customer',
    is_anonymized   BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_name_len CHECK (CHAR_LENGTH(full_name) >= 1)
);

CREATE TABLE transaction_categories (
    category_id     INT             AUTO_INCREMENT PRIMARY KEY,
    category_code   VARCHAR(40)     NOT NULL UNIQUE,
    category_name   VARCHAR(80)     NOT NULL,
    direction       ENUM('credit','debit','info')
                    NOT NULL,
    description     TEXT            NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
);

CREATE TABLE raw_sms (
    raw_sms_id      INT             AUTO_INCREMENT PRIMARY KEY,
    sms_address     VARCHAR(40)     NULL,
    sms_date_ms     BIGINT          NOT NULL,
    readable_date   VARCHAR(50)     NULL,
    body            TEXT            NOT NULL,
    body_hash       CHAR(64)        NOT NULL UNIQUE,
    parse_status    ENUM('pending','parsed','failed','ignored')
                    NOT NULL        DEFAULT 'pending',
    ingested_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_raw_date CHECK (sms_date_ms > 0)
);



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

    external_tx_ref     VARCHAR(40)     NULL UNIQUE,
    financial_tx_id     VARCHAR(40)     NULL,
    category_id         INT             NOT NULL,
    amount              DECIMAL(15,2)   NOT NULL,
    fee                 DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    currency            CHAR(3)         NOT NULL DEFAULT 'RWF',
    new_balance         DECIMAL(15,2)   NULL,
    tx_timestamp        DATETIME        NOT NULL,
    status              ENUM('completed','failed','reversed')
                        NOT NULL        DEFAULT 'completed',
    token               VARCHAR(50)     NULL,
    message_note        TEXT            NULL,

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

) COMMENT='Parsed MoMo transactions (fact table)';

CREATE TABLE transaction_participants (
    participant_id  INT             AUTO_INCREMENT PRIMARY KEY,

    transaction_id  INT             NOT NULL,
    user_id         INT             NOT NULL,
    role            ENUM('sender','receiver','agent','merchant')
                    NOT NULL                                        COMMENT 'Role of this user in this transaction',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tp_combo UNIQUE (transaction_id, user_id, role),

    transaction_id  INT             NOT NULL UNIQUE,
    user_id         INT             NOT NULL UNIQUE,
    role            ENUM('sender','receiver','agent','merchant')
                    NOT NULL UNIQUE,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tp_tx
        FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tp_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE

) COMMENT='M:N junction — who participated in which transaction and how';

CREATE TABLE system_logs (
    log_id          INT             AUTO_INCREMENT PRIMARY KEY,
    raw_sms_id      INT             NULL,
    transaction_id  INT             NULL,
    log_level       ENUM('INFO','WARN','ERROR','DEBUG')
                    NOT NULL,

    stage           VARCHAR(40)     NOT NULL                        COMMENT 'e.g. ingest, parse, categorize, persist',
    message         TEXT            NOT NULL,
    details_json    JSON            NULL                            COMMENT 'Structured context (regex match, fields, etc.)',

    stage           VARCHAR(40)     NOT NULL,
    message         TEXT            NOT NULL,
    details_json    JSON            NULL,

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_rawsms
        FOREIGN KEY (raw_sms_id) REFERENCES raw_sms(raw_sms_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_log_tx
        FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        ON DELETE SET NULL ON UPDATE CASCADE

) ENGINE=InnoDB COMMENT='Pipeline event log for data processing observability';

CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_name ON users(full_name);

CREATE INDEX idx_raw_status ON raw_sms(parse_status);
CREATE INDEX idx_raw_date ON raw_sms(sms_date_ms);

CREATE INDEX idx_tx_timestamp ON transactions(tx_timestamp);
CREATE INDEX idx_tx_category ON transactions(category_id);
CREATE INDEX idx_tx_status ON transactions(status);
CREATE INDEX idx_tx_finid ON transactions(financial_tx_id);

CREATE INDEX idx_tp_tx ON transaction_participants(transaction_id);
CREATE INDEX idx_tp_user ON transaction_participants(user_id);

CREATE INDEX idx_log_level ON system_logs(log_level);
CREATE INDEX idx_log_stage ON system_logs(stage);
CREATE INDEX idx_log_time ON system_logs(created_at);
