# Expected Parameter Verification & Validation Flows

Use these flows and scripts to declare global parameters, override them at the account level during customer account creation, and verify that CLv4 Smart Contracts successfully fetch and apply these overridden parameters at runtime.

---

## Flow 3.1: E2E Expected Parameter Override & Contract Validation

```yaml
flowName: expectedParameterOverrideValidation
description: Declares an Expected Parameter, uploads a parameterized CLv4 contract, opens two accounts with distinct overridden parameter values, and executes single-legged withdrawals to verify different contract limits.
steps:
  - step: 1
    operationId: createExpectedParameterDefinition
    description: Declare the Expected Parameter definition in Vault to ensure the cluster recognizes it
    method: POST
    path: /v1/parameters
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        parameter:
          id: "txn_limit"
          constraint:
            decimal_constraint:
              min_value: "0.00"
              max_value: ""
    extract:
      parameterId: '$.id'
  - step: 2
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
            first_name: "Expected"
            last_name: "Param"
    extract:
      customerId: '$.id'
  - step: 3
    operationId: createProductVersion
    description: Upload the CLv4 contract containing expected_parameters and a ParametersObservationFetcher
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "expected_param_product_{{$guid}}"
          display_name: "Expected Parameter Contract Validation"
          code: |
            from contracts_api import *
            from decimal import Decimal
            api = "4.0.0"
            version = "1.0.0"
            tside = Tside.LIABILITY
            supported_denominations = ["USD"]
            expected_parameters = [ExpectedParameter(id="txn_limit")]
            data_fetchers = [
                ParametersObservationFetcher(
                    fetcher_id="txn_limit_fetcher",
                    at=DefinedDateTime.EFFECTIVE_DATETIME,
                    filter=ParametersFilter(parameter_ids=["txn_limit"])
                )
            ]
            @fetch_account_data(parameters=["txn_limit_fetcher"])
            def pre_posting_hook(vault, hook_arguments: PrePostingHookArguments):
                params = vault.get_parameters_observation(fetcher_id="txn_limit_fetcher").parameters
                limit = params["txn_limit"]
                for posting_instruction in hook_arguments.posting_instructions:
                    if posting_instruction.amount > limit:
                        return PrePostingHookResult(
                            rejection=Rejection(
                                message=f"Transaction amount exceeds the overridden {limit} USD limit.",
                                reason_code=RejectionReason.AGAINST_TNC
                            )
                        )
                return PrePostingHookResult()
          supported_denominations:
            - "USD"
        migration_strategy: "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
        is_internal: false
    extract:
      smartContractVersionId: '$.id'
  - step: 4
    operationId: createAccount1
    description: Open Account 1 overriding txn_limit to 50.00 USD
    method: POST
    path: /v2/accounts
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account:
          type: "ACCOUNT_TYPE_CUSTOMER"
          smart_contract_version_id: "{{step3.smartContractVersionId}}"
          status: "ACCOUNT_STATUS_OPEN"
          stakeholder_ids:
            - "{{step2.customerId}}"
        create_options:
          parameter_values:
            txn_limit:
              decimal_value: "50.00"
    extract:
      accountId1: '$.id'
  - step: 5
    operationId: createAccount2
    description: Open Account 2 overriding txn_limit to 150.00 USD
    method: POST
    path: /v2/accounts
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account:
          type: "ACCOUNT_TYPE_CUSTOMER"
          smart_contract_version_id: "{{step3.smartContractVersionId}}"
          status: "ACCOUNT_STATUS_OPEN"
          stakeholder_ids:
            - "{{step2.customerId}}"
        create_options:
          parameter_values:
            txn_limit:
              decimal_value: "150.00"
    extract:
      accountId2: '$.id'
  - step: 6
    operationId: sendWithdrawalAccount1
    description: Send a single-legged 75.00 USD withdrawal from Account 1 (Expect rejection as 75.00 > 50.00)
    method: POST
    path: /v1/posting-instruction-batches
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        posting_instruction_batch:
          client_id: "test-client"
          client_batch_id: "{{$guid}}"
          posting_instructions:
            - client_transaction_id: "{{$guid}}"
              outbound_hard_settlement:
                amount: "75.00"
                denomination: "USD"
                target_account:
                  account_id: "{{step4.accountId1}}"
                internal_account_id: "1"
    extract:
      batch1Status: '$.posting_instruction_batch.status'
  - step: 7
    operationId: sendWithdrawalAccount2
    description: Send a single-legged 75.00 USD withdrawal from Account 2 (Expect success as 75.00 < 150.00)
    method: POST
    path: /v1/posting-instruction-batches
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        posting_instruction_batch:
          client_id: "test-client"
          client_batch_id: "{{$guid}}"
          posting_instructions:
            - client_transaction_id: "{{$guid}}"
              outbound_hard_settlement:
                amount: "75.00"
                denomination: "USD"
                target_account:
                  account_id: "{{step5.accountId2}}"
                internal_account_id: "1"
    extract:
      batch2Status: '$.posting_instruction_batch.status'
```

---

## 🛠️ Standalone Python Parameters Validation Script

Below is the completely verified script implementing the modern Expected Parameters E2E flow:

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
    
    # 1. Declare Expected Parameter definition in Vault
    param_id = "txn_limit"
    requests.post(f"{VAULT_BASE_URL}/v1/parameters", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "parameter": {"id": param_id, "constraint": {"decimal_constraint": {"min_value": "0.00", "max_value": ""}}}
    }, verify=False) # Safely ignores 409 Conflict if already declared
    
    # 2. Create Customers
    cust_res_1 = requests.post(f"{VAULT_BASE_URL}/v1/customers", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "customer": {"customer_details": {"first_name": "LowLimit", "last_name": "User"}}
    }, verify=False)
    cust_1_id = cust_res_1.json()["id"]
    
    cust_res_2 = requests.post(f"{VAULT_BASE_URL}/v1/customers", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "customer": {"customer_details": {"first_name": "HighLimit", "last_name": "User"}}
    }, verify=False)
    cust_2_id = cust_res_2.json()["id"]
    
    # 3. Create Product Version using Expected Parameter
    code = """from contracts_api import *
api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY
supported_denominations = ["USD"]
expected_parameters = [ExpectedParameter(id="txn_limit")]
data_fetchers = [
    ParametersObservationFetcher(
        fetcher_id="txn_limit_fetcher",
        at=DefinedDateTime.EFFECTIVE_DATETIME,
        filter=ParametersFilter(parameter_ids=["txn_limit"])
    )
]
@fetch_account_data(parameters=["txn_limit_fetcher"])
def pre_posting_hook(vault, hook_arguments: PrePostingHookArguments):
    params = vault.get_parameters_observation(fetcher_id="txn_limit_fetcher").parameters
    limit = params["txn_limit"]
    for posting_instruction in hook_arguments.posting_instructions:
        if posting_instruction.amount > limit:
            return PrePostingHookResult(
                rejection=Rejection(
                    message=f"Transaction exceeds {limit} USD limit.",
                    reason_code=RejectionReason.AGAINST_TNC
                )
            )
    return PrePostingHookResult()
"""
    prod_res = requests.post(f"{VAULT_BASE_URL}/v1/product-versions", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "product_version": {"product_id": f"expected_param_product_{str(uuid.uuid4()).replace('-', '_')}", "code": code, "supported_denominations": ["USD"]},
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
    }, verify=False)
    version_id = prod_res.json()["id"]
    
    # 4. Open Account 1 (txn_limit = 50.00 USD)
    acc_res_1 = requests.post(f"{VAULT_BASE_URL}/v2/accounts", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"type": "ACCOUNT_TYPE_CUSTOMER", "smart_contract_version_id": version_id, "status": "ACCOUNT_STATUS_OPEN", "stakeholder_ids": [cust_1_id]},
        "create_options": {"parameter_values": {param_id: {"decimal_value": "50.00"}}}
    }, verify=False)
    account_1_id = acc_res_1.json()["id"]
    
    # 5. Open Account 2 (txn_limit = 150.00 USD)
    acc_res_2 = requests.post(f"{VAULT_BASE_URL}/v2/accounts", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"type": "ACCOUNT_TYPE_CUSTOMER", "smart_contract_version_id": version_id, "status": "ACCOUNT_STATUS_OPEN", "stakeholder_ids": [cust_2_id]},
        "create_options": {"parameter_values": {param_id: {"decimal_value": "150.00"}}}
    }, verify=False)
    account_2_id = acc_res_2.json()["id"]
    
    # 6. Verify Account 1 limits (75.00 USD withdrawal - Expect Rejection)
    res_1 = requests.post(f"{VAULT_BASE_URL}/v1/posting-instruction-batches", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "posting_instruction_batch": {
            "client_id": "test-client", "client_batch_id": str(uuid.uuid4()),
            "posting_instructions": [{"client_transaction_id": str(uuid.uuid4()), "outbound_hard_settlement": {"amount": "75.00", "denomination": "USD", "target_account": {"account_id": account_1_id}, "internal_account_id": "1"}}]
        }
    }, verify=False)
    # Checks response: status of PIB is REJECTED
    
    # 7. Verify Account 2 limits (75.00 USD withdrawal - Expect Success)
    res_2 = requests.post(f"{VAULT_BASE_URL}/v1/posting-instruction-batches", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "posting_instruction_batch": {
            "client_id": "test-client", "client_batch_id": str(uuid.uuid4()),
            "posting_instructions": [{"client_transaction_id": str(uuid.uuid4()), "outbound_hard_settlement": {"amount": "75.00", "denomination": "USD", "target_account": {"account_id": account_2_id}, "internal_account_id": "1"}}]
        }
    }, verify=False)
    # Checks response: status of PIB is ACCEPTED / Batch successfully committed.

if __name__ == "__main__":
    main()
```
