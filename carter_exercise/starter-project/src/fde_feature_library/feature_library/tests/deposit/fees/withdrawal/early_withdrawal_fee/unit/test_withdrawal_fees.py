# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.addresses as common_addresses

# features
import feature_library.common.calendar_utils as calendar_utils
import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.withdrawal.early_withdrawal_fees as early_withdrawal_fees

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AccountNotificationDirective,
    AttributeHookArguments,
    AttributeHookResult,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    CalendarEvent,
    CalendarsObservation,
    CustomInstruction,
    InboundHardSettlement,
    OutboundHardSettlement,
    ParametersObservation,
    Phase,
    Posting,
    Rejection,
    RejectionReason,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    DEFAULT_DATETIME,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

DEFAULT_CALENDAR_EVENT = CalendarEvent(
    id="SPRING_BANK_HOLIDAY",
    calendar_id="PUBLIC_HOLIDAYS",
    start_datetime=datetime(2026, 5, 25, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
    end_datetime=datetime(2026, 5, 26, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
)


def none_to_zero(d: Decimal | None = None) -> Decimal:
    return d if d is not None else Decimal(0)


class WithdrawalFeesTest(FeatureTest):
    def setup_mock_data(
        self,
        effective_datetime: datetime = DEFAULT_DATETIME,
        early_withdrawal_flat_fee: Decimal | None = None,
        early_withdrawal_percentage_fee: Decimal | None = None,
        fee_free_withdrawal_percentage_limit: Decimal | None = None,
        maximum_withdrawal_percentage_limit: Decimal | None = None,
        default_bal: Decimal | None = None,
        withdrawals_tracker_bal: Decimal | None = None,
    ):
        default_bal = none_to_zero(default_bal)
        withdrawals_tracker_bal = none_to_zero(withdrawals_tracker_bal)
        self.effective_datetime = effective_datetime
        # mock vault
        denom_params = {denomination_module.DENOMINATION_PARAM.id: self.default_denomination}
        early_withdrawal_fees_params = {
            early_withdrawal_fees.EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id: none_to_zero(
                early_withdrawal_flat_fee
            ),
            early_withdrawal_fees.EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id: none_to_zero(
                early_withdrawal_percentage_fee
            ),
            early_withdrawal_fees.FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: none_to_zero(
                fee_free_withdrawal_percentage_limit
            ),
            early_withdrawal_fees.MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: none_to_zero(
                maximum_withdrawal_percentage_limit
            ),
        }
        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            early_withdrawal_fees.WITHDRAWAL_FEES_POF.fetcher_id: ParametersObservation(
                parameters=early_withdrawal_fees_params, value_datetime=effective_datetime
            ),
        }
        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, self.default_denomination, Phase.COMMITTED
                ): Balance(default_bal, Decimal(0), default_bal),
                BalanceCoordinate(
                    early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                    DEFAULT_ASSET,
                    self.default_denomination,
                    Phase.COMMITTED,
                ): Balance(withdrawals_tracker_bal, Decimal(0), withdrawals_tracker_bal),
            },
        )
        withdrawals_tracker_live_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                    DEFAULT_ASSET,
                    self.default_denomination,
                    Phase.COMMITTED,
                ): Balance(withdrawals_tracker_bal, Decimal(0), withdrawals_tracker_bal),
            },
        )
        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                early_withdrawal_fees.fetchers.ALL_BALANCES_LIVE_BOF_ID: BalancesObservation(
                    balances=default_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
                early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_LIVE_BOF.fetcher_id: (
                    BalancesObservation(
                        balances=withdrawals_tracker_live_bals,
                        value_datetime=effective_datetime,
                        at_datetime=effective_datetime,
                    )
                ),
            },
            calendars_observation_fetchers_mapping={
                calendar_utils.PUBLIC_HOLIDAYS_COF.fetcher_id: CalendarsObservation(
                    calendars={"&{PUBLIC_HOLIDAYS}": [DEFAULT_CALENDAR_EVENT]},
                    value_datetime=effective_datetime,
                )
            },
            parameters_observation_fetchers_mapping=params_obs,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=early_withdrawal_fees_params | denom_params,
            balances=default_bals,
        )

    def withdrawal_posting(
        self,
        withdrawal_amt: Decimal,
        effective_datetime: datetime = DEFAULT_DATETIME,
        calendar_override: bool = False,
    ) -> OutboundHardSettlement:
        instruction_details = {
            "calendar_override": str(calendar_override),
        }
        withdrawal = OutboundHardSettlement(
            amount=withdrawal_amt,
            denomination=self.default_denomination,
            target_account_id=ACCOUNT_ID,
            internal_account_id="1",
            instruction_details=instruction_details,
        )
        withdrawal._set_output_attributes(
            value_datetime=effective_datetime,
            client_batch_id="12345",
            own_account_id=ACCOUNT_ID,
            committed_postings=[
                Posting(
                    credit=False,
                    amount=withdrawal_amt,
                    denomination=self.default_denomination,
                    account_id=ACCOUNT_ID,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                )
            ],
            tside=Tside.LIABILITY,
        )
        return withdrawal


class WithdrawalFeesNotificationTest(WithdrawalFeesTest):
    product_name = "TEST_PRODUCT"

    @pytest.mark.unit
    def test_notification_type(self):
        result = early_withdrawal_fees.notification_type(product_name=self.product_name)

        self.assertEqual(result, "TEST_PRODUCT_WITHDRAWAL_FEE")

    @pytest.mark.unit
    def test_withdrawal_fee_notification(self):
        expected_result = AccountNotificationDirective(
            notification_type="TEST_PRODUCT_WITHDRAWAL_FEE",
            notification_details={
                "account_id": "vault_account_id",
                "denomination": DEFAULT_DENOMINATION,
                "withdrawal_amount": "20.00",
                "flat_fee_amount": "5.00",
                "percentage_fee_amount": "10.00",
                "total_fee_amount": "15.00",
                "client_batch_id": "withdrawal_client_batch_id",
            },
        )

        result = early_withdrawal_fees.generate_withdrawal_fee_notification(
            account_id="vault_account_id",
            denomination=self.default_denomination,
            withdrawal_amount=Decimal("20"),
            flat_fee_amount=Decimal("5"),
            percentage_fee_amount=Decimal("10"),
            product_name=self.product_name,
            client_batch_id="withdrawal_client_batch_id",
        )
        self.assertEqual(result, expected_result)


class ValidatePrePostingTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_valid_withdrawal_does_not_raise_rejection(self):
        self.setup_mock_data(
            maximum_withdrawal_percentage_limit=Decimal("0.3"),
            default_bal=Decimal(90),
        )
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(Decimal("26.99"))
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_withdrawal_exceeds_current_balance_raises_rejection(self):
        self.setup_mock_data(
            default_bal=Decimal(90),
        )
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(Decimal("90.01"))
        expected_result = Rejection(
            message="The withdrawal amount of 90.01 GBP exceeds the available balance of 90 GBP.",
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_partial_withdrawal_exceeds_maximum_withdrawal_limit_raises_rejection(self):
        default_bal = Decimal(65)
        withdrawals_tracker = Decimal(25)
        maximum_withdrawal_percentage_limit = Decimal("0.5")
        self.setup_mock_data(
            maximum_withdrawal_percentage_limit=maximum_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker,
        )
        available_limit: Decimal = (
            ((default_bal + withdrawals_tracker) * maximum_withdrawal_percentage_limit)
            - withdrawals_tracker
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(available_limit, Decimal(20))
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(Decimal("45.01"))

        expected_result = Rejection(
            message="The withdrawal amount of 45.01 GBP would exceed "
            f"the available withdrawal limit of {available_limit} GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_withdrawal_on_calendar_event_raises_rejection(self):
        self.setup_mock_data(
            effective_datetime=DEFAULT_CALENDAR_EVENT.start_datetime,
            maximum_withdrawal_percentage_limit=Decimal(1),
            default_bal=Decimal(90),
            withdrawals_tracker_bal=Decimal(0),
        )
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(
            withdrawal_amt=Decimal(20), effective_datetime=DEFAULT_CALENDAR_EVENT.start_datetime
        )
        expected_result = Rejection(
            message="Cannot withdraw on public holidays.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_withdrawal_on_calendar_event_with_override_does_not_raise_rejection(self):
        self.setup_mock_data(
            effective_datetime=DEFAULT_CALENDAR_EVENT.start_datetime,
            maximum_withdrawal_percentage_limit=Decimal(1),
            default_bal=Decimal(90),
            withdrawals_tracker_bal=Decimal(0),
        )
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(
            withdrawal_amt=Decimal(20),
            effective_datetime=DEFAULT_CALENDAR_EVENT.start_datetime,
            calendar_override=True,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_early_withdrawal_fees_exceed_withdrawal_amount_raises_rejection(self):
        early_withdrawal_flat_fee = Decimal("28.01")
        early_withdrawal_percentage_fee = Decimal("0.3")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=Decimal(0),
            maximum_withdrawal_percentage_limit=Decimal(1),
            default_bal=Decimal(90),
        )
        withdrawal_amt = Decimal(40)
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(withdrawal_amt=withdrawal_amt)
        fees: Decimal = early_withdrawal_flat_fee + early_withdrawal_percentage_fee * withdrawal_amt
        self.assertEqual(early_withdrawal_percentage_fee * withdrawal_amt, Decimal(12))
        self.assertEqual(fees, Decimal("40.01"))
        expected_result = Rejection(
            message=f"The withdrawal fees of {fees} GBP are not covered by "
            f"the withdrawal amount of {withdrawal_amt} GBP.",
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_early_withdrawal_fees_covered_by_withdrawal_amount(self):
        early_withdrawal_flat_fee = Decimal("27.99")
        early_withdrawal_percentage_fee = Decimal("0.3")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=Decimal(0),
            maximum_withdrawal_percentage_limit=Decimal(1),
            default_bal=Decimal(90),
        )
        withdrawal_amt = Decimal(40)
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(withdrawal_amt=withdrawal_amt)
        fees: Decimal = early_withdrawal_flat_fee + early_withdrawal_percentage_fee * withdrawal_amt
        self.assertEqual(early_withdrawal_percentage_fee * withdrawal_amt, Decimal(12))
        self.assertEqual(fees, Decimal("39.99"))
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[withdrawal],
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_deposit_does_not_raise_rejection(self):
        self.setup_mock_data()
        deposit_amt = Decimal(30)
        deposit = InboundHardSettlement(
            amount=deposit_amt,
            denomination=self.default_denomination,
            target_account_id=ACCOUNT_ID,
            internal_account_id="1",
        )
        deposit._set_output_attributes(
            value_datetime=DEFAULT_DATETIME,
            own_account_id=ACCOUNT_ID,
            committed_postings=[
                Posting(
                    credit=True,
                    amount=deposit_amt,
                    denomination=self.default_denomination,
                    account_id=ACCOUNT_ID,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                )
            ],
            tside=Tside.LIABILITY,
        )
        result = early_withdrawal_fees.validate(
            state=self.state,
            posting_instructions=[deposit],
        )
        self.assertIsNone(result)


class HandleWithdrawalsTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_tracker_and_notification_returned(self):
        withdrawal_amt = Decimal(40)
        flat_fee_amount = Decimal(5)
        early_withdrawal_percentage_fee = Decimal("0.1")
        percentage_fee_amount: Decimal = early_withdrawal_percentage_fee * withdrawal_amt
        withdrawal: OutboundHardSettlement = self.withdrawal_posting(withdrawal_amt=withdrawal_amt)
        expected_result = early_withdrawal_fees.HandleWithdrawalsResult(
            custom_instructions=[
                CustomInstruction(
                    postings=[
                        Posting(
                            credit=False,
                            amount=withdrawal_amt,
                            denomination=self.default_denomination,
                            account_id=ACCOUNT_ID,
                            account_address=common_addresses.INTERNAL_CONTRA,
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=True,
                            amount=withdrawal_amt,
                            denomination=self.default_denomination,
                            account_id=ACCOUNT_ID,
                            account_address=early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                    ],
                    value_datetime=DEFAULT_DATETIME,
                    instruction_details={"description": "Updating the withdrawals tracker balance"},
                    override_all_restrictions=True,
                )
            ],
            account_notification_directives=[
                AccountNotificationDirective(
                    notification_type=f"TEST_PRODUCT{early_withdrawal_fees.WITHDRAWAL_FEE_SUFFIX}",
                    notification_details={
                        "account_id": ACCOUNT_ID,
                        "denomination": self.default_denomination,
                        "withdrawal_amount": str(
                            withdrawal_amt.quantize(Decimal("0.01"), ROUND_HALF_UP)
                        ),
                        "flat_fee_amount": str(
                            flat_fee_amount.quantize(Decimal("0.01"), ROUND_HALF_UP)
                        ),
                        "percentage_fee_amount": str(
                            percentage_fee_amount.quantize(Decimal("0.01"), ROUND_HALF_UP)
                        ),
                        "total_fee_amount": str(
                            (flat_fee_amount + percentage_fee_amount).quantize(
                                Decimal("0.01"), ROUND_HALF_UP
                            )
                        ),
                        "client_batch_id": "12345",
                    },
                )
            ],
        )
        self.setup_mock_data(
            early_withdrawal_flat_fee=flat_fee_amount,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            default_bal=Decimal(50),
            withdrawals_tracker_bal=Decimal(40),
        )
        result = early_withdrawal_fees.handle_withdrawals(
            state=self.state,
            posting_instructions=[withdrawal],
            product_name="TEST_PRODUCT",
        )
        self.assertTupleEqual(result, expected_result)


class GetCurrentWithdrawalAmountDefaultBalanceAdjustmentTest(FeatureTest):
    @pytest.mark.unit
    def test_get_current_withdrawal_amount_default_balance_adjustment_returns_interface(self):
        result = early_withdrawal_fees.get_current_withdrawal_amount_default_balance_adjustment(
            withdrawal_amount=Decimal(100)
        )
        self.assertEqual(result.calculate_balance_adjustment(), Decimal(100))


class GetCustomerDepositAmountTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_get_customer_deposit_amount_without_balance_adjustments(self):
        self.setup_mock_data(
            default_bal=Decimal(400),
            withdrawals_tracker_bal=Decimal(100),
        )
        result = early_withdrawal_fees.get_customer_deposit_amount(state=self.state)
        # deposit_amount = 400 + 100 + 0 (no balance adjustments)
        self.assertEqual(result, Decimal(500))

    @pytest.mark.unit
    def test_get_customer_deposit_amount_with_balance_adjustments(self):
        self.setup_mock_data(
            default_bal=Decimal(400),
            withdrawals_tracker_bal=Decimal(100),
        )
        positive_balance_adjustment = (
            early_withdrawal_fees.deposit_interfaces.DefaultBalanceAdjustment(
                calculate_balance_adjustment=lambda **kwargs: Decimal(10)
            )
        )
        negative_balance_adjustment = (
            early_withdrawal_fees.deposit_interfaces.DefaultBalanceAdjustment(
                calculate_balance_adjustment=lambda **kwargs: Decimal(-35)
            )
        )
        result = early_withdrawal_fees.get_customer_deposit_amount(
            state=self.state,
            balance_adjustments=[positive_balance_adjustment, negative_balance_adjustment],
        )
        # deposit_amount = 400 + 100 + 10 - 35
        self.assertEqual(result, Decimal(475))

    @pytest.mark.unit
    def test_get_customer_deposit_amount_with_balance_adjustments_with_optional_parameters(self):
        self.setup_mock_data(
            default_bal=Decimal(400),
            withdrawals_tracker_bal=Decimal(100),
        )
        balance_adjustment = early_withdrawal_fees.deposit_interfaces.DefaultBalanceAdjustment(
            calculate_balance_adjustment=lambda **kwargs: Decimal(10)
        )
        result = early_withdrawal_fees.get_customer_deposit_amount(
            state=self.state,
            balance_adjustments=[balance_adjustment],
        )
        # deposit_amount = 400 + 100 + 10
        self.assertEqual(result, Decimal(510))


class UpdateWithdrawalsTrackerTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_update_tracked_withdrawals_returns_custom_instruction_for_withdrawal(self):
        self.setup_mock_data()
        withdrawal_amt = Decimal(100)
        expected_result = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=withdrawal_amt,
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=common_addresses.INTERNAL_CONTRA,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=withdrawal_amt,
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                value_datetime=DEFAULT_DATETIME,
                instruction_details={"description": "Updating the withdrawals tracker balance"},
                override_all_restrictions=True,
            )
        ]

        result = early_withdrawal_fees._update_tracked_withdrawals(
            account_id=ACCOUNT_ID,
            withdrawal_amount=withdrawal_amt,
            denomination=self.default_denomination,
            effective_datetime=DEFAULT_DATETIME,
        )
        self.assertListEqual(result, expected_result)

    @pytest.mark.unit
    def test_update_tracked_withdrawals_returns_blank_list_for_zero_withdrawal_amount(self):
        self.setup_mock_data()
        withdrawal_amt = Decimal(0)
        result = early_withdrawal_fees._update_tracked_withdrawals(
            account_id=ACCOUNT_ID,
            withdrawal_amount=withdrawal_amt,
            denomination=self.default_denomination,
            effective_datetime=DEFAULT_DATETIME,
        )
        self.assertListEqual(result, [])


class ResetWithdrawalsTrackerTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_reset_withdrawals_tracker_returns_custom_instruction_when_balance_non_zero(self):
        self.setup_mock_data(
            withdrawals_tracker_bal=Decimal(100),
        )
        expected_result = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=Decimal(100),
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal(100),
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=common_addresses.INTERNAL_CONTRA,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                value_datetime=DEFAULT_DATETIME,
                instruction_details={"description": "Resetting the withdrawals tracker"},
                override_all_restrictions=True,
            )
        ]

        result = early_withdrawal_fees.reset_withdrawals_tracker(
            state=self.state,
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_reset_withdrawals_tracker_returns_blank_list_when_balance_zero(self):
        self.setup_mock_data()
        result = early_withdrawal_fees.reset_withdrawals_tracker(
            state=self.state,
        )
        self.assertEqual(result, [])


class CalculateLimitsTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_calculate_maximum_withdrawal_limit(self):
        maximum_withdrawal_percentage_limit = Decimal(20)
        default_bal = Decimal(100)
        self.setup_mock_data(
            maximum_withdrawal_percentage_limit=maximum_withdrawal_percentage_limit,
            default_bal=default_bal,
        )
        result = early_withdrawal_fees._calculate_maximum_withdrawal_limit(
            state=self.state,
        )
        expected_result = (maximum_withdrawal_percentage_limit * default_bal).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_calculate_fee_free_withdrawal_limit(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.2")
        default_bal = Decimal(100)
        self.setup_mock_data(
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
        )
        expected_result = (fee_free_withdrawal_percentage_limit * default_bal).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        result = early_withdrawal_fees._calculate_fee_free_withdrawal_limit(
            state=self.state,
        )
        self.assertEqual(result, expected_result)


class CalculateWithdrawalAmountSubjectToFeeTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_no_previous_withdrawals(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.4")
        default_bal = Decimal(100)
        withdrawal_amt = Decimal(100)
        self.setup_mock_data(
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
        )

        # withdrawal of 100, fee free limit 40%, no previous withdrawals
        expected_result = (
            withdrawal_amt - default_bal * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        result = early_withdrawal_fees._calculate_withdrawal_amount_subject_to_fees(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_previous_withdrawals_below_fee_free_limit_and_remain_within_fee_free_limit(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.4")
        default_bal = Decimal(100)
        withdrawal_amt = Decimal(10)
        withdrawals_tracker_bal = Decimal(25)
        self.setup_mock_data(
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )

        # withdrawal of 10, fee free limit 40%, previous withdrawals 25
        # => fee free limit remaining 15, hence not subject to fees
        fee_free_limit = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_limit, Decimal(50))
        fee_free_limit_remaining = fee_free_limit - withdrawals_tracker_bal
        self.assertEqual(fee_free_limit_remaining, Decimal(25))
        withdrawal_amount_subject_to_fees = max(
            Decimal(0), withdrawal_amt - fee_free_limit_remaining
        )
        self.assertEqual(withdrawal_amount_subject_to_fees, Decimal(0))
        expected_result = withdrawal_amount_subject_to_fees
        result = early_withdrawal_fees._calculate_withdrawal_amount_subject_to_fees(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_remaining_fee_free_limit_used_and_exceeded_by_withdrawal(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.4")
        default_bal = Decimal(100)
        withdrawal_amt = Decimal(100)
        withdrawals_tracker_bal = Decimal(25)
        self.setup_mock_data(
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )

        # withdrawal of 100, fee free limit 40%, previous withdrawals 25
        # => fee free limit remaining 25, 75 of withdrawal amount subject to fees
        fee_free_limit = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_limit, Decimal(50))
        fee_free_limit_remaining = fee_free_limit - withdrawals_tracker_bal
        self.assertEqual(fee_free_limit_remaining, Decimal(25))
        withdrawal_amount_subject_to_fees = max(
            Decimal(0), withdrawal_amt - fee_free_limit_remaining
        )
        self.assertEqual(withdrawal_amount_subject_to_fees, Decimal(75))
        expected_result = withdrawal_amount_subject_to_fees
        result = early_withdrawal_fees._calculate_withdrawal_amount_subject_to_fees(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_previous_withdrawals_exceed_fee_free_limit(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.4")
        default_bal = Decimal(60)
        withdrawal_amt = Decimal(60)
        withdrawals_tracker_bal = Decimal(40)
        self.setup_mock_data(
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )

        # withdrawal of 60, fee free limit 40%, previous withdrawals 40
        # => fee free limit remaining 0, 100% of withdrawal amount subject to fees
        fee_free_limit = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_limit, Decimal(40))
        fee_free_limit_remaining = fee_free_limit - withdrawals_tracker_bal
        self.assertEqual(fee_free_limit_remaining, Decimal(0))
        withdrawal_amount_subject_to_fees = max(
            Decimal(0), withdrawal_amt - fee_free_limit_remaining
        )
        self.assertEqual(withdrawal_amount_subject_to_fees, Decimal(60))
        expected_result = withdrawal_amount_subject_to_fees
        result = early_withdrawal_fees._calculate_withdrawal_amount_subject_to_fees(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)


class CalculateWithdrawalFeeAmountsTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_flat_and_percentage_fee_returned_when_positive_amount_subject_to_fee(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.1")
        default_bal = Decimal(75)
        withdrawals_tracker_bal = Decimal(25)
        withdrawal_amt = Decimal(45)
        early_withdrawal_flat_fee = Decimal(10)
        early_withdrawal_percentage_fee = Decimal("0.2")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )
        fee_free_withdrawal_limit: Decimal = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_withdrawal_limit, Decimal(10))
        fee_free_withdrawal_limit_remaining: Decimal = max(
            Decimal(0), fee_free_withdrawal_limit - withdrawals_tracker_bal
        )
        self.assertEqual(fee_free_withdrawal_limit_remaining, Decimal(0))
        amount_subject_to_fee = withdrawal_amt - fee_free_withdrawal_limit_remaining
        self.assertEqual(amount_subject_to_fee, withdrawal_amt)
        percentage_fee = amount_subject_to_fee * early_withdrawal_percentage_fee
        self.assertEqual(percentage_fee, Decimal(9))
        self.assertEqual(percentage_fee + early_withdrawal_flat_fee, Decimal(19))
        expected_result = early_withdrawal_fees.WithdrawalFeeAmounts(
            early_withdrawal_flat_fee, percentage_fee
        )
        result = early_withdrawal_fees.calculate_withdrawal_fee_amounts(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_flat_and_percentage_fee_returned_with_balance_adjustments(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.1")
        default_bal = Decimal(67)
        bal_adjustment = Decimal(8)
        withdrawals_tracker_bal = Decimal(25)
        withdrawal_amt = Decimal(45)
        early_withdrawal_flat_fee = Decimal(10)
        early_withdrawal_percentage_fee = Decimal("0.2")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )
        fee_free_withdrawal_limit: Decimal = (
            (default_bal + withdrawals_tracker_bal + bal_adjustment)
            * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_withdrawal_limit, Decimal(10))
        fee_free_withdrawal_limit_remaining: Decimal = max(
            Decimal(0), fee_free_withdrawal_limit - withdrawals_tracker_bal
        )
        self.assertEqual(fee_free_withdrawal_limit_remaining, Decimal(0))
        amount_subject_to_fee = withdrawal_amt - fee_free_withdrawal_limit_remaining
        self.assertEqual(amount_subject_to_fee, withdrawal_amt)
        percentage_fee = amount_subject_to_fee * early_withdrawal_percentage_fee
        self.assertEqual(percentage_fee, Decimal(9))
        self.assertEqual(percentage_fee + early_withdrawal_flat_fee, Decimal(19))
        expected_result = early_withdrawal_fees.WithdrawalFeeAmounts(
            early_withdrawal_flat_fee, percentage_fee
        )
        positive_bal_adjustment = early_withdrawal_fees.deposit_interfaces.DefaultBalanceAdjustment(
            calculate_balance_adjustment=lambda **kwargs: bal_adjustment
        )
        result = early_withdrawal_fees.calculate_withdrawal_fee_amounts(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
            balance_adjustments=[
                positive_bal_adjustment,
            ],
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_zero_fee_returned_when_zero_amount_subject_to_fee(self):
        fee_free_withdrawal_percentage_limit = Decimal("0.1")
        default_bal = Decimal(96)
        withdrawals_tracker_bal = Decimal(4)
        withdrawal_amt = Decimal(6)
        early_withdrawal_flat_fee = Decimal(10)
        early_withdrawal_percentage_fee = Decimal("0.2")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )
        fee_free_withdrawal_limit: Decimal = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_withdrawal_limit, Decimal(10))
        fee_free_withdrawal_limit_remaining: Decimal = max(
            Decimal(0), fee_free_withdrawal_limit - withdrawals_tracker_bal
        )
        self.assertEqual(fee_free_withdrawal_limit_remaining, Decimal(6))
        amount_subject_to_fee = withdrawal_amt - fee_free_withdrawal_limit_remaining
        self.assertEqual(amount_subject_to_fee, Decimal(0))
        percentage_fee = amount_subject_to_fee * early_withdrawal_percentage_fee
        self.assertEqual(percentage_fee, Decimal(0))
        self.assertEqual(percentage_fee + early_withdrawal_flat_fee, Decimal(10))
        expected_result = early_withdrawal_fees.WithdrawalFeeAmounts(Decimal(0), Decimal(0))
        result = early_withdrawal_fees.calculate_withdrawal_fee_amounts(
            state=self.state,
            withdrawal_amount=withdrawal_amt,
        )
        self.assertEqual(result, expected_result)


class AttributeHelpersTest(WithdrawalFeesTest):
    @pytest.mark.unit
    def test_get_maximum_withdrawal_limit_attribute(
        self,
    ):
        maximum_withdrawal_percentage_limit = Decimal("0.2")
        default_bal = Decimal(50)
        withdrawal_tracker_bal = Decimal(30)
        self.setup_mock_data(
            maximum_withdrawal_percentage_limit=maximum_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawal_tracker_bal,
        )
        max_withdrawal_limit = (
            (default_bal + withdrawal_tracker_bal) * maximum_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(max_withdrawal_limit, Decimal(16))
        expected_result = AttributeHookResult(attribute_value=max_withdrawal_limit)
        result = early_withdrawal_fees.maximum_withdrawal_limit_attribute_handler(
            vault=self.mock_vault,
            hook_arguments=AttributeHookArguments(
                attribute_name=early_withdrawal_fees.MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE.name,
                effective_datetime=self.effective_datetime,
            ),
        )
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_get_fee_free_withdrawal_limit_attribute(
        self,
    ):
        fee_free_withdrawal_percentage_limit = Decimal("0.1")
        default_bal = Decimal(96)
        withdrawals_tracker_bal = Decimal(4)
        early_withdrawal_flat_fee = Decimal(10)
        early_withdrawal_percentage_fee = Decimal("0.2")
        self.setup_mock_data(
            early_withdrawal_flat_fee=early_withdrawal_flat_fee,
            early_withdrawal_percentage_fee=early_withdrawal_percentage_fee,
            fee_free_withdrawal_percentage_limit=fee_free_withdrawal_percentage_limit,
            default_bal=default_bal,
            withdrawals_tracker_bal=withdrawals_tracker_bal,
        )
        fee_free_withdrawal_limit: Decimal = (
            (default_bal + withdrawals_tracker_bal) * fee_free_withdrawal_percentage_limit
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(fee_free_withdrawal_limit, Decimal(10))
        expected_result = AttributeHookResult(attribute_value=fee_free_withdrawal_limit)
        result = early_withdrawal_fees.fee_free_withdrawal_limit_attribute_handler(
            vault=self.mock_vault,
            hook_arguments=AttributeHookArguments(
                attribute_name=early_withdrawal_fees.FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE.name,
                effective_datetime=self.effective_datetime,
            ),
        )
        self.assertEqual(result, expected_result)
