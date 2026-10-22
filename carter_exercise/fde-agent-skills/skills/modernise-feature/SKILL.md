---
name: modernise-feature
description: Refactor old Thought Machine Vault Smart Contract features to align with the latest 'feature_library' conventions, including state management, interface implementation, and testing standards. Use when bringing a legacy feature up to current standards.
compatibility: Requires a Vault client workspace with the feature_library and Inception SDK test framework. Reference documentation bundled for Vault 5.9.
audience: client
---

# Modernise Feature

This skill provides a systematic workflow for refactoring legacy Smart Contract features into the modern standards used in the `feature_library`.

## Workflow

### 0. Version Identification
Before starting any work, you MUST ask the user which **Vault version** (e.g., 5.9) and **Contracts API version** (CLV3 or CLV4) they are working with. This information is critical for selecting the correct reference documentation and following the appropriate implementation standards.

### 1. Smart Contract Reference Documentation

**STRICT MANDATE**: Always consult the authoritative reference documentation in `../common-references/contracts_api_documentation/vault-<version>/` for the specific Vault version being used (e.g., `vault-5-9/`). You MUST strictly verify methods and parameters of objects (e.g., the `vault` object)—NEVER guess method names, signatures, or parameters.

This folder is organized as follows (using Contracts API 4 as the standard):

- **Contracts API V4** (also known as **CLV4**, short for Contracts Language Version 4): Standard for new contracts.
  - Base Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/`
- **Contracts API V3** (also known as **CLV3**, short for Contracts Language Version 3): For legacy or specific V3 requirements.
  - Base Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_3xx/`

### 2. Analysis

- Identify the core logic and parameters of the legacy feature.
- Determine which hooks/events the feature supports (e.g., `pre_posting`, `post_posting`, `scheduled_event`, `scheduled_code`).
- Determine if it should implement a specific interface (e.g., `interest_type_interface` in `deposit.interfaces`).

### 3. State & Parameter Management

- **Metadata**: Add `__smart_contract_feature__ = True` at the top.
- **State**: Transition from direct vault/parameter access to `SmartContractState`. Implement a single `_append_to_state` helper that accepts a configuration object (see [patterns.md](references/patterns.md)) to consolidate parameters and optional balances. This helper MUST ONLY be implemented if the feature defines its own `expected_parameters` or `data_fetchers`.
- **Preloading Prevention**: When using a feature that implements an `_append_to_state` helper (or equivalent logic to consolidate its own parameters into the state object), you MUST NOT preload those same parameters when calling `state_utils.initialise_state` in the smart contract's hooks. This prevents redundant data fetching and ensures the feature remains responsible for its own state management.
- **Parameter Scoping**: The `_append_to_state` helper MUST ONLY consolidate parameters defined within the feature itself. Do NOT add parameters from other features or common modules (like `denomination`) to the state within this helper.
- **External Parameters**: For parameters from other modules (like `denomination`), do NOT fetch them inside the feature logic. Instead, check if they exist in `state` using `state_utils.check_parameters_exist()` and retrieve them from `state.parameters`. All external parameters accessed within a feature MUST be included in the feature's `expected_parameters` list. If they are missing, you MUST NOT return early or return a rejection. Instead, assert that the rejection from `check_parameters_exist` is `None` (e.g. `assert rejection is None, rejection`). This ensures that configuration errors (missing parameters in fetchers) are caught early and fail fast. Refer to [patterns.md](references/patterns.md) for examples.
- **Naming Conventions**: Rigorously follow the naming conventions in [patterns.md](references/patterns.md). Use suffixes (`_PARAM_ID`, `_PARAM`) for parameter constants. **ExpectedParameter object names MUST be constants (all caps) and MUST be defined directly under their corresponding ID constant.** Replace all legacy Derived Parameters with the modern `Attribute` standard. Refer to [patterns.md](references/patterns.md) for naming conventions.
- **ExpectedParameter Attributes**: Ensure all `ExpectedParameter` objects include `triggers_pre_parameter_change_hook` and `triggers_post_parameter_change_hook`. These MUST default to `False` unless the legacy feature explicitly requires them to be `True`. Do NOT include the `constraint` attribute in `ExpectedParameter` objects.
- **Fetcher Filters**: The `ParametersFilter` in a feature's `ParametersObservationFetcher` MUST include all parameter IDs in the feature's `expected_parameters` list, which includes both internal and external parameters. All Observation fetchers (Parameters, Balances, etc.) MUST have their `at` attribute explicitly populated. If not specified in the legacy feature, it MUST default to `DefinedDateTime.EFFECTIVE_DATETIME`.
- **Time Parameters**: Consolidate separate `hour`, `minute`, and `second` parameters into a single string parameter (formatted as "HH:MM:SS") using the `_TIME_PARAM` suffix. These should be retrieved from the string using `hour, minute, second = map(int, time_string.split(":"))`.
- **Configuration**: Use a `NamedTuple` (e.g., `FetchersConfig`) to consolidate fetcher IDs, parameter IDs, and common constants (like precision). Pass this config object to entry-point functions instead of individual IDs. Provide a `DEFAULT_FETCHERS_CONFIG` instance.
- **Docstrings**: Add or update comprehensive docstrings for all functions, excluding test functions. Docstrings MUST follow the Google style and adhere to `ruff` linting rules:
  - The first line (summary) MUST end with a period, question mark, or exclamation point (`D400`, `D415`).
  - One-line docstrings MUST fit on a single line (`D200`).
  - Multi-line docstrings MUST have the summary line start on the first line (`D212`) and have a single blank line between the summary line and the description/Args section (`D205`).
  - Followed by an `Args` section (including types and descriptions) and a `Returns` section (including types and descriptions).

### 4. Logic Refactoring

- **NamedTuples**: Replace unnamed tuples with descriptive **NamedTuples** for all complex return values.
- **Type Annotations**: Add type annotations to all variables when they are created within a function (e.g., `variable_name: type = value`).
- **Prohibited Methods**: Avoid private member access (e.g., `_replace()`). Replace all calls to `vault.get_account_creation_datetime()` with `vault.get_account_activation_datetime()` as this is the standard for modern features. Refer to [patterns.md](references/patterns.md) for alternatives.
- **Constants**: If the feature defines schedules, include `from zoneinfo import ZoneInfo` in the standard-library imports and define a `UTC` constant after the imports: `UTC = ZoneInfo("UTC")`.
- **Entry Points**: Implement standardized entry points based on the feature's role:
  - **Validation**: `validate(*, state, postings, ...)`
  - **Side-Effects**: `handle_withdrawals(...)` or `handle_deposits(...)`. When generating side-effects (e.g., `CustomInstruction`), utilize `posting_utils.create_postings` instead of manual `Posting` instantiation. Refer to [patterns.md](references/patterns.md).
  - **Schedules**: `get_scheduled_events(...)` and `schedule_logic(...)`. `get_scheduled_events` MUST return a `dict[str, ScheduledEvent]` and use `assert` statements for parameter validation. When setting a `start_datetime` for a schedule, it MUST take into account the account's local timezone (`state.vault.events_timezone`) if effective_datetime is being overwritten. Refer to [patterns.md](references/patterns.md) for implementation details.
- **Results**: Return descriptive result NamedTuples for any function producing side-effects (e.g., `HandleWithdrawalsResult`, `ScheduleLogicResult`) ONLY when the function returns multiple different types of objects. If a function only returns a single type of object (e.g., only `custom_instructions`), it MUST return that type directly instead of wrapping it in a NamedTuple. For example, `schedule_logic` should only return `ScheduleLogicResult` if it returns more than just `custom_instructions`. `get_scheduled_events` is an exception and always returns a dictionary.
- **Flattening (Optional)**: Identify and flatten complex or heavily nested logic using a functional approach (e.g., guard clauses, early returns, helper mapping functions). **Favour the use of list comprehensions over `for` loops** for transforming or filtering data. Refer to [patterns.md](references/patterns.md) for functional examples.

### 5. Interface Implementation

- Map the refactored functions to a descriptive interface. Ensure the primary feature consumes this interface to call the secondary feature's logic.

### 6. Testing Update

- **Test Categorization**: All test classes (or individual methods if appropriate) MUST be annotated with the relevant `@pytest.mark` marker:
  - **Unit Tests**: `@pytest.mark.unit`
  - **Simulation Tests**: `@pytest.mark.sim`
  - **End-to-End (e2e) Tests**: `@pytest.mark.e2e`
  - **Accelerated e2e Tests**: `@pytest.mark.accelerated_e2e` (specifically for e2e tests that verify schedules).
- **Unit Tests**: Inherit from `FeatureTest`.
- **Simulation Tests**: Inherit from `inception_sdk.test_framework.contracts.simulation.utils.SimulationTestCase`. Use the `SubTest` pattern and organize resources into `simulation/` subdirectories (accounts, parameters, etc.).
  - **Base Class Pattern**: For complex contracts, use a base test class to define common `parameter_resource_dirs`, `internal_accounts`, and a `get_simulation_test_scenario` helper.
  - **Smart Contract Path**: Place the Smart Contract used for simulation and e2e tests in the root of the feature's test directory (e.g., `tests/<feature_name>/smart_contract.py`). Define the `SMART_CONTRACT` path as a `Path` object (e.g., `SMART_CONTRACT = Path("tests/lending/principal/maximum_loan_principal_sc.py")`). However, you MUST explicitly cast it to a string (e.g., `str(SMART_CONTRACT)`) when using it as a key in `contract_filepaths` or `self.smart_contract_path_to_content` to avoid `KeyError`.
  - **Contract Attributes**: The simulation contract MUST have its `tside` attribute set based on the feature type: `Tside.LIABILITY` for deposit features and `Tside.ASSET` for lending features.
  - **Parameters**: When referencing parameters, utilize the CLU notation (`&{parameter_name}`) directly through the feature's constants, and avoid any manual stripping of this notation. For complex parameter definitions, leverage `parameter_resource_dirs` to point to the feature's CLU resource YAML definitions. When a concrete denomination is required for parameters (e.g., in `parameters.py`), import `DEFAULT_DENOMINATION` from `feature_library.tests.common.test_denomination`.
  - **Timezone Testing**: Simulation tests for features that create `scheduled_events` MUST be parameterized across different timezones. Use `@parameterized.expand(timezones)` from `parameterized` and `tests.sim_utils`. Ensure:
    - The `get_simulation_test_scenario` helper supports a `default_tz` argument.
    - A `create_update_pgtz_instruction` event is included at the start of each simulation to set the Processing Group Timezone.
    - All event and assertion timestamps within the test method are localized using the `default_tz`.
    - All `ExpectedSchedule` run times are converted to UTC (e.g., `run_times=[accrual_event.astimezone(UTC)]`) to match the simulator's internal format.
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
                events=[create_update_pgtz_instruction(start, timezone=default_tz)],
            )
        ] + sub_tests
        ...
    ```
  - **SubTest Design**:
    - **Assertions**: Include `expected_balances_at_ts`, `expected_schedules`, or `expected_contract_notifications` in the same `SubTest` as the event that triggers them.
    - **Exact Timing**: Always assert at the **exact** execution timestamp. Side-effects are processed immediately by the simulator.
  - **Verifying Notifications**: To verify account notifications, use the `expected_contract_notifications` field within a `SubTest`. This field takes a list of `ExpectedContractNotification` objects. Note that all values in the `notification_details` dictionary must be strings.
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
- **End-to-End (e2e) Tests**: Update existing e2e tests or create new ones if they don't exist. Inherit from `inception_sdk.test_framework.endtoend.End2EndTest` or `inception_sdk.test_framework.endtoend.AcceleratedEnd2EndTest`. It is often appropriate to reuse the same Smart Contract as simulation tests, but dedicated contracts can be used if necessary. Organize resources into `e2e/` subdirectories (`accounts.py`, `parameters.py`).
  - **Setup**: In `setUpClass`, configure `endtoend.testhandle` with `CONTRACTS`, `TSIDE_TO_INTERNAL_ACCOUNT_ID`, `PARAMETER_RESOURCE_DIRS`, and `FLAG_DEFINITIONS`.
  - **Helper Preference**: When writing e2e tests, you MUST try to identify and use the correct helper from `endtoend.contracts_helper` in the first instance. If a suitable helper is not available in `contracts_helper`, you should then use `endtoend.core_api_helper`.
  - **Common Helpers**:
    - `endtoend.postings_helper`: Use `inbound_hard_settlement()`, `outbound_hard_settlement()`, `inbound_auth()`, `outbound_auth()`, `auth_adjustment()`, `settlement()`, `create_transfer()`, or `create_custom_instruction()`. Use `get_posting_batch()` to check for rejections.
    - `endtoend.balances_helper`: Use `wait_for_account_balances()` with `BalanceDimensions` to verify account states.
    - `endtoend.schedule_helper`: In accelerated tests, use `trigger_next_schedule_job()` and `wait_for_schedule_job()` to manually execute schedules.
  - **Verification**: Verify feature behavior using the most relevant `endtoend` helpers for the scenario. When a concrete denomination is required for parameters, import `DEFAULT_DENOMINATION` from `feature_library.tests.common.test_denomination`.
- **Event Timing**: Ensure simulation events that require time (e.g. interest application) occur only after their defined duration (frequency) and NOT immediately after simulation start.
- **Cleanup**: Ensure all manual patches in `setUp` are closed using `addCleanup`.
- See [testing.md](references/testing.md) for detailed test standards and patterns.

## Reference Material

- **Patterns**: [patterns.md](references/patterns.md) - State, Entry Points, and Results.
- **Testing**: [testing.md](references/testing.md) - Mocking and cleanup standards.
