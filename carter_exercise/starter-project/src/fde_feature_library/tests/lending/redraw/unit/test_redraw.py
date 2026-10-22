# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, call, patch, sentinel

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.lending.redraw.redraw as redraw
from feature_library.common.state_utils import SmartContractState

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Posting,
    Rejection,
    RejectionReason,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import SentinelPosting


class RedrawTestCommon(FeatureTest):
    default_denomination = "AUD"
    tside = Tside.ASSET


class AutoRepaymentTest(RedrawTestCommon):
    default_account_id = "default_account"
    default_due_posting_instructions = [
        RedrawTestCommon().custom_instruction(
            postings=[
                Posting(
                    credit=False,
                    amount=Decimal("50"),
                    denomination=RedrawTestCommon().default_denomination,
                    account_id=default_account_id,
                    account_address="PRINCIPAL_DUE",
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=True,
                    amount=Decimal("50"),
                    denomination=RedrawTestCommon().default_denomination,
                    account_id=sentinel.internal_account_id,
                    account_address="INTERNAL",
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=False,
                    amount=Decimal("10"),
                    denomination=RedrawTestCommon().default_denomination,
                    account_id=default_account_id,
                    account_address="INTEREST_DUE",
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=True,
                    amount=Decimal("10"),
                    denomination=RedrawTestCommon().default_denomination,
                    account_id=sentinel.internal_account_id,
                    account_address="INTERNAL",
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ]
        )
    ]
    default_repayment_hierarchy = ["PRINCIPAL_DUE", "INTEREST_DUE"]

    @pytest.mark.unit
    def test_no_redraw_balance_returns_no_postings(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("0"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=self.default_due_posting_instructions,
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        self.assertEqual(auto_repayment_result, [])

    @pytest.mark.unit
    def test_no_due_amount_balances_returns_no_postings(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=[],
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        self.assertEqual(auto_repayment_result, [])

    @pytest.mark.unit
    def test_no_repayment_hierarchy_returns_no_postings(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=self.default_due_posting_instructions,
            repayment_hierarchy=[],
        )

        # assertions
        self.assertEqual(auto_repayment_result, [])

    @patch.object(redraw.payments, "redistribute_postings")
    @pytest.mark.unit
    def test_redraw_balance_pays_off_part_of_first_due_balance(
        self,
        mock_redistribute_postings: MagicMock,
    ):
        auto_repay_due_postings = [SentinelPosting("auto_repay_principal_due_balance")] * 2
        mock_redistribute_postings.return_value = auto_repay_due_postings

        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=[
                self.custom_instruction(
                    postings=[
                        Posting(
                            credit=False,
                            amount=Decimal("60"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=self.default_account_id,
                            account_address="PRINCIPAL_DUE",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=True,
                            amount=Decimal("60"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id="1",
                            account_address="INTERNAL",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                    ]
                )
            ],
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        mock_redistribute_postings.assert_called_with(
            debit_account=self.default_account_id,
            denomination=self.default_denomination,
            amount=Decimal("55"),
            credit_account=self.default_account_id,
            credit_address="PRINCIPAL_DUE",
            debit_address="REDRAW",
        )
        self.assertEqual(
            auto_repayment_result,
            [
                CustomInstruction(
                    postings=auto_repay_due_postings,  # type: ignore
                    instruction_details={
                        "description": "Auto repay due balances from the redraw balance",
                        "event": "PROCESS_AUTO_REPAYMENT_FROM_REDRAW_BALANCE",
                    },
                    override_all_restrictions=True,
                )
            ],
        )

    @patch.object(redraw.payments, "redistribute_postings")
    @pytest.mark.unit
    def test_redraw_balance_pays_off_all_of_first_due_balance_and_part_of_second_due_balance(
        self,
        mock_redistribute_postings: MagicMock,
    ):
        auto_repay_due_postings = [
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
        ]
        mock_redistribute_postings.side_effect = [
            [auto_repay_due_postings[0], auto_repay_due_postings[1]],
            [auto_repay_due_postings[2], auto_repay_due_postings[3]],
        ]

        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=self.default_due_posting_instructions,
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        mock_redistribute_postings.assert_has_calls(
            [
                call(
                    debit_account=self.default_account_id,
                    denomination=self.default_denomination,
                    amount=Decimal("50"),
                    credit_account=self.default_account_id,
                    credit_address="PRINCIPAL_DUE",
                    debit_address="REDRAW",
                ),
                call(
                    debit_account=self.default_account_id,
                    denomination=self.default_denomination,
                    amount=Decimal("5"),
                    credit_account=self.default_account_id,
                    credit_address="INTEREST_DUE",
                    debit_address="REDRAW",
                ),
            ]
        )
        self.assertEqual(
            auto_repayment_result,
            [
                CustomInstruction(
                    postings=auto_repay_due_postings,  # type: ignore
                    instruction_details={
                        "description": "Auto repay due balances from the redraw balance",
                        "event": "PROCESS_AUTO_REPAYMENT_FROM_REDRAW_BALANCE",
                    },
                    override_all_restrictions=True,
                )
            ],
        )

    @patch.object(redraw.payments, "redistribute_postings")
    @pytest.mark.unit
    def test_redraw_balance_pays_off_all_due_balances(
        self,
        mock_redistribute_postings: MagicMock,
    ):
        auto_repay_due_postings = [
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
        ]
        mock_redistribute_postings.side_effect = [
            [auto_repay_due_postings[0], auto_repay_due_postings[1]],
            [auto_repay_due_postings[2], auto_repay_due_postings[3]],
        ]

        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=[
                self.custom_instruction(
                    postings=[
                        Posting(
                            credit=False,
                            amount=Decimal("30"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=self.default_account_id,
                            account_address="PRINCIPAL_DUE",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=True,
                            amount=Decimal("30"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=sentinel.internal_account_id,
                            account_address="INTERNAL",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=False,
                            amount=Decimal("25"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=self.default_account_id,
                            account_address="INTEREST_DUE",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=True,
                            amount=Decimal("25"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=sentinel.internal_account_id,
                            account_address="INTERNAL",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                    ]
                )
            ],
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        mock_redistribute_postings.assert_has_calls(
            [
                call(
                    debit_account=self.default_account_id,
                    denomination=self.default_denomination,
                    amount=Decimal("30"),
                    credit_account=self.default_account_id,
                    credit_address="PRINCIPAL_DUE",
                    debit_address="REDRAW",
                ),
                call(
                    debit_account=self.default_account_id,
                    denomination=self.default_denomination,
                    amount=Decimal("25"),
                    credit_account=self.default_account_id,
                    credit_address="INTEREST_DUE",
                    debit_address="REDRAW",
                ),
            ]
        )
        self.assertEqual(
            auto_repayment_result,
            [
                CustomInstruction(
                    postings=auto_repay_due_postings,  # type: ignore
                    instruction_details={
                        "description": "Auto repay due balances from the redraw balance",
                        "event": "PROCESS_AUTO_REPAYMENT_FROM_REDRAW_BALANCE",
                    },
                    override_all_restrictions=True,
                )
            ],
        )

    @patch.object(redraw.payments, "redistribute_postings")
    @pytest.mark.unit
    def test_redraw_balance_pays_off_all_due_balances_with_leftover_redraw(
        self,
        mock_redistribute_postings: MagicMock,
    ):
        auto_repay_due_postings = [
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_principal_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
            SentinelPosting("auto_repay_interest_due_balance"),
        ]
        mock_redistribute_postings.side_effect = [
            [
                auto_repay_due_postings[0],
                auto_repay_due_postings[1],
                auto_repay_due_postings[2],
                auto_repay_due_postings[3],
            ]
        ]

        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-55.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(account_id=self.default_account_id),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        auto_repayment_result = redraw.auto_repayment(
            state=mock_state,
            due_amount_posting_instructions=[
                self.custom_instruction(
                    postings=[
                        Posting(
                            credit=False,
                            amount=Decimal("30"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=self.default_account_id,
                            account_address="PRINCIPAL_DUE",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            credit=True,
                            amount=Decimal("30"),
                            denomination=RedrawTestCommon().default_denomination,
                            account_id=sentinel.internal_account_id,
                            account_address="INTERNAL",
                            asset=DEFAULT_ASSET,
                            phase=Phase.COMMITTED,
                        ),
                    ]
                )
            ],
            repayment_hierarchy=self.default_repayment_hierarchy,
        )

        # assertions
        mock_redistribute_postings.assert_called_once_with(
            debit_account=self.default_account_id,
            denomination=self.default_denomination,
            amount=Decimal("30"),
            credit_account=self.default_account_id,
            credit_address="PRINCIPAL_DUE",
            debit_address="REDRAW",
        )
        self.assertEqual(
            auto_repayment_result,
            [
                CustomInstruction(
                    postings=auto_repay_due_postings,
                    instruction_details={
                        "description": "Auto repay due balances from the redraw balance",
                        "event": "PROCESS_AUTO_REPAYMENT_FROM_REDRAW_BALANCE",
                    },
                    override_all_restrictions=True,
                )
            ],
        )


class HandleOverpaymentTest(RedrawTestCommon):
    @patch.object(redraw.posting_utils, "create_postings")
    @pytest.mark.unit
    def test_handle_overpayment_rebalances_to_redraw(self, mock_create_postings: MagicMock):
        mock_vault = self.create_mock()
        mock_state = SmartContractState(
            balances=sentinel.balances,
            parameters={denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        mock_create_postings.return_value = [sentinel.redraw_postings]

        result = redraw.handle_overpayment(
            state=mock_state,
            overpayment_amount=sentinel.overpayment_amount,
        )

        self.assertListEqual(result, [sentinel.redraw_postings])
        mock_create_postings.assert_called_once_with(
            debit_account=mock_vault.account_id,
            denomination=sentinel.denomination,
            amount=sentinel.overpayment_amount,
            credit_account=mock_vault.account_id,
            credit_address=redraw.REDRAW_ADDRESS,
        )


class GetAvailableRedrawFundsTest(RedrawTestCommon):
    @pytest.mark.unit
    def test_returns_redraw_balance(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=sentinel.denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(credit=Decimal("10"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )

        redraw_funds = redraw.get_available_redraw_funds(
            state=mock_state,
        )

        # assertions
        self.assertEqual(redraw_funds, Decimal("10"))


class RejectClosureWhenOutstandingRedrawFundsTest(RedrawTestCommon):
    default_balances = sentinel.balances

    @pytest.mark.unit
    def test_rejects_when_redraw_has_positive_balance(self):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("10"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        outstanding_redraw_funds_rejection = redraw.reject_closure_when_outstanding_redraw_funds(
            state=mock_state,
        )

        # assertions
        self.assertEqual(
            outstanding_redraw_funds_rejection,
            Rejection(
                message="The loan cannot be closed until all remaining redraw funds are cleared.",
                reason_code=RejectionReason.AGAINST_TNC,
            ),
        )

    @pytest.mark.unit
    def test_rejects_when_redraw_has_negative_balance(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("-10"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        outstanding_redraw_funds_rejection = redraw.reject_closure_when_outstanding_redraw_funds(
            state=mock_state,
        )

        # assertions
        self.assertEqual(
            outstanding_redraw_funds_rejection,
            Rejection(
                message="The loan cannot be closed until all remaining redraw funds are cleared.",
                reason_code=RejectionReason.AGAINST_TNC,
            ),
        )

    @pytest.mark.unit
    def test_does_not_reject_when_redraw_has_zero_balance(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(Decimal("0"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        outstanding_redraw_funds_rejection = redraw.reject_closure_when_outstanding_redraw_funds(
            state=mock_state,
        )

        # assertions
        self.assertIsNone(outstanding_redraw_funds_rejection)


class ValidateRedrawFundsTest(RedrawTestCommon):
    default_balances = sentinel.balances

    @pytest.mark.unit
    def test_posting_amount_of_0_is_accepted(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(credit=Decimal("10.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        validate_redraw_funds_result = redraw.validate_redraw_funds(
            state=mock_state,
            posting_amount=Decimal("0"),
        )

        # assertions
        self.assertIsNone(validate_redraw_funds_result)

    @pytest.mark.unit
    def test_posting_amount_below_the_redraw_balance_is_accepted(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(credit=Decimal("10.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        validate_redraw_funds_result = redraw.validate_redraw_funds(
            state=mock_state,
            posting_amount=Decimal("5.25"),
        )

        # assertions
        self.assertIsNone(validate_redraw_funds_result)

    @pytest.mark.unit
    def test_posting_amount_equal_to_the_redraw_balance_is_accepted(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(credit=Decimal("10.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        validate_redraw_funds_result = redraw.validate_redraw_funds(
            state=mock_state,
            posting_amount=Decimal("10"),
        )

        # assertions
        self.assertIsNone(validate_redraw_funds_result)

    @pytest.mark.unit
    def test_posting_amount_above_redraw_balance_is_rejected(
        self,
    ):
        mock_state = SmartContractState(
            balances=BalanceDefaultDict(
                mapping={
                    BalanceCoordinate(
                        account_address="REDRAW",
                        asset=DEFAULT_ASSET,
                        denomination=self.default_denomination,
                        phase=Phase.COMMITTED,
                    ): Balance(credit=Decimal("10.00"))
                }
            ),
            parameters={denomination_module.DENOMINATION_PARAM_ID: self.default_denomination},
            vault=self.create_mock(),
            effective_datetime=sentinel.effective_datetime,
            inflight_postings=None,
        )
        validate_redraw_funds_result = redraw.validate_redraw_funds(
            state=mock_state,
            posting_amount=Decimal("10.01"),
        )

        # assertions
        expected_rejection = Rejection(
            message=f"Transaction amount 10.01 {self.default_denomination} is greater than "
            f"the available redraw funds of 10.00 {self.default_denomination}.",
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )
        self.assertEqual(expected_rejection, validate_redraw_funds_result)
