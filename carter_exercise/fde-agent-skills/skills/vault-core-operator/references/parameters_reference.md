# Parameters & Value Hierarchies API Reference

Quick, high-signal lookup card for declaring parameters, setting global/account values, and hierarchy nodes.

---

## 💡 Expected Parameters (Preferred Modern Paradigm)
In modern CLv4 smart contracts, we **always prefer Expected Parameters** over old-style template/instance/global parameters wherever possible. 

### How Expected Parameters Work:
1.  **Define in Contract**: The contract declares its required parameter IDs in the metadata `expected_parameters = [ExpectedParameter(id="txn_limit")]`.
2.  **Declare in Vault**: The parameter ID must exist as a registered definition in the Vault cluster. Create/declare it via `POST /v1/parameters` (see below).
3.  **Populate Value**: Override values can be bound at account creation using `"create_options.parameter_values"` on `POST /v2/accounts` or at node level.
4.  **Fetch in Hook**: Access expected parameter values inside hooks via `@fetch_account_data` and a `ParametersObservationFetcher` or `ParametersIntervalFetcher` (e.g. `vault.get_parameters_observation(fetcher_id="...").parameters["txn_limit"]`).

---

## 🏛️ Legacy Parameters Compatibility (Instance, Template, Global)
Older smart contracts may still utilize legacy parameter configurations. Understand the structural differences:

### 1. Template Parameters:
*   **Context**: Defined at the product/contract level (constant across all accounts of this product).
*   **Filing Rule**: Must be supplied inside the `params` array inside the product version payload during `POST /v1/product-versions` (see `products_reference.md`).
*   **Access**: Accessed via name timeseries inside hooks: `vault.get_parameter_timeseries(name="param_name")`.

### 2. Instance Parameters:
*   **Context**: Configured uniquely per-account.
*   **Filing Rule**: Declared under the contract metadata `parameters = [Parameter(...)]` and populated under `"create_options.parameter_values"` on `POST /v2/accounts`.
*   **Access**: Accessed via name timeseries inside hooks.

---

### ⚙️ POST /v1/parameters (Create Expected/Instance Parameter Definition)
Registers a parameter definition in Vault. (Required for Expected Parameters, and for defining constraints on Instance/Global parameters).

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "parameter": {
    "id": "string (the parameter ID, e.g. txn_limit, required)",
    "constraint": {
      "decimal_constraint": {
        "min_value": "string (optional, inclusive, e.g. 0.00)",
        "max_value": "string (optional)"
      },
      "string_constraint": {
        "min_length": "integer (optional)",
        "max_length": "integer (optional)"
      }
    }
  }
}
```
*Note: If the parameter definition already exists on the cluster, this endpoint returns HTTP `409 Conflict`. Always safely catch 409 as a valid indicator of pre-existence.*

---

### 🔄 POST /v1/parameter-values (Create Parameter Value Override)
Updates or sets a parameter value for a specific owner (e.g. account, plan, hierarchy node) at a point in time.

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "parameter_value": {
    "parameter_id": "string (required)",
    "account_id": "string (optional, set when overriding on Account level)",
    "value": {
      "decimal_value": "string (decimal string format, required if decimal, e.g. \"150.00\")",
      "string_value": "string (optional)"
    },
    "effective_timestamp": "string (RFC3339 timestamp, optional)"
  }
}
```

---

### 🌳 POST /v1/parameter-value-hierarchy-nodes (Create Hierarchy Node)
Defines a node in a parameter value hierarchy (e.g. attaching branch-level rates that inherit fallback values).

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "parameter_value_hierarchy_node": {
    "id": "string (the node ID, e.g. branch_north, required)",
    "parent_id": "string (optional, parent hierarchy node ID)",
    "description": "string (optional)"
  }
}
```

---

### 🌐 POST /v1/global-parameters (Create Global Parameter Definition)
Registers a parameter that applies bank-wide (e.g. base interest rate or transactional currency).

**Request Payload:**
```json
{
  "request_id": "string (UUID, required)",
  "global_parameter": {
    "id": "string (the parameter ID, e.g. bank_base_rate, required)",
    "constraint": {
      "decimal_constraint": {
        "min_value": "string",
        "max_value": "string"
      }
    }
  }
}
```
