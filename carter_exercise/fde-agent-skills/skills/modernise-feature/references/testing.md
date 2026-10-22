# Modern Testing Standards

This document defines the testing standards for features in the `feature_library`.

## 1. Unit Tests

- **Base Class**: Inherit from `inception_sdk.test_framework.contracts.unit.common.FeatureTest`.
- **Mock State**: Use `MagicMock` to directly mock `SmartContractState` and populate its attributes (`vault`, `effective_datetime`, `parameters`, `balances`).
- **Mocking Strategy**: **Favour `@patch.object` over `@patch` or the `with patch(...)` context manager** for better type safety and to avoid hardcoded string paths. When mocking a function imported from another module (e.g. `balance_utils.get_available_balance`), patch it where it is used in the feature module.
- **Denomination**: When a concrete denomination is required in unit tests (e.g. for `setup_mock_data`), you MUST import `DEFAULT_DENOMINATION` from `tests.common.test_denomination`.
- **Patch Cleanup**: If using `patch.start()` in `setUp`, always include `self.addCleanup(patcher.stop)` to prevent mock pollution across tests.
- **Sentinels**: Use `sentinel` objects for values that do not affect the test outcome. For `contracts_api` objects that require validation, use the sentinel classes in `inception_sdk.test_framework.contracts.unit.contracts_api_sentinels` (e.g., `SentinelCustomInstruction`).

### `setup_mock_data` Helper

Implement a `setup_mock_data` helper in your test class to centralize the creation of mock vaults, fetchers, and states.

```python
def setup_mock_data(self, default_bal: Decimal = Decimal(0)):
    # 1. Define mock parameters and balances
    # 2. Create mock vault with fetchers mapping
    self.mock_vault = self.create_mock(
        account_id=ACCOUNT_ID,
        balances_observation_fetchers_mapping={...},
        parameters_observation_fetchers_mapping={...},
    )
    # 3. Create mock state for testing logic
    self.state = MagicMock(
        vault=self.mock_vault,
        parameters={...},
        balances={...},
    )
```

### Posting Helpers

Create specialized helpers to generate realistic `InboundHardSettlement` or `OutboundHardSettlement` objects with appropriate `committed_postings` for your feature.

```python
def withdrawal_posting(self, amount: Decimal) -> OutboundHardSettlement:
    withdrawal = OutboundHardSettlement(amount=amount, ...)
    withdrawal._set_output_attributes(committed_postings=[...])
    return withdrawal
```

## 2. Simulation Tests

Simulation tests provide end-to-end verification by simulating the vault's behavior over time.

### Directory Structure

Organize simulation tests into a `simulation/` directory, with the Smart Contract shared with e2e tests located in the feature's test root:

- `smart_contract.py`: A minimal wrapper contract that imports the feature being tested, located in `tests/<feature_group>/<feature_name>/`. It MUST define `tside` as `Tside.LIABILITY` for deposit features or `Tside.ASSET` for lending features.
- `simulation/accounts.py`: Defines default internal and customer accounts. It MUST use `dict[str, str]` for `default_internal_accounts` and import `ASSET` or `LIABILITY` from `inception_sdk.test_framework.common.constants`.

    ```python
    from inception_sdk.test_framework.common.constants import ASSET, LIABILITY

    CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
    DUMMY_INTERNAL_ACCOUNT = "DUMMY_ACCOUNT"

    default_internal_accounts: dict[str, str] = {
        DUMMY_INTERNAL_ACCOUNT: LIABILITY,
    }
    ```
- `simulation/dimensions.py`: Defines balance dimensions (addresses, assets, denominations).
- `simulation/parameters.py`: Defines default parameter values. When a concrete denomination is required, import `DEFAULT_DENOMINATION` from `feature_library.tests.common.test_denomination`.
- `simulation/test_<feature_name>.py`: The main test file containing simulation logic.

### Base Test Class
Implement a base test class to centralize common configuration and scenario creation. Utilize `parameter_resource_dirs` to refer to CLU resource definitions instead of manually defining `ParameterResource` objects with stripped notation.

```python
SMART_CONTRACT = Path("tests/some_feature/smart_contract.py")

UTC = ZoneInfo("UTC")

class FeatureBaseTest(SimulationTestCase):
    # Use resource directories for CLU parameters
    parameter_resource_dirs = [
        str(Path("src/feature_library/some_feature/parameter_resource_defs")),
        str(Path("src/feature_library/common/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = []
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=UTC)


    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        debug=False,
        default_tz: ZoneInfo | None = None,
    ):
        localised_sub_tests: list[SubTest] = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz or UTC)],
            )
        ] + sub_tests

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[str(SMART_CONTRACT)],
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[dimensions.DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            parameters=self.parameters,
            debug=debug,
        )
```

### `SubTest` Pattern
Use `SubTest` to break down simulation scenarios into logical, verifiable steps. For features with schedules, use `@parameterized.expand(timezones)` to ensure robust behavior across local time offsets.

```python
@parameterized.expand(timezones)
@pytest.mark.sim
def test_feature_behavior(self, default_tz: ZoneInfo):
    # Localize timestamps to the test timezone
    start = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=default_tz)
    accrual_event = start.replace(hour=23, minute=59, second=59)
    end = accrual_event + relativedelta(seconds=1)

    sub_tests = [
        SubTest(
            description="Initial deposit",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="100",
                    event_datetime=start,
                    target_account_id=accounts.CUSTOMER_ACCOUNT,
                    internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    denomination=dimensions.DEFAULT_DENOMINATION,
                ),
            ],
            expected_balances_at_ts={
                start: {
                    accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(100))]
                }
            },
        ),
        SubTest(
            description="Check schedule creation",
            events=[],
            expected_schedules=[
                ExpectedSchedule(
                    # Convert to UTC for matching against simulator records
                    run_times=[accrual_event.astimezone(UTC)],
                    event_id="ACCRUE_INTEREST",
                    account_id=accounts.CUSTOMER_ACCOUNT,
                )
            ],
        ),
    ]

    test_scenario = self.get_simulation_test_scenario(
        start=start, 
        end=end, 
        sub_tests=sub_tests,
        default_tz=default_tz
    )
    self.run_test_scenario(test_scenario)
```

### Verification

- **Balances**: Use `expected_balances_at_ts` to verify balance transitions.
- **Notifications**: Use `expected_contract_notifications` to verify triggered events.
- **Rejections**: Use `ExpectedRejection` to verify validation logic.

### Event Timing & Windows

When testing time-dependent logic (e.g., schedules, frequencies), ensure events are simulated realistically:

- **Frequency Adherence**: Events that require time (like interest application) MUST NOT happen immediately after simulation start. They must occur after the duration defined by their frequency (e.g., one month for monthly frequency).
- **Simulation Windows**: Set the simulation `start` and `end` times to properly encompass the expected event.
  - Example: For a monthly interest application starting on Jan 1st, the simulation must run until at least Feb 1st to verify the application logic.
- **Buffer**: Always ensure the simulation start time is at least one second before the first event or schedule activation.


## 3. End-to-End (e2e) Tests

End-to-end tests verify feature behavior in a live-like environment using the Inception SDK's e2e framework.

### Directory Structure

Organize e2e tests into an `e2e/` directory:

- `e2e/parameters.py`: Defines default parameter values for account creation. When a concrete denomination is required, import `DEFAULT_DENOMINATION` from `feature_library.tests.common.test_denomination`.

- `e2e/test_<feature_name>.py`: The main test file containing e2e scenarios.

### Base Test Class

Configure the e2e environment by populating `endtoend.testhandle` attributes within `setUpClass` to ensure configuration is local to the test class and prevent clashes.

```python
from inception_sdk.test_framework import endtoend

class FeatureE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/some_feature/smart_contract.py")),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/some_feature/parameter_resource_defs")),
            str(Path("src/feature_library/common/parameter_resource_defs")),
        ]
        super().setUpClass()

    @pytest.mark.accelerated_e2e
    def test_feature_behavior(self):
        endtoend.standard_setup()
        # ... implementation using endtoend helpers ...
```

## 4. Mock Expectations
...
Use `assert_has_calls` or `assert_called_once_with` to verify exact arguments.

## 4. Testing `validate` & Handlers

- **Rejection Testing**: Assert that `validate` returns the expected `Rejection` object with the correct message and reason code.
- **Side Effect Testing**: When testing `handle_withdrawals` or similar, verify the returned `NamedTuple` contains the correct `CustomInstruction` and `AccountNotificationDirective` lists.
