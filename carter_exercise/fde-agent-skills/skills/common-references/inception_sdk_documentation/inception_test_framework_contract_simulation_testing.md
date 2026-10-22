_© Thought Machine Group Limited 2021_

_All Rights Reserved. Confidential - Limited Distribution to Authorized Persons Only, Pursuant to the Terms of the Agreement between You and Thought Machine Group Limited granting you a licence for the software to which this documentation relates. This software is protected as an unpublished work and constitutes a trade secret of Thought Machine Group Limited, 5 New Street Square, London EC4A 3TW._

# Inception Test Framework Contract Simulation Testing

## General information

Simulation tests are provided for each product and can be found in `library/<product_name>/contracts/tests/simulation/<product_name>_test.py`. These tests are designed to demonstrate the features of a product such as charging fees, accruing interest, and preventing postings by creating a series of Events (e.g. an inbound posting) which are sent to the `/v1/contracts:simulate` endpoint and then parsing the response to verify that e.g. the correct balances have been updated. The test defines the simulated time-period which can be days or years, allowing tests on scheduled events to also be created.

## Configuration

See `documentation/inception_test_framework_configuration.md`

## Running Simulation Tests

Thought Machine uses Please internally as the BUILD system which can be used for running tests (among other things). Externally, the Python `unittest` module can be used to run the packaged tests. Instructions for each method are given below.

### Python

Ensure that all necessary Python packages are present by running:

```bash
pip install -r requirements.txt
```

> NOTE: The minimum supported Python version is `3.10`

To run all simulation tests in a file for a product, run:

```bash
python3.10 -m unittest library/<product>/test/simulation/<test_file>.py
```

To run a specific test, run:

```bash
python3.10 -m unittest library.<product>.test.simulation.<file>.<TestClass>.<test_name>
```

### Please

To run all tests, run `plz test`.

To run a specific test, run `plz test //path/to/build/file:test_name`

E.g. `plz test //library/current_account/test/simulation:current_account_test`

To run all tests in a folder, you can use `plz test //path/to/folder/...`

## Navigating the Contract Simulation Test Utils

The Inception Release folder contains a set of helper utilities for writing simulation tests along with tests that test the functionality of the helpers themselves. From the top-level of the folder, these can be found by navigating to `inception_sdk/test_framework/contracts/simulation/`. The below table highlights some of the key files and folders and gives a brief summary of their contents:

| File or Folder                      | Description                                                                                                                                              |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| utils.py                            | This module exposes helper methods for constructing test scenarios                                                                                       |
| helper.py                           | Exposes helper methods for creating simulation instructions                                                                                              |
| vault_caller.py                     | A helper script which provides a way of calling the simulate endpoint without writing REST requests directly. Available from the Vault Documentation Hub |
| common/data_objects/data_objects.py | Exposes data objects used by the simulation test framework                                                                                               |
| common/data_objects/events/*        | Exposes data objects representing the Simulation API instructions                                                                                        |

## Helper Methods

It is recommended to make use of the `SubTest` data object (see `inception_sdk/test_framework/contracts/simulation/data_objects/data_objects.py`) for constructing simulation tests. This allows the construction of an easier-to-follow narrative of event and expected side-effects rather than a list of events followed by a list of side-effects/checks. An example of the suggested structure is shown below:

```python
def test_grace_period(self):
    # Checks for scenarios when grace period is active.
    start = datetime(2019, 1, 1, tzinfo=timezone.utc)
    end = datetime(2019, 1, 25, tzinfo=timezone.utc)
    template_params = default_template_params.copy()
    instance_params = default_instance_params.copy()
    instance_params["deposit_period"] = "0"
    instance_params["cool_off_period"] = "0"
    instance_params["grace_period"] = "11"
    instance_params["period_end_hour"] = "0"

    sub_test_1_ts = start + relativedelta(days=8, hour=21, minute=0, second=1)
    sub_test_2_ts = start + relativedelta(days=9, hours=23, minutes=59, seconds=59)
    sub_test_3_ts = start + relativedelta(days=11, hour=0, minute=0, second=1)
    sub_test_4_ts = start + relativedelta(days=12, hour=0, minute=0, second=1)

    sub_tests = [
        SubTest(
            description="Withdrawal within grace period should be accepted",
            events=[
                create_inbound_hard_settlement_instruction(
                    target_account_id=TD_ACCOUNT,
                    amount="100.00",
                    event_datetime=start + relativedelta(days=1),
                ),
                create_outbound_hard_settlement_instruction(
                    target_account_id=TD_ACCOUNT,
                    amount="25.00",
                    event_datetime=sub_test_1_ts,
                ),
            ],
            expected_balances_at_ts={
                sub_test_1_ts: {TD_ACCOUNT: [(GBP_DEFAULT_DIMENSIONS, "75")]},
            },
        ),
        SubTest(
            description="Deposit within grace period should be accepted",
            events=[
                create_inbound_hard_settlement_instruction(
                    target_account_id=TD_ACCOUNT,
                    amount="17.00",
                    event_datetime=sub_test_2_ts,
                ),
            ],
            expected_balances_at_ts={
                sub_test_2_ts: {TD_ACCOUNT: [(GBP_DEFAULT_DIMENSIONS, "92")]},
            },
        ),
        SubTest(
            description="Deposit outside grace period should be rejected.",
            events=[
                create_inbound_hard_settlement_instruction(
                    target_account_id=TD_ACCOUNT,
                    amount="18.00",
                    event_datetime=sub_test_3_ts,
                ),
            ],
            expected_balances_at_ts={
                sub_test_3_ts: {TD_ACCOUNT: [(GBP_DEFAULT_DIMENSIONS, "92")]},
            },
        ),
        SubTest(
            description="Withdrawal outside grace period should be rejected.",
            events=[
                create_outbound_hard_settlement_instruction(
                    target_account_id=TD_ACCOUNT,
                    amount="17.00",
                    event_datetime=sub_test_4_ts,
                ),
            ],
            expected_balances_at_ts={
                sub_test_4_ts: {TD_ACCOUNT: [(GBP_DEFAULT_DIMENSIONS, "92")]},
            },
        ),
    ]

    test_scenario = self._get_simulation_test_scenario(
        start=start,
        end=end,
        sub_tests=sub_tests,
        template_params=template_params,
        instance_params=instance_params,
        internal_accounts=default_internal_accounts,
    )
    self.run_test_scenario(test_scenario)
```

## Accounts V2 Simulation

Following the release of Accounts V2, the Inception Test Framework has been updated to support the simulation of Accounts V2.

The SimulationTestScenario object has been updated with a new argument, use_v1_accounts, which is set to True by default. To use Accounts V2 in all Simulation Tests, when creating the SimulationTestScenario, set this new argument to False, as shown below:

```python
SimulationTestScenario(
    start=start,
    end=end,
    sub_tests=sub_tests,
    contract_config=contract_config,
    internal_accounts=internal_accounts,
    debug=debug,
    use_v1_accounts=False,
)
```

With Accounts V2, if an error is thrown, the Simulation will not immediately terminate when the Smart Contract raises an Error. Instead, it will be returned in the Simulation Response, allowing more scenarios to be tested via Simulation Testing.

For example, a test scenario can assert on an Error Message, a fix could be implemented (ex: Account Conversion to Product Version with a fix), then assert that the Error is no longer being thrown by the contract.

Additional simulation test assertions are now available for testing:

- Contract Errors
- Activation Rejections
- Conversion Rejections
- Deactivation Rejections

An example of the suggested structure for Simulation of Accounts V2 is shown below:

```python
def test_expected_contract_error(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check Account Activation Rejection",
                expected_contract_errors=[
                    ExpectedContractError(
                        timestamp=start,
                        account_id=self.account_id_base,
                        exception_type="InvalidOperation",
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            use_v1_accounts=False,
        )

        self.run_test_scenario(test_scenario)
```

## CLU Syntax Support

The test framework has built-in support for CLU reference syntax in simulation tests and will remove reference syntax within contracts and supervisor contracts prior to simulation execution.
For example, if the contract contains:

```python
vault.get_flag_timeseries(flag="&{my_flag_definition}")
```

then `&{my_flag_definition}` will be replaced with `my_flag_definition`, resulting in:

```python
vault.get_flag_timeseries(flag="my_flag_definition")
```

This applies to all resource types and the test writer must ensure that the relevant resources are created in the simulation. This can be done in two ways:

1. The `SimulationTestCase` exposes `calendar_ids: list[str]` and `flag_definition_ids: list[str]` as class attributes. If populated, the test framework will automatically insert relevant `create_calendar` and `create_flag_definition` instructions at the beginning of the simulation window for the test writer.
2. The test writer can manually insert the desired instructions within their tests (e.g. in the example above, add `create_flag_definition(id="my_flag_definition", timestamp=<desired_timestamp>)` to a `SubTest`'s events).

This approach is different to the end-to-end framework as the simulator inherently provides test isolation and there is no need to manipulate resource ids. Please refer to [E2E CLU Syntax Support](/documentation/inception_test_framework_e2e.md#clu-syntax-support) for more information.

## Parameters

In the Core API, `parameter_value.id` is generated by Vault on creation and returned to the client
in the response. This ID is then required when making an `UpdateParameterValue` request for the
given parameter value. The E2E framework supports accessing this natively since
it calls the Core API directly.

In contrast, the simulation framework allows the `id` field to be explicitly passed into the
`CreateParameterValue` simulation event. This allows subsequent updating of the Parameter Value.
To use account and globally owned parameter values within simulation tests,
the required resources can be provided in the `parameters` and
`globally_owned_parameter_values` attributes in `SimulationTestScenario` respectively.

The simulation framework provides the helper function `create_parameter_resource_mapping()`
to create a mapping from `parameter_id` to the tuple `(parameter_value, parameter_value_id)` where
the `parameter_value_id` is a generated UUID. This mapping links the `parameter_id` to the
specific `parameter_value_id` to support updating this specific parameter value within a subtest.

Note: Currently, there is no way to update parameter values that are created in the `create_options`
of an account creation instruction, such as creating the accounts in the test set up.
This limitation will be addressed in a future update.

### Example Usage of Parameter Value Ids

```python
    def test_example_parameter_value_mapping_usage(self):
        # Define globally owned parameter values
        globally_owned_parameter_values: dict[str, core_api.ParameterValue] = {
            "SOME_DATETIME_PARAMETER_RESOURCE": core_api.DatetimeParameterValue(
                date_time_value=datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
            ),
        }

        # Create a mapping from parameter_id to (parameter_value, parameter_value_id)
        globally_owned_parameter_value_mapping = create_parameter_resource_mapping(
            globally_owned_parameter_values
        )

        # Use the mapped ID to construct an update event
        new_parameter_value = sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=globally_owned_parameter_value_mapping[
                    "SOME_DATETIME_PARAMETER_RESOURCE"
                ][1],
                effective_to_timestamp=start + relativedelta(seconds=5),
                is_cancelled=False,
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )
```
