# Product Version Conversion & Account Upgrades

Use these flows and scripts to migrate/convert existing customer accounts to new smart contract versions in a fully synchronous operation.

---

## Flow 2.1: Synchronous Account Product Upgrade

```yaml
flowName: synchronousAccountProductUpgrade
description: Creates a customer, uploads Product Version 1.0.0, opens a customer account, uploads Product Version 2.0.0, and executes a fully synchronous account conversion to Version 2.0.0.
steps:
  - step: 1
    operationId: createCustomer
    description: Create the stakeholder customer
    method: POST
    path: /v1/customers
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        customer:
          customer_details:
            title: "Mr"
            first_name: "Conversion"
            last_name: "Tester"
    extract:
      customerId: '$.id'
  - step: 2
    operationId: createProductVersionV1
    description: Upload Product Version 1.0.0 (Smart Contract V4)
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "upgrade_product_{{$guid}}"
          display_name: "Conversion Demo V1"
          code: |
            from contracts_api import Tside
            api = "4.0.0"
            version = "1.0.0"
            tside = Tside.LIABILITY
            supported_denominations = ["USD"]
          supported_denominations:
            - "USD"
        migration_strategy: "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
        is_internal: false
    extract:
      smartContractVersion1Id: '$.id'
      productId: '$.product_id'
  - step: 3
    operationId: createAccount
    description: Open the customer's v2 account under Product Version 1.0.0
    method: POST
    path: /v2/accounts
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account:
          type: "ACCOUNT_TYPE_CUSTOMER"
          smart_contract_version_id: "{{step2.smartContractVersion1Id}}"
          status: "ACCOUNT_STATUS_OPEN"
          stakeholder_ids:
            - "{{step1.customerId}}"
    extract:
      accountId: '$.id'
  - step: 4
    operationId: createProductVersionV2
    description: Upload Product Version 2.0.0 as a new version of the existing Product ID, including conversion_hook
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "{{step2.productId}}"
          display_name: "Conversion Demo V2"
          code: |
            from contracts_api import Tside, ConversionHookArguments, ConversionHookResult
            api = "4.0.0"
            version = "2.0.0"
            tside = Tside.LIABILITY
            supported_denominations = ["USD"]
            def conversion_hook(vault, hook_arguments: ConversionHookArguments) -> ConversionHookResult:
                return ConversionHookResult()
          supported_denominations:
            - "USD"
        migration_strategy: "PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION"
        is_internal: false
    extract:
      smartContractVersion2Id: '$.id'
  - step: 5
    operationId: upgradeAccount
    description: Upgrade the account to Product Version 2.0.0. The upgrade is fully SYNCHRONOUS and returns the converted account immediately in the response body.
    method: PUT
    path: /v2/accounts/{{step3.accountId}}
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account:
          id: "{{step3.accountId}}"
          smart_contract_version_id: "{{step4.smartContractVersion2Id}}"
        update_mask:
          paths:
            - "smart_contract_version_id"
    extract:
      updatedVersionId: '$.smart_contract_version_id'
```

---

## 🛠️ Standalone Python Conversion Script

Below is the verified standalone Python script that performs the fully synchronous account conversion:

```python
import uuid
import json
import requests

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

VAULT_BASE_URL = "https://core-api.core-development.tmachine.io"
JWT_SERVICE_URL = "https://jwt-service.core-development.tmachine.io/token"

def get_vault_jwt():
    res = requests.post(JWT_SERVICE_URL, json={
        "kid": "default",
        "claims": {"scp": ["core:read", "core:write", "core:execute"]}
    }, verify=False)
    res.raise_for_status()
    return res.json()["token"]

def main():
    token = get_vault_jwt()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    
    # Create Customer
    cust_res = requests.post(f"{VAULT_BASE_URL}/v1/customers", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "customer": {"customer_details": {"first_name": "Conversion", "last_name": "Tester"}}
    }, verify=False)
    cust_id = cust_res.json()["id"]
    
    # Upload Product Version 1.0.0
    product_id = f"upgrade_product_{str(uuid.uuid4()).replace('-', '_')}"
    code_v1 = "from contracts_api import Tside\napi = '4.0.0'\nversion = '1.0.0'\ntside = Tside.LIABILITY\nsupported_denominations = ['USD']"
    prod_res_v1 = requests.post(f"{VAULT_BASE_URL}/v1/product-versions", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "product_version": {"product_id": product_id, "code": code_v1, "supported_denominations": ["USD"]},
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
    }, verify=False)
    version_1_id = prod_res_v1.json()["id"]
    
    # Open Customer Account
    acc_res = requests.post(f"{VAULT_BASE_URL}/v2/accounts", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"type": "ACCOUNT_TYPE_CUSTOMER", "smart_contract_version_id": version_1_id, "status": "ACCOUNT_STATUS_OPEN", "stakeholder_ids": [cust_id]}
    }, verify=False)
    account_id = acc_res.json()["id"]
    
    # Upload Product Version 2.0.0
    code_v2 = "from contracts_api import Tside, ConversionHookArguments, ConversionHookResult\napi = '4.0.0'\nversion = '2.0.0'\ntside = Tside.LIABILITY\nsupported_denominations = ['USD']\ndef conversion_hook(vault, hook_arguments: ConversionHookArguments) -> ConversionHookResult:\n    return ConversionHookResult()"
    prod_res_v2 = requests.post(f"{VAULT_BASE_URL}/v1/product-versions", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "product_version": {"product_id": product_id, "code": code_v2, "supported_denominations": ["USD"]},
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION"
    }, verify=False)
    version_2_id = prod_res_v2.json()["id"]
    
    # Request conversion (Sync PUT request)
    conv_res = requests.put(f"{VAULT_BASE_URL}/v2/accounts/{account_id}", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"id": account_id, "smart_contract_version_id": version_2_id},
        "update_mask": {"paths": ["smart_contract_version_id"]}
    }, verify=False)
    
    result = conv_res.json()
    print(f"🎉 Conversion response received synchronously:")
    print(f"   - Upgraded Smart Contract Version ID: {result.get('smart_contract_version_id')}")

if __name__ == "__main__":
    main()
```
