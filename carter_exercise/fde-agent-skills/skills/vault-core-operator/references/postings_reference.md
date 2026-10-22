# Postings & Ingestion API Reference

Quick, high-signal lookup card for submitting posting batches, authorizations, captures, client setups, and future-dated postings.

---

### 💸 POST /v1/posting-instruction-batches (Create Posting Batch)
Main endpoint for posting instructions atomically to the ledger.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required for idempotency)",
  "posting_instruction_batch": {
    "client_id": "string (required, e.g. card-processor, bank-clearing)",
    "client_batch_id": "string (UUID, required)",
    "posting_instructions": [
      {
        "client_transaction_id": "string (required, unique per txn ID)",
        "value_timestamp": "string (RFC3339 timestamp, e.g. \"2026-06-25T12:00:00Z\", optional for future-dating)",
        "booking_timestamp": "string (RFC3339 timestamp, e.g. \"2026-06-25T12:00:00Z\", optional for future-dating)",
        "outbound_hard_settlement": {
          "amount": "string (decimal string format, e.g. \"10.50\", required)",
          "denomination": "string (e.g. USD, GBP)",
          "target_account": { "account_id": "string (customer account ID)" },
          "internal_account_id": "string (optional, defaults to \"1\")"
        },
        "inbound_hard_settlement": {
          "amount": "string",
          "denomination": "string",
          "target_account": { "account_id": "string" },
          "internal_account_id": "string (optional, defaults to \"1\")"
        },
        "transfer": {
          "amount": "string",
          "denomination": "string",
          "debtor_target_account": { "account_id": "string" },
          "creditor_target_account": { "account_id": "string" },
          "creditor_target_sub_account_id": "string (optional)",
          "creditor_target_account_address": "string (optional, defaults to DEFAULT)"
        },
        "outbound_authorisation": {
          "amount": "string",
          "denomination": "string",
          "target_account": { "account_id": "string" },
          "internal_account_id": "string (optional, defaults to \"1\")"
        },
        "settlement": {
          "amount": "string (optional, defaults to original auth amount)",
          "final": "boolean (true to release remainder of hold)"
        },
        "release": {
          "amount": "string (optional, releases part or whole hold)"
        }
      }
    ]
  }
}
```
*Note 1: Always pass amount fields as string decimal representations (e.g., `"10.50"`). Sending them as numbers (10.50) will break JSON parsing.*

*Note 2: For E2E tests, `"1"` is the pre-configured default Bank Central Clearing/Internal Account on core-development environments. Always use `"1"` for your `internal_account_id` contra-accounts to avoid ACCOUNT_NOT_FOUND rejections.*

*Note 3: In 2-Phase Postings (authorisation + settlement/release), the subsequent `settlement` or `release` instructions MUST reference the exact same `client_transaction_id` declared in the original `outbound_authorisation` payload.*

---

## 🔮 Future-Dated Postings Guidelines
Vault Core supports future-dating of transactions. Ensure you follow these strict rules to avoid ledger-level rejections:

### 1. Instruction-Level Placement Only
*   **CRITICAL**: `value_timestamp` and `booking_timestamp` **MUST** be specified at the **individual instruction level** (inside each item of the `posting_instructions` list, sibling to the instruction variant object).
*   **DO NOT** place `value_timestamp` or `booking_timestamp` at the root batch-level (`posting_instruction_batch`), which is fully deprecated on CLv4/modern environments and will cause a schema/validation failure.

### 2. The 90-Day System Boundary
*   **CRITICAL**: Both `value_timestamp` and `booking_timestamp` must **NOT** exceed **90 calendar days** in the future.
*   If a posting is future-dated over 90 days (e.g., trying to future-date by 3 calendar months + 1 day), the ledger will reject the transaction with a `MoreThanNinetyDaysInFuture` validation violation.

### 3. Timestamp Format
*   Always format the `value_timestamp` and `booking_timestamp` as valid **RFC3339 string timestamps** with UTC offset (e.g., `"2026-06-25T12:00:00Z"`).

---

### 🔌 POST /v1/postings-api-clients (Create Postings Client)
Registers an ingestion client which determines the Kafka topics and response routing paths.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "postings_api_client": {
    "id": "string (the client ID, e.g. card-processor, required)",
    "display_name": "string (optional)",
    "response_topic": "string (optional, e.g. card-responses)"
  }
}
```
*Note: If postings are rejected with "unauthorized client" errors, register your `client_id` (like `card-processor` or `test-client`) first using this endpoint.*
