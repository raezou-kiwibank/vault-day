# Products & Smart Contracts API Reference

Quick, high-signal lookup card for compiling and uploading CLv4 Product Versions.

---

### 📝 POST /v1/product-versions (Create Product Version)
Compiles and uploads CLv4 smart contract code to the Vault cluster.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "product_version": {
    "product_id": "string (the custom product ID, e.g. my_savings_contract, required)",
    "display_name": "string (required)",
    "code": "string (raw CLv4 python code, required)",
    "supported_denominations": ["string (e.g. USD, GBP, required)"],
    "params": [
      {
        "name": "string (the template parameter ID defined in the contract, required if contract has template-level parameters)",
        "value": "string (template parameter default value, e.g. \"0\")"
      }
    ]
  },
  "migration_strategy": "string (strictly PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT or PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION, required)",
  "is_internal": "boolean (false for customer products, true for bank internal products, required)"
}
```
*Note 1: If the CLv4 smart contract defines non-optional, template-level parameters (e.g. `monthly_account_fee_application_hour` in standard operating account templates), they **MUST** be supplied with values inside the `"params"` array on creation. Omitting them will result in HTTP `400 Bad Request (INVALID_ARGUMENT)`.*

*Note 2: Uploading the very first version of a product requires `PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT`. Uploading a subsequent version update to an existing Product ID requires `PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION`.*

**Response Fields:**
*   `id`: `string` (The generated, auto-incremented integer string representing the version ID. **CRITICAL**: Use this version `id` string for all v2 Account openings!)
