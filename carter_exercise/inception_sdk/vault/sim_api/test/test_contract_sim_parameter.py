# standard libs
from datetime import datetime
from decimal import Decimal

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateParameterAccountConstraint(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter=dict(id="1", constraint=dict(account_constraint={})),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameter(
            id="1",
            constraint=core_api.AccountConstraint(
                account_constraint=core_api.AccountConstraintValue()
            ),
        ),
    )


class TestCreateParameterDatetimeConstraint(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter=dict(
            id="1",
            constraint=dict(
                date_time_constraint=dict(
                    precision="MINUTE",
                    earliest="2024-01-01T00:00:00+00:00",
                    latest="2024-12-31T00:00:00+00:00",
                )
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameter(
            id="1",
            constraint=core_api.DatetimeConstraint(
                date_time_constraint=core_api.DatetimeConstraintValue(
                    precision=core_api.DatetimeConstraintPrecision.MINUTE,
                    earliest=datetime(2024, 1, 1, tzinfo=UTC),
                    latest=datetime(2024, 12, 31, tzinfo=UTC),
                )
            ),
        ),
    )


class TestCreateParameterDecimalConstraint(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter=dict(
            id="1",
            constraint=dict(
                decimal_constraint=dict(
                    min_value="0",
                    max_value="10",
                )
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameter(
            id="1",
            constraint=core_api.DecimalConstraint(
                decimal_constraint=core_api.DecimalConstraintValue(
                    min_value=Decimal(0),
                    max_value=Decimal(10),
                )
            ),
        ),
    )


class TestCreateParameterEnumerationConstraint(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter=dict(
            id="1",
            constraint=dict(
                enumeration_constraint=dict(
                    permitted_values=["a", "b"],
                )
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameter(
            id="1",
            constraint=core_api.EnumerationConstraint(
                enumeration_constraint=core_api.EnumerationConstraintValue(
                    permitted_values=["a", "b"],
                )
            ),
        ),
    )


class TestCreateParameterStringConstraint(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter=dict(
            id="1",
            constraint=dict(
                string_constraint=dict(
                    min_length=0,
                    max_length=10,
                )
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameter(
            id="1",
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(
                    min_length=0,
                    max_length=10,
                )
            ),
        ),
    )


class TestUpdateSmartContractParam(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        update_smart_contract_param=dict(
            smart_contract_version_id="1",
            parameter_name="2",
            new_parameter_value="3",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.UpdateSmartContractParam(
            smart_contract_version_id="1",
            parameter_name="2",
            new_parameter_value="3",
        ),
    )
