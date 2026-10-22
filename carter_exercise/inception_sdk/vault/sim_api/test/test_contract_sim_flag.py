# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateAccountFlag(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_flag=dict(
            account_id="1",
            description="description",
            effective_timestamp="2024-12-31T00:00:00+00:00",
            expiry_timestamp="2025-12-31T00:00:00+00:00",
            flag_definition_id="2",
            is_backdated=False,
            value="FLAG_VALUE_ON",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateFlagForAccount(
            account_id="1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            flag_definition_id="2",
            is_backdated=False,
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        ),
    )


class TestCreateCustomerFlag(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_flag=dict(
            customer_id="1",
            description="description",
            effective_timestamp="2024-12-31T00:00:00+00:00",
            expiry_timestamp="2025-12-31T00:00:00+00:00",
            flag_definition_id="2",
            is_backdated=False,
            value="FLAG_VALUE_ON",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateFlagForCustomer(
            customer_id="1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            flag_definition_id="2",
            is_backdated=False,
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        ),
    )


class TestCreatePaymentDeviceFlag(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_flag=dict(
            description="description",
            effective_timestamp="2024-12-31T00:00:00+00:00",
            expiry_timestamp="2025-12-31T00:00:00+00:00",
            flag_definition_id="1",
            is_backdated=False,
            payment_device_id="2",
            value="FLAG_VALUE_ON",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateFlagForPaymentDevice(
            description="description",
            effective_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
            flag_definition_id="1",
            is_backdated=False,
            payment_device_id="2",
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        ),
    )
