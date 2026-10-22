# standard libs
import uuid
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as contract_sim
from inception_sdk.test_framework.contracts.simulation.helper import (
    batch_create_parameter_values,
    create_parameter,
    create_parameter_value,
    update_parameter_value,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    skipForVaultVersionLessThan,
)


class TestHelper(SimulationTestCase):

    def test_parameter_value_creation_string_constraint(self):
        parameter_id = "new_string_param_test"
        account_id = "123"
        str_parameter_value = "test string"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id=parameter_id,
            value=core_api.StringParameterValue(string_value=str_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'string_value:\"{str_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
        ]

        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_account_constraint(self):
        parameter_id = "new_account_param_test"
        account_id = "123"
        account_parameter_value = "5"

        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.AccountConstraint(
                account_constraint=core_api.AccountConstraintValue()
            ),
        )
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id=parameter_id,
            value=core_api.AccountIdParameterValue(account_id_value=account_parameter_value),
            effective_from_timestamp=start,
            account_config_group_id=None,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id, account_parameter_value],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'account_id_value:\"{account_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_decimal_constraint(self):
        parameter_id = "new_decimal_param_test"
        decimal_parameter_value = "17"
        account_id = "123"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id="new_decimal_param_test",
            constraint=core_api.DecimalConstraint(
                decimal_constraint=core_api.DecimalConstraintValue(min_value="0", max_value="100")
            ),
        )
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id=parameter_id,
            value=core_api.DecimalParameterValue(decimal_value=decimal_parameter_value),
            effective_from_timestamp=start,
            account_config_group_id=None,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'decimal_value:\"{decimal_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_enumeration_constraint(self):
        parameter_id = "new_enumeration_param_test"
        account_id = "123"
        enumeration_parameter_value = "red"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.EnumerationConstraint(
                enumeration_constraint=core_api.EnumerationConstraintValue(
                    permitted_values=["green", "gold", "red"]
                )
            ),
        )
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id=parameter_id,
            value=core_api.EnumerationParameterValue(enumeration_value=enumeration_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'enumeration_value:\"{enumeration_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_date_time_constraint(self):
        parameter_id = "new_datetime_param_test"
        account_id = "123"
        date_time_parameter_value = datetime(year=2020, month=1, day=2, tzinfo=timezone.utc)
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id="new_datetime_param_test",
            constraint=core_api.DatetimeConstraint(
                date_time_constraint=core_api.DatetimeConstraintValue(
                    precision=core_api.DatetimeConstraintPrecision.MINUTE,
                    earliest="2020-01-01T00:00:00Z",
                    latest="2040-01-01T00:00:00Z",
                )
            ),
        )
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id=parameter_id,
            value=core_api.DatetimeParameterValue(date_time_value=date_time_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        # seconds is base on the parameter value given so this should be constant.
        expected_seconds = "{seconds:1577923200}"
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'date_time_value:{expected_seconds}\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
        ]
        str_res = str(res)
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_string_constraint(self):
        parameter_id = "new_string_param_test"
        account_id = "123"
        str_parameter_value = "test string"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=parameter_id,
            value=core_api.StringParameterValue(string_value=str_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'string_value:\"{str_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]

        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_account_constraint(self):
        parameter_id = "new_account_param_test"
        account_id = "123"
        account_parameter_value = "5"

        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.AccountConstraint(
                account_constraint=core_api.AccountConstraintValue()
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=parameter_id,
            value=core_api.AccountIdParameterValue(account_id_value=account_parameter_value),
            effective_from_timestamp=start,
            account_config_group_id=None,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id, account_parameter_value],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'account_id_value:\"{account_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_decimal_constraint(self):
        parameter_id = "new_decimal_param_test"
        decimal_parameter_value = "17"
        account_id = "123"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id="new_decimal_param_test",
            constraint=core_api.DecimalConstraint(
                decimal_constraint=core_api.DecimalConstraintValue(min_value="0", max_value="100")
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=parameter_id,
            value=core_api.DecimalParameterValue(decimal_value=decimal_parameter_value),
            effective_from_timestamp=start,
            account_config_group_id=None,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'decimal_value:\"{decimal_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_enumeration_constraint(self):
        parameter_id = "new_enumeration_param_test"
        account_id = "123"
        enumeration_parameter_value = "red"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id=parameter_id,
            constraint=core_api.EnumerationConstraint(
                enumeration_constraint=core_api.EnumerationConstraintValue(
                    permitted_values=["green", "gold", "red"]
                )
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=parameter_id,
            value=core_api.EnumerationParameterValue(enumeration_value=enumeration_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'enumeration_value:\"{enumeration_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_date_time_constraint(self):
        parameter_id = "new_datetime_param_test"
        account_id = "123"
        date_time_parameter_value = datetime(year=2020, month=1, day=2, tzinfo=timezone.utc)
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)
        parameter = core_api.ParameterResource(
            id="new_datetime_param_test",
            constraint=core_api.DatetimeConstraint(
                date_time_constraint=core_api.DatetimeConstraintValue(
                    precision=core_api.DatetimeConstraintPrecision.MINUTE,
                    earliest="2020-01-01T00:00:00Z",
                    latest="2040-01-01T00:00:00Z",
                )
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=parameter_id,
            value=core_api.DatetimeParameterValue(date_time_value=date_time_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        # seconds is base on the parameter value given so this should be constant.
        expected_seconds = "{seconds:1577923200}"
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'date_time_value:{expected_seconds}\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]
        str_res = str(res)
        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    def test_parameter_value_creation_and_update_with_clu_syntax(self):
        clu_parameter_id = "&{new_string_param_test}"
        parameter_id = "new_string_param_test"
        account_id = "123"
        str_parameter_value = "test string"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        update_ts = start + relativedelta(minutes=1)
        end = start + relativedelta(minutes=2)

        parameter = core_api.ParameterResource(
            id=clu_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        parameter_value_id = str(uuid.uuid4())
        parameter_value = contract_sim.CreateParameterValue(
            id=parameter_value_id,
            parameter_id=clu_parameter_id,
            value=core_api.StringParameterValue(string_value=str_parameter_value),
            effective_from_timestamp=start,
            is_backdated=False,
            cancel_timestamp=None,
            account_id=account_id,
        )
        new_parameter_value = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=parameter_value_id, effective_to_timestamp=update_ts, is_cancelled=False
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        events = [
            create_parameter(timestamp=start, parameter=parameter),
            create_parameter_value(timestamp=start, parameter_value=parameter_value),
            update_parameter_value(timestamp=start, update_parameter_value=new_parameter_value),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        # the parameter IDs in the logs here do not have the CLU syntax
        # and hence prove that the CLU syntax is being stripped out
        search_strings = [
            f'created parameter "{parameter_id}"',
            f"['created value \\'string_value:\"{str_parameter_value}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id}"\']',
            f'[\'updated parameter value "{parameter_value_id}" for parameter "{parameter_id}" '
            f'with Account owner "{account_id}"\']',
        ]

        for search_string in search_strings:
            self.assertIn(search_string, str_res)

    @skipForVaultVersionLessThan(
        Version("5.8.0"),
        "Prior to Vault 5.8.0, Contract Simulation did not support Batch "
        "Creation of Parameter Values.",
    )
    def test_parameter_values_batch_creation(self):
        parameter_id_1 = "parameter-id-1"
        parameter_id_2 = "parameter-id-2"
        account_id = "123"
        str_value_1 = "string-value-1"
        str_value_2 = "string-value-2"
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=1)
        parameter_1 = core_api.ParameterResource(
            id=parameter_id_1,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        parameter_2 = core_api.ParameterResource(
            id=parameter_id_2,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        batch_request = contract_sim.BatchCreateParameterValues(
            parameter_values=[
                core_api.CreateParameterValueV1ParameterValue(
                    parameter_id=parameter_id_1,
                    value=core_api.StringParameterValue(string_value=str_value_1),
                    is_backdated=False,
                    cancel_timestamp=None,
                    account_id=account_id,
                ),
                core_api.CreateParameterValueV1ParameterValue(
                    parameter_id=parameter_id_2,
                    value=core_api.StringParameterValue(string_value=str_value_2),
                    is_backdated=False,
                    cancel_timestamp=None,
                    account_id=account_id,
                ),
            ],
        )
        events = [
            create_parameter(timestamp=start, parameter=parameter_1),
            create_parameter(timestamp=start, parameter=parameter_2),
            batch_create_parameter_values(
                timestamp=start + relativedelta(seconds=5),
                batch_create_parameter_values=batch_request,
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[account_id],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{parameter_id_1}"',
            f'created parameter "{parameter_id_2}"',
            f"['created value \\'string_value:\"{str_value_1}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id_1}"\', ',
            f"'created value \\'string_value:\"{str_value_2}\"\\' "
            f'owned by account "{account_id}" for parameter "{parameter_id_2}"\']',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)
