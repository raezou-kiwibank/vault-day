# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.lending.addresses as lending_addresses

# features
import feature_library.lending.interest.interest_capitalisation as interest_capitalisation  # noqa: E501

# contracts api
from contracts_api import DEFAULT_ASSET, BalanceCoordinate, CustomInstruction, Phase

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelPosting,
)

PRINCIPAL_COORDINATE = BalanceCoordinate(
    "PRINCIPAL",
    DEFAULT_ASSET,
    sentinel.denomination,
    Phase.COMMITTED,
)


class InterestCapitalisationTest(FeatureTest):
    maxDiff = None


@patch.object(interest_capitalisation.accruals, "create_receivable_accrual_application_postings")
@patch.object(interest_capitalisation.posting_utils, "create_postings")
@patch.object(interest_capitalisation.balance_utils, "balance_at_coordinates")
@patch.object(interest_capitalisation.utils, "round_decimal")
class HandleInterestCapitalisationTest(InterestCapitalisationTest):
    @pytest.mark.unit
    def test_handle_interest_capitalisation_applies_pending_capitalisation_accrued_interest(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
        mock_accrual_application_postings: MagicMock,
    ):
        mock_round_decimal.return_value = Decimal("1")
        mock_balance_at_coordinates.return_value = sentinel.unrounded_interest
        application_posting = SentinelPosting("application")
        tracker_posting = SentinelPosting("tracker")
        mock_accrual_application_postings.return_value = [application_posting]
        mock_create_postings.return_value = [tracker_posting]

        mock_state = MagicMock(
            vault=self.create_mock(account_id=sentinel.account_id),
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                ),
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID: sentinel.capitalised_received_account,  # noqa: E501
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: sentinel.capitalised_receivable_account,  # noqa: E501
                interest_capitalisation.application_precision_module.APPLICATION_PRECISION_PARAM.id: 2,  # noqa: E501
            },
        )

        result = interest_capitalisation.handle_interest_capitalisation(
            state=mock_state,
            accrual_address=sentinel.address_pending_capitalisation,
            target_address=lending_addresses.PRINCIPAL,
            account_type=sentinel.account_type,
        )
        self.assertListEqual(
            result,
            [
                CustomInstruction(
                    postings=[application_posting, tracker_posting],
                    instruction_details={
                        "description": "Capitalise interest accrued to principal",
                        "event": "END_OF_REPAYMENT_HOLIDAY",
                        "gl_impacted": "True",
                        "account_type": sentinel.account_type,
                    },
                ),
            ],
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=mock_state.balances,
            denomination=sentinel.denomination,
            address=sentinel.address_pending_capitalisation,
        )
        mock_round_decimal.assert_called_once_with(
            amount=sentinel.unrounded_interest, decimal_places=2
        )
        mock_accrual_application_postings.assert_called_once_with(
            customer_account=sentinel.account_id,
            denomination=sentinel.denomination,
            accrual_amount=sentinel.unrounded_interest,
            application_amount=Decimal("1"),
            accrual_customer_address=sentinel.address_pending_capitalisation,
            accrual_internal_account=sentinel.capitalised_receivable_account,
            application_customer_address=lending_addresses.PRINCIPAL,
            application_internal_account=sentinel.capitalised_received_account,
        )

        mock_create_postings.assert_called_once_with(
            amount=Decimal("1"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address=lending_addresses.CAPITALISED_INTEREST_TRACKER,
            credit_address=interest_capitalisation.common_addresses.INTERNAL_CONTRA,
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_handle_interest_capitalisation_does_nothing_if_no_pending_capitalisation_accrued_interest(  # noqa: E501
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
        mock_accrual_application_postings: MagicMock,
    ):
        mock_round_decimal.return_value = Decimal("0")
        mock_balance_at_coordinates.return_value = sentinel.unrounded_interest
        mock_state = MagicMock(
            vault=self.create_mock(account_id=sentinel.account_id),
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                ),
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID: sentinel.capitalised_received_account,  # noqa: E501
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: sentinel.capitalised_receivable_account,  # noqa: E501
                interest_capitalisation.application_precision_module.APPLICATION_PRECISION_PARAM.id: 2,  # noqa: E501
            },
        )
        result = interest_capitalisation.handle_interest_capitalisation(
            state=mock_state,
            accrual_address=sentinel.address_pending_capitalisation,
            account_type=sentinel.account_type,
        )
        self.assertListEqual([], result)

        mock_balance_at_coordinates.assert_called_once_with(
            balances=mock_state.balances,
            denomination=sentinel.denomination,
            address=sentinel.address_pending_capitalisation,
        )
        mock_round_decimal.assert_called_once_with(
            amount=sentinel.unrounded_interest, decimal_places=2
        )
        mock_create_postings.assert_not_called()
        mock_accrual_application_postings.assert_not_called()

    @pytest.mark.unit
    def test_handle_interest_capitalisation_does_nothing_if_negative_accrued_capitalised_interest(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
        mock_accrual_application_postings: MagicMock,
    ):
        mock_round_decimal.return_value = Decimal("-10")
        mock_balance_at_coordinates.return_value = sentinel.unrounded_interest
        mock_state = MagicMock(
            vault=self.create_mock(account_id=sentinel.account_id),
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                ),
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID: sentinel.capitalised_received_account,  # noqa: E501
                interest_capitalisation.CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: sentinel.capitalised_receivable_account,  # noqa: E501
                interest_capitalisation.application_precision_module.APPLICATION_PRECISION_PARAM.id: 2,  # noqa: E501
            },
        )
        result = interest_capitalisation.handle_interest_capitalisation(
            state=mock_state,
            accrual_address=sentinel.address_pending_capitalisation,
            account_type=sentinel.account_type,
        )
        self.assertListEqual([], result)

        mock_balance_at_coordinates.assert_called_once_with(
            balances=mock_state.balances,
            denomination=sentinel.denomination,
            address=sentinel.address_pending_capitalisation,
        )
        mock_round_decimal.assert_called_once_with(
            amount=sentinel.unrounded_interest, decimal_places=2
        )
        mock_create_postings.assert_not_called()
        mock_accrual_application_postings.assert_not_called()


@patch.object(interest_capitalisation, "is_capitalise_penalty_interest")
@patch.object(interest_capitalisation, "handle_interest_capitalisation")
class HandlePenaltyInterestCapitalisationTest(InterestCapitalisationTest):
    @pytest.mark.unit
    def test_handle_penalty_interest_capitalisation_no_capitalisation(
        self,
        mock_handle_interest_capitalisation: MagicMock,
        mock_is_capitalise_penalty_interest: MagicMock,
    ):
        mock_is_capitalise_penalty_interest.return_value = False
        mock_state = MagicMock()
        result = interest_capitalisation.handle_penalty_interest_capitalisation(
            state=mock_state,
            account_type=sentinel.account_type,
        )
        self.assertListEqual([], result)
        mock_is_capitalise_penalty_interest.assert_called_once_with(state=mock_state)
        mock_handle_interest_capitalisation.assert_not_called()

    @pytest.mark.unit
    def test_handle_penalty_interest_capitalisation_with_capitalisation(
        self,
        mock_handle_interest_capitalisation: MagicMock,
        mock_is_capitalise_penalty_interest: MagicMock,
    ):
        mock_is_capitalise_penalty_interest.return_value = True
        mock_handle_interest_capitalisation.return_value = [sentinel.custom_instructions]
        mock_state = MagicMock()
        result = interest_capitalisation.handle_penalty_interest_capitalisation(
            state=mock_state,
            account_type=sentinel.account_type,
        )
        self.assertListEqual(result, [sentinel.custom_instructions])
        mock_handle_interest_capitalisation.assert_called_once_with(
            state=mock_state,
            account_type=sentinel.account_type,
            accrual_address="ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION",
            target_address="PRINCIPAL",
        )


class IsCapitalisePenaltyInterestTest(InterestCapitalisationTest):
    @pytest.mark.unit
    def test_is_capitalise_penalty_interest(self):
        mock_state = MagicMock(
            parameters={interest_capitalisation.CAPITALISE_PENALTY_INTEREST_PARAM_ID: "True"}
        )
        result = interest_capitalisation.is_capitalise_penalty_interest(
            state=mock_state,
        )
        self.assertTrue(result)


@patch.object(interest_capitalisation.application_precision_module, "get_application_precision")
@patch.object(interest_capitalisation, "handle_interest_capitalisation")
@patch.object(interest_capitalisation.balance_utils, "balance_at_coordinates")
class HandleOverpaymentsToPenaltiesPendingCapitalisationTest(InterestCapitalisationTest):
    @pytest.mark.unit
    def test_handle_overpayments_to_penalties_pending_capitalisation(
        self,
        balance_at_coordinates: MagicMock,
        mock_handle_interest_capitalisation: MagicMock,
        mock_get_application_precision: MagicMock,
    ):
        mock_handle_interest_capitalisation.return_value = [sentinel.capitalisation_postings]

        mock_state = MagicMock(
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                ),
            }
        )

        result = interest_capitalisation.handle_overpayments_to_penalties_pending_capitalisation(
            state=mock_state,
        )

        self.assertListEqual([sentinel.capitalisation_postings], result)
        mock_handle_interest_capitalisation.assert_called_once_with(
            state=mock_state,
            accrual_address="ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION",
            target_address="DEFAULT",
            account_type="",
        )

    @pytest.mark.unit
    def test_handle_overpayments_to_penalties_pending_capitalisation_zero_balance(
        self,
        mock_balance_at_coordinates: MagicMock,
        mock_handle_interest_capitalisation: MagicMock,
        mock_get_application_precision: MagicMock,
    ):
        mock_handle_interest_capitalisation.return_value = []
        mock_state = MagicMock(
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                )
            }
        )

        result = interest_capitalisation.handle_overpayments_to_penalties_pending_capitalisation(
            state=mock_state,
        )

        self.assertListEqual([], result)
        mock_handle_interest_capitalisation.assert_called_once_with(
            state=mock_state,
            accrual_address="ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION",
            target_address="DEFAULT",
            account_type="",
        )

    @pytest.mark.unit
    def test_handle_overpayments_to_penalties_pending_capitalisation_negative_balance(
        self,
        mock_balance_at_coordinates: MagicMock,
        mock_handle_interest_capitalisation: MagicMock,
        mock_get_application_precision: MagicMock,
    ):
        mock_handle_interest_capitalisation.return_value = []
        mock_state = MagicMock(
            parameters={
                interest_capitalisation.denomination_module.DENOMINATION_PARAM_ID: (
                    sentinel.denomination
                )
            }
        )

        result = interest_capitalisation.handle_overpayments_to_penalties_pending_capitalisation(
            state=mock_state,
        )

        self.assertListEqual([], result)
        mock_handle_interest_capitalisation.assert_called_once_with(
            state=mock_state,
            accrual_address="ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION",
            target_address="DEFAULT",
            account_type="",
        )
