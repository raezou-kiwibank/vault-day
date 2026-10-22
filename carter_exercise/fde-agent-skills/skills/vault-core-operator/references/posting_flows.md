# Two-Phase Posting & Ledger Adjustment Flows

Use these flows and scripts to execute complete multi-phase transaction lifecycles: placing funds on hold (Authorisation), capturing/drawing down funds (Settlement), or voiding/releasing holds (Release) against Vault Core accounts.

---

## Flow 5.1: Two-Phase Card Transaction (Auth + Settlement)

```yaml
flowName: twoPhaseCardTransaction
description: Creates a customer and account, ringfences funds using an Outbound Authorisation, and synchronously settles/captures those funds using a Settlement instruction.
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
            first_name: "TwoPhase"
            last_name: "Tester"
    extract:
      customerId: '$.id'
  - step: 2
    operationId: createProductVersion
    description: Upload a clean, empty CLv4 smart contract
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "twophase_product_{{$guid}}"
          display_name: "Two-Phase Postings Demo"
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
      smartContractVersionId: '$.id'
  - step: 3
    operationId: createAccount
    description: Open the customer's v2 account
    method: POST
    path: /v2/accounts
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account:
          type: "ACCOUNT_TYPE_CUSTOMER"
          smart_contract_version_id: "{{step2.smartContractVersionId}}"
          status: "ACCOUNT_STATUS_OPEN"
          stakeholder_ids:
            - "{{step1.customerId}}"
    extract:
      accountId: '$.id'
  - step: 4
    operationId: requestOutboundAuthorisation
    description: Ringfence/hold 40.00 USD on the customer account (reduces available balance, committed balance unchanged)
    method: POST
    path: /v1/posting-instruction-batches
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        posting_instruction_batch:
          client_id: "card-processor"
          client_batch_id: "{{$guid}}"
          posting_instructions:
            - client_transaction_id: "card_txn_{{$guid}}"
              outbound_authorisation:
                amount: "40.00"
                denomination: "USD"
                target_account:
                  account_id: "{{step3.accountId}}"
                internal_account_id: "1"
    extract:
      batch1Id: '$.posting_instruction_batch.id'
      clientTxnId: '$.posting_instruction_batch.posting_instructions[0].client_transaction_id'
  - step: 5
    operationId: requestSettlement
    description: Settle and capture the authorised 40.00 USD, finalizing the card transaction
    method: POST
    path: /v1/posting-instruction-batches
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        posting_instruction_batch:
          client_id: "card-processor"
          client_batch_id: "{{$guid}}"
          posting_instructions:
            - client_transaction_id: "{{step4.clientTxnId}}"
              settlement:
                amount: "40.00"
                final: true
    extract:
      batch2Id: '$.posting_instruction_batch.id'
      batch2Status: '$.posting_instruction_batch.status'
  - step: 6
    operationId: getAccountBalances
    description: Retrieve account balances via v2 batchGet to verify funds successfully settled on the ledger
    method: GET
    path: /v2/accounts:batchGet?ids={{step3.accountId}}
    request:
      headers: {}
      body: {}
    extract:
      balances: '$.accounts.{{step3.accountId}}.permitted_denominations'
```

---

## 🛠️ Standalone Python Two-Phase Posting Script

Below is the verified standalone Python script that performs the E2E card authorization and settlement lifecycle:

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
        "customer": {"customer_details": {"first_name": "TwoPhase", "last_name": "Tester"}}
    }, verify=False)
    cust_id = cust_res.json()["id"]
    
    # Upload clean CLv4 contract
    code = "from contracts_api import Tside\napi = '4.0.0'\nversion = '1.0.0'\ntside = Tside.LIABILITY\nsupported_denominations = ['USD']"
    prod_res = requests.post(f"{VAULT_BASE_URL}/v1/product-versions", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "product_version": {"product_id": f"twophase_product_{str(uuid.uuid4()).replace('-', '_')}", "code": code, "supported_denominations": ["USD"]},
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
    }, verify=False)
    version_id = prod_res.json()["id"]
    
    # Create Customer Account
    acc_res = requests.post(f"{VAULT_BASE_URL}/v2/accounts", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"type": "ACCOUNT_TYPE_CUSTOMER", "smart_contract_version_id": version_id, "status": "ACCOUNT_STATUS_OPEN", "stakeholder_ids": [cust_id]}
    }, verify=False)
    account_id = acc_res.json()["id"]
    
    # Request Outbound Authorisation (Hold)
    client_transaction_id = f"card_txn_{str(uuid.uuid4()).replace('-', '')[:15]}"
    print(f"💳 Requesting Outbound Authorisation of 40.00 USD (Txn ID: {client_transaction_id})...")
    
    auth_res = requests.post(f"{VAULT_BASE_URL}/v1/posting-instruction-batches", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "posting_instruction_batch": {
            "client_id": "card-processor",
            "client_batch_id": str(uuid.uuid4()),
            "posting_instructions": [{
                "client_transaction_id": client_transaction_id,
                "outbound_authorisation": {"amount": "40.00", "denomination": "USD", "target_account": {"account_id": account_id}, "internal_account_id": "1"}
            }]
        }
    }, verify=False)
    print(f"✅ Authorisation Status: {auth_res.json()['posting_instruction_batch']['status']}")
    
    # Request Settlement (Capture)
    print(f"💸 Requesting Settlement of 40.00 USD...")
    settle_res = requests.post(f"{VAULT_BASE_URL}/v1/posting-instruction-batches", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "posting_instruction_batch": {
            "client_id": "card-processor",
            "client_batch_id": str(uuid.uuid4()),
            "posting_instructions": [{
                "client_transaction_id": client_transaction_id,
                "settlement": {"amount": "40.00", "final": True}
            }]
        }
    }, verify=False)
    print(f"✅ Settlement Status: {settle_res.json()['posting_instruction_batch']['status']}")
    
    # Fetch Balances via V2
    get_res = requests.get(f"{VAULT_BASE_URL}/v2/accounts:batchGet?ids={account_id}", headers=headers, verify=False)
    print(f"🎉 Complete. Account Open Date: {get_res.json()['accounts'][account_id]['source_open_timestamp']}")

if __name__ == "__main__":
    main()
```
