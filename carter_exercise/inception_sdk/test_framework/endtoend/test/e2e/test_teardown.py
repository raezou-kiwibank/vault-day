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


class TestTearDownTestResource(endtoend.End2Endtest):

    def test_resources_torn_down(self):

        customer_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account(
            customer=customer_id, contract="test_contract"
        )
        account_id = account["id"]
        plan_id = endtoend.supervisors_helper.link_accounts_to_supervisor(
            supervisor_contract="test_supervisor", account_list=[account_id]
        )

        endtoend.End2Endtest.tearDown(self)

        customer = endtoend.core_api_helper.get_customer(customer_id=customer_id)
        self.assertEqual(customer["status"], "CUSTOMER_STATUS_DECEASED")

        account = endtoend.contracts_helper.get_account(account_id=account_id)
        self.assertEqual(account["status"], "ACCOUNT_STATUS_CLOSED")

        plan = endtoend.supervisors_helper.get_plan_details(plan_id=plan_id)
        self.assertEqual(plan["status"], "PLAN_STATUS_CLOSED")

    def test_account_not_created_via_framework_torn_down(self):

        customer_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account(
            customer=customer_id, contract="test_contract"
        )
        account_id = account["id"]

        # clearing this means the teardown relies on fetching customer accounts
        endtoend.testhandle.accounts.clear()

        endtoend.End2Endtest.tearDown(self)

        customer = endtoend.core_api_helper.get_customer(customer_id=customer_id)
        self.assertEqual(customer["status"], "CUSTOMER_STATUS_DECEASED")

        account = endtoend.contracts_helper.get_account(account_id=account_id)
        self.assertEqual(account["status"], "ACCOUNT_STATUS_CLOSED")

    def tearDown(self):
        # we trigger e2e teardown inside the test and don't need to rerun it
        pass
