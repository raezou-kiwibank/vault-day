# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateAccountInstruction(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account=dict(
            id="1",
            instance_param_vals=dict(a="1", b="2"),
            product_version_id="2",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccount(
            id="1",
            instance_param_vals=dict(a="1", b="2"),
            product_version_id="2",
        ),
    )


class TestCreatePlan(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_plan=dict(
            id="1",
            details=dict(a="1", b="2"),
            processing_group_id="2",
            supervisor_contract_version_id="3",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePlan(
            id="1",
            details=dict(a="1", b="2"),
            processing_group_id="2",
            supervisor_contract_version_id="3",
        ),
    )


class TestCreateAccountPlanAssociation(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_account_plan_assoc=dict(
            account_id="1", id="2", plan_id="3", status="ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE"
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateAccountPlanAssoc(
            account_id="1",
            id="2",
            plan_id="3",
            status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
        ),
    )


class TestUpdateAccount(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        update_account=dict(
            id="1",
            status="ACCOUNT_STATUS_CLOSED",
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.UpdateAccount(id="1", status=core_api.AccountStatus.ACCOUNT_STATUS_CLOSED),
    )


class TestUpdateProcessingGroup(
    TestPydanticModelOutputForSimulation.Base[sim.UpdateProcessingGroup]
):
    dictionary = dict(
        processing_group=dict(
            id="pg_id",
            timezone="UTC",
            status="PROCESSING_GROUP_STATUS_ACTIVE",
        ),
        update_mask=dict(paths=["timezone"]),
        # TODO (TM-127875): expose this field when it is re-enabled in the class.
        # minimum_observation_timestamp_update_options=dict(
        #     schedules_observe_balances_at_unpause_time=True
        # ),
    )
    resource = sim.UpdateProcessingGroup(
        processing_group=sim.ProcessingGroup(
            id="pg_id",
            timezone=UTC,
            status=core_api.ProcessingGroupStatus.ACTIVE,
        ),
        update_mask=core_api.UpdateMask(paths=["timezone"]),
        # TODO: expose this field when it is re-enabled in the class.
        # minimum_observation_timestamp_update_options=core_api.MinimumObservationTimestampUpdateOptions(  # noqa: E501
        #     schedules_observe_balances_at_unpause_time=True
        # ),
    )


class TestSimulationRequestBody(TestPydanticModelOutputForSimulation.Base[sim.SimulateRequest]):
    dictionary = dict(
        start_timestamp="2024-12-31T00:00:00+00:00",
        end_timestamp="2025-12-31T00:00:00+00:00",
        smart_contracts=[
            dict(
                code="# smart contract code",
                smart_contract_param_vals=dict(a="1", b="2"),
                smart_contract_version_id="1",
            )
        ],
        existing_smart_contracts=[
            dict(
                id="2",
            )
        ],
        supervisor_contracts=[
            dict(
                code="# supervisor contract code",
                supervisor_contract_version_id="3",
            )
        ],
        existing_supervisor_contracts=[
            dict(
                id="4",
            )
        ],
        contract_modules=[
            dict(
                code="# contract module code",
                contract_module_version_id="5",
            )
        ],
        existing_contract_modules=[
            dict(
                id="6",
            )
        ],
        existing_accounts=[
            dict(
                account_id="7",
                is_internal=False,
            )
        ],
        existing_product_data_behaviour=dict(
            include_all=False,
            include_data_types=[
                sim.IncludeDataTypes.GLOBAL_PARAMETERS.value,
                sim.IncludeDataTypes.TEMPLATE_PARAMETERS.value,
                sim.IncludeDataTypes.CALENDARS.value,
            ],
        ),
        instructions=[
            dict(
                timestamp="2025-06-30T00:00:00+00:00",
                create_account=dict(
                    id="1",
                    instance_param_vals=None,
                    product_version_id="1",
                ),
            )
        ],
        outputs=[
            dict(
                timestamp="2025-06-30T00:00:00+00:00",
                derived_params=dict(
                    account_id="7",
                ),
            )
        ],
    )
    resource = sim.SimulateRequest(
        start_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        end_timestamp=datetime(2025, 12, 31, tzinfo=UTC),
        smart_contracts=[
            sim.SmartContract(
                code="# smart contract code",
                smart_contract_param_vals=dict(a="1", b="2"),
                smart_contract_version_id="1",
            )
        ],
        existing_smart_contracts=[
            sim.ExistingContractOrModule(
                id="2",
            )
        ],
        supervisor_contracts=[
            sim.SupervisorContract(
                code="# supervisor contract code",
                supervisor_contract_version_id="3",
            )
        ],
        existing_supervisor_contracts=[
            sim.ExistingContractOrModule(
                id="4",
            )
        ],
        contract_modules=[
            sim.ContractModule(
                code="# contract module code",
                contract_module_version_id="5",
            )
        ],
        existing_contract_modules=[
            sim.ExistingContractOrModule(
                id="6",
            )
        ],
        existing_accounts=[
            sim.ExistingAccount(
                account_id="7",
                is_internal=False,
            )
        ],
        existing_product_data_behaviour=sim.ExistingProductDataBehaviour(
            include_all=False,
            include_data_types=[
                sim.IncludeDataTypes.GLOBAL_PARAMETERS,
                sim.IncludeDataTypes.TEMPLATE_PARAMETERS,
                sim.IncludeDataTypes.CALENDARS,
            ],
        ),
        instructions=[
            sim.Instruction(
                timestamp=datetime(2025, 6, 30, tzinfo=UTC),
                instruction=sim.CreateAccount(
                    id="1",
                    product_version_id="1",
                ),
            )
        ],
        outputs=[
            sim.Output(
                timestamp=datetime(2025, 6, 30, tzinfo=UTC),
                derived_params=sim.DerivedParams(
                    account_id="7",
                ),
            )
        ],
    )
