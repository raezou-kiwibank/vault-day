# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.common.balance_helpers import (
    BalanceDimensions,
    NetBalance,
    NetBalances,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedContractNotification,
    SimulationTestScenario,
    SubAccountConfig,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_custom_instruction,
    create_inbound_authorisation_instruction,
    create_inbound_hard_settlement_instruction,
    create_outbound_authorisation_instruction,
    create_outbound_hard_settlement_instruction,
    create_transfer_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    skipForMissingExtension,
    skipForVaultVersionLessThan,
)
from inception_sdk.vault.core_api import SubAccountStatus

PAYMENT_ATM_INSTRUCTION_DETAILS = {"TRANSACTION_TYPE": "ATM"}
DEBUG_NOTIFICATION = "DEBUG_NOTIFICATION"

# Accounts
CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
# Internal accounts
INTERNAL_ACCOUNT_1 = "1"
INTERNAL_ACCOUNT_2 = "2"
INTERNAL_ACCOUNT_3 = "3"

# Dimensions
DEFAULT_DIMENSION = BalanceDimensions(denomination="GBP")
INTERNAL_CONTRA_DIMENSION = BalanceDimensions(address="INTERNAL_CONTRA", denomination="GBP")
PENDING_OUT_DIMENSION = BalanceDimensions(
    denomination="GBP", phase="POSTING_PHASE_PENDING_OUTGOING"
)
PENDING_IN_DIMENSION = BalanceDimensions(denomination="GBP", phase="POSTING_PHASE_PENDING_INCOMING")
DEFAULT_EUR_DIMENSION = BalanceDimensions(denomination="EUR")


default_template_params: dict[str, str] = {}
default_internal_accounts = {
    "1": "LIABILITY",
    "2": "LIABILITY",
    "3": "ASSET",
}

default_simulation_start_date = datetime(year=2022, month=1, day=1, tzinfo=timezone.utc)


class IABalancesTestBase(SimulationTestCase):
    account_id_base = CUSTOMER_ACCOUNT
    contract_filepaths = [
        "inception_sdk/test_framework/contracts/simulation/test/mock_product/internal_accounts_v2_balances_contract.py"  # noqa
    ]

    def setUp(self):
        super().setUp()

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        internal_accounts=None,
        debug=False,
        use_v1_accounts=True,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepaths[0]],
            template_params=template_params or default_template_params.copy(),
            account_configs=[
                AccountConfig(
                    account_id_base=self.account_id_base,
                )
            ],
        )

        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts or default_internal_accounts,
            debug=debug,
            use_v1_accounts=use_v1_accounts,
        )


ACTIVATION_SUBTEST = SubTest(
    description="Check balances after account opening",
    expected_balances_at_ts={
        default_simulation_start_date: {
            CUSTOMER_ACCOUNT: [
                (DEFAULT_DIMENSION, Decimal("50")),
                (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
            ],
            INTERNAL_ACCOUNT_1: [
                (DEFAULT_DIMENSION, Decimal("-100")),
            ],
            INTERNAL_ACCOUNT_2: [
                (DEFAULT_DIMENSION, Decimal("50")),
            ],
        }
    },
)


class TestSimpleIHS(IABalancesTestBase):
    start = default_simulation_start_date
    posting_time = start + relativedelta(seconds=1)
    end = posting_time + relativedelta(seconds=1)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Simple IHS posting",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=posting_time,
                )
            ],
            expected_balances_at_ts={
                posting_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("60")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "60"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestSimpleOHS(IABalancesTestBase):
    start = default_simulation_start_date
    posting_time = start + relativedelta(seconds=1)
    end = posting_time + relativedelta(seconds=1)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Simple OHS posting",
            events=[
                create_outbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=posting_time,
                )
            ],
            expected_balances_at_ts={
                posting_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("40")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-90")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "40"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestMultipleSequentialPostings(IABalancesTestBase):
    start = default_simulation_start_date
    posting_time_1 = start + relativedelta(seconds=1)
    posting_time_2 = start + relativedelta(seconds=2)
    posting_time_3 = start + relativedelta(seconds=3)
    end = start + relativedelta(seconds=4)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Simple IHS posting",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=posting_time_1,
                )
            ],
            expected_balances_at_ts={
                posting_time_1: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("60")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
        ),
        SubTest(
            description="Simple OHS posting",
            events=[
                create_outbound_hard_settlement_instruction(
                    amount="12",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_2,
                    denomination="GBP",
                    event_datetime=posting_time_2,
                )
            ],
            expected_balances_at_ts={
                posting_time_2: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("48")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("62")),
                    ],
                }
            },
        ),
        SubTest(
            description="Simple CI posting",
            events=[
                create_custom_instruction(
                    amount="17",
                    debtor_target_account_id=CUSTOMER_ACCOUNT,
                    creditor_target_account_id=INTERNAL_ACCOUNT_1,
                    debtor_target_account_address="DEFAULT",
                    creditor_target_account_address="DEFAULT",
                    event_datetime=posting_time_3,
                )
            ],
            expected_balances_at_ts={
                posting_time_3: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("31")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-93")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("62")),
                    ],
                }
            },
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestBackdatedPosting(IABalancesTestBase):
    start = default_simulation_start_date
    posting_time = start + relativedelta(seconds=2)
    backdated_posting_time = posting_time - relativedelta(seconds=1)
    end = posting_time + relativedelta(seconds=4)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Backdated posting",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=posting_time,
                    value_timestamp=backdated_posting_time,
                )
            ],
            expected_balances_at_ts={
                posting_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("60")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "60"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
        )
        self.run_test_scenario(test_scenario)


class TestSequentialBackdatedPostings(IABalancesTestBase):
    """
    time           0---1---2---3---4---5---6--->
    event time     ------------A-------B------->
    value time     --------A-------B----------->

    Posting A - backdated
    Posting B - backdated

    """

    start = default_simulation_start_date
    pA_event_time = start + relativedelta(seconds=3)
    pA_value_time = start + relativedelta(seconds=2)
    pB_event_time = start + relativedelta(seconds=5)
    pB_value_time = start + relativedelta(seconds=4)
    end = start + relativedelta(seconds=6)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Backdated Posting A",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="15",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pA_event_time,
                    value_timestamp=pA_value_time,
                )
            ],
            expected_balances_at_ts={
                pA_value_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("65")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-115")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
                pA_event_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("65")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-115")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "65"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pA_event_time,
                )
            ],
        ),
        SubTest(
            description="Backdated Posting B",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="7",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pB_event_time,
                    value_timestamp=pB_value_time,
                )
            ],
            expected_balances_at_ts={
                pB_value_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("72")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-122")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
                pB_event_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("72")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-122")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "72"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pB_event_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestBackdatedPostingsWhereValueTimesAreStrictlyBeforeEventTimes(IABalancesTestBase):
    """
    time           0---1---2---3---4---5---6--->
    event time     ----------------A---B------->
    value time     --------A---B--------------->

    Posting A - backdated
    Posting B - backdated

    """

    start = default_simulation_start_date
    pA_event_time = start + relativedelta(seconds=4)
    pA_value_time = start + relativedelta(seconds=2)
    pB_event_time = start + relativedelta(seconds=5)
    pB_value_time = start + relativedelta(seconds=3)
    end = start + relativedelta(seconds=6)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Backdated Posting A",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="15",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pA_event_time,
                    value_timestamp=pA_value_time,
                )
            ],
            expected_balances_at_ts={
                pA_value_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("65")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-115")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
                # ! assertion on the Posting A's event time doesn't work
                # ! because Posting B is valued before this.
                # pA_event_time: {
                #     CUSTOMER_ACCOUNT: [
                #         (DEFAULT_DIMENSION, Decimal("65")),
                #         (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                #     ],
                #     INTERNAL_ACCOUNT_1: [
                #         (DEFAULT_DIMENSION, Decimal("-115")),
                #     ],
                #     INTERNAL_ACCOUNT_2: [
                #         (DEFAULT_DIMENSION, Decimal("50")),
                #     ],
                # }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "65"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pA_event_time,
                )
            ],
        ),
        SubTest(
            description="Backdated Posting B",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="7",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pB_event_time,
                    value_timestamp=pB_value_time,
                )
            ],
            expected_balances_at_ts={
                pB_value_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("72")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-122")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
                pB_event_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("72")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-122")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "72"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pB_event_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestBackdatedPostingToBeforePreviousBackdatedPosting(IABalancesTestBase):
    """
    time           0---1---2---3---4---5---6--->
    event time     ----------------A---B------->
    value time     --------B---A--------------->

    Posting A - backdated
    Posting B - backdated to before posting A

    """

    start = default_simulation_start_date
    pA_event_time = start + relativedelta(seconds=4)
    pA_value_time = start + relativedelta(seconds=3)
    pB_event_time = start + relativedelta(seconds=5)
    pB_value_time = start + relativedelta(seconds=2)
    end = start + relativedelta(seconds=6)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Backdated Posting A",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="15",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pA_event_time,
                    value_timestamp=pA_value_time,
                )
            ],
            expected_balances_at_ts={
                # ! assertion on the Posting A's value AND event time doesn't work
                # ! because Posting B is valued before both of these.
                # pA_value_time: {
                #     CUSTOMER_ACCOUNT: [
                #         (DEFAULT_DIMENSION, Decimal("65")),
                #         (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                #     ],
                #     INTERNAL_ACCOUNT_1: [
                #         (DEFAULT_DIMENSION, Decimal("-115")),
                #     ],
                #     INTERNAL_ACCOUNT_2: [
                #         (DEFAULT_DIMENSION, Decimal("50")),
                #     ],
                # },
                # pA_event_time: {
                #     CUSTOMER_ACCOUNT: [
                #         (DEFAULT_DIMENSION, Decimal("65")),
                #         (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                #     ],
                #     INTERNAL_ACCOUNT_1: [
                #         (DEFAULT_DIMENSION, Decimal("-115")),
                #     ],
                #     INTERNAL_ACCOUNT_2: [
                #         (DEFAULT_DIMENSION, Decimal("50")),
                #     ],
                # },
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "65"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pA_event_time,
                )
            ],
        ),
        SubTest(
            description="Backdated Posting B",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="7",
                    target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    event_datetime=pB_event_time,
                    value_timestamp=pB_value_time,
                )
            ],
            expected_balances_at_ts={
                # ! assertion on the Posting B's value time doesn't work because the FW loses
                # ! granularity of the backdated posting to before an existing value timestamp
                # pB_value_time: {
                #     CUSTOMER_ACCOUNT: [
                #         (DEFAULT_DIMENSION, Decimal("72")),
                #         (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                #     ],
                #     INTERNAL_ACCOUNT_1: [
                #         (DEFAULT_DIMENSION, Decimal("-122")),
                #     ],
                #     INTERNAL_ACCOUNT_2: [
                #         (DEFAULT_DIMENSION, Decimal("50")),
                #     ],
                # },
                pB_event_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("72")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-122")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                },
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "72"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=pB_event_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestMultipleCurrencies(IABalancesTestBase):
    start = default_simulation_start_date
    posting_1_time = start + relativedelta(seconds=1)
    posting_2_time = start + relativedelta(seconds=2)
    end = posting_2_time + relativedelta(seconds=1)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Simple IHS posting",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=posting_1_time,
                )
            ],
            expected_balances_at_ts={
                posting_1_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("60")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "60"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_1_time,
                )
            ],
        ),
        SubTest(
            description="Simple IHS posting in EUR",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="15",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_2,
                    denomination="EUR",
                    event_datetime=posting_2_time,
                )
            ],
            expected_balances_at_ts={
                posting_2_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("60")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                        (DEFAULT_EUR_DIMENSION, Decimal("15")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-110")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                        (DEFAULT_EUR_DIMENSION, Decimal("-15")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "60"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_2_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestPendingPhases(IABalancesTestBase):
    start = default_simulation_start_date
    posting_1_time = start + relativedelta(seconds=1)
    posting_2_time = start + relativedelta(seconds=2)
    end = posting_2_time + relativedelta(seconds=1)
    template_params = {
        **default_template_params,
    }

    sub_tests = [
        ACTIVATION_SUBTEST,
        SubTest(
            description="Inbound Authorisation",
            events=[
                create_inbound_authorisation_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=posting_1_time,
                )
            ],
            expected_balances_at_ts={
                posting_1_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                        (PENDING_IN_DIMENSION, Decimal("10")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-100")),
                        (PENDING_IN_DIMENSION, Decimal("-10")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "50"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_1_time,
                )
            ],
        ),
        SubTest(
            description="Outbound Authorisation",
            events=[
                create_outbound_authorisation_instruction(
                    amount="15",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_2,
                    denomination="GBP",
                    event_datetime=posting_2_time,
                )
            ],
            expected_balances_at_ts={
                posting_2_time: {
                    CUSTOMER_ACCOUNT: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                        (INTERNAL_CONTRA_DIMENSION, Decimal("0")),
                        (PENDING_IN_DIMENSION, Decimal("10")),
                        (PENDING_OUT_DIMENSION, Decimal("-15")),
                    ],
                    INTERNAL_ACCOUNT_1: [
                        (DEFAULT_DIMENSION, Decimal("-100")),
                        (PENDING_IN_DIMENSION, Decimal("-10")),
                    ],
                    INTERNAL_ACCOUNT_2: [
                        (DEFAULT_DIMENSION, Decimal("50")),
                        (PENDING_OUT_DIMENSION, Decimal("15")),
                    ],
                }
            },
            expected_contract_notifications=[
                ExpectedContractNotification(
                    notification_type=DEBUG_NOTIFICATION,
                    notification_details={"default_committed": "50"},
                    resource_id=CUSTOMER_ACCOUNT,
                    resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    timestamp=posting_2_time,
                )
            ],
        ),
    ]

    def test_v1(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=True,
        )
        self.run_test_scenario(test_scenario)

    def test_v2(self):
        test_scenario = self.get_simulation_test_scenario(
            start=default_simulation_start_date,
            end=self.end,
            sub_tests=self.sub_tests,
            template_params=self.template_params,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestSubAccountPosting(SimulationTestCase):
    SUB_ACCOUNT_METADATA_CONTRACT_FILE = "inception_sdk/test_framework/contracts/simulation/test/mock_product/sub_account_metadata_contract.py"  # noqa

    start = default_simulation_start_date
    inbound_hard_settlement_time = start + relativedelta(seconds=1)
    transfer_time = start + relativedelta(seconds=2)
    outbound_authorisation_time = start + relativedelta(seconds=3)
    end = start + relativedelta(seconds=4)

    sub_account_id = "sub_account_id"
    sub_account_address = "DEFAULT"

    sub_tests = [
        SubTest(
            description="Inbound Hard Settlement of 10 GBP to a Sub-Account",
            events=[
                create_inbound_hard_settlement_instruction(
                    amount="10",
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    event_datetime=inbound_hard_settlement_time,
                    target_sub_account_id=sub_account_id,
                )
            ],
            expected_net_balances={
                inbound_hard_settlement_time: NetBalances(
                    value_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("10"),
                            sub_account_id=sub_account_id,
                        )
                    ],
                    booking_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("10"),
                            sub_account_id=sub_account_id,
                        )
                    ],
                ),
            },
        ),
        SubTest(
            description="Transfer of 5 GBP from parent Account to its Sub-Account",
            events=[
                create_transfer_instruction(
                    amount="5",
                    event_datetime=transfer_time,
                    creditor_target_account_id=CUSTOMER_ACCOUNT,
                    debtor_target_account_id=CUSTOMER_ACCOUNT,
                    denomination="GBP",
                    creditor_target_sub_account_id=sub_account_id,
                    creditor_target_account_address=sub_account_address,
                )
            ],
            expected_net_balances={
                transfer_time: NetBalances(
                    value_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("-5"),
                            sub_account_id="",
                        ),
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("15"),
                            sub_account_id=sub_account_id,
                        ),
                    ],
                    booking_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("-5"),
                            sub_account_id="",
                        ),
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.COMMITTED,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("15"),
                            sub_account_id=sub_account_id,
                        ),
                    ],
                ),
            },
        ),
        SubTest(
            description="Outbound Authorisation of 3 GBP from Sub-Account",
            events=[
                create_outbound_authorisation_instruction(
                    amount="3",
                    event_datetime=outbound_authorisation_time,
                    target_account_id=CUSTOMER_ACCOUNT,
                    internal_account_id=INTERNAL_ACCOUNT_1,
                    denomination="GBP",
                    target_sub_account_id=sub_account_id,
                    target_account_address=sub_account_address,
                )
            ],
            expected_net_balances={
                outbound_authorisation_time: NetBalances(
                    value_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.PENDING_OUTGOING,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("-3"),
                            sub_account_id=sub_account_id,
                        )
                    ],
                    booking_net_balances=[
                        NetBalance(
                            account_id=CUSTOMER_ACCOUNT,
                            account_address=sub_account_address,
                            phase=core_api.PostingPhase.PENDING_OUTGOING,
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination="GBP",
                            amount=Decimal("-3"),
                            sub_account_id=sub_account_id,
                        )
                    ],
                ),
            },
        ),
    ]

    @skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
    @skipForVaultVersionLessThan(Version("5.11.0"))
    def test_sub_account_posting(self):
        contract_config = ContractConfig(
            contract_file_path=self.SUB_ACCOUNT_METADATA_CONTRACT_FILE,
            template_params={},
            smart_contract_version_id="1",
            account_configs=[
                AccountConfig(
                    account_id_base=CUSTOMER_ACCOUNT,
                    permitted_denominations=["GBP"],
                    sub_accounts=[
                        SubAccountConfig(
                            id=self.sub_account_id,
                            type="SAVE",
                            status=SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    ],
                )
            ],
        )

        test_scenario = SimulationTestScenario(
            start=self.start,
            end=self.end,
            sub_tests=self.sub_tests,
            contract_config=contract_config,
            internal_accounts={"1": "LIABILITY"},
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)
