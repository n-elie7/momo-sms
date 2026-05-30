# MoMo Transactions API

**Base URL:** `http://localhost:8080`
**Data format:** JSON (`application/json`, UTF-8)
**Authentication:** HTTP Basic Auth on every request

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Status Codes](#2-status-codes)
3. [Transaction Object](#3-transaction-object)
4. [Endpoints](#4-endpoints)
   - [GET /transactions](#41-get-transactions)
   - [GET /transactions/{id}](#42-get-transactionsid)
   - [POST /transactions](#43-post-transactions)
   - [PUT /transactions/{id}](#44-put-transactionsid)
   - [DELETE /transactions/{id}](#45-delete-transactionsid)
5. [Security](#5-security)

---

## 1. Authentication

All endpoints require HTTP Basic Auth. Send these credentials with every request:

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `momo2024` |

The `Authorization` header looks like this:

```
Authorization: Basic YWRtaW46bW9tbzIwMjQ=
```

With `curl`, use the `-u` flag and it handles the encoding automatically:

```bash
curl -u admin:momo2024 http://localhost:8080/transactions
```

Any request without valid credentials gets a `401` back and nothing else runs.

---

## 2. Status Codes

| Code | Meaning               | When it happens                                          |
|------|-----------------------|----------------------------------------------------------|
| 200  | OK                    | GET, PUT, or DELETE completed successfully               |
| 201  | Created               | POST created a new record                                |
| 400  | Bad Request           | JSON is malformed, `body` field is missing, or a query param is invalid |
| 401  | Unauthorized          | Wrong credentials or `Authorization` header is missing   |
| 404  | Not Found             | The `{id}` in the URL does not exist                     |
| 405  | Method Not Allowed    | That HTTP method is not supported on that path           |
| 409  | Conflict              | POST was sent with an `id` that already exists           |
| 500  | Internal Server Error | Something went wrong on the server side                  |

---

## 3. Transaction Object

Every endpoint that returns a transaction uses this structure:

| Field             | Type           | Description                                                        |
|-------------------|----------------|--------------------------------------------------------------------|
| `id`              | string         | Unique ID, e.g. `txn-0001691`                                      |
| `tx_category`     | string         | Category detected from the SMS body (see list below)               |
| `amount`          | number or null | Transaction amount in RWF                                          |
| `fee`             | number or null | Fee in RWF, if the SMS mentions one                                |
| `balance`         | number or null | Account balance after the transaction, if the SMS mentions it      |
| `sender`          | string or null | Name or phone number of who sent the money                         |
| `receiver`        | string or null | Name or phone number of who received the money                     |
| `financial_tx_id` | string or null | MTN's transaction ID, pulled from the SMS text                     |
| `timestamp`       | string         | ISO-8601 UTC time, converted from the XML date attribute           |
| `readable_date`   | string         | Date as it appears in the XML, e.g. `16 Jan 2025 12:13:29 AM`     |
| `body`            | string         | The original SMS text, unchanged                                   |
| `raw_date`        | integer        | Epoch milliseconds — used for sorting, do not change this          |

**`tx_category` values:**

| Value                  | What it means                                   |
|------------------------|-------------------------------------------------|
| `payment_sent`         | Payment sent to a person or merchant            |
| `transfer_sent`        | Peer-to-peer transfer via `*165*S*`             |
| `bank_deposit`         | Cash or bank deposit into MoMo via `*113*R*`    |
| `received`             | Money received from another MoMo user           |
| `airtime_cashpower`    | Airtime or MTN Cash Power purchase via `*162*`  |
| `direct_payment_debit` | Business debit via `*164*S*`                    |
| `bank_transfer_out`    | Transfer from MoMo to a bank account            |
| `bundle`               | Data or voice bundle purchase                   |
| `withdrawal`           | Cash withdrawal through an agent                |
| `reversal`             | A transaction that was reversed                 |
| `failed_txn`           | A transaction that failed                       |
| `otp`                  | One-time password SMS — no financial data       |
| `other`                | SMS format not matched by any known pattern     |

---

## 4. Endpoints

---

### 4.1 GET /transactions

Returns all transactions, sorted newest first, in pages.

**Query parameters**

| Parameter     | Type    | Default | Description                                         |
|---------------|---------|---------|-----------------------------------------------------|
| `page`        | integer | `1`     | Which page to return (starts at 1)                  |
| `page_size`   | integer | `100`   | How many records per page (max 500)                 |
| `tx_category` | string  | —       | Only return records of this category                |

**Request**

```bash
curl -u admin:momo2024 \
     "http://localhost:8080/transactions?page=1&page_size=2"
```

**Response — 200 OK**

```json
{
  "data": [
    {
      "id": "txn-0001691",
      "tx_category": "payment_sent",
      "amount": 24900.0,
      "fee": 0.0,
      "balance": 75100.0,
      "sender": null,
      "receiver": "Robert Brown",
      "financial_tx_id": "37832903831",
      "timestamp": "2025-01-15T22:13:29+00:00",
      "readable_date": "16 Jan 2025 12:13:29 AM",
      "body": "TxId: 37832903831. Your payment of 24,900 RWF to Robert Brown 23478 has been completed at 2025-01-15 22:13:22. Your new balance: 75,100 RWF. Fee was 0 RWF.",
      "raw_date": 1736979209935
    },
    {
      "id": "txn-0001690",
      "tx_category": "payment_sent",
      "amount": 1500.0,
      "fee": 0.0,
      "balance": 3500.0,
      "sender": null,
      "receiver": "Samuel Carter",
      "financial_tx_id": "51350491173",
      "timestamp": "2025-01-15T18:35:06+00:00",
      "readable_date": "15 Jan 2025 8:35:06 PM",
      "body": "TxId: 51350491173. Your payment of 1,500 RWF to Samuel Carter 58769 has been completed at 2025-01-15 18:35:00. Your new balance: 3,500 RWF. Fee was 0 RWF.",
      "raw_date": 1736966106920
    }
  ],
  "total": 1691,
  "page": 1,
  "page_size": 2,
  "pages": 846
}
```

**Filtered request**

```bash
curl -u admin:momo2024 \
     "http://localhost:8080/transactions?tx_category=received&page_size=5"
```

**Errors**

| Code | Response body                                      | Reason                        |
|------|----------------------------------------------------|-------------------------------|
| 400  | `{"error": "Invalid page_size", "status": 400}`    | Param is not a valid integer  |
| 401  | `{"error": "Unauthorized", "status": 401}`         | Wrong or missing credentials  |

---

### 4.2 GET /transactions/{id}

Returns one transaction by its ID.

**Path parameter**

| Parameter | Type   | Description                          |
|-----------|--------|--------------------------------------|
| `id`      | string | The transaction ID, e.g. `txn-0001691` |

**Request**

```bash
curl -u admin:momo2024 \
     "http://localhost:8080/transactions/txn-0001691"
```

**Response — 200 OK**

```json
{
  "id": "txn-0001691",
  "tx_category": "payment_sent",
  "amount": 24900.0,
  "fee": 0.0,
  "balance": 75100.0,
  "sender": null,
  "receiver": "Robert Brown",
  "financial_tx_id": "37832903831",
  "timestamp": "2025-01-15T22:13:29+00:00",
  "readable_date": "16 Jan 2025 12:13:29 AM",
  "body": "TxId: 37832903831. Your payment of 24,900 RWF to Robert Brown 23478 has been completed at 2025-01-15 22:13:22. Your new balance: 75,100 RWF. Fee was 0 RWF.",
  "raw_date": 1736979209935
}
```

**Errors**

| Code | Response body                                        | Reason                       |
|------|------------------------------------------------------|------------------------------|
| 401  | `{"error": "Unauthorized", "status": 401}`           | Wrong or missing credentials |
| 404  | `{"error": "Transaction not found", "status": 404}`  | ID does not exist            |

---

### 4.3 POST /transactions

Adds a new transaction. Only `body` is required — every other field is read from the SMS text automatically if you leave it out.

**Request body fields**

| Field             | Type   | Required | Description                                               |
|-------------------|--------|----------|-----------------------------------------------------------|
| `body`            | string | Yes      | The SMS text. All financial fields are parsed from this.  |
| `id`              | string | No       | Custom ID. A UUID is generated if not provided.           |
| `tx_category`     | string | No       | Overrides the category detected from the body             |
| `amount`          | number | No       | Overrides the amount detected from the body               |
| `fee`             | number | No       | Overrides the fee detected from the body                  |
| `balance`         | number | No       | Overrides the balance detected from the body              |
| `sender`          | string | No       | Overrides the sender detected from the body               |
| `receiver`        | string | No       | Overrides the receiver detected from the body             |
| `financial_tx_id` | string | No       | Overrides the MTN transaction ID detected from the body   |
| `timestamp`       | string | No       | ISO-8601 string. Defaults to current UTC time if omitted. |
| `readable_date`   | string | No       | Human-readable date label                                 |

**Request**

```bash
curl -u admin:momo2024 \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{
           "body": "You have received 15000 RWF from Jane Smith (*********013) on your mobile money account at 2024-06-01 09:00:00. Message from sender: . Your new balance:20000 RWF. Financial Transaction Id: 11122233344."
         }' \
     "http://localhost:8080/transactions"
```

**Response — 201 Created**

```json
{
  "id": "a3f1c920-7d4e-4b2a-9c8e-1d2f3e4a5b6c",
  "tx_category": "received",
  "amount": 15000.0,
  "fee": null,
  "balance": 20000.0,
  "sender": "Jane Smith",
  "receiver": null,
  "financial_tx_id": "11122233344",
  "timestamp": "2024-06-01T07:00:00+00:00",
  "readable_date": "",
  "body": "You have received 15000 RWF from Jane Smith (*********013) on your mobile money account at 2024-06-01 09:00:00. Message from sender: . Your new balance:20000 RWF. Financial Transaction Id: 11122233344.",
  "raw_date": 1748678400000
}
```

**Errors**

| Code | Response body                                                  | Reason                               |
|------|----------------------------------------------------------------|--------------------------------------|
| 400  | `{"error": "'body' is required...", "status": 400}`            | body field is missing or empty       |
| 400  | `{"error": "Invalid JSON body", "status": 400}`                | Request body is not valid JSON       |
| 401  | `{"error": "Unauthorized", "status": 401}`                     | Wrong or missing credentials         |
| 409  | `{"error": "Transaction 'x' already exists", "status": 409}`   | The given id already exists          |

---

### 4.4 PUT /transactions/{id}

Updates fields on an existing transaction. Only the fields you send are changed — everything else stays the same. `id` and `raw_date` cannot be changed and are ignored even if you include them.

If you update `body`, any financial field you did not include in the request is re-read from the new body text automatically.

**Path parameter**

| Parameter | Type   | Description                       |
|-----------|--------|-----------------------------------|
| `id`      | string | ID of the transaction to update   |

**Writable fields:**
`tx_category`, `amount`, `fee`, `balance`, `sender`, `receiver`, `financial_tx_id`, `timestamp`, `readable_date`, `body`

**Request**

```bash
curl -u admin:momo2024 \
     -X PUT \
     -H "Content-Type: application/json" \
     -d '{
           "fee": 100.0,
           "receiver": "Jane Smith"
         }' \
     "http://localhost:8080/transactions/txn-0001691"
```

**Response — 200 OK**

```json
{
  "id": "txn-0001691",
  "tx_category": "payment_sent",
  "amount": 24900.0,
  "fee": 100.0,
  "balance": 75100.0,
  "sender": null,
  "receiver": "Jane Smith",
  "financial_tx_id": "37832903831",
  "timestamp": "2025-01-15T22:13:29+00:00",
  "readable_date": "16 Jan 2025 12:13:29 AM",
  "body": "TxId: 37832903831. Your payment of 24,900 RWF to Robert Brown 23478 has been completed at 2025-01-15 22:13:22. Your new balance: 75,100 RWF. Fee was 0 RWF.",
  "raw_date": 1736979209935
}
```

**Errors**

| Code | Response body                                        | Reason                        |
|------|------------------------------------------------------|-------------------------------|
| 400  | `{"error": "Invalid JSON body", "status": 400}`      | Request body is not valid JSON |
| 401  | `{"error": "Unauthorized", "status": 401}`           | Wrong or missing credentials  |
| 404  | `{"error": "Transaction not found", "status": 404}`  | ID does not exist             |

---

### 4.5 DELETE /transactions/{id}

Removes a transaction permanently from memory.

Note: the store is in-memory only. The record is not removed from the XML file, so it comes back if the server restarts.

**Path parameter**

| Parameter | Type   | Description                      |
|-----------|--------|----------------------------------|
| `id`      | string | ID of the transaction to delete  |

**Request**

```bash
curl -u admin:momo2024 \
     -X DELETE \
     "http://localhost:8080/transactions/txn-0001691"
```

**Response — 200 OK**

```json
{
  "message": "Transaction txn-0001691 deleted successfully.",
  "status": 200
}
```

**Errors**

| Code | Response body                                        | Reason                       |
|------|------------------------------------------------------|------------------------------|
| 401  | `{"error": "Unauthorized", "status": 401}`           | Wrong or missing credentials |
| 404  | `{"error": "Transaction not found", "status": 404}`  | ID does not exist            |

---

## 5. Security

### Why Basic Auth is a problem

Every request sends the username and password, encoded in Base64 but not encrypted. Anyone who can intercept the HTTP traffic can decode it in seconds. The credentials are also static — they never expire on their own, so if the password leaks the only fix is to change it manually and redeploy.

### Better options

**JWT (JSON Web Tokens)**
The user logs in once at a `/auth/login` endpoint and gets back a signed token with an expiry time. Every request after that sends only the token, not the password. When the token expires the user logs in again. Tokens can also be scoped — one token might have read-only access, another can write. This is the most practical upgrade for this project since it needs no external service.

**OAuth 2.0**
Used when you want third-party apps to access the API on behalf of a user — for example, a mobile app logging in with a Google account. More complex to set up but standard across the industry. Supports short-lived access tokens and refresh tokens that extend the session without re-entering a password.

**API Keys**
Each client gets a long random key, sent in a header like `X-API-Key`. Simpler than JWT, easier to rotate than a shared password, and can be tied to specific clients. Still needs HTTPS to be safe in transit.

For this project, JWT is the right next step. It fixes the core problem — credentials travelling with every request — without needing anything outside the standard Python library.

---

*MoMo SMS Data Processing API — ALU Software Engineering, 2024*