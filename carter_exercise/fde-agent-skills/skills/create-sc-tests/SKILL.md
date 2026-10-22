---
name: create-sc-tests
description: Create a unit, simulation, and e2e test suite for a Thought Machine Vault Smart Contract using the Inception SDK test framework. Use after a contract has been written or converted, or when test coverage needs extending.
compatibility: Requires a Vault client workspace with the Inception SDK test framework and feature_library. Reference documentation bundled for Vault 5.9.
audience: client
---

# Create Smart Contract Tests

This skill provides a systematic workflow to follow when creating tests for a Smart Contract

## Workflow

### 0. Version Identification
Before starting any work, you MUST know the **Vault version** (e.g., 5.9) the product uses. This information is critical for selecting the correct reference documentation and following the appropriate testing standards. Read it from the header of `documentation/IMPLEMENTATION_PLAN.md`. Ask the user only if there is no plan or it does not say.

### 1. Access the inception_sdk and Contracts API documentation

Smart Contracts are typically tested using the inception_sdk test framework.

#### Inception SDK Documentation
Access the documentation on testing using the inception_sdk framework in the [inception_sdk_documentation folder](../common-references/inception_sdk_documentation).

There is information on:
- The test framework approach
- Unit testing
- Simulation testing
- E2E testing
- And how to debug contracts

#### Contracts API Reference Documentation
**Definitive Reference**: Always consult the versioned reference documentation in `../common-references/contracts_api_documentation/vault-<version>/` for the specific Vault version being used (e.g., `vault-5-9/`).

Contracts API 4 is known as **CLV4** (short for Contracts Language Version 4).

- **Contracts API V4 (CLV4)**: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/`

#### Core API Reference Documentation
E2E tests drive the Vault Core API. Check the endpoint, request body and response fields in `../common-references/core_api_documentation/vault-<version>/core_api.json` instead of guessing them. The file is large, so search it for the path or schema you need (for example `/v1/posting-instruction-batches`) and do not read it whole.

#### Inception SDK Source
The SDK documentation does not list every assertion or helper. When it is silent on one you need, read the installed `inception_sdk` package in the project's virtual environment instead of guessing. For example, the fields of `SubTest` and the `Expected...` classes are in `inception_sdk/test_framework/contracts/simulation/data_objects/data_objects.py` (that is where the violation assertions are defined: `expected_contract_violations` for a posting the contract rejects, and `expected_account_violations` and `expected_posting_violations` for the platform's own), and the simulation event helpers are in `inception_sdk/test_framework/contracts/simulation/helper.py`.

### 2. Read the test plan and scope the work

The tests implement `documentation/TEST_PLAN.md` in the product directory, written by `create-test-plan`. If it does not exist, use the create-test-plan skill and a sub agent to come up with a test plan for the new contract. Do not invent scenarios.

Features are delivered one at a time. Read `documentation/IMPLEMENTATION_PLAN.md` and write tests for the feature(s) whose Status is `Implemented` and that have no tests yet, using the scenario group with the same feature name, plus any cross-cutting scenarios that apply. If a feature already has tests, for example because a previous run reported a failure and the contract was fixed since, keep them: add only the scenarios still missing and run them all (step 4). Do not write tests for features that are still `Planned`. Without a plan, cover the whole contract.

For each scenario in scope:
- **Levels**: write the levels the scenario lists. Every scenario gets a unit test; add a simulation test where it says `Simulation: yes`. Write e2e tests only for the plan's "E2E recommendations", and only once no feature in `IMPLEMENTATION_PLAN.md` is still `Planned`: they come last, after every feature is implemented. They run against a real Vault, which cannot delete what they create, and their journeys cross features. While a feature is still `Planned`, write none and list the recommendations you left out (step 5). On the run that finds every feature `Implemented`, write all of the plan's e2e recommendations that have no tests yet, including those of earlier features.
- **Tag**: for a `[library]` scenario, write one test that shows the product wires the library feature correctly and do not re-test library internals. For a `[custom]` scenario, write the full boundary and corner set.
- **Status**: skip scenarios marked `[Retired]`. Test a `provisional: <default>` outcome against that default and keep the marker in a comment, so the test can be found and changed when the question is resolved.
- **Traceability**: put the scenario ID (and the `AC-xx` or `D-xx` from its Origin) in the test name or docstring, so every test traces back to its scenario.
- **Expected values** come from the scenario's worked numbers, never from running the contract. If a correct test fails, the contract or the plan is wrong: diagnose it as step 4 says, and never change the expected value to match the contract.

### 3. Create the tests

If not there already, create a `tests` directory (e.g`tests/`, `tests/unit/`,`tests/simulation/`, etc.) inside the product directory, wherever the project places products (check its `AGENTS.md`/`README.md` or existing structure; ask the user if unclear), following the standard product directory structure below:

```
.
└── mortgage_product/
    ├── contracts/
    │   ├── template/
    │   │   ├── __init__.py      # Remember empty __init__.py files
    │   │   └── mortgage.py      # The smart contract
    │   ├── __init__.py
    │   └── mortgage_rendered.py # An empty py file for production use
    ├── tests/
    │   ├── e2e/
    │   │   ├── __init__.py
    │   │   ├── accounts.py
    │   │   ├── parameters.py
    │   │   ├── test_file_name.py
    │   │   └── ...
    │   ├── simulation/
    │   │   ├── __init__.py
    │   │   ├── accounts.py
    │   │   ├── dimensions.py
    │   │   ├── parameters.py
    │   │   ├── test_file_name.py
    │   │   └── ...
    │   ├── unit/
    │   │   ├── __init__.py
    │   │   ├── test_file_name.py
    │   │   └── ...
    │   └── __init__.py
    ├── parameters/
    │   └── parameter_name.resource.yaml
    ├── flag_definitions/
    │   └── flag_name.resource.yaml
    └── ...
```

Ensure that EVERY subdirectory created contains an empty __init__.py file. This is critical for Python to correctly resolve imports during testing.

Identify any vault resources (e.g. ExpectedParameters, Flags) in the smart contract that contain the clu notation (e.g. `&{parameter_id}`). Create the required resource.yaml files with the clu_definition and put these under a relevant directory e.g. `parameters`. You can look at the feature_library for an example.

Create the relevant unit, simulation and e2e tests from the test plan using the inception sdk. Make sure every in-scope scenario from the test plan (step 2) has its tests and that they pass. You can use the examples (see [example_test_structures](./references/example_test_structures)) to see examples of what the directory should look like and how to configure the tests. Note that these examples are not complete or passing tests (e.g. contain broken imports), they are there just an example to provide a rough structure.

Follow guidelines attained from the documentation and these additional guidelines below:

- **Unit Tests**:
  - Inherit from `inception_sdk.test_framework.contracts.unit.common.FeatureTest`.
  - **Helper Functions**: If you implement new helper functions directly within the smart contract (i.e., logic that is not part of an existing feature from the `feature_library`), you MUST add unit tests to verify their logic in isolation.
  - When unit testing aim for 100% coverage.
- **Simulation Tests**:
  - Inherit from `inception_sdk.test_framework.contracts.simulation.utils.SimulationTestCase`.
  - **Base Class Pattern**: For complex contracts, use a base test class to define common `parameter_resource_dirs`, `internal_accounts`, and a `get_simulation_test_scenario` helper. This helper should streamline the creation of `SimulationTestScenario` objects by providing default `AccountConfig` and `ContractConfig`.
  - **Smart Contract Path**: ALWAYS wrap the `SMART_CONTRACT` path in a `Path` object (e.g., `SMART_CONTRACT = Path("tests/lending/principal/maximum_loan_principal_sc.py")`). However, you MUST explicitly cast it to a string (e.g., `str(SMART_CONTRACT)`) when using it as a key in `contract_filepaths` or `self.smart_contract_path_to_content` to avoid `KeyError`.
  - **Timezone Testing**: Use `@parameterized.expand(timezones)` to test schedules across different timezones, where `timezones` is a list of `ZoneInfo` values that you define once in the product's simulation tests (for example `[ZoneInfo("UTC"), ZoneInfo("America/New_York"), ZoneInfo("Australia/Sydney")]`). Include an `update_pgtz_instruction` event, from `inception_sdk.test_framework.contracts.simulation.helper`, at the start of each simulation.
    ```python
    @parameterized.expand(timezones)
    def test_schedule_across_timezones(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # Event occurs at midnight local time
        expected_event_time = start + relativedelta(days=1)
        end = expected_event_time + relativedelta(hours=1)

        sub_tests = [
            SubTest(
                description="Setup account",
                events=[...],
            ),
            SubTest(
                description="Check event occurs at local midnight",
                expected_balances_at_ts={
                    expected_event_time: { ... }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    def get_simulation_test_scenario(self, start, end, sub_tests, default_tz=UTC, ...):
        # Always inject the PGTZ update as the first sub-test
        localised_sub_tests = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[update_pgtz_instruction(start, timezone=default_tz)],
            )
        ] + sub_tests
        ...
    ```
  - **Additional Helpers**: Beyond postings and parameters, use these `inception_sdk.test_framework.contracts.simulation.helper` utilities:
    - `create_flag_definition_event`: To define account/customer flags.
    - `create_flag_event`: To apply flags to accounts or customers.
    - `create_calendar_event`: To define and create calendars.
  - **SubTest Design**:
    - **Isolation**: Each `SubTest` should ideally focus on one logical step (e.g., "Initial Deposit", "Accrue Interest", "Apply Interest").
    - **Assertions**: Include `expected_balances_at_ts`, `expected_schedules`, or `expected_contract_notifications` in the same `SubTest` as the event that triggers them.
    - **Exact Timing**: Always assert at the **exact** execution timestamp. The simulator processes events and their side-effects at the same point in time, so there is no need to add an offset (e.g., `+ relativedelta(seconds=1)`) to check results.
  - **Internal Accounts**: In `tests/simulation/accounts.py`, ALWAYS use `dict[str, str]` for `default_internal_accounts` (account ID to `ASSET` or `LIABILITY`) and import `ASSET` or `LIABILITY` from `inception_sdk.test_framework.common.constants`. The e2e tests use a different dictionary, `internal_accounts_tside`.
  - **Feature Coverage**: Ensure that simulation tests cover ALL features included in the Smart Contract. While all features do not need to be validated in a single test case, the collective test suite for the contract MUST exercise and verify the behavior of every function from the integrated features used by the smart contract. Take the simulation scenarios to include from the test plan (step 2) and ensure these are added.
  - **Parameter Resource Paths**: In the product's base test class (e.g. `MortgageTestBase`), ensure `parameter_resource_dirs` uses relative paths (e.g., `../../feature_library/src/feature_library/...`) so the simulator can find the YAML definitions from the test's context.
  - **Simulating Parameter Changes**: Use the `create_parameter_value` helper from `inception_sdk.test_framework.contracts.simulation.helper` combined with the `CreateParameterValue` data object from `inception_sdk.vault.sim_api.contract_sim`.
    - **Account Level**:
      ```python
      create_parameter_value(
          timestamp=event_time,
          parameter_value=CreateParameterValue(
              parameter_id="some_expected_param",
              value=DecimalParameterValue(decimal_value=Decimal("0.10")),
              account_id=accounts.CUSTOMER_ACCOUNT,
          ),
      )
      ```
    - **Global Level**: Set `global_=True`.
      ```python
      create_parameter_value(
          timestamp=event_time,
          parameter_value=CreateParameterValue(
              parameter_id="some_expected_param",
              value=StringParameterValue(string_value="actual"),
              global_=True,
          ),
      )
      ```
    - **Node Level**: Use `parameter_value_hierarchy_node_id`.
      ```python
      create_parameter_value(
          timestamp=event_time,
          parameter_value=CreateParameterValue(
              parameter_id="some_expected_param",
              value=DecimalParameterValue(decimal_value=Decimal("5")),
              parameter_value_hierarchy_node_id="SOME_NODE_ID",
          ),
      )
      ```
  - **Simulating Postings**: When simulating postings, use the following helper functions from `inception_sdk.test_framework.contracts.simulation.helper`:
    - `create_auth_adjustment_posting_instruction_event`
    - `create_custom_instruction_posting_instruction_event`
    - `create_inbound_authorisation_posting_instruction_event`
    - `create_inbound_hard_settlement_posting_instruction_event`
    - `create_outbound_authorisation_posting_instruction_event`
    - `create_outbound_hard_settlement_posting_instruction_event`
    - `create_release_posting_instruction_event`
    - `create_settlement_posting_instruction_event`
    - `create_transfer_posting_instruction_event`
  - **Verifying Balances**: To verify balances after a simulation event (e.g., a posting or a scheduled event), use the `expected_balances_at_ts` field within a `SubTest`. You do NOT need to add a second to the event time to see the effect on the balance; the simulator reflects the state immediately after the event has processed at the same timestamp.
  - **Verifying Rejected Postings**: A simulation test can assert why a posting was rejected, not only that the balances did not change, so do not leave the reason to the unit test or an e2e test. The simulator returns, for each posting instruction, three lists: `contract_violations` (what the contract's own `Rejection` produced, with a `violation_type` such as `WRONG_DENOMINATION` or `INSUFFICIENT_FUNDS`, and the `reason` text), `account_violations` (for example an unsupported denomination) and `posting_violations` (for example a client transaction that already exists). Assert the one that holds the rejection with `SubTest.expected_contract_violations`, `expected_account_violations` or `expected_posting_violations`. Each maps the event timestamp to a list of `ExpectedContractViolation`, `ExpectedAccountViolation` or `ExpectedPostingViolation`, with an optional `client_transaction_id`. The comparison is on the whole violation object, so the `reason` text and the deprecated `type` field must match as well. Read the real values from the raw payload (see Reading the Raw Payload) instead of guessing them, but take the expected reason code from the scenario, never from the payload. `expected_posting_rejections` is deprecated. If the plan says the simulation cannot assert the reason (for example a "unit-only" level or a default for an open question about it), that premise is wrong for this SDK: assert the reason in the simulation test as well, and say so in the report so the plan can be corrected. Do not change the plan.
  - **Verifying Notifications**: To verify account notifications in a simulation test, use the `expected_contract_notifications` field within a `SubTest`. This field takes a list of `ExpectedContractNotification` objects. Note that all values in the `notification_details` dictionary must be strings.
    ```python
    expected_contract_notifications=[
        ExpectedContractNotification(
            timestamp=expected_event_datetime,
            notification_type="SOME_NOTIFICATION_TYPE",
            notification_details={
                "account_id": accounts.CUSTOMER_ACCOUNT,
                "amount": "100.00",
            },
            resource_id=accounts.CUSTOMER_ACCOUNT,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
    ]
    ```
- **End-to-End (e2e) Tests**:
  - Inherit from `inception_sdk.test_framework.endtoend.End2Endtest` (the SDK spells it with a lower-case `t`) or `inception_sdk.test_framework.endtoend.AcceleratedEnd2EndTest`.
  - **Setup**: In `setUpClass`, configure `endtoend.testhandle` with:
    - `CONTRACTS`: Map internal IDs to contract file paths and template parameters.
    - `TSIDE_TO_INTERNAL_ACCOUNT_ID`: Map each `AccountV2TSide` to a list of internal account IDs.
    - `PARAMETER_RESOURCE_DIRS`: List of paths to CLU resource YAMLs.
    - `FLAG_DEFINITIONS`: Map flag IDs to their resource YAML paths.
  - **Default Values Setup**:
    - Within `tests/e2e/parameters.py`, default parameters should be defined as a dictionary named `default_parameter_values`, which is of type `dict[str, ParameterValue]`.
    - Within `tests/e2e/accounts.py`, the internal accounts should be defined as a dictionary named `internal_accounts_tside`, which is of type `dict[AccountV2TSide, list[str]]` (`AccountV2TSide` is in `inception_sdk.vault.core_api`). This dictionary will be used when setting `testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID`. It is not the same dictionary as the simulation tests' `default_internal_accounts`.
  - **Helper Preference**: When writing e2e tests, you MUST try to identify and use the correct helper from `endtoend.contracts_helper` in the first instance. If a suitable helper is not available in `contracts_helper`, you should then use `endtoend.core_api_helper`. If that has no function for the call either, build the request from the Core API specification (see step 1: the endpoint, the request body and the required fields) and send it with `endtoend.helper.send_request`. Do not guess a payload, and do not make raw `requests` calls that bypass the framework's authentication.
  - **Common Helpers**:
    - `endtoend.postings_helper`: Use `inbound_hard_settlement()`, `outbound_hard_settlement()`, `inbound_auth()`, `outbound_auth()`, `auth_adjustment()`, `settlement()`, `create_transfer()`, or `create_custom_instruction()`. Use `get_posting_batch()` to check for rejections.
    - `endtoend.balances_helper`: Use `wait_for_account_balances()` with `BalanceDimensions` to verify account states.
    - `endtoend.schedule_helper`: In accelerated tests, use `trigger_next_schedule_job()` and `wait_for_schedule_job()` to manually execute schedules.
    - `endtoend.contracts_helper`: Use `create_account_v2()` with `CreateOptions` to specify parameter values to be used by the account. Do not use `create_account()`, as this function has been deprecated.
  - **Accelerated Tests**: Use the `@endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules` decorator to manage schedule execution.

**Vault environment.** Simulation and e2e tests call a real Vault Core environment through the project's environment config; unit tests do not. The user owns that connection (the project's `AGENTS.md` says where the config lives). If a simulation or e2e test cannot reach Vault (the config is missing or invalid, the connection is refused or times out, or authentication fails), stop. Do not look for credentials elsewhere, do not create or edit the environment config, and do not report those tests as passing. Report the tests that are written but not run, with the error, ask the user to set up the connection to a Vault Core environment, and return control. A `VaultException` returned by the simulator is not an environment problem: it is a contract or test problem, so debug it as below.

If you are stuck and need help debugging refer to the debugging guidelines in the documentation if those do not help follow these guidelines when simulation testing:

- **Debugging with Simulation Logs**:
  - Run the tests with LOGLEVEL="DEBUG", set before the test process starts. The framework then logs the raw JSON request it sends to the simulate endpoint (logger `sim_test_request_logger`) and every line of the raw streamed response (logger `sim_test_response_logger`), which can be inspected for error messages.
  - **Reading the Raw Payload**: When an assertion fails and the cause is not obvious, read what the simulator actually returned instead of guessing. The request holds the contract code, the parameters and the `events`. Each response line is either an `error` or a `result` at a `timestamp`. The `result` fields (for example `balances`, `posting_instruction_batches`, `contract_notification_events` and `hook_execution_logs`) are defined by the schema `v1contractsSimulateContractsResponse` for `POST /v1/contracts:simulate` in `core_api.json` (see step 1). pytest shows captured log output only for failing tests; its `--log-cli-level=DEBUG` option streams it live. `run_test_scenario` returns the response only after every assertion has passed, and `debug=True` on `SimulationTestScenario` only streams the response and adds no output, so use the log to see the payload of a failing assertion.
  - **Exhaustive Log Analysis**: Do NOT just look at the last error. Scroll up through the full output. Look for `VaultException` which contains the most specific causes of failure.
  - **Common Failure Indicators**:
    - `"The fetcher id '...' was not defined in the 'parameters' of the '@fetch_account_data' decorator"`: You are trying to use a parameter in a hook that wasn't fetched.
    - `"OWNER_NOT_FOUND"`: Usually occurs in `create_parameter_value` events when you provide an `account_id` for a parameter that is defined as Global (or vice versa). Use `global_=True` for global parameters.
    - `"IllegalPython"`: Indicates a syntax error or a decorator usage error (like missing `attribute_name` in `attribute_hook`).
  - **Trace Stack Traces**: The `stack_trace` field in the `VaultException` metadata points directly to the line in the contract (or library feature) where the error occurred. Use this to identify which feature function is failing due to missing state data.

### 4. Run and Verify

Run the tests with the command the project documents (its `AGENTS.md` or `README.md`) and do not invent one. Work from the cheapest level up, so that a contract that fails at unit level does not cost simulation runs:

1. Run the new unit tests and fix what fails.
2. Run the new simulation tests and fix what fails.
3. Run the new e2e tests, if you wrote any, and fix what fails.
4. Last, run the whole suite for the product (the existing tests together with the new ones, at the levels the project runs) to show that nothing regressed. If a shared test file you touched, such as a base class or an accounts module, broke an earlier test, correct your change. If an earlier test fails and nothing you changed is used by it, it was already failing: report it and do not edit it.

If a simulation or e2e test cannot reach Vault, follow the Vault environment rule in step 3.

**Fix what is yours.** A failure caused by the test code itself (an import, the setup, the wrong helper, the wrong shape of an event or a parameter, an assertion on the wrong field) is yours to fix. Use the debugging guidance in step 3. Make at most three rounds of fixes per level. If a test still fails after that, stop fixing it and report it.

**Diagnose what is not yours.** If a correct test fails, the contract or the plan is wrong (see Expected values in step 2). Work out which, with evidence, before you do anything else:
- *Contradictory scenarios*: compare the failing scenario with the other scenarios in `TEST_PLAN.md` that start from the same set-up. If two of them give the same inputs different expected outcomes, no contract can satisfy both. This is a plan defect that names both scenarios, and it is not a contract defect.
- *Plan defect*: the scenario's expected outcome contradicts the requirements or a recorded decision, or its worked numbers are wrong.
- *Contract defect*: the contract's behaviour differs from what the scenario's `AC-xx` or `D-xx` in `REQUIREMENTS.md` asks for, and the scenarios do not contradict each other.
- If the evidence does not decide it, say so and give both readings.

Never change the plan or an expected value, and never skip the test or mark it as an expected failure. For a plan defect, contradictory scenarios or an undecided case, leave the test failing, carry on with the rest of the run, and report it: the user decides, through `create-test-plan`.

**Fix a contract defect, within a bound.** Do not edit the contract yourself. Run the `create-smart-contract` skill's "Fixing a Feature After Its Tests Failed" section for that feature (in a sub agent if your tool supports it), and give it the failing scenario IDs, expected against actual, and your diagnosis with its evidence. Then re-run the failing tests, and then the level you were on. Fix a contract defect as soon as you find it, before you move to the next level.
- Make at most three of these fix rounds in the whole run, not three per error.
- Stop at once, before the third, and report, if any of these happens after a fix: the same tests fail with the same message; the number of failing tests does not fall; or a test that passed before now fails. A fix that breaks a scenario that passed means the two scenarios contradict each other for the same inputs, so report both as a plan defect.
- If a fix adds, removes or changes a parameter, a schedule or another Vault resource, stop and report. The CLU pack is out of date, and `create-clu-resources` has to run before the tests are trusted. Do not run it yourself, because it can ask the user for values.
- The fix never edits a test, the plan or an expected value.

### 5. Report and Hand Back

Report the scenario IDs implemented at each level against the plan's counts, any scenario not implemented and why, the e2e recommendations left out because a feature is still `Planned` (by ID), any test written but not run and why (for example Vault is not reachable), the result of each run in step 4 including the final full-suite run, and the `provisional` outcomes the tests rely on. For every failing test give the scenario ID, expected against actual (for a simulation test, the relevant part of the raw simulator payload), your diagnosis (contract defect, plan defect, contradictory scenarios or undecided) and the evidence. If you ran contract fix rounds, say how many, and for each round what was wrong and which contract lines changed, so that no change to the contract is silent.

Then suggest the next step. For a plan defect or contradictory scenarios, suggest revising those scenarios, named, with `create-test-plan`. For a contract defect that is still failing, suggest `create-smart-contract` to fix the feature, naming the failing scenario IDs, and say why the fix rounds stopped. If a fix changed a Vault resource, suggest `create-clu-resources` and then `create-sc-tests` again. Return control to the user. Start nothing.
