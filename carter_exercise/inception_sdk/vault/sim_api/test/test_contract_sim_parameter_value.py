# standard libs
from datetime import datetime
from decimal import Decimal

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateParameterValueAccount(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"account_id_value": "4"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": "5",
            "global": None,
            "parameter_value_hierarchy_node_id": None,
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.AccountIdParameterValue(account_id_value="4"),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            account_id="5",
        ),
    )


class TestCreateParameterValueDatetime(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"date_time_value": "2024-12-31T00:00:00+00:00"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": "5",
            "global": None,
            "parameter_value_hierarchy_node_id": None,
        },
    )

    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            account_id="5",
        ),
    )


class TestCreateParameterValueDecimal(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"decimal_value": "1.234"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": "5",
            "global": None,
            "parameter_value_hierarchy_node_id": None,
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.DecimalParameterValue(decimal_value=Decimal("1.234")),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            account_id="5",
        ),
    )


class TestCreateParameterValueEnumeration(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"enumeration_value": "enum"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": "5",
            "global": None,
            "parameter_value_hierarchy_node_id": None,
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.EnumerationParameterValue(enumeration_value="enum"),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            account_id="5",
        ),
    )


class TestCreateParameterValueString(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"string_value": "string"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": "5",
            "global": None,
            "parameter_value_hierarchy_node_id": None,
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.StringParameterValue(string_value="string"),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            account_id="5",
        ),
    )


class TestCreateParameterValueGlobalOwner(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"string_value": "string"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": None,
            "global": True,
            "parameter_value_hierarchy_node_id": None,
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.StringParameterValue(string_value="string"),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            global_=True,
        ),
    )


class TestCreateParameterValueParameterHierarchyOwner(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value={
            "id": None,
            "parameter_id": "3",
            "value": {"string_value": "string"},
            "effective_from_timestamp": "2024-12-31T00:00:00+00:00",
            "cancel_timestamp": "2025-12-31T00:00:00+00:00",
            "is_backdated": False,
            "account_id": None,
            "global": None,
            "parameter_value_hierarchy_node_id": "5",
        },
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValue(
            id=None,
            parameter_id="3",
            value=core_api.StringParameterValue(string_value="string"),
            effective_from_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            cancel_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            is_backdated=False,
            parameter_value_hierarchy_node_id="5",
        ),
    )


class TestUpdateParameterValue(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        update_parameter_value=dict(
            parameter_value=dict(
                id="6",
                effective_to_timestamp="2025-12-31T00:00:00+00:00",
                is_cancelled=False,
            ),
            update_mask=dict(
                paths=["effective_to_timestamp"],
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id="6",
                effective_to_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
                is_cancelled=False,
            ),
            update_mask=core_api.UpdateMask(
                paths=["effective_to_timestamp"],
            ),
        ),
    )
