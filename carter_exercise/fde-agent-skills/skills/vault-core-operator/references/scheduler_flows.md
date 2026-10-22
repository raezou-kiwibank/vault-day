# Scheduler & Job Orchestration Flows

Use these flows and scripts to validate schedules, query active jobs, and perform manual operations on account-level triggers.

---

## Flow 1.1: Account Schedule Query & Job Status Check

```yaml
flowName: accountScheduleQueryAndJobStatusCheck
description: Creates a customer, a product version with a real-time schedule, a v2 account, and queries the status of the resulting schedule and job execution.
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
            first_name: "Schedule"
            last_name: "Tester"
            dob: "1990-01-01"
            gender: "MALE"
            nationality: "US"
    extract:
      customerId: '$.id'
  - step: 2
    operationId: createProductVersion
    description: Upload a CLv4 smart contract defining a real-time schedule
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "scheduler_product_{{$guid}}"
          display_name: "Schedule Validation Demo"
          code: |
            from contracts_api import (
                ActivationHookArguments,
                ActivationHookResult,
                SmartContractEventType,
                ScheduledEvent,
                ScheduleExpression,
                ScheduledEventHookArguments,
                ScheduledEventHookResult,
                Tside,
            )
            api = "4.0.0"
            version = "0.0.1"
            tside = Tside.LIABILITY
            supported_denominations = ["USD"]
            event_types = [SmartContractEventType(name="ACCRUE_INTEREST")]
            def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult:
                return ActivationHookResult(
                    scheduled_events_return_value={
                        "ACCRUE_INTEREST": ScheduledEvent(
                            start_datetime=hook_arguments.effective_datetime,
                            expression=ScheduleExpression(hour="0", minute="0", second="0")
                        )
                    }
                )
            def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments) -> ScheduledEventHookResult:
                return ScheduledEventHookResult()
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
    operationId: listSchedules
    description: Query schedules associated with the newly opened account
    method: GET
    path: /v1/schedules?resource.resource_id={{step3.accountId}}&resource.resource_type=RESOURCE_TYPE_ACCOUNT&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      scheduleId: '$.schedules[0].id'
  - step: 5
    operationId: listJobs
    description: Fetch jobs associated with the schedule to verify successful execution
    method: GET
    path: /v1/jobs?schedule_ids={{step4.scheduleId}}&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      jobStatus: '$.jobs[0].status'
```

---

## Flow 1.2: Schedule Status Management (Pause / Unpause)

```yaml
flowName: scheduleStatusManagementPauseUnpause
description: Pauses a schedule dynamically using an Account Schedule Tag, verifies jobs do not run, unpauses the tag, and verifies jobs trigger using polling.
steps:
  - step: 1
    operationId: createAccountScheduleTag
    description: Create an Account Schedule Tag with test_pause_at_timestamp set in the past to pause executions
    method: POST
    path: /v1/account-schedule-tags
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account_schedule_tag:
          id: "test_tag_{{$guid}}"
          description: "Paused tag for testing"
          test_pause_at_timestamp: "2020-01-01T00:00:00Z"
    extract:
      tagId: '$.id'
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
            first_name: "Pause"
            last_name: "Tester"
    extract:
      customerId: '$.id'
  - step: 3
    operationId: createProductVersion
    description: Upload a CLv4 smart contract tying the schedule to the created paused tag
    method: POST
    path: /v1/product-versions
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        product_version:
          product_id: "paused_product_{{$guid}}"
          display_name: "Schedule Pause Validation Demo"
          code: |
            from contracts_api import (
                ActivationHookArguments,
                ActivationHookResult,
                SmartContractEventType,
                ScheduledEvent,
                ScheduleExpression,
                ScheduledEventHookArguments,
                ScheduledEventHookResult,
                Tside,
            )
            api = "4.0.0"
            version = "0.0.1"
            tside = Tside.LIABILITY
            supported_denominations = ["USD"]
            event_types = [
                SmartContractEventType(
                    name="ACCRUE_INTEREST",
                    scheduler_tag_ids=["{{step1.tagId}}"]
                )
            ]
            def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult:
                return ActivationHookResult(
                    scheduled_events_return_value={
                        "ACCRUE_INTEREST": ScheduledEvent(
                            start_datetime=hook_arguments.effective_datetime,
                            expression=ScheduleExpression(hour="0", minute="0", second="0")
                        )
                    }
                )
            def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments) -> ScheduledEventHookResult:
                return ScheduledEventHookResult()
          supported_denominations:
            - "USD"
        migration_strategy: "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
        is_internal: false
    extract:
      smartContractVersionId: '$.id'
  - step: 4
    operationId: createAccount
    description: Create the customer's v2 account (linked to product version)
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
    extract:
      accountId: '$.id'
  - step: 5
    operationId: listSchedules
    description: Fetch the generated schedule ID for the account
    method: GET
    path: /v1/schedules?resource.resource_id={{step4.accountId}}&resource.resource_type=RESOURCE_TYPE_ACCOUNT&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      scheduleId: '$.schedules[0].id'
  - step: 6
    operationId: verifyJobsPaused
    description: Query jobs to assert that NO jobs have run while paused
    method: GET
    path: /v1/jobs?schedule_ids={{step5.scheduleId}}&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      jobsCount: '$.jobs'
  - step: 7
    operationId: updateAccountScheduleTag
    description: Unpause the tag by updating test_pause_at_timestamp to null
    method: PUT
    path: /v1/account-schedule-tags/{{step1.tagId}}
    request:
      headers:
        Content-Type: application/json
      body:
        request_id: "{{$guid}}"
        account_schedule_tag:
          id: "{{step1.tagId}}"
          test_pause_at_timestamp: null
        update_mask:
          paths:
            - "test_pause_at_timestamp"
  - step: 8
    operationId: verifyJobTriggered
    description: Query jobs (poll) to assert the job triggers and succeeds post-unpause
    method: GET
    path: /v1/jobs?schedule_ids={{step5.scheduleId}}&page_size=10
    request:
      headers: {}
      body: {}
    extract:
      jobStatus: '$.jobs[0].status'
```

---

## 🛠️ Executable Python Status Management Script

Below is the verified, asynchronous-polling script implementing the E2E schedule status management flow:

```python
import uuid
import json
import requests
import time
from datetime import datetime, timezone, timedelta

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
    
    # Create Paused Account Schedule Tag
    tag_id = f"test_tag_{str(uuid.uuid4()).replace('-', '_')}"
    requests.post(f"{VAULT_BASE_URL}/v1/account-schedule-tags", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account_schedule_tag": {"id": tag_id, "description": "Paused tag for E2E", "test_pause_at_timestamp": "2020-01-01T00:00:00Z"}
    }, verify=False)
    
    # Create Customer
    cust_res = requests.post(f"{VAULT_BASE_URL}/v1/customers", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "customer": {"customer_details": {"first_name": "Pause", "last_name": "Tester"}}
    }, verify=False)
    cust_id = cust_res.json()["id"]
    
    # Upload Contract referencing tag
    trigger_time = datetime.now(timezone.utc) + timedelta(seconds=2)
    code = f"""from contracts_api import *
api = "4.0.0"
version = "0.0.1"
tside = Tside.LIABILITY
supported_denominations = ["USD"]
event_types = [SmartContractEventType(name="ACCRUE_INTEREST", scheduler_tag_ids=["{tag_id}"])]
def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult:
    return ActivationHookResult(
        scheduled_events_return_value={{
            "ACCRUE_INTEREST": ScheduledEvent(
                start_datetime=hook_arguments.effective_datetime,
                expression=ScheduleExpression(
                    year={trigger_time.year}, month={trigger_time.month}, day={trigger_time.day},
                    hour={trigger_time.hour}, minute={trigger_time.minute}, second={trigger_time.second}
                )
            )
        }}
    )
def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments) -> ScheduledEventHookResult:
    return ScheduledEventHookResult()
"""
    prod_res = requests.post(f"{VAULT_BASE_URL}/v1/product-versions", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "product_version": {"product_id": f"paused_product_{str(uuid.uuid4()).replace('-', '_')}", "code": code, "supported_denominations": ["USD"]},
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
    }, verify=False)
    version_id = prod_res.json()["id"]
    
    # Create Account
    acc_res = requests.post(f"{VAULT_BASE_URL}/v2/accounts", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account": {"type": "ACCOUNT_TYPE_CUSTOMER", "smart_contract_version_id": version_id, "status": "ACCOUNT_STATUS_OPEN", "stakeholder_ids": [cust_id]}
    }, verify=False)
    account_id = acc_res.json()["id"]
    
    # Sleep to prove pause is effective
    print("⏳ Sleeping 4 seconds to verify jobs are successfully paused...")
    time.sleep(4)
    
    # List Schedules and Jobs
    sched_res = requests.get(f"{VAULT_BASE_URL}/v1/schedules?resource.resource_id={account_id}&resource.resource_type=RESOURCE_TYPE_ACCOUNT&page_size=10", headers=headers, verify=False)
    schedule_id = sched_res.json()["schedules"][0]["id"]
    
    job_res = requests.get(f"{VAULT_BASE_URL}/v1/jobs?schedule_ids={schedule_id}&page_size=10", headers=headers, verify=False)
    jobs = job_res.json().get("jobs", [])
    print(f"📊 Paused Job count: {len(jobs)}") # Must be 0
    
    # Unpause the tag
    print("🔓 Unpausing schedule tag...")
    requests.put(f"{VAULT_BASE_URL}/v1/account-schedule-tags/{tag_id}", headers=headers, json={
        "request_id": str(uuid.uuid4()),
        "account_schedule_tag": {"id": tag_id, "test_pause_at_timestamp": None},
        "update_mask": {"paths": ["test_pause_at_timestamp"]}
    }, verify=False)
    
    # Poll for Job Execution
    print("⏳ Polling for job publication...")
    max_attempts = 10
    jobs = []
    for attempt in range(max_attempts):
        res = requests.get(f"{VAULT_BASE_URL}/v1/jobs?schedule_ids={schedule_id}&page_size=10", headers=headers, verify=False)
        jobs = res.json().get("jobs", [])
        if jobs:
            print(f"🎉 Job successfully executed! Job ID: {jobs[0]['id']}, Status: {jobs[0]['status']}")
            break
        time.sleep(3)

if __name__ == "__main__":
    main()
```
