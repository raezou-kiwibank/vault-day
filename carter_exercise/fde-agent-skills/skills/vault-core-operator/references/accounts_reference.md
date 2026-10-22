# Accounts & Customers API Reference

Quick, high-signal lookup card for Customer, Account, and Balance creation and retrieval.

---

### 👤 POST /v1/customers (Create Customer)
Creates a new customer record to act as an account stakeholder.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "customer": {
    "customer_details": {
      "title": "string (optional, e.g. Mr, Mrs)",
      "first_name": "string (required)",
      "last_name": "string (required)",
      "dob": "string (YYYY-MM-DD, optional)",
      "gender": "string (optional, e.g. MALE, FEMALE)",
      "nationality": "string (optional, ISO 2-letter, e.g. GB, US)",
      "email_address": "string (optional)",
      "mobile_phone_number": "string (optional)"
    }
  }
}
```
**Response Fields:**
*   `id`: `string` (The generated customer/stakeholder ID)

---

### 🏦 POST /v2/accounts (Create Account)
Opens a new customer or internal account.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "account": {
    "type": "string (strictly ACCOUNT_TYPE_CUSTOMER or ACCOUNT_TYPE_INTERNAL, required)",
    "smart_contract_version_id": "string (numeric string representing contract version, required for customer accounts)",
    "status": "string (strictly ACCOUNT_STATUS_OPEN or ACCOUNT_STATUS_PENDING, required for customer accounts)",
    "stakeholder_ids": ["string (customer IDs, optional)"]
  },
  "create_options": {
    "parameter_values": {
      "<parameter_id>": {
        "decimal_value": "string (decimal string format, e.g. \"50.00\", required)"
      }
    }
  }
}
```
*Note: Always pass instance parameter overrides under `create_options.parameter_values` as string decimal values (e.g., `"50.00"`). Sending raw numbers (50 or 50.00) will break JSON parsing in Vault's protobuf layer.*

**Response Fields:**
*   `id`: `string` (The generated account ID)

---

### 🔍 GET /v2/accounts:batchGet (Batch Retrieve Accounts)
Retrieves account configurations. *Note: Single-resource GET `/v2/accounts/{id}` is NOT implemented on v2.*

**Query Parameters:**
*   `ids`: `string` (Repeatable, e.g. `?ids=id_1&ids=id_2`, required)

**Response Fields:**
*   `accounts`: `map<string, Account>` (Keyed on Account ID)

---

### 📊 GET /v2/balances/live (Retrieve Live Balances)
Queries current live balances for an account. *Note: There is no root `/v2/balances` endpoint. Always query `/v2/balances/live`.*

**Query Parameters:**
*   `account_id`: `string` (required)
*   `page_size`: `integer` (strictly required, cannot be omitted or 0, e.g. `10`)

**Request Example:**
`GET https://core-api.core-development.tmachine.io/v2/balances/live?account_id=<id>&page_size=10`

**Response Fields:**
*   `balances`: `array` (List of balance objects with `amount`, `denomination`, `phase` [COMMITTED, PENDING_OUT, PENDING_IN], and `account_address`)

---

### ➕ POST /v1/sub-accounts (Create Sub-Account)
Creates a sub-account (pocket/savings envelope) linked to an existing parent account.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "sub_account": {
    "account_id": "string (parent account ID, required)",
    "type": "string (SAVE, SPEND, etc., must match contract sub_account_types, required)",
    "status": "string (SUB_ACCOUNT_STATUS_OPEN, required)"
  }
}
```
**Response Fields:**
*   `id`: `string` (The generated sub-account ID)
