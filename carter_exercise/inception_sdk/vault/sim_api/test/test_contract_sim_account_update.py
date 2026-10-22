# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateAccountUpdateInstanceParamVals(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account_update=dict(
            id="1",
            account_id="2",
            create_timestamp="2024-01-01T00:00:00+00:00",
            instance_param_vals_update=dict(
                instance_param_vals=dict(a="1", b="2"),
            ),
            last_status_update_timestamp="2024-01-01T00:00:00+00:00",
            account_update_batch_id="3",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccountUpdateWithInstanceParamValsUpdate(
            id="1",
            account_id="2",
            create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            instance_param_vals_update=sim.InstanceParamValsUpdate(
                instance_param_vals=dict(a="1", b="2"),
            ),
            last_status_update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            account_update_batch_id="3",
        ),
    )


class TestCreateAccountUpdateProductVersion(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account_update=dict(
            id="1",
            account_id="2",
            create_timestamp="2024-01-01T00:00:00+00:00",
            product_version_update=dict(
                product_version_id="3",
                instance_param_vals_to_add=dict(a="1", b="2"),
                schedule_migration_type="SCHEDULE_MIGRATION_TYPE_RECREATE_ALL_SCHEDULES_AND_GROUPS",
            ),
            last_status_update_timestamp="2024-01-01T00:00:00+00:00",
            account_update_batch_id="4",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccountUpdateWithProductVersionUpdate(
            id="1",
            account_id="2",
            create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            product_version_update=sim.ProductVersionUpdate(
                product_version_id="3",
                instance_param_vals_to_add=dict(a="1", b="2"),
                schedule_migration_type=sim.ScheduleMigrationType.SCHEDULE_MIGRATION_TYPE_RECREATE_ALL_SCHEDULES_AND_GROUPS,  # noqa: E501
            ),
            last_status_update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            account_update_batch_id="4",
        ),
    )


class TestCreateAccountUpdateActivation(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account_update=dict(
            id="1",
            account_id="2",
            create_timestamp="2024-01-01T00:00:00+00:00",
            activation_update=dict(),
            last_status_update_timestamp="2024-01-01T00:00:00+00:00",
            account_update_batch_id="4",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccountUpdateWithActivationUpdate(
            id="1",
            account_id="2",
            create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            activation_update=dict(),
            last_status_update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            account_update_batch_id="4",
        ),
    )


class TestCreateAccountUpdateClosure(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account_update=dict(
            id="1",
            account_id="2",
            create_timestamp="2024-01-01T00:00:00+00:00",
            closure_update=dict(),
            last_status_update_timestamp="2024-01-01T00:00:00+00:00",
            account_update_batch_id="4",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccountUpdateWithClosureUpdate(
            id="1",
            account_id="2",
            create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            closure_update=dict(),
            last_status_update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            account_update_batch_id="4",
        ),
    )
