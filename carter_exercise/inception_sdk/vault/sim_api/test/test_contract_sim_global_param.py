# standard libs
from datetime import datetime
from decimal import Decimal
from unittest import TestCase

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.pydantic_types import OneOfException
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateGlobalParameterInstructionDate(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_global_parameter=dict(
            global_parameter={
                "date": dict(
                    type="DATE_TYPE_ABSOLUTE",
                    start="2024-01-01",
                    end="2024-12-31",
                ),
                "denomination": None,
                "description": "description",
                "display_name": "display name",
                "id": "global_param",
                "number": None,
                "str": None,
            },
            initial_value="2024-06-01",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateGlobalParameter(
            global_parameter=sim.GlobalParameter(
                date_=sim.DateType(
                    type=core_api.DateValueType.ABSOLUTE,
                    start=sim.DateValue(year=2024, month=1, day=1),
                    end=sim.DateValue(year=2024, month=12, day=31),
                ),
                description="description",
                display_name="display name",
                id="global_param",
            ),
            initial_value="2024-06-01",
        ),
    )


class TestCreateGlobalParameterInstructionNumber(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_global_parameter=dict(
            global_parameter={
                "date": None,
                "denomination": None,
                "description": "description",
                "display_name": "display name",
                "id": "global_param",
                "number": dict(
                    value_type="NUMBER_FIELD_DISPLAY_STYLE_PLAIN",
                    min_value="1.234",
                    max_value="12.34",
                    step="0.001",
                ),
                "str": None,
            },
            initial_value="2.345",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateGlobalParameter(
            global_parameter=sim.GlobalParameter(
                description="description",
                display_name="display name",
                id="global_param",
                number=sim.NumberType(
                    value_type=core_api.NumberValueType.PLAIN,
                    min_value=Decimal("1.234"),
                    max_value=Decimal("12.34"),
                    step=Decimal("0.001"),
                ),
            ),
            initial_value="2.345",
        ),
    )


class TestCreateGlobalParameterInstructionDenomination(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_global_parameter=dict(
            global_parameter={
                "date": None,
                "denomination": dict(
                    permitted_denominations=["AUD"],
                ),
                "description": "description",
                "display_name": "display name",
                "id": "global_param",
                "number": None,
                "str": None,
            },
            initial_value="AUD",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateGlobalParameter(
            global_parameter=sim.GlobalParameter(
                denomination=sim.DenominationType(
                    permitted_denominations=["AUD"],
                ),
                description="description",
                display_name="display name",
                id="global_param",
            ),
            initial_value="AUD",
        ),
    )


class TestCreateGlobalParameterInstructionString(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_global_parameter=dict(
            global_parameter={
                "date": None,
                "denomination": None,
                "description": "description",
                "display_name": "display name",
                "id": "global_param",
                "number": None,
                "str": dict(),
            },
            initial_value="some string",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateGlobalParameter(
            global_parameter=sim.GlobalParameter(
                description="description",
                display_name="display name",
                id="global_param",
                str_=sim.StringType(),
            ),
            initial_value="some string",
        ),
    )


class TestCreateGlobalParameterInstructionValidation(TestCase):

    def test_validation(self):
        with self.assertRaises(OneOfException):
            sim.GlobalParameter.model_validate(
                dict(
                    description="description",
                    display_name="display name",
                    id="global_param",
                    number=dict(
                        value_type="NUMBER_FIELD_DISPLAY_STYLE_PLAIN",
                        min_value=Decimal("1.234"),
                        max_value=Decimal("12.34"),
                        step=Decimal("0.01"),
                    ),
                    str_=dict(),
                )
            )
