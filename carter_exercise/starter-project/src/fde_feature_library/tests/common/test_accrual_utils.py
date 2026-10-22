# standard libs
from decimal import Decimal
from unittest.mock import sentinel

import pytest

# features
import feature_library.common.accrual_utils as accruals

# contracts api
from contracts_api import DEFAULT_ADDRESS, DEFAULT_ASSET, CustomInstruction, Phase, Posting

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class AccrualsTestCommon(FeatureTest):
    maxDiff = None


class AccrualCustomInstructionTest(AccrualsTestCommon):
    common_args = {
        "customer_account": sentinel.customer_account,
        "denomination": sentinel.denomination,
        "customer_address": sentinel.customer_address,
        "internal_account": sentinel.internal_account,
    }

    @pytest.mark.unit
    def test_create_payable_accrual_custom_instruction_payable_non_reversal(self):
        result = accruals.create_payable_accrual_custom_instruction(
            amount=Decimal("1"),
            reversal=False,
            instruction_details={"test": "details"},
            **self.common_args,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=Decimal("1"),
                        denomination=sentinel.denomination,
                        account_id=sentinel.internal_account,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal("1"),
                        denomination=sentinel.denomination,
                        account_id=sentinel.customer_account,
                        account_address=sentinel.customer_address,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={"test": "details"},
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_create_payable_accrual_custom_instruction_0_amount(self):
        self.assertListEqual(
            accruals.create_payable_accrual_custom_instruction(
                amount=Decimal("0"),
                instruction_details={"test": "details"},
                **self.common_args,
            ),
            [],
        )

    @pytest.mark.unit
    def test_create_payable_accrual_custom_instruction_negative_amount(self):
        # A negative payable should result in a DEBIT to customer (flipped)
        result = accruals.create_payable_accrual_custom_instruction(
            amount=Decimal("-1"),
            reversal=False,
            instruction_details={"test": "details"},
            **self.common_args,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].instruction_details, {"test": "details"})
        self.assertEqual(result[0].override_all_restrictions, True)
        self.assertCountEqual(
            result[0].postings,
            [
                Posting(
                    credit=False,
                    amount=Decimal("1"),
                    denomination=sentinel.denomination,
                    account_id=sentinel.customer_account,
                    account_address=sentinel.customer_address,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=True,
                    amount=Decimal("1"),
                    denomination=sentinel.denomination,
                    account_id=sentinel.internal_account,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ],
        )


class CreateAccrualApplicationPostingsTest(AccrualsTestCommon):
    common_args = {
        "customer_account": sentinel.customer_account,
        "denomination": sentinel.denomination,
        "accrual_customer_address": sentinel.accrual_customer_address,
        "accrual_internal_account": sentinel.accrual_internal_account,
        "application_internal_account": sentinel.application_internal_account,
        "application_customer_address": sentinel.application_customer_address,
    }

    @pytest.mark.unit
    def test_create_payable_accrual_application_postings_payable(self):
        result = accruals.create_payable_accrual_application_postings(
            application_amount=Decimal("1"),
            accrual_amount=Decimal("1.5"),
            **self.common_args,
        )
        expected = [
            # Application (Credit Customer)
            Posting(
                credit=False,
                amount=Decimal("1"),
                denomination=sentinel.denomination,
                account_address=DEFAULT_ADDRESS,
                account_id=sentinel.application_internal_account,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
            Posting(
                credit=True,
                amount=Decimal("1"),
                denomination=sentinel.denomination,
                account_address=sentinel.application_customer_address,
                account_id=sentinel.customer_account,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
            # Reversal of Payable (Debit Customer)
            Posting(
                credit=False,
                amount=Decimal("1.5"),
                denomination=sentinel.denomination,
                account_id=sentinel.customer_account,
                account_address=sentinel.accrual_customer_address,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
            # Reversal of Payable (Credit Internal)
            Posting(
                credit=True,
                amount=Decimal("1.5"),
                denomination=sentinel.denomination,
                account_id=sentinel.accrual_internal_account,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_create_payable_accrual_application_postings_zero_amount(self):
        self.assertListEqual(
            accruals.create_payable_accrual_application_postings(
                application_amount=Decimal("0"),
                accrual_amount=Decimal("0"),
                **self.common_args,
            ),
            [],
        )


class AccrualApplicationCustomInstructionTest(AccrualsTestCommon):
    common_args = {
        "customer_account": sentinel.customer_account,
        "denomination": sentinel.denomination,
        "accrual_customer_address": sentinel.accrual_customer_address,
        "accrual_internal_account": sentinel.accrual_internal_account,
        "application_internal_account": sentinel.application_internal_account,
        "application_customer_address": sentinel.application_customer_address,
    }

    @pytest.mark.unit
    def test_create_payable_accrual_application_custom_instruction_payable(self):
        result = accruals.create_payable_accrual_application_custom_instruction(
            application_amount=Decimal("1"),
            accrual_amount=Decimal("1.5"),
            instruction_details={"test": "details"},
            **self.common_args,
        )
        expected = [
            CustomInstruction(
                postings=[
                    # Application (Credit Customer)
                    Posting(
                        credit=False,
                        amount=Decimal("1"),
                        denomination=sentinel.denomination,
                        account_address=DEFAULT_ADDRESS,
                        account_id=sentinel.application_internal_account,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal("1"),
                        denomination=sentinel.denomination,
                        account_address=sentinel.application_customer_address,
                        account_id=sentinel.customer_account,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    # Reversal of Payable (Debit Customer)
                    Posting(
                        credit=False,
                        amount=Decimal("1.5"),
                        denomination=sentinel.denomination,
                        account_id=sentinel.customer_account,
                        account_address=sentinel.accrual_customer_address,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    # Reversal of Payable (Credit Internal)
                    Posting(
                        credit=True,
                        amount=Decimal("1.5"),
                        denomination=sentinel.denomination,
                        account_id=sentinel.accrual_internal_account,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={"test": "details"},
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_create_payable_accrual_application_custom_instruction_zero_amount(self):
        self.assertListEqual(
            accruals.create_payable_accrual_application_custom_instruction(
                application_amount=Decimal("0"),
                accrual_amount=Decimal("0"),
                instruction_details={"test": "details"},
                **self.common_args,
            ),
            [],
        )

    @pytest.mark.unit
    def test_create_payable_accrual_application_custom_instruction_negative_application_flips(self):
        # Negative payable application flips from Credit Customer to Debit Customer
        result = accruals.create_payable_accrual_application_custom_instruction(
            application_amount=Decimal("-1"),
            accrual_amount=Decimal("0"),
            instruction_details={"test": "details"},
            **self.common_args,
        )
        # result[0] is the CustomInstruction
        # result[0].postings contains the individual Posting objects
        self.assertEqual(len(result[0].postings), 2)
        self.assertCountEqual(
            result[0].postings,
            [
                # Application (Debit Customer because of negative amount)
                Posting(
                    credit=False,
                    amount=Decimal("1"),
                    denomination=sentinel.denomination,
                    account_address=sentinel.application_customer_address,
                    account_id=sentinel.customer_account,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=True,
                    amount=Decimal("1"),
                    denomination=sentinel.denomination,
                    account_address=DEFAULT_ADDRESS,
                    account_id=sentinel.application_internal_account,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ],
        )

    @pytest.mark.unit
    def test_create_payable_accrual_application_custom_instruction_negative_accrual_flips(self):
        # Negative payable accrual reversal flips from Debit Customer to Credit Customer
        result = accruals.create_payable_accrual_application_custom_instruction(
            application_amount=Decimal("1"),
            accrual_amount=Decimal("-1.5"),
            instruction_details={"test": "details"},
            **self.common_args,
        )
        # 1. Application (Credit Customer) - Decimal(1)
        # 2. Reversal of negative accrual (Credit Customer) - Decimal(1.5)
        # Result: Total 2.5 credit to customer
        self.assertEqual(len(result[0].postings), 4)
        customer_postings = [
            p for p in result[0].postings if p.account_id == sentinel.customer_account
        ]
        self.assertTrue(all(p.credit for p in customer_postings))
        self.assertEqual(sum(p.amount for p in customer_postings), Decimal("2.5"))
