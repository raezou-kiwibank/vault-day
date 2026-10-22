---
name: vault-core-operator
description: "Assists users in building API flows and quickly creating resources (customers, products, and accounts) for Vault Core demos, enforcing modern best practices like v2 APIs and CLv4."
compatibility: Requires a Vault Core environment or client workspace. Supports CLv4 and v2 API endpoints.
audience: client
---

# Vault Core Operator Skill

This skill helps you work with the Vault Core API to design and execute resource creation flows for demos, testing, and prototyping. It strictly enforces Vault Core modern standards: avoiding deprecated endpoints (such as v1 accounts) and ensuring correct data propagation, postings structures, and smart contract design (always use CLv4).

---

## 1. Core Constraints & API Versioning

### API Versioning & Endpoints
*   **Accounts**: NEVER use `/v1/accounts`. ALWAYS use `/v2/accounts`.
*   **Balances**: NEVER use `/v1/balances`. ALWAYS use `/v2/balances/live` (and always supply the mandatory `page_size` parameter).
*   **General**: Avoid any endpoints or fields marked as deprecated in the protobuf definitions.

### Smart Contracts (CLv4 Only)
*   **CLv4 Specification**: Never use CLv3 contracts. ALWAYS use CLv4 (`api = '4.0.0'`) for product versions.
*   **Imports**: In CLv4, always import types directly from `contracts_api`:
    ```python
    from contracts_api import (
        PrePostingHookArguments,
        PrePostingHookResult,
        Rejection,
        RejectionReason,
        Tside,
    )
    ```
*   **Enum Safety**: The rejection reason for terms/conditions is strictly `RejectionReason.AGAINST_TNC`. Do NOT use `AGAINST_TANDC` or `AGAINST_TERMS_AND_CONDITIONS` which will raise a runtime contract exception (`AttributeError`).

---

## 2. Workspace Independence & Code Consistency Rules

### Workspace Isolation
*   When this skill is activated **outside** of the main `core3` repository (e.g. in a blank, temporary, or secondary workspace), you **MUST NOT** attempt to search the workspace, list files, run `plz` commands, or run `grep_search` looking for repository-specific E2E tests. Operate in a **purely self-contained generator mode** utilizing only the reference documents packaged within this skill.

### Reusable Code Templates & Code Consistency
*   Do **NOT** write custom connection logic, requests blocks, or API wrappers from scratch. Different, bespoke scripts every time lead to typos and syntax mismatch.
*   When generating Stage 2 Python scripts, you **MUST** read and use the clean, class-based helper client defined in [references/vault_e2e_template.py](references/vault_e2e_template.py).
*   Copy this base class and only customize the `main()` orchestration flow to implement the specific test case required by the user.

---

## 3. Resource Dependency & Data Propagation Rules

Creating resources in Vault Core requires a strict sequence of dependencies and precise field bindings:

```
  JWT Token
     │
     ▼
┌──────────────┐      ┌─────────────────┐
│ v1 Customer  │      │ v1 Prod Version │
└──────┬───────┘      └────────┬────────┘
       │                       │
       │ customer_id           │ smart_contract_version_id
       │                       │ (extracted integer string "id")
       ▼                       ▼
┌───────────────────────────────────────┐
│              v2 Account               │
└──────────────────┬────────────────────┘
                   │
                   │ account_id
                   ▼
┌───────────────────────────────────────┐
│     v1 Posting Instruction Batch      │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│              v2 Balances              │
└───────────────────────────────────────┘
```

### Dependency Chain Detail:
1.  **Authentication**: Fetch the token dynamically from the local JWT service.
2.  **Create Customer** (`POST /v1/customers`):
    *   Generates and extracts `customerId` (from `$.id`).
3.  **Create Product Version** (`POST /v1/product-versions`):
    *   Uploads CLv4 contract code.
    *   **CRITICAL**: You must extract the response `"id"` field (e.g. `"90986"`), which is the auto-incremented string representation of an integer. Do NOT use the alphanumeric `product_id` you defined.
    *   **Template Parameters**: If the smart contract defines non-optional, template-level parameters, they **MUST** be supplied with values inside the `"params"` array on creation (see `products_reference.md`).
4.  **Create Account** (`POST /v2/accounts`):
    *   **CRITICAL**: Include `"type": "ACCOUNT_TYPE_CUSTOMER"` in the `account` object.
    *   **CRITICAL**: Include `"status": "ACCOUNT_STATUS_OPEN"` or `"ACCOUNT_STATUS_PENDING"` in the `account` object.
    *   Propagate the extracted integer `smart_contract_version_id` string from Step 3.
    *   Propagate the `customerId` into `stakeholder_ids`.
5.  **Create Postings (PIB)** (`POST /v1/posting-instruction-batches`):
    *   **CRITICAL**: `posting_instruction_batch` requires a root-level `client_id` field.
    *   **CRITICAL**: Each instruction in the `posting_instructions` array requires a `client_transaction_id` at the root of the instruction object (sibling to the `transfer` object), not nested inside the `transfer` object itself.
    *   **Future-Dated Postings**: Apply `value_timestamp` and `booking_timestamp` **strictly at the instruction level** (never at root batch-level). Future-dated postings **MUST NOT exceed 90 calendar days (90 days) in the future** (the absolute system boundary).
6.  **Check Balances** (`GET /v2/balances/live`):
    *   Fetch latest live balances for the generated `account_id` to verify posting completion (pass mandatory `page_size=10`).

---

## 4. Two-Stage Interaction Model

Follow this lifecycle for user requests:

### Stage 1: Design (Flow Blueprint)
First, output a structured YAML flow mapping the logical steps.

**OUTPUT FORMAT COMPLIANCE**:
*   Output **ONLY** valid YAML.
*   Do **NOT** wrap the code in a markdown code block (no backticks).
*   Start directly with `flowName:`.
*   Use JSONPath notation (e.g., `$.data.id`) for all extraction paths.

### Stage 2: Execution (Implementation Scripts)
Once the user approves the YAML flow, generate executable scripts implementing the learnings and dynamic JWT retrieval, strictly using the class template in [references/vault_e2e_template.py](references/vault_e2e_template.py).

---

## 5. Troubleshooting & Learnings (What NOT to do)

| What Failed (Anti-Pattern) | Why It Failed | Correct Implementation |
| :--- | :--- | :--- |
| `product_id` in v2 Account payload | Field deprecated & removed from v2 accounts. | Use `smart_contract_version_id` instead. |
| Using `product_id` (e.g. `my_prod_id`) as the version ID | `smart_contract_version_id` requires a string representation of an integer. | Extract `"id"` from `v1/product-versions` response (e.g., `"90986"`). |
| Omitting `type` or `status` in v2 Account | Required fields for v2 customer account creation. | Include `"type": "ACCOUNT_TYPE_CUSTOMER"` and `"status": "ACCOUNT_STATUS_OPEN"`. |
| `RejectionReason.AGAINST_TANDC` | Raises `AttributeError` exception in Python contract interpreter. | Use `RejectionReason.AGAINST_TNC`. |
| Nesting `client_transaction_id` inside `transfer` | Returns `INVALID_ARGUMENT: missing client_transaction_id field`. | Place `client_transaction_id` on the posting instruction level (sibling to `transfer`). |
| Omitting `client_id` in PIB | Returns `INVALID_ARGUMENT: missing client_id field`. | Include `"client_id"` under `posting_instruction_batch`. |
| Omitting `start_datetime` in `ScheduledEvent` | Returns `InvalidSmartContractError: The start_datetime of a ScheduledEvent cannot be None`. | Pass `start_datetime=hook_arguments.effective_datetime` explicitly. |
| Omitting `page_size` in v1 `ListSchedules` | Required parameter in protobuf definition. | Always pass `page_size=10` (or similar non-zero value) in query params. |
| Using `GET /v2/accounts/{id}` | Endpoint not implemented on v2; returns `501 Not Implemented`. | Query account details via batch get: `GET /v2/accounts:batchGet?ids={id}`. |
| Asynchronous polling for v2 Account upgrade | Upgrade operations on `PUT /v2/accounts/{id}` are fully synchronous. | The converted account details are returned instantly in the response body. |
| Multi-account parameter fetch in `pre_posting_hook` | Creditor accounts do not evaluate `@fetch_account_data` decorators. | Use single-legged postings (like `outbound_hard_settlement` with an `internal_account_id` set to `"1"`) to isolate hook validation to the initiating customer account. |
| Root-level `value_timestamp` in PIB | Root-level batch timestamp deprecated in CLv4 and modern environments. | Specify `value_timestamp` and `booking_timestamp` **strictly on the individual instruction level**. |
| Future-dating over 90 days in value_timestamp | Ledger validates that future dated postings do not exceed 90 calendar days. | Restrict both value and booking timestamps to be **<= 90 calendar days in the future**. |
| Using `GET /v2/balances` | Endpoint does not exist; returns `404 Not Found`. | Always fetch live balances via `GET /v2/balances/live?account_id=<id>&page_size=10`. |
| Creating Product Version with unrendered template parameters | Contract compilation fails for missing template parameters. | Supply default values under `"product_version.params"` list on creation payload. |

---

## 6. Advanced & Specialized Flow References

If the user request matches specific product operations or architectural setups, load these dedicated reference files:
*   **Schedules & Jobs**: See [references/scheduler_flows.md](references/scheduler_flows.md) for details on querying schedules and analyzing executed jobs.
*   **Account Upgrades / Conversions**: See [references/conversion_flows.md](references/conversion_flows.md) for executing fully synchronous product version migrations on open accounts.
*   **Expected Parameters**: See [references/parameter_flows.md](references/parameter_flows.md) for declaring expected parameters and validating their account overrides.
*   **Two-Phase Postings**: See [references/posting_flows.md](references/posting_flows.md) for executing full card authorization and settlement lifecycles.

---

## 7. API Reference Sheets (Progressive Disclosure)

If you need to verify exact API JSON structures, request payloads, or parameter types (especially when operating outside of the core3 repository), load **ONLY** the relevant reference sheet below:
*   **Accounts & Customers**: See [references/accounts_reference.md](references/accounts_reference.md) for `/v1/customers`, `/v2/accounts`, `/v2/balances/live`, and `/v1/sub-accounts`.
*   **Postings & API Clients**: See [references/postings_reference.md](references/postings_reference.md) for `/v1/posting-instruction-batches` and `/v1/postings-api-clients`.
*   **Expected Parameters**: See [references/parameters_reference.md](references/parameters_reference.md) for `/v1/parameters`, `/v1/parameter-values`, and hierarchy nodes.
*   **Scheduler & Calendars**: See [references/scheduler_reference.md](references/scheduler_reference.md) for `/v1/schedules`, `/v1/jobs`, schedule tags, and calendar entries.
*   **Restrictions & Flags**: See [references/restrictions_reference.md](references/restrictions_reference.md) for `/v1/flags`, `/v1/flag-definitions`, and restrictions sets.
*   **Products & Smart Contracts**: See [references/products_reference.md](references/products_reference.md) for `/v1/product-versions`.

---

## 8. Reference Prompts

### Good Prompts to Trigger This Skill:
*   *"I want to test a simple smart contract pre-posting hook on core-development. Create a flow that uploads the contract, creates accounts, and runs transfers to test it."*
*   *"Show me how to create a customer, open a v2 account with a CLv4 smart contract, send some postings, and then query the resulting balances."*
*   *"Show me how to query account schedules and verify automated job execution on core-development."*
*   *"Show me how to convert an existing customer account from one product version to another synchronously on core-development."*
*   *"Show me how to test Expected Parameter overrides on account level in CLv4 smart contracts."*
*   *"Show me how to execute a 2-phase card transaction E2E hold and capture postings cycle."*
*   *"Show me how to create and submit a future-dated transaction on core-development."*

---

## 9. Canonical Reference Flow (Complete End-to-End E2E Scenario)

```yaml
flowName: prePostingAndBalanceValidation
description: Creates two customers, uploads a CLv4 transaction limit contract, opens two accounts, runs success/rejection transfer tests, and queries balances.
steps:
  - step: 1
    operationId: createSenderCustomer
    description: Create the sender stakeholder customer
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
            first_name: "Sender"
            last_name: "User"
            dob: "1990-01-01"
            gender: "MALE"
            nationality: "US"
    extract:
      senderCustomerId: '$.id'
  - step: 2
    operationId: createRecipientCustomer
    description: Create the recipient stakeholder customer
    method: POST
    path: /v1/customers
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        customer:
          customer_details:
            title: "Mrs"
            first_name: "Recipient"
            last_name: "User"
            dob: "1992-02-02"
            gender: "FEMALE"
            nationality: "US"
    extract:
      recipientCustomerId: '$.id'
  - step: 3
    operationId: createProductVersion
    description: Upload a CLv4 product version with an amount limit check of 100 USD
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "pre_posting_limit_product_{{$guid}}"
          display_name: "Pre-Posting Limit Validation Demo"
          code: |
            from contracts_api import (
                PrePostingHookArguments,
                PrePostingHookResult,
                Rejection,
                RejectionReason,
                Tside,
            )
            api = "4.0.0"
            version = "0.0.1"
            tside = Tside.LIABILITY
            def pre_posting_hook(vault, hook_arguments: PrePostingHookArguments):
                for posting_instruction in hook_arguments.posting_instructions:
                    if posting_instruction.amount > 100:
                        return PrePostingHookResult(
                            rejection=Rejection(
                                message="Transaction amount exceeds the 100.00 USD limit.",
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
    operationId: createSenderAccount
    description: Create the sender's account using the newly uploaded smart contract version
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
            - "{{step1.senderCustomerId}}"
    extract:
      senderAccountId: '$.id'
  - step: 5
    operationId: createRecipientAccount
    description: Create the recipient's account using the newly uploaded smart contract version
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
            - "{{step2.recipientCustomerId}}"
    extract:
      recipientAccountId: '$.id'
  - step: 6
    operationId: sendTransferUnderLimit
    description: Send a successful transfer of 50.00 USD
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
              transfer:
                amount: "50.00"
                denomination: "USD"
                debtor_target_account:
                  account_id: "{{step4.senderAccountId}}"
                creditor_target_account:
                  account_id: "{{step5.recipientAccountId}}"
    extract:
      batchId: '$.posting_instruction_batch.id'
  - step: 7
    operationId: sendTransferOverLimit
    description: Send an over-limit transfer of 150.00 USD (expects rejection)
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
              transfer:
                amount: "150.00"
                denomination: "USD"
                debtor_target_account:
                  account_id: "{{step4.senderAccountId}}"
                creditor_target_account:
                  account_id: "{{step5.recipientAccountId}}"
    extract:
      batchStatus: '$.posting_instruction_batch.status'
  - step: 8
    operationId: getSenderBalances
    description: Fetch the updated balances for the sender account
    method: GET
    path: /v2/balances/live?account_id={{step4.senderAccountId}}&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      balances: '$.balances'
```
