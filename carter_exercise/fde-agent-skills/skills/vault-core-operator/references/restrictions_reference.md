# Restrictions & Flags API Reference

Quick, high-signal lookup card for creating account-level flags, definitions, and active restriction sets.

---

### 🚩 POST /v1/flag-definitions (Create Flag Definition)
Declares a new active flag type in Vault (e.g. `CARD_LOST`, `SANCTIONED`, `VIP_CUSTOMER`).

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "flag_definition": {
    "id": "string (the flag ID, e.g. CARD_LOST, required)",
    "name": "string (optional)",
    "description": "string (optional)"
  }
}
```

---

### 📌 POST /v1/flags (Apply Flag to Account)
Applies a declared flag to an account to trigger contract logic or restriction hooks.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "flag": {
    "definition_id": "string (the target flag definition ID, required)",
    "account_id": "string (the customer account ID, required)",
    "expiry_timestamp": "string (RFC3339 timestamp, optional)",
    "description": "string (optional)"
  }
}
```

---

### 🛡️ POST /v1/restriction-set-definitions (Create Restriction Definition)
Defines a transactional block rule (e.g., blocking debit cards or international withdrawals).

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "restriction_set_definition": {
    "id": "string (the restriction ID, e.g. block_debits, required)",
    "description": "string (optional)"
  }
}
```

---

### 🔒 POST /v1/restriction-sets (Apply Restriction Set to Account)
Applies a restriction set to an account to enforce blocking rules.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "restriction_set": {
    "restriction_set_definition_id": "string (the restriction definition ID, required)",
    "account_id": "string (the customer account ID, required)",
    "expiry_timestamp": "string (RFC3339 timestamp, optional)"
  }
}
```
