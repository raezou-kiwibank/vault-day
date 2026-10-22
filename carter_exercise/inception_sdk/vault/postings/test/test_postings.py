# standard libs
from unittest import TestCase

# inception sdk
from inception_sdk.vault.postings.posting_classes import Transfer


class PostingClassesTest(TestCase):
    def test_transfer_to_dict_without_sub_accounts(self):
        transfer = Transfer(
            amount="10.50",
            debtor_target_account_id="debtor-1",
            creditor_target_account_id="creditor-1",
            denomination="GBP",
        )
        expected = {
            "transfer": {
                "amount": "10.50",
                "denomination": "GBP",
                "debtor_target_account": {
                    "account_id": "debtor-1",
                },
                "creditor_target_account": {
                    "account_id": "creditor-1",
                },
                "instruction_details": None,
            }
        }
        self.assertEqual(transfer.to_dict(), expected)

    def test_transfer_to_dict_with_sub_accounts(self):
        transfer = Transfer(
            amount="10.50",
            debtor_target_account_id="debtor-1",
            creditor_target_account_id="creditor-1",
            denomination="GBP",
            debtor_target_sub_account_id="debtor-sub-1",
            creditor_target_sub_account_id="creditor-sub-1",
            debtor_target_account_address="DEFAULT",
            creditor_target_account_address="DEFAULT",
        )
        expected = {
            "transfer": {
                "amount": "10.50",
                "denomination": "GBP",
                "debtor_target_account": {
                    "account_id": "debtor-1",
                },
                "creditor_target_account": {
                    "account_id": "creditor-1",
                },
                "instruction_details": None,
                "debtor_target_sub_account_id": "debtor-sub-1",
                "debtor_target_account_address": "DEFAULT",
                "creditor_target_sub_account_id": "creditor-sub-1",
                "creditor_target_account_address": "DEFAULT",
            }
        }
        self.assertEqual(transfer.to_dict(), expected)
