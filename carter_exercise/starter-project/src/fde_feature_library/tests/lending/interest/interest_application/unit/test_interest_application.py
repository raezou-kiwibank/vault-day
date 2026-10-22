# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination_module
import feature_library.lending.interest.interest_application as interest_application
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelBalancesObservation,
)

from tests.utils import initialise_mock_state

ACCRUED_RECEIVABLE_COORDINATE = BalanceCoordinate(
    interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    DEFAULT_ASSET,
    sentinel.denomination,
    Phase.COMMITTED,
)

PARAM_ACCRUED_INTEREST_RECEIVABLE_ACCOUNT = (
    interest_application.interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID
)
PARAM_INTEREST_RECEIVED_ACCOUNT = interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID
PARAM_APPLICATION_PRECISION = application_precision_module.APPLICATION_PRECISION_PARAM.id


class InterestApplicationTestCommon(FeatureTest):
    maxDiff = None

    def create_mock(
        self,
        account_id: str = sentinel.account_id,
        balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
        parameters_observation_fetchers_mapping: dict[str, ParametersObservation] | None = None,
        **kwargs,
    ) -> MagicMock:
        balances_observation_fetchers_mapping = balances_observation_fetchers_mapping or {
            interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                balances=BalanceDefaultDict()
            )
        }
        parameters_observation_fetchers_mapping = parameters_observation_fetchers_mapping or {
            interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID: ParametersObservation(
                parameters=getattr(self, "parameters", {}),
                value_datetime=DEFAULT_DATETIME,
            )
        }
        return super().create_mock(
            account_id=account_id,
            balances_observation_fetchers_mapping=balances_observation_fetchers_mapping,
            parameters_observation_fetchers_mapping=parameters_observation_fetchers_mapping,
            **kwargs,
        )


class InterestApplicationTest(InterestApplicationTestCommon):
    # These amounts are such that accrued interest at effective datetime (20.4469) rounds
    # differently to the sum of rounded non-eia (10.12345) and eia (20.4469-10.12345)
    # i.e. round(20.4469, 2) -> 20.45 != round(10.12345, 2) + round(10.32345, 2) -> 20.44
    effective_datetime_balances = BalanceDefaultDict(
        mapping={
            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("20.4469")),
        }
    )
    one_month_ago_balances = BalanceDefaultDict(
        mapping={
            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("10.12345")),
        }
    )

    parameters = {
        PARAM_APPLICATION_PRECISION: 2,
        denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
        PARAM_ACCRUED_INTEREST_RECEIVABLE_ACCOUNT: sentinel.accrued_int_receivable_account,
        PARAM_INTEREST_RECEIVED_ACCOUNT: sentinel.interest_received_account,
    }

    @patch.object(interest_application, "_get_interest_to_apply")
    @patch.object(
        interest_application.accrual_utils, "create_receivable_accrual_application_postings"
    )
    @pytest.mark.unit
    def test_apply_interest(
        self,
        mock_create_payable_accrual_application_postings: MagicMock,
        mock_get_interest_to_apply: MagicMock,
    ):
        mock_vault = self.create_mock(
            account_id=sentinel.account_id,
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=self.effective_datetime_balances
                ),
                interest_application.ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID: (
                    SentinelBalancesObservation("one_month_ago")
                ),
            },
        )
        mock_get_interest_to_apply.return_value = lending_interfaces.InterestAmounts(
            eia_accrued=Decimal("10.32345"),
            eia_rounded_accrued=Decimal("10.32"),
            non_eia_accrued=Decimal("10.42345"),
            non_eia_rounded_accrued=Decimal("10.42"),
            total_rounded=Decimal("20.75"),
        )
        mock_create_payable_accrual_application_postings.return_value = [
            sentinel.application_posting
        ]

        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters=self.parameters,
        )

        daily_accrual_postings = interest_application.apply_interest(
            state=state,
            previous_application_datetime=sentinel.previous_application_datetime,
        )

        self.assertEqual(daily_accrual_postings, [sentinel.application_posting])
        mock_create_payable_accrual_application_postings.assert_called_once_with(
            customer_account=sentinel.account_id,
            denomination=sentinel.denomination,
            application_amount=Decimal("20.75"),
            accrual_amount=Decimal("20.74690"),
            accrual_customer_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,  # noqa: E501
            accrual_internal_account=sentinel.accrued_int_receivable_account,
            application_customer_address=interest_application.lending_addresses.INTEREST_DUE,
            application_internal_account=sentinel.interest_received_account,
        )
        mock_get_interest_to_apply.assert_called_once_with(
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=sentinel.balances_one_month_ago,
            denomination=sentinel.denomination,
            application_precision=2,
            effective_datetime=sentinel.effective_datetime,
            previous_application_datetime=sentinel.previous_application_datetime,
            accrual_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        )

    @pytest.mark.unit
    def test_get_application_precision(self):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={PARAM_APPLICATION_PRECISION: 2},
        )
        self.assertEqual(
            interest_application.application_precision_module.get_application_precision(
                state=state, application_precision_param_id=PARAM_APPLICATION_PRECISION
            ),
            2,
        )

    @pytest.mark.unit
    def test_get_interest_to_apply_effective_effective_datetime_greater_than_1_month_from_previous(
        self,
    ):
        effective_datetime = DEFAULT_DATETIME + relativedelta(months=1, days=1)
        previous_application_datetime = DEFAULT_DATETIME
        result = interest_application._get_interest_to_apply(
            effective_datetime=effective_datetime,
            previous_application_datetime=previous_application_datetime,
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=self.one_month_ago_balances,
            denomination=sentinel.denomination,
            application_precision=2,
            accrual_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        )
        self.assertEqual(
            result,
            lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("10.32345"),
                eia_rounded_accrued=Decimal("10.33"),
                non_eia_accrued=Decimal("10.12345"),
                non_eia_rounded_accrued=Decimal("10.12"),
                total_rounded=Decimal("20.45"),
            ),
        )

    @pytest.mark.unit
    def test_get_interest_to_apply_effective_effective_datetime_exactly_1_month_from_previous(
        self,
    ):
        effective_datetime = DEFAULT_DATETIME + relativedelta(months=1)
        previous_application_datetime = DEFAULT_DATETIME
        result = interest_application._get_interest_to_apply(
            effective_datetime=effective_datetime,
            previous_application_datetime=previous_application_datetime,
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=self.one_month_ago_balances,
            denomination=sentinel.denomination,
            application_precision=2,
            accrual_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        )
        self.assertEqual(
            result,
            lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("10.32345"),
                eia_rounded_accrued=Decimal("10.33"),
                non_eia_accrued=Decimal("10.12345"),
                non_eia_rounded_accrued=Decimal("10.12"),
                total_rounded=Decimal("20.45"),
            ),
        )

    @pytest.mark.unit
    def test_get_interest_to_apply_effective_effective_datetime_less_than_1_month_from_previous(
        self,
    ):
        effective_datetime = DEFAULT_DATETIME + relativedelta(days=10)
        previous_application_datetime = DEFAULT_DATETIME
        result = interest_application._get_interest_to_apply(
            effective_datetime=effective_datetime,
            previous_application_datetime=previous_application_datetime,
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=self.one_month_ago_balances,
            denomination=sentinel.denomination,
            application_precision=2,
            accrual_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        )
        self.assertEqual(
            result,
            lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("20.4469"),
                eia_rounded_accrued=Decimal("20.45"),
                non_eia_accrued=Decimal("0"),
                non_eia_rounded_accrued=Decimal("0"),
                total_rounded=Decimal("20.45"),
            ),
        )

    @pytest.mark.unit
    def test_get_interest_to_apply_effective_effective_datetime_equal_previous(
        self,
    ):
        effective_datetime = DEFAULT_DATETIME
        previous_application_datetime = DEFAULT_DATETIME
        result = interest_application._get_interest_to_apply(
            effective_datetime=effective_datetime,
            previous_application_datetime=previous_application_datetime,
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=self.one_month_ago_balances,
            denomination=sentinel.denomination,
            application_precision=2,
            accrual_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        )
        self.assertEqual(
            result,
            lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("20.4469"),
                eia_rounded_accrued=Decimal("20.45"),
                non_eia_accrued=Decimal("0"),
                non_eia_rounded_accrued=Decimal("0"),
                total_rounded=Decimal("20.45"),
            ),
        )

    @patch.object(interest_application, "_get_interest_to_apply")
    @pytest.mark.unit
    def test_get_interest_to_apply_wrapper(
        self,
        mock_get_interest_to_apply: MagicMock,
    ):
        mock_get_interest_to_apply.return_value = sentinel.interest_amounts
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=self.effective_datetime_balances
                ),
                interest_application.ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID: (
                    SentinelBalancesObservation("one_month_ago_accrual")
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters=self.parameters,
        )

        self.assertEqual(
            interest_application.get_interest_to_apply(
                state=state,
                previous_application_datetime=sentinel.previous_application_datetime,
            ),
            sentinel.interest_amounts,
        )

        mock_get_interest_to_apply.assert_called_once_with(
            balances_at_application=self.effective_datetime_balances,
            balances_one_repayment_period_ago=sentinel.balances_one_month_ago_accrual,
            denomination=sentinel.denomination,
            application_precision=2,
            effective_datetime=sentinel.effective_datetime,
            previous_application_datetime=sentinel.previous_application_datetime,
            accrual_address="ACCRUED_INTEREST_RECEIVABLE",
        )


class RepayAccruedInterestTest(InterestApplicationTestCommon):
    parameters: dict[str, str | Decimal] = {
        denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
        PARAM_ACCRUED_INTEREST_RECEIVABLE_ACCOUNT: sentinel.receivable,
        PARAM_INTEREST_RECEIVED_ACCOUNT: sentinel.received,
        PARAM_APPLICATION_PRECISION: Decimal("2"),
    }

    effective_datetime_balances = BalanceDefaultDict(
        mapping={
            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("20.4469")),
        }
    )

    @pytest.mark.unit
    def test_repay_accrued_interest_with_0_repayment_amount(self):
        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=sentinel.state, repayment_amount=Decimal("0")
            ),
            [],
        )

    @pytest.mark.unit
    def test_repay_accrued_interest_with_negative_repayment_amount(self):
        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=sentinel.state, repayment_amount=Decimal("-1")
            ),
            [],
        )

    @pytest.mark.unit
    def test_repay_accrued_interest_with_no_accrued_interest(self):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={
                            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("0")),
                        }
                    )
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            parameters=self.parameters,
        )

        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=state,
                repayment_amount=Decimal("10"),
            ),
            [],
        )

    @pytest.mark.unit
    def test_repay_accrued_interest_with_0_rounded_accrued_interest(self):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={
                            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("0.001")),
                        }
                    )
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            parameters=self.parameters,
        )

        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=state,
                repayment_amount=Decimal("10"),
            ),
            [],
        )

    @patch.object(
        interest_application.accrual_utils, "create_receivable_accrual_application_postings"
    )
    @pytest.mark.unit
    def test_repay_accrued_interest_with_rounded_interest_equal_to_repayment(
        self,
        mock_create_payable_accrual_application_postings: MagicMock,
    ):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={
                            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("1.01234")),
                        }
                    )
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            parameters=self.parameters,
        )
        mock_create_payable_accrual_application_postings.return_value = [sentinel.apply_posting]

        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=state,
                repayment_amount=Decimal("1.01"),
            ),
            [sentinel.apply_posting],
        )

        mock_create_payable_accrual_application_postings.assert_called_once_with(
            customer_account=mock_vault.account_id,
            denomination=sentinel.denomination,
            application_amount=Decimal("1.01"),
            accrual_amount=Decimal("1.01234"),
            accrual_customer_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,  # noqa: E501
            accrual_internal_account=sentinel.receivable,
            application_customer_address=interest_application.DEFAULT_ADDRESS,
            application_internal_account=sentinel.received,
        )

    @patch.object(
        interest_application.accrual_utils, "create_receivable_accrual_application_postings"
    )
    @pytest.mark.unit
    def test_repay_accrued_interest_with_rounded_interest_less_than_repayment(
        self,
        mock_create_payable_accrual_application_postings: MagicMock,
    ):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={
                            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("1.01234")),
                        }
                    )
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            parameters=self.parameters,
        )
        mock_create_payable_accrual_application_postings.return_value = [sentinel.apply_posting]

        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=state,
                repayment_amount=Decimal("10"),
            ),
            [sentinel.apply_posting],
        )

        mock_create_payable_accrual_application_postings.assert_called_once_with(
            customer_account=mock_vault.account_id,
            denomination=sentinel.denomination,
            application_amount=Decimal("1.01"),
            accrual_amount=Decimal("1.01234"),
            accrual_customer_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,  # noqa: E501
            accrual_internal_account=sentinel.receivable,
            application_customer_address=interest_application.DEFAULT_ADDRESS,
            application_internal_account=sentinel.received,
        )

    @patch.object(
        interest_application.accrual_utils, "create_receivable_accrual_application_postings"
    )
    @pytest.mark.unit
    def test_repay_accrued_interest_with_interest_over_repayment(
        self,
        mock_create_payable_accrual_application_postings: MagicMock,
    ):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                interest_application.ACCRUED_INTEREST_ET_BOF_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={
                            ACCRUED_RECEIVABLE_COORDINATE: Balance(debit=Decimal("1.01234")),
                        }
                    )
                ),
            }
        )
        state = initialise_mock_state(
            vault=mock_vault,
            parameters=self.parameters,
        )
        mock_create_payable_accrual_application_postings.return_value = [sentinel.apply_posting]

        self.assertListEqual(
            interest_application.repay_accrued_interest(
                state=state,
                repayment_amount=Decimal("1.00"),
            ),
            [sentinel.apply_posting],
        )

        mock_create_payable_accrual_application_postings.assert_called_once_with(
            customer_account=mock_vault.account_id,
            denomination=sentinel.denomination,
            application_amount=Decimal("1.00"),
            accrual_amount=Decimal("1.00"),
            accrual_customer_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,  # noqa: E501
            accrual_internal_account=sentinel.receivable,
            application_customer_address=interest_application.DEFAULT_ADDRESS,
            application_internal_account=sentinel.received,
        )
