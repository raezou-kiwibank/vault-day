# standard libs
from typing import cast

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend

endtoend.testhandle.CONTRACTS = {
    "test_contract": {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
}

endtoend.testhandle.SUPERVISORCONTRACTS = {
    "test_supervisor": {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "supervisor_template.py"
    }
}


class TestRenderedSupervisor(endtoend.End2Endtest):

    def test_rendered_supervisor_schedules_are_controlled(self):
        cust_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account(
            customer=cust_id,
            contract="test_contract",
            status="ACCOUNT_STATUS_OPEN",
        )

        plan_id = endtoend.supervisors_helper.link_accounts_to_supervisor(
            "test_supervisor", [account["id"]]
        )

        plan_schedules = endtoend.schedule_helper.get_plan_schedules(plan_id=plan_id)

        # we've defined schedules as dict[str, str] but for tags specifically we get list[str]
        # fixing the return type hint causes more issues than it solves and this is only really
        # addressed by using proper classes for vault types, which is on the to-do list for SDK v2
        accrue_offset_tags = cast(list[str], plan_schedules["ACCRUE_OFFSET_INTEREST"]["tags"])
        accrue_fees_tags = cast(list[str], plan_schedules["ACCRUE_FEES"]["tags"])

        # No schedules are explicitly controlled so default paused tag is used everywhere
        self.assertListEqual(accrue_offset_tags, [endtoend.testhandle.default_paused_tag_id])
        self.assertListEqual(accrue_fees_tags, [endtoend.testhandle.default_paused_tag_id])
