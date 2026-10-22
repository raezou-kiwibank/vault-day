# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestV2CreateCustomerAccount(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        v2_create_account=dict(
            account=dict(
                status="ACCOUNT_STATUS_OPEN",
                type="ACCOUNT_TYPE_CUSTOMER",
                smart_contract_version_id="1",
                parameter_value_hierarchy_node_id="pvhn-1",
                permitted_denominations=["a", "b", "c"],
                alias="a",
                details=dict(a="1", b="2"),
                processing_group_id="b",
                id="c",
            ),
            create_options=dict(
                parameter_values=dict(parameter_a=dict(string_value="X")), sub_accounts=None
            ),
        ),
    )

    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.V2CreateAccount(
            account=sim.CustomerAccountRequestBody(
                status=sim.AccountV2Status.ACCOUNT_STATUS_OPEN,
                alias="a",
                details=dict(a="1", b="2"),
                processing_group_id="b",
                smart_contract_version_id="1",
                parameter_value_hierarchy_node_id="pvhn-1",
                permitted_denominations=["a", "b", "c"],
                id="c",
            ),
            create_options=sim.CreateOptions(
                parameter_values=dict(parameter_a=core_api.StringParameterValue(string_value="X"))
            ),
        ),
    )


class TestV2CreateInternalAccount(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        v2_create_account=dict(
            account=dict(
                status="ACCOUNT_STATUS_OPEN",
                type="ACCOUNT_TYPE_INTERNAL",
                alias="a",
                details=dict(a="1", b="2"),
                processing_group_id="b",
                processing_label=None,
                t_side="T_SIDE_LIABILITY",
                id="c",
            ),
            create_options=None,
        ),
    )

    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.V2CreateAccount(
            account=sim.InternalAccountRequestBody(
                status=sim.AccountV2Status.ACCOUNT_STATUS_OPEN,
                alias="a",
                details=dict(a="1", b="2"),
                processing_group_id="b",
                t_side=core_api.AccountV2TSide.T_SIDE_LIABILITY,
                id="c",
            ),
        ),
    )


class TestV2UpdateAccount(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        v2_update_account=dict(
            account=dict(
                id="a",
                smart_contract_version_id="1",
                status="ACCOUNT_STATUS_CLOSED",
                parameter_value_hierarchy_node_id="pvhn-1",
                processing_label="c",
            ),
            update_mask=dict(paths=["a", "b", "c"]),
        ),
    )

    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.V2UpdateAccount(
            account=sim.UpdateAccountV2Account(
                id_="a",
                smart_contract_version_id="1",
                parameter_value_hierarchy_node_id="pvhn-1",
                status=sim.AccountV2Status.ACCOUNT_STATUS_CLOSED,
                processing_label="c",
            ),
            update_mask=core_api.UpdateMask(paths=["a", "b", "c"]),
        ),
    )
