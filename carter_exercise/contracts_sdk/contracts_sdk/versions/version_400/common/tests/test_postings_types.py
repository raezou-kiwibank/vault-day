from unittest import TestCase
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from ..types import (
    AdjustmentAmount,
    AuthorisationAdjustment,
    Balance,
    BalanceCoordinate,
    
    CustomInstruction,
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    PostingInstructionEnrichment,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Phase,
    Posting,
    Release,
    Settlement,
    TransactionCode,
    Transfer,
    Tside,
)
from .....utils.exceptions import (
    StrongTypingError,
    InvalidSmartContractError,
)


from .....utils.types_utils import (
    ContractsLanguageDunderMixin,
)
from .....utils.feature_flags import (
    skip_if_not_enabled,
    
    ENRICH_POSTING_INSTRUCTIONS,
    POSTINGS_TARGET_ADDRESS,
    
    
)


class TestPostingTypes(TestCase):
    test_account_id = "test_account_id"
    

    

    # Posting

    def test_posting_repr_inherited_from_mixin(self):
        posting = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        self.assertTrue(issubclass(Posting, ContractsLanguageDunderMixin))
        self.assertIn("Posting", repr(posting))

    def test_posting_equality(self):
        posting = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        other_posting = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        self.assertEqual(posting, other_posting)
        other_posting_with_int_amount = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=10,
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        self.assertEqual(posting, other_posting_with_int_amount)

    def test_posting_unequal_denomination(self):
        posting = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        other_posting = Posting(
            credit=True,
            denomination="USD",  # different field
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        self.assertNotEqual(posting, other_posting)

    def test_posting_class_attributes(self):
        posting = Posting(
            credit=True,
            denomination="GBP",
            account_address="DEFAULT",
            account_id="1",
            amount=Decimal(10),
            asset="DEFAULT",
            phase=Phase.COMMITTED,
        )
        self.assertEqual(posting.credit, True)
        self.assertEqual(posting.denomination, "GBP")
        self.assertEqual(posting.account_address, "DEFAULT")
        self.assertEqual(posting.account_id, "1")
        self.assertEqual(posting.amount, Decimal(10))
        self.assertEqual(posting.asset, "DEFAULT")
        self.assertEqual(posting.phase, Phase.COMMITTED)

    def test_posting_class_attributes_invalid_phase(self):
        with self.assertRaises(StrongTypingError) as e:
            Posting(
                credit=True,
                denomination="GBP",
                account_address="DEFAULT",
                account_id="1",
                amount=Decimal(10),
                asset="DEFAULT",
                phase="not a phase",
            )
        self.assertEqual("'phase' must be set to a Phase value", str(e.exception))

    def test_posting_class_attributes_missing(self):
        with self.assertRaises(TypeError) as ex:
            Posting()

        self.assertIn(
            (
                "__init__() missing 6 required keyword-only arguments: 'credit', 'amount', "
                "'denomination', 'account_address', 'asset', and 'phase'"
            ),
            str(ex.exception),
        )

    def test_posting_class_attributes_empty(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Posting(
                credit=True,
                denomination="",
                account_address="",
                account_id="",
                amount=Decimal(10),
                asset="",
                phase=Phase.COMMITTED,
            )

        self.assertIn(
            (
                "Postings missing required argument(s): "
                "['denomination', 'account_address', 'asset', 'account_id']"
            ),
            str(ex.exception),
        )

    def test_posting_class_attributes_internal_account_processing_label_empty(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Posting(
                credit=True,
                denomination="GBP",
                account_address="DEFAULT",
                account_id="1",
                internal_account_processing_label="",
                amount=Decimal(10),
                asset="DEFAULT",
                phase=Phase.COMMITTED,
            )

        self.assertIn(
            "'Posting.internal_account_processing_label' must be a non-empty string",
            str(ex.exception),
        )

    def test_posting_class_attributes_internal_account_processing_label_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Posting(
                credit=True,
                denomination="GBP",
                account_address="DEFAULT",
                account_id="1",
                internal_account_processing_label=1,
                amount=Decimal(10),
                asset="DEFAULT",
                phase=Phase.COMMITTED,
            )

        self.assertIn(
            "'Posting.internal_account_processing_label' expected str if populated, got '1' of type int",
            str(ex.exception),
        )

    def test_posting_class_raises_error_if_missing_account_identifier(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Posting(
                credit=True,
                denomination="GBP",
                account_address="DEFAULT",
                amount=Decimal(10),
                asset="DEFAULT",
                phase=Phase.COMMITTED,
            )

        self.assertIn(
            "At least one of account_id and internal_account_processing_label must be provided",
            str(ex.exception),
        )

    def test_posting_class_attributes_skips_validation(self):
        # InvalidSmartContractError not raised
        Posting(
            credit=True,
            denomination="",
            account_address="",
            account_id="",
            amount=Decimal(10),
            asset="",
            phase=Phase.COMMITTED,
            _from_proto=True,
        )

    def test_posting_class_raises_with_negative_amount(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Posting(
                credit=True,
                denomination="GBP",
                account_address="DEFAULT",
                account_id="1",
                amount=Decimal(-10),
                asset="DEFAULT",
                phase=Phase.COMMITTED,
            )

        self.assertIn("Amount must be greater than 0, -10", str(ex.exception))

    

    # TransactionCode

    def test_transaction_code_repr(self):
        transaction_code = TransactionCode(
            domain="Blossom",
            family="Buttercup",
            subfamily="Bubbles",
        )
        expected = "TransactionCode(domain='Blossom', family='Buttercup', subfamily='Bubbles')"
        self.assertEqual(expected, repr(transaction_code))

    def test_transaction_code(self):
        transaction_code = TransactionCode(
            domain="Blossom",
            family="Buttercup",
            subfamily="Bubbles",
        )
        self.assertEqual("Blossom", transaction_code.domain)

    def test_transaction_code_equality(self):
        transaction_code = TransactionCode(
            domain="Blossom",
            family="Buttercup",
            subfamily="Bubbles",
        )
        other_transaction_code = TransactionCode(
            domain="Blossom",
            family="Buttercup",
            subfamily="Bubbles",
        )
        self.assertEqual(transaction_code, other_transaction_code)

    def test_transaction_code_unequal_domain(self):
        transaction_code = TransactionCode(
            domain="Blossom",
            family="Buttercup",
            subfamily="Bubbles",
        )
        other_transaction_code = TransactionCode(
            domain="Bunny",
            family="Buttercup",
            subfamily="Bubbles",
        )
        self.assertNotEqual(transaction_code, other_transaction_code)

    def test_transaction_code_raises_with_domain_not_populated(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            TransactionCode(
                domain="",
                family="Buttercup",
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.domain' must be a non-empty string",
        )

    def test_transaction_code_raises_with_domain_incorrect_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain=5,
                family="Buttercup",
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.domain' expected str, got '5' of type int",
        )

    def test_transaction_code_raises_with_domain_none(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain=None,
                family="Buttercup",
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.domain' expected str, got None",
        )

    def test_transaction_code_raises_with_family_not_populated(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            TransactionCode(
                domain="Blossom",
                family="",
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.family' must be a non-empty string",
        )

    def test_transaction_code_raises_with_family_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain="Blossom",
                family=5,
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.family' expected str, got '5' of type int",
        )

    def test_transaction_code_raises_with_family_none(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain="Blossom",
                family=None,
                subfamily="Bubbles",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.family' expected str, got None",
        )

    def test_transaction_code_raises_with_subfamily_not_populated(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            TransactionCode(
                domain="Blossom",
                family="Buttercup",
                subfamily="",
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.subfamily' must be a non-empty string",
        )

    def test_transaction_code_raises_with_subfamily_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain="Blossom",
                family="Buttercup",
                subfamily=5,
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.subfamily' expected str, got '5' of type int",
        )

    def test_transaction_code_raises_with_subfamily_none(self):
        with self.assertRaises(StrongTypingError) as ex:
            TransactionCode(
                domain="Blossom",
                family="Buttercup",
                subfamily=None,
            )
        self.assertEqual(
            str(ex.exception),
            "'TransactionCode.subfamily' expected str, got None",
        )

    def test_transaction_code_raises_with_domain_not_set(self):
        with self.assertRaises(TypeError):
            TransactionCode(
                family="Family",
                subfamily="Sub-Family",
            )

    def test_transaction_code_raises_with_family_not_set(self):
        with self.assertRaises(TypeError):
            TransactionCode(
                domain="Domain",
                subfamily="Sub-Family",
            )

    def test_transaction_code_raises_with_subfamily_not_set(self):
        with self.assertRaises(TypeError):
            TransactionCode(
                domain="Domain",
                family="Family",
            )

    # AdjustmentAmount

    def test_adjustment_amount_repr(self):
        amount = AdjustmentAmount(amount=-Decimal("10.57"))
        expected = "AdjustmentAmount(amount=Decimal('-10.57'), replacement_amount=None)"
        self.assertEqual(expected, repr(amount))

    def test_adjustment_amount_both_arguments_not_set(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            AdjustmentAmount()
        self.assertEqual(
            "Either amount or replacement amount argument must be set, not both.", str(ex.exception)
        )

    def test_adjustment_amount_both_arguments_set(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            AdjustmentAmount(amount=Decimal(1), replacement_amount=Decimal(2))
        self.assertEqual(
            "Either amount or replacement amount argument must be set, not both.", str(ex.exception)
        )

    def test_adjustment_amount_init(self):
        auth_amount = AdjustmentAmount(amount=Decimal(-10))
        self.assertEqual(auth_amount.amount, Decimal(-10))
        self.assertEqual(auth_amount.replacement_amount, None)
        auth_amount = AdjustmentAmount(replacement_amount=Decimal(1))
        self.assertEqual(auth_amount.amount, None)
        self.assertEqual(auth_amount.replacement_amount, Decimal(1))
        auth_amount_int = AdjustmentAmount(amount=-10)
        self.assertEqual(auth_amount_int.amount, Decimal(-10))
        self.assertEqual(auth_amount_int.replacement_amount, None)
        auth_amount_int = AdjustmentAmount(replacement_amount=1)
        self.assertEqual(auth_amount_int.amount, None)
        self.assertEqual(auth_amount_int.replacement_amount, Decimal(1))

    def test_adjustment_amount_equality(self):
        auth_amount = AdjustmentAmount(amount=Decimal(10))
        other_auth_amount = AdjustmentAmount(amount=Decimal(10))
        self.assertEqual(auth_amount, other_auth_amount)

    def test_adjustment_amount_unequal_amount(self):
        auth_amount = AdjustmentAmount(amount=Decimal(10))
        other_auth_amount = AdjustmentAmount(amount=Decimal(42))
        self.assertNotEqual(auth_amount, other_auth_amount)

    def test_adjustment_amount_skips_validation_with_from_proto(self):
        auth_amount = AdjustmentAmount(
            amount=Decimal(-10), replacement_amount=Decimal(1), _from_proto=True
        )
        self.assertEqual(auth_amount.amount, Decimal(-10))
        self.assertEqual(auth_amount.replacement_amount, Decimal(1))

    # PostingInstructions

    # OutboundAuthorisation

    def test_outbound_auth_repr_inherited_from_mixin(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(OutboundAuthorisation, ContractsLanguageDunderMixin))
        self.assertIn("OutboundAuthorisation", repr(pi))

    def test_outbound_auth_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            OutboundAuthorisation(amount=Decimal(10))
        self.assertEqual(
            "Authorisation.__init__() missing 4 required keyword-only arguments: "
            "'client_transaction_id', 'denomination', 'target_account_id', and "
            "'internal_account_id'",
            str(ex.exception),
        )

    def test_outbound_auth_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(True, pi.advice)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_outbound_auth_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "account_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "account_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_outbound_auth_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            internal_account_processing_label="2",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_auth_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            target_account_address="address",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_auth_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            asset="asset",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("asset", pi.asset)

    

    def test_outbound_auth_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_outbound_auth_unequal_instruction_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test42"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_outbound_auth_default_attributes_no_output_attrs(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(False, pi.advice)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertEqual({}, pi.batch_details)
        # Private attribute used in balances calculation
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001
        self.assertIsNone(pi.localised_booking_datetime)  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_outbound_auth_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_outbound_auth_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_auth_default_attributes_no_output_attrs_with_target_account_address(
        self,
    ):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_auth_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.asset)

    def test_outbound_auth_posting_instruction_skip_type_checking(self):
        pi = OutboundAuthorisation(
            client_transaction_id=1,
            target_account_id=1,
            internal_account_id=1,
            amount=1,
            denomination=1,
            advice=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.client_transaction_id)
        self.assertEqual(1, pi.target_account_id)
        self.assertEqual(1, pi.internal_account_id)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.denomination)
        self.assertEqual(1, pi.advice)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_outbound_auth_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            OutboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                instruction_details=123,
            )

        self.assertIn(
            "'OutboundAuthorisation.instruction_details' expected Dict[str, str] if populated, "
            "got '123' of type int",
            str(ex.exception),
        )

    def test_outbound_auth_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            OutboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                transaction_code=123,
            )

        self.assertIn(
            "'OutboundAuthorisation.transaction_code' expected TransactionCode if populated, got "
            "'123' of type int",
            str(ex.exception),
        )

    
    def test_outbound_auth_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_outbound_auth_instruction_balances_errors_if_committed_postings_not_provided(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )
        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The OutboundAuthorisation posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_outbound_auth_instruction_balances_errors_if_tside_not_provided(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_OUT,
                    amount=Decimal(10),
                    denomination="GBP",
                ),
            ],
        )
        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "A tside must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_outbound_auth_instruction_balances_for_both_tsides(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

    def test_outbound_auth_instruction_balances_for_both_tsides_in_balances_args(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
        )

        balances = pi.balances(tside=Tside.ASSET)
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
        )

        balances = pi.balances(tside=Tside.LIABILITY)
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

    def test_balances_method_filters_on_own_account_id(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id="filter-out-this-account-pls",
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(1984),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_balances_method_filters_on_account_id_in_balances_arg(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id="filter-out-this-account-pls",
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(1984),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances(account_id=self.test_account_id)
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_balances_method_filters_account_id_in_balances_arg_not_own_account_id(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id="filter-out-this-account-pls",
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(1984),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id="filter-out-this-account-pls",
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances(account_id=self.test_account_id)
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_balances_method_returns_zero_default_dict_for_non_existing_balance_key(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            )
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            Balance(
                credit=Decimal(0),
                debit=Decimal(0),
                net=Decimal(0),
            ),
            balances[
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                )
            ],
        )
        self.assertEqual(
            Balance(
                credit=Decimal(0),
                debit=Decimal(10),
                net=Decimal(10),
            ),
            balances[
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                )
            ],
        )

    def test_outbound_authorisation_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            OutboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Authorisation.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_outbound_authorisation_with_value_datetime_set_afterwards_raises_error(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'OutboundAuthorisation' object has no setter",
            str(ex.exception),
        )

    def test_outbound_authorisation_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            OutboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Authorisation.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_outbound_authorisation_with_booking_datetime_set_afterwards_raises_error(self):
        pi = OutboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'OutboundAuthorisation' object has no setter",
            str(ex.exception),
        )

    # InboundAuthorisation

    def test_inbound_auth_repr_inherited_from_mixin(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        self.assertTrue(issubclass(InboundAuthorisation, ContractsLanguageDunderMixin))
        self.assertIn("InboundAuthorisation", repr(pi))

    def test_inbound_auth_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            InboundAuthorisation(amount=Decimal(10))
        self.assertEqual(
            "Authorisation.__init__() missing 4 required keyword-only arguments: "
            "'client_transaction_id', 'denomination', 'target_account_id', and "
            "'internal_account_id'",
            str(ex.exception),
        )

    def test_inbound_auth_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(True, pi.advice)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_inbound_auth_all_attribute_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_inbound_auth_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            internal_account_processing_label="2",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_auth_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            target_account_address="address",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_auth_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            asset="asset",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("asset", pi.asset)

    

    def test_inbound_auth_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_inbound_auth_unequal_transaction_code(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="AAA", family="B", subfamily="C")
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_inbound_auth_default_attributes_no_output_attrs(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(False, pi.advice)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertEqual({}, pi.batch_details)
        # Private attribute - used for balances calc.
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001
        self.assertIsNone(pi.localised_booking_datetime)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_inbound_auth_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_inbound_auth_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_auth_default_attributes_no_output_attrs_with_target_account_address(
        self,
    ):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_auth_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.asset)

    def test_inbound_auth_posting_instruction_skip_type_checking(self):
        pi = InboundAuthorisation(
            client_transaction_id=1,
            target_account_id=1,
            internal_account_id=1,
            amount=1,
            denomination=1,
            advice=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.client_transaction_id)
        self.assertEqual(1, pi.target_account_id)
        self.assertEqual(1, pi.internal_account_id)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.denomination)
        self.assertEqual(1, pi.advice)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_inbound_auth_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            InboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                instruction_details=123,
            )

        self.assertIn(
            "'InboundAuthorisation.instruction_details' expected Dict[str, str] if populated, got "
            "'123' of type int",
            str(ex.exception),
        )

    def test_inbound_auth_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            InboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                transaction_code=123,
            )

        self.assertIn(
            "'InboundAuthorisation.transaction_code' expected TransactionCode if populated, got "
            "'123' of type int",
            str(ex.exception),
        )

    
    def test_inbound_auth_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_inbound_auth_instruction_balances_errors_if_committed_postings_not_provided(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )
        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The InboundAuthorisation posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_inbound_auth_instruction_balances_for_both_tsides(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertDictEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_inbound_authorisation_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            InboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Authorisation.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_inbound_authorisation_with_value_datetime_set_afterwards_raises_error(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'InboundAuthorisation' object has no setter",
            str(ex.exception),
        )

    def test_inbound_authorisation_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            InboundAuthorisation(
                client_transaction_id="xx",
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Authorisation.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_inbound_authorisation_with_booking_datetime_set_afterwards_raises_error(self):
        pi = InboundAuthorisation(
            client_transaction_id="xx",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'InboundAuthorisation' object has no setter",
            str(ex.exception),
        )

    # AuthorisationAdjustment

    def test_auth_adjust_repr_inherited_from_mixin(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(AuthorisationAdjustment, ContractsLanguageDunderMixin))
        self.assertIn("AuthorisationAdjustment", repr(pi))

    def test_auth_adjust_equality(self):
        adj = AuthorisationAdjustment(
            client_transaction_id="42", adjustment_amount=AdjustmentAmount(amount=Decimal(10))
        )
        other_adj = AuthorisationAdjustment(
            client_transaction_id="42", adjustment_amount=AdjustmentAmount(amount=Decimal(10))
        )
        self.assertEqual(adj, other_adj)
        other_adj_with_int_amount = AuthorisationAdjustment(
            client_transaction_id="42", adjustment_amount=AdjustmentAmount(amount=10)
        )
        self.assertEqual(adj, other_adj_with_int_amount)

    def test_auth_adjust_unequal_client_transaction_id(self):
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        adj = AuthorisationAdjustment(
            client_transaction_id="42", adjustment_amount=adjustment_amount
        )
        other_adj = AuthorisationAdjustment(
            client_transaction_id="24", adjustment_amount=adjustment_amount
        )
        self.assertNotEqual(adj, other_adj)

    def test_auth_adjust_posting_instruction_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            AuthorisationAdjustment()
        self.assertEqual(
            "AuthorisationAdjustment.__init__() missing 2 required keyword-only arguments: "
            "'client_transaction_id' and 'adjustment_amount'",
            str(ex.exception),
        )

    def test_auth_adjust_posting_instruction_raises_with_adjustment_amount_not_populated(self):
        with self.assertRaises(StrongTypingError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=None,
                advice=True,
                override_all_restrictions=True,
            )
        self.assertEqual(
            "AuthorisationAdjustment 'adjustment_amount' must be populated",
            str(ex.exception),
        )

    def test_auth_adjust_posting_instruction_raises_with_adjustment_amount_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=234,
                advice=True,
                override_all_restrictions=True,
            )
        self.assertEqual(
            "'AuthorisationAdjustment.adjustment_amount' expected AdjustmentAmount, got '234' of "
            "type int",
            str(ex.exception),
        )

    def test_auth_adjust_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=adjustment_amount,
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            target_account_id=self.test_account_id,
            internal_account_id="1",
            authorised_amount=Decimal(110),
            delta_amount=Decimal(10),
            denomination="GBP",
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertTrue(pi.advice)
        self.assertEqual(adjustment_amount, pi.adjustment_amount)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(110), pi.authorised_amount)
        self.assertEqual(Decimal(10), pi.delta_amount)
        self.assertEqual("GBP", pi.denomination)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_auth_adjust_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=adjustment_amount,
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_auth_adjust_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=adjustment_amount,
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            internal_account_processing_label="2",
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_auth_adjust_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=adjustment_amount,
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            target_account_address="address",
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_auth_adjust_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        adjustment_amount = AdjustmentAmount(amount=Decimal(10))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=adjustment_amount,
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            asset="asset",
        )
        self.assertEqual("asset", pi.asset)

    

    def test_auth_adjust_default_attributes_no_output_attrs(self):
        adjustment_amount = AdjustmentAmount(replacement_amount=Decimal(50))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx", adjustment_amount=adjustment_amount
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertFalse(pi.advice)
        self.assertEqual(adjustment_amount, pi.adjustment_amount)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001
        self.assertEqual({}, pi.batch_details)
        # Release specific output attributes
        self.assertIsNone(pi.authorised_amount)
        self.assertIsNone(pi.delta_amount)
        self.assertIsNone(pi.denomination)
        self.assertIsNone(pi.target_account_id)
        self.assertIsNone(pi.internal_account_id)
        self.assertIsNone(pi.localised_booking_datetime)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_auth_adjust_default_attributes_no_output_attrs_with_enrichment_details(self):
        adjustment_amount = AdjustmentAmount(replacement_amount=Decimal(50))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx", adjustment_amount=adjustment_amount
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_auth_adjust_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        adjustment_amount = AdjustmentAmount(replacement_amount=Decimal(50))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx", adjustment_amount=adjustment_amount
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_auth_adjust_default_attributes_no_output_attrs_with_target_account_adress(
        self,
    ):
        adjustment_amount = AdjustmentAmount(replacement_amount=Decimal(50))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx", adjustment_amount=adjustment_amount
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_auth_adjust_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        adjustment_amount = AdjustmentAmount(replacement_amount=Decimal(50))
        pi = AuthorisationAdjustment(
            client_transaction_id="xx", adjustment_amount=adjustment_amount
        )
        self.assertIsNone(pi.asset)

    def test_auth_adjust_posting_instruction_skip_type_checking(self):
        pi = AuthorisationAdjustment(
            client_transaction_id=1,
            adjustment_amount=1,
            advice=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.client_transaction_id)
        self.assertEqual(1, pi.advice)
        self.assertEqual(1, pi.adjustment_amount)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_auth_adjust_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
                advice=True,
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details=123,
            )

        self.assertIn(
            "'AuthorisationAdjustment.instruction_details' expected Dict[str, str] if populated, "
            "got '123' of type int",
            str(ex.exception),
        )

    def test_auth_adjust_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
                advice=True,
                override_all_restrictions=True,
                transaction_code=123,
            )

        self.assertIn(
            "'AuthorisationAdjustment.transaction_code' expected TransactionCode if populated, "
            "got '123' of type int",
            str(ex.exception),
        )

    
    def test_auth_adjust_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_auth_adjust_instruction_balances_errors_if_committed_postings_not_provided(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The AuthorisationAdjustment posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_auth_adjust_instruction_balances_for_both_tsides(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_auth_adjust_instruction_zero_amount(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
        )
        # Amount is zero not None
        self.assertEqual(pi.adjustment_amount.amount, Decimal("0"))
        self.assertIsNone(pi.adjustment_amount.replacement_amount)
        self.assertIsNone(pi.authorised_amount)
        self.assertIsNone(pi.delta_amount)

    def test_auth_adjust_instruction_zero_replacement_amount(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(replacement_amount=Decimal(0)),
        )
        # Replacement amount is zero not None
        self.assertIsNone(pi.adjustment_amount.amount)
        self.assertEqual(pi.adjustment_amount.replacement_amount, Decimal("0"))
        self.assertIsNone(pi.authorised_amount)
        self.assertIsNone(pi.delta_amount)

    def test_auth_adjust_instruction_zero_authorised_amount(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
        )
        pi._set_output_attributes(  # noqa: SLF001
            authorised_amount=Decimal("0"),
        )
        # Authorised amount is zero not None
        self.assertEqual(pi.adjustment_amount.amount, Decimal("0"))
        self.assertIsNone(pi.adjustment_amount.replacement_amount)
        self.assertEqual(pi.authorised_amount, Decimal("0"))
        self.assertIsNone(pi.delta_amount)

    def test_auth_adjust_instruction_zero_delta_amount(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
        )
        pi._set_output_attributes(  # noqa: SLF001
            delta_amount=Decimal("0"),
        )
        # Delta amount is zero not None
        self.assertEqual(pi.adjustment_amount.amount, Decimal("0"))
        self.assertIsNone(pi.adjustment_amount.replacement_amount)
        self.assertIsNone(pi.authorised_amount)
        self.assertEqual(pi.delta_amount, Decimal("0"))

    def test_auth_adjust_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "AuthorisationAdjustment.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_auth_adjust_with_value_datetime_set_afterwards_raises_error(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'AuthorisationAdjustment' object has no setter",
            str(ex.exception),
        )

    def test_auth_adjust_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            AuthorisationAdjustment(
                client_transaction_id="xx",
                adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "AuthorisationAdjustment.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_auth_adjust_with_booking_datetime_set_afterwards_raises_error(self):
        pi = AuthorisationAdjustment(
            client_transaction_id="xx",
            adjustment_amount=AdjustmentAmount(amount=Decimal(0)),
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'AuthorisationAdjustment' object has no setter",
            str(ex.exception),
        )

    # Settlement

    def test_settlement_repr_inherited_from_mixin(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(Settlement, ContractsLanguageDunderMixin))
        self.assertIn("Settlement", repr(pi))

    def test_settlement_posting_instruction_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            Settlement()
        self.assertEqual(
            "Settlement.__init__() missing 1 required keyword-only argument: "
            "'client_transaction_id'",
            str(ex.exception),
        )

    def test_settlement_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            target_account_id=self.test_account_id,
            internal_account_id="1",
            denomination="GBP",
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertTrue(pi.final)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_settlement_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_settlement_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            internal_account_processing_label="2",
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_settlement_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            target_account_address="address",
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_settlement_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            asset="asset",
        )
        self.assertEqual("asset", pi.asset)

    

    def test_settlement_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_settlement_unequal_transaction_code(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="AAA", family="B", subfamily="C")
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_settlement_default_attributes_no_output_attrs(self):
        pi = Settlement(client_transaction_id="xx")
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertFalse(pi.final)
        self.assertIsNone(pi.amount)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001
        self.assertEqual({}, pi.batch_details)
        # Release specific output attributes
        self.assertIsNone(pi.denomination)
        self.assertIsNone(pi.target_account_id)
        self.assertIsNone(pi.internal_account_id)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_settlement_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi = Settlement(client_transaction_id="xx")
        self.assertEqual({}, pi.enrichment_details)

    def test_settlement_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = Settlement(client_transaction_id="xx")
        self.assertIsNone(pi.internal_account_processing_label)

    def test_settlement_posting_instruction_skip_type_checking(self):
        pi = Settlement(
            client_transaction_id=1,
            amount=1,
            final=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.client_transaction_id)
        self.assertEqual(1, pi.final)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_settlement_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Settlement(
                client_transaction_id="xx",
                final=True,
                amount=Decimal(10),
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details=123,
            )

        self.assertIn(
            "'Settlement.instruction_details' expected Dict[str, str] if populated, got '123' of "
            "type int",
            str(ex.exception),
        )

    def test_settlement_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Settlement(
                client_transaction_id="xx",
                final=True,
                amount=Decimal(10),
                override_all_restrictions=True,
                transaction_code=123,
            )

        self.assertIn(
            "'Settlement.transaction_code' expected TransactionCode if populated, got '123' of "
            "type int",
            str(ex.exception),
        )

    
    def test_settlement_posting_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_settlement_posting_instruction_balances_errors_if_committed_postings_not_provided(
        self,
    ):
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )  # noqa: SLF001

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The Settlement posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_settlement_posting_instruction_balances_for_both_tsides(self):
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

    def test_settlement_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Settlement(
                client_transaction_id="xx",
                final=True,
                amount=Decimal(10),
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Settlement.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_settlement_with_value_datetime_set_afterwards_raises_error(self):
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'Settlement' object has no setter",
            str(ex.exception),
        )

    def test_settlement_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Settlement(
                client_transaction_id="xx",
                final=True,
                amount=Decimal(10),
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Settlement.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_settlement_with_booking_datetime_set_afterwards_raises_error(self):
        pi = Settlement(
            client_transaction_id="xx",
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'Settlement' object has no setter",
            str(ex.exception),
        )

    # Release

    def test_release_repr_inherited_from_mixin(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(Release, ContractsLanguageDunderMixin))
        self.assertIn("Release", repr(pi))

    def test_release_posting_instruction_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            Release()
        self.assertEqual(
            "Release.__init__() missing 1 required keyword-only argument: 'client_transaction_id'",
            str(ex.exception),
        )

    def test_release_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_release_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_release_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            internal_account_processing_label="2",
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_release_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            target_account_address="address",
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_release_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            asset="asset",
        )
        self.assertEqual("asset", pi.asset)

    

    def test_release_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_release_unequal_transaction_code(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="AAA", family="B", subfamily="C")
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_release_default_attributes_no_output_attrs(self):
        pi = Release(
            client_transaction_id="xx",
        )
        # Direct attributes
        self.assertEqual("xx", pi.client_transaction_id)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001
        self.assertEqual({}, pi.batch_details)
        # Release specific output attributes
        self.assertIsNone(pi.amount)
        self.assertIsNone(pi.denomination)
        self.assertIsNone(pi.target_account_id)
        self.assertIsNone(pi.internal_account_id)
        self.assertIsNone(pi.localised_booking_datetime)

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_release_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi = Release(
            client_transaction_id="xx",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_release_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = Release(
            client_transaction_id="xx",
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_release_default_attributes_no_output_attrs_with_target_account_address(
        self,
    ):
        pi = Release(
            client_transaction_id="xx",
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_release_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        pi = Release(
            client_transaction_id="xx",
        )
        self.assertIsNone(pi.asset)

    def test_release_posting_instruction_skip_type_checking(self):
        pi = Release(
            client_transaction_id=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.client_transaction_id)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_release_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Release(
                client_transaction_id="xx",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details=123,
            )

        self.assertIn(
            "'Release.instruction_details' expected Dict[str, str] if populated, got '123' of "
            "type int",
            str(ex.exception),
        )

    def test_release_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Release(
                client_transaction_id="xx", override_all_restrictions=True, transaction_code=123
            )

        self.assertIn(
            "'Release.transaction_code' expected TransactionCode if populated, got '123' of type "
            "int",
            str(ex.exception),
        )

    
    def test_release_posting_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_release_posting_instruction_balances_errors_if_committed_postings_not_provided(self):
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The Release posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_release_posting_instruction_balances_for_both_tsides(self):
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

    def test_release_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Release(
                client_transaction_id="xx",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Release.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_release_with_value_datetime_set_afterwards_raises_error(self):
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'Release' object has no setter",
            str(ex.exception),
        )

    def test_release_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Release(
                client_transaction_id="xx",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Release.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_release_with_booking_datetime_set_afterwards_raises_error(self):
        pi = Release(
            client_transaction_id="xx",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'Release' object has no setter",
            str(ex.exception),
        )

    # CustomInstruction

    def test_custom_instruction_repr_inherited_from_mixin(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = CustomInstruction(
            postings=pi_committed_postings,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertTrue(issubclass(CustomInstruction, ContractsLanguageDunderMixin))
        self.assertIn("CustomInstruction", repr(pi))

    def test_custom_instruction_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            CustomInstruction()
        self.assertEqual(
            "CustomInstruction.__init__() missing 1 required keyword-only argument: 'postings'",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_wrong_value_datetime_type(self):
        value_datetime = "2002"
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            "Expected datetime if populated, got '2002' of type str",
            str(ex.exception),
        )

    def test_custom_instruction_with_value_datetime_raises_with_non_utc_timezone(self):
        value_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("US/Pacific"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            "'value_datetime' of CustomInstruction must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_custom_instruction_with_value_datetime_raises_with_non_zoneinfo_timezone(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "'value_datetime' of CustomInstruction must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_wrong_booking_datetime_type(self):
        booking_datetime = "2002"
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                booking_datetime=booking_datetime,
            )
        self.assertEqual(
            "Expected datetime if populated, got '2002' of type str",
            str(ex.exception),
        )

    def test_custom_instruction_with_booking_datetime_raises_with_non_utc_timezone(self):
        booking_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("US/Pacific"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                booking_datetime=booking_datetime,
            )
        self.assertEqual(
            "'booking_datetime' of CustomInstruction must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_custom_instruction_with_booking_datetime_raises_with_non_zoneinfo_timezone(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(
                postings=pi_committed_postings,
                override_all_restrictions=True,
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "'booking_datetime' of CustomInstruction must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_custom_instruction_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = CustomInstruction(
            postings=pi_committed_postings,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual(pi_committed_postings[0], pi.postings[0])
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_custom_instruction_all_attributes_sets_enrichment_details(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = CustomInstruction(
            postings=pi_committed_postings,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_custom_instruction_all_attributes_with_value_datetime_and_booking_datetime(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        value_datetime = datetime(2002, 2, 3, tzinfo=ZoneInfo("UTC"))
        booking_datetime = datetime(2002, 2, 4, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = CustomInstruction(
            postings=pi_committed_postings,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
            value_datetime=value_datetime,
            booking_datetime=booking_datetime,
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
        )
        self.assertEqual(value_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(booking_datetime, pi.booking_datetime)

    def test_custom_instruction_default_attributes_no_output_attrs(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        pi = CustomInstruction(postings=pi_committed_postings)
        # Direct attributes
        self.assertEqual(pi_committed_postings[0], pi.postings[0])
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi.localised_booking_datetime)
        self.assertEqual({}, pi.batch_details)
        # This is set to the postings for the CustomInstructions
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_custom_instruction_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        pi = CustomInstruction(postings=pi_committed_postings)
        self.assertEqual({}, pi.enrichment_details)

    def test_custom_instruction_default_attributes_no_output_attrs_with_value_and_booking_datetime(
        self,
    ):
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        pi = CustomInstruction(postings=pi_committed_postings)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.value_datetime)

    def test_custom_instruction_skip_type_checking(self):
        pi = CustomInstruction(
            postings=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.postings)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_custom_instruction_skips_validation(self):
        # This raises no error with invalid attributes when _from_proto=True.
        custom_instruction = CustomInstruction(postings=1, _from_proto=True)
        self.assertEqual(1, custom_instruction.postings)

    def test_custom_instruction_raises_with_postings_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(postings="Posting")

        self.assertIn(
            "Expected list of Posting objects for 'CustomInstruction.postings', got 'Posting'",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_postings_not_provided(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(postings=None)

        self.assertIn(
            "'CustomInstruction.postings' must be a non empty list, got None",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_empty_postings(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            CustomInstruction(postings=[])

        self.assertIn(
            "'CustomInstruction.postings' must be a non empty list, got []",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_postings_invalid_element_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(postings=[1])

        self.assertIn(
            "'CustomInstruction.postings[0]' expected Posting, got '1'",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_postings_element_being_none(self):
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(postings=[None])

        self.assertIn(
            "'CustomInstruction.postings[0]' expected Posting, got None",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_invalid_transaction_code(self):
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(
                postings=[
                    Posting(
                        account_id=self.test_account_id,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=False,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(10),
                        denomination="GBP",
                    )
                ],
                transaction_code=123,
            )

        self.assertIn(
            "'CustomInstruction.transaction_code' expected TransactionCode if populated, got "
            "'123' of type int",
            str(ex.exception),
        )

    def test_custom_instruction_raises_with_invalid_instruction_details(self):
        with self.assertRaises(StrongTypingError) as ex:
            CustomInstruction(
                postings=[
                    Posting(
                        account_id=self.test_account_id,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=False,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(10),
                        denomination="GBP",
                    )
                ],
                instruction_details=123,
            )

        self.assertIn(
            "'CustomInstruction.instruction_details' expected Dict[str, str] if populated, got "
            "'123' of type int",
            str(ex.exception),
        )

    
    def test_custom_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = CustomInstruction(
            postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_OUT,
                    amount=Decimal(10),
                    denomination="GBP",
                ),
            ],
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_custom_instruction_default_balances_returned_if_committed_postings_not_provided(self):
        pi = CustomInstruction(
            postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_OUT,
                    amount=Decimal(10),
                    denomination="GBP",
                ),
            ],
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id, tside=Tside.ASSET
        )
        pi._committed_postings = []  # noqa: SLF001

        balances = pi.balances()
        self.assertEqual(
            {},
            balances,
        )

    def test_custom_instruction_balances_for_both_tsides(self):
        pi = CustomInstruction(
            postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.PENDING_IN,
                    amount=Decimal(10),
                    denomination="GBP",
                ),
            ],
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_custom_instruction_aggregated_balances(self):
        pi = CustomInstruction(
            postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.PENDING_IN,
                    amount=Decimal(10),
                    denomination="GBP",
                ),
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.PENDING_IN,
                    amount=Decimal(15),
                    denomination="GBP",
                ),
            ],
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                ): Balance(
                    credit=Decimal(25),
                    debit=Decimal(0),
                    net=Decimal(-25),
                ),
            },
            balances,
        )

    

    # InboundHardSettlement

    def test_inbound_settle_repr_inherited_from_mixin(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(InboundHardSettlement, ContractsLanguageDunderMixin))
        self.assertIn("InboundHardSettlement", repr(pi))

    def test_inbound_settle_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            InboundHardSettlement()
        self.assertEqual(
            "HardSettlement.__init__() missing 4 required keyword-only arguments: 'amount', "
            "'denomination', 'target_account_id', and 'internal_account_id'",
            str(ex.exception),
        )

    def test_inbound_settle_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(True, pi.advice)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_inbound_settle_output_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_inbound_settle_output_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            internal_account_processing_label="2",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_settle_output_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            target_account_address="address",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_settle_output_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            asset="asset",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("asset", pi.asset)

    

    def test_inbound_settle_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_inbound_settle_unequal_transaction(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="AAA", family="B", subfamily="C")
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_inbound_settle_default_attributes_no_output_attrs(self):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(False, pi.advice)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi.localised_booking_datetime)
        self.assertEqual({}, pi.batch_details)
        # Private attribute used in balances calculation
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_inbound_settle_default_attributes_no_output_attrs_with_enrichment_details(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_inbound_settle_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_settle_default_attributes_no_output_attrs_with_target_account_address(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_inbound_settle_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.asset)

    def test_inbound_settle_posting_instruction_skip_type_checking(self):
        pi = InboundHardSettlement(
            target_account_id=1,
            internal_account_id=1,
            amount=1,
            denomination=1,
            advice=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.target_account_id)
        self.assertEqual(1, pi.internal_account_id)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.denomination)
        self.assertEqual(1, pi.advice)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    
    def test_inbound_settle_posting_instruction_balances_errors_if_own_account_id_not_provided(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_inbound_settle_posting_instruction_balances_errors_if_committed_postings_not_provided(
        self,
    ):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The InboundHardSettlement posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_inbound_settle_posting_instruction_balances_for_both_tsides(self):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
            committed_postings=committed_postings,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(10),
                    debit=Decimal(0),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

    def test_inbound_settle_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            InboundHardSettlement(
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                advice=True,
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "HardSettlement.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_inbound_settle_with_value_datetime_set_afterwards_raises_error(self):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'InboundHardSettlement' object has no setter",
            str(ex.exception),
        )

    def test_inbound_settle_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            InboundHardSettlement(
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                advice=True,
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "HardSettlement.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_inbound_settle_with_booking_datetime_set_afterwards_raises_error(self):
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'InboundHardSettlement' object has no setter",
            str(ex.exception),
        )

    # OutboundHardSettlement

    def test_outbound_settle_repr_inherited_from_mixin(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(OutboundHardSettlement, ContractsLanguageDunderMixin))
        self.assertIn("OutboundHardSettlement", repr(pi))

    def test_outbound_settle_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            OutboundHardSettlement()
        self.assertEqual(
            "HardSettlement.__init__() missing 4 required keyword-only arguments: 'amount', "
            "'denomination', 'target_account_id', and 'internal_account_id'",
            str(ex.exception),
        )

    def test_outbound_settle_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(True, pi.advice)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_outbound_settle_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    def test_outbound_settle_all_attributes_sets_internal_account_processing_label(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            internal_account_processing_label="2",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("2", pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_settle_all_attributes_sets_target_account_address(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            target_account_address="address",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("address", pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_settle_all_attributes_sets_asset(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            asset="asset",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        self.assertEqual("asset", pi.asset)

    

    def test_outbound_settle_default_attributes_no_output_attrs(self):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.target_account_id)
        self.assertEqual("1", pi.internal_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(False, pi.advice)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertEqual({}, pi.batch_details)
        self.assertIsNone(pi.localised_booking_datetime)
        # Private attribute used in balances calculation
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_outbound_settle_default_attributes_no_output_attrs_with_enrichment_details(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_outbound_settle_default_attributes_no_output_attrs_with_internal_account_processing_label(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.internal_account_processing_label)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_settle_default_attributes_no_output_attrs_with_target_account_address(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.target_account_address)

    @skip_if_not_enabled(POSTINGS_TARGET_ADDRESS)
    def test_outbound_settle_default_attributes_no_output_attrs_with_asset(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertIsNone(pi.asset)

    def test_outbound_settle_posting_instruction_skip_type_checking(self):
        pi = OutboundHardSettlement(
            target_account_id=1,
            internal_account_id=1,
            amount=1,
            denomination=1,
            advice=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.target_account_id)
        self.assertEqual(1, pi.internal_account_id)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.denomination)
        self.assertEqual(1, pi.advice)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    
    def test_outbound_settle_posting_instruction_balances_errors_if_own_account_id_not_provided(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_outbound_settle_posting_instruction_balances_errors_if_committed_postings_not_provided(
        self,
    ):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The OutboundHardSettlement posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_outbound_settle_posting_instruction_balances_for_both_tsides(self):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_outbound_settle_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            OutboundHardSettlement(
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                advice=True,
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "HardSettlement.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_outbound_settle_with_value_datetime_set_afterwards_raises_error(self):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'OutboundHardSettlement' object has no setter",
            str(ex.exception),
        )

    def test_outbound_settle_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            OutboundHardSettlement(
                target_account_id=self.test_account_id,
                internal_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                advice=True,
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "HardSettlement.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_outbound_settle_with_booking_datetime_set_afterwards_raises_error(self):
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            advice=True,
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'OutboundHardSettlement' object has no setter",
            str(ex.exception),
        )

    # Transfer

    def test_transfer_repr_inherited_from_mixin(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertTrue(issubclass(Transfer, ContractsLanguageDunderMixin))
        self.assertIn("Transfer", repr(pi))

    def test_transfer_raises_with_missing_attributes(self):
        with self.assertRaises(TypeError) as ex:
            Transfer()
        self.assertEqual(
            "Transfer.__init__() missing 4 required keyword-only arguments: 'amount', "
            "'denomination', 'debtor_target_account_id', and 'creditor_target_account_id'",
            str(ex.exception),
        )

    def test_transfer_all_attributes(self):
        pi_datetime = datetime(2002, 2, 2, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=pi_datetime,
            value_datetime=pi_datetime,
            booking_datetime=pi_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_instruction_id",
            batch_details={"THOUGHT": "MACHINE"},
            client_id="TEST_CLIENT_ID",
            localised_booking_datetime=pi_datetime,
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.debtor_target_account_id)
        self.assertEqual("1", pi.creditor_target_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual(10, pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(True, pi.override_all_restrictions)
        self.assertEqual(transaction_code, pi.transaction_code)
        self.assertEqual("test", pi.instruction_details["testy"])
        # Indirect attributes
        self.assertEqual(pi_datetime, pi.value_datetime)
        self.assertEqual(pi_datetime, pi.insertion_datetime)
        self.assertEqual(pi_datetime, pi.booking_datetime)
        self.assertEqual("instruction_id", pi.id)
        self.assertEqual("batch_id", pi.batch_id)
        self.assertEqual("CoreContracts_instruction_id", pi.unique_client_transaction_id)
        self.assertEqual("client_batch_id", pi.client_batch_id)
        self.assertEqual("TEST_CLIENT_ID", pi.client_id)
        self.assertEqual("MACHINE", pi.batch_details["THOUGHT"])
        self.assertEqual(pi_datetime, pi.localised_booking_datetime)
        # Private attributes (to be used in balances calculation)
        self.assertEqual(pi_committed_postings[0], pi._committed_postings[0])  # noqa: SLF001

    

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_transfer_all_attributes_sets_enrichment_details(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pi._set_output_attributes(  # noqa: SLF001
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, pi.enrichment_details)

    

    def test_transfer_equality(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertEqual(pi, other_pi)

    def test_transfer_unequal_transaction_code(self):
        transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
        other_transaction_code = TransactionCode(domain="AAA", family="B", subfamily="C")
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=transaction_code,
            instruction_details={"testy": "test"},
        )
        other_pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=other_transaction_code,
            instruction_details={"testy": "test"},
        )

        self.assertNotEqual(pi, other_pi)

    def test_transfer_default_attributes_no_output_attrs(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # Direct attributes
        self.assertEqual(self.test_account_id, pi.debtor_target_account_id)
        self.assertEqual("1", pi.creditor_target_account_id)
        self.assertEqual(Decimal(10), pi.amount)
        self.assertEqual("GBP", pi.denomination)
        self.assertEqual(False, pi.override_all_restrictions)
        self.assertIsNone(pi.transaction_code)
        self.assertEqual({}, pi.instruction_details)
        # Indirect attributes
        self.assertIsNone(pi.insertion_datetime)
        self.assertIsNone(pi.id)
        self.assertIsNone(pi.value_datetime)
        self.assertIsNone(pi.booking_datetime)
        self.assertIsNone(pi.batch_id)
        self.assertIsNone(pi.unique_client_transaction_id)
        self.assertIsNone(pi.client_batch_id)
        self.assertIsNone(pi.client_id)
        self.assertIsNone(pi.localised_booking_datetime)
        self.assertEqual({}, pi.batch_details)
        # Private attribute used in balances calculation
        self.assertIsNone(pi._committed_postings)  # noqa: SLF001

    
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_transfer_default_attributes_no_output_attrs_with_enrichment_details(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        self.assertEqual({}, pi.enrichment_details)

    def test_transfer_posting_instruction_skip_type_checking(self):
        pi = Transfer(
            debtor_target_account_id=1,
            creditor_target_account_id=1,
            amount=1,
            denomination=1,
            transaction_code=1,
            instruction_details=1,
            override_all_restrictions=1,
            _from_proto=True,
        )
        # Direct attributes
        self.assertEqual(1, pi.debtor_target_account_id)
        self.assertEqual(1, pi.creditor_target_account_id)
        self.assertEqual(1, pi.amount)
        self.assertEqual(1, pi.denomination)
        self.assertEqual(1, pi.override_all_restrictions)
        self.assertEqual(1, pi.transaction_code)
        self.assertEqual(1, pi.instruction_details)

    def test_transfer_posting_instruction_raises_with_invalid_instruction_details_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Transfer(
                debtor_target_account_id=self.test_account_id,
                creditor_target_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details=123,
            )

        self.assertIn(
            "'Transfer.instruction_details' expected Dict[str, str] if populated, got '123' of "
            "type int",
            str(ex.exception),
        )

    def test_transfer_posting_instruction_raises_with_invalid_transaction_code_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            Transfer(
                debtor_target_account_id=self.test_account_id,
                creditor_target_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                override_all_restrictions=True,
                transaction_code=123,
            )

        self.assertIn(
            "'Transfer.transaction_code' expected TransactionCode if populated, got '123' of type "
            "int",
            str(ex.exception),
        )

    
    def test_transfer_posting_instruction_balances_errors_if_own_account_id_not_provided(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        pi._set_output_attributes(  # noqa: SLF001
            committed_postings=[],
            tside=Tside.ASSET,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    def test_transfer_posting_instruction_balances_errors_if_committed_postings_not_provided(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            tside=Tside.LIABILITY,
        )

        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "The Transfer posting instruction type does not support the balances "
            "method for the non-historical data as committed_postings are not available.",
        ):
            pi.balances()

    def test_transfer_posting_instruction_balances_for_both_tsides(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )
        committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
        ]

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.LIABILITY,
        )

        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(-10),
                ),
            },
            balances,
        )

        pi._set_output_attributes(  # noqa: SLF001
            own_account_id=self.test_account_id,
            committed_postings=committed_postings,
            tside=Tside.ASSET,
        )
        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    def test_transfer_with_value_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Transfer(
                debtor_target_account_id=self.test_account_id,
                creditor_target_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                value_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Transfer.__init__() got an unexpected keyword argument 'value_datetime'",
            str(ex.exception),
        )

    def test_transfer_with_value_datetime_set_afterwards_raises_error(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.value_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'value_datetime' of 'Transfer' object has no setter",
            str(ex.exception),
        )

    def test_transfer_with_booking_datetime_raises(self):
        with self.assertRaises(TypeError) as ex:
            Transfer(
                debtor_target_account_id=self.test_account_id,
                creditor_target_account_id="1",
                amount=Decimal(10),
                denomination="GBP",
                override_all_restrictions=True,
                transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
                instruction_details={"testy": "test"},
                booking_datetime=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "Transfer.__init__() got an unexpected keyword argument 'booking_datetime'",
            str(ex.exception),
        )

    def test_transfer_with_booking_datetime_set_afterwards_raises_error(self):
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
            override_all_restrictions=True,
            transaction_code=TransactionCode(domain="A", family="B", subfamily="C"),
            instruction_details={"testy": "test"},
        )

        with self.assertRaises(AttributeError) as ex:
            pi.booking_datetime = datetime.fromtimestamp(1, timezone.utc)
        self.assertEqual(
            "property 'booking_datetime' of 'Transfer' object has no setter",
            str(ex.exception),
        )


class TestPostingInstructionEnrichment(TestCase):
    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_repr(self):
        posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"1": "a", "2": "b", "3": "c"},
        )
        expected = "PostingInstructionEnrichment(details={'1': 'a', '2': 'b', '3': 'c'})"
        self.assertEqual(expected, repr(posting_instruction_enrichment))

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment(self):
        posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"1": "a", "2": "b", "3": "c"},
        )
        self.assertEqual({"1": "a", "2": "b", "3": "c"}, posting_instruction_enrichment.details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_equality(self):
        posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"1": "a", "2": "b", "3": "c"},
        )
        other_posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"1": "a", "2": "b", "3": "c"},
        )
        self.assertEqual(posting_instruction_enrichment, other_posting_instruction_enrichment)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_unequal_details(self):
        posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"1": "a", "2": "b", "3": "c"},
        )
        other_posting_instruction_enrichment = PostingInstructionEnrichment(
            details={"4": "d", "5": "e", "6": "f"},
        )
        self.assertNotEqual(posting_instruction_enrichment, other_posting_instruction_enrichment)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_size_at_limit(self):
        details = {}
        # key length: 1, value length: 119, total 120*10=1200
        for i in range(10):
            details[f"{i}"] = "a" * 119
        posting_instruction_enrichment = PostingInstructionEnrichment(
            details=details,
        )
        self.assertEqual(details, posting_instruction_enrichment.details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_details_none_raises(self):
        with self.assertRaises(TypeError) as ex:
            PostingInstructionEnrichment()

        self.assertEqual(
            str(ex.exception),
            "PostingInstructionEnrichment.__init__() missing 1 required keyword-only argument: 'details'",
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_size_over_limit_raises(self):
        details = {}
        # key length: 1, value length: 119, total 120*9=1080
        for i in range(9):
            details[f"{i}"] = "a" * 119
        # key length: 1, value length: 120, total 1080+121=1201
        details["9"] = "a" * 120
        with self.assertRaises(InvalidSmartContractError) as ex:
            PostingInstructionEnrichment(
                details=details,
            )

        self.assertEqual(
            str(ex.exception),
            "Cannot enrich Posting Instruction with 1201 key/values, maximum length is 1200",
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_key_non_string_raises(self):
        with self.assertRaises(StrongTypingError) as ex:
            PostingInstructionEnrichment(
                details={1: "a"},
            )

        self.assertEqual(
            str(ex.exception),
            "Expected str, got '1' of type int",
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_value_non_string_raises(self):
        with self.assertRaises(StrongTypingError) as ex:
            PostingInstructionEnrichment(
                details={"b": 2},
            )

        self.assertEqual(
            str(ex.exception),
            "Expected str, got '2' of type int",
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_key_non_ascii_raises(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            PostingInstructionEnrichment(
                details={"a": "b", "ç": "d"},
            )

        self.assertEqual(
            str(ex.exception),
            "Cannot enrich Posting Instruction with non ASCII characters: ç: d",
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_posting_instruction_enrichment_value_non_ascii_raises(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            PostingInstructionEnrichment(
                details={"a": "b", "c": "õ"},
            )

        self.assertEqual(
            str(ex.exception), "Cannot enrich Posting Instruction with non ASCII characters: c: õ"
        )


class TestPostingInstructionBaseBalancesMethod(TestCase):
    client_transaction_id = "xx"
    denomination = "GBP"
    transaction_code = TransactionCode(domain="A", family="B", subfamily="C")
    instruction_details = {"testy": "test"}

    test_account_id = "test_account_id"
    test_internal_account_id = "1"
    

    def setUp(self) -> None:
        """
        Note that the instruction attributes in the set-up can be considered dummy data and will
        NOT align with the `committed_postings` set as an output attribute for each test case.
        The `balances()` method calculates the balances solely on the committed postings so the
        discrepancy does not affect the testing of this behaviour.
        """
        outbound_authorisation = OutboundAuthorisation(
            client_transaction_id=self.client_transaction_id,
            target_account_id=self.test_account_id,
            internal_account_id=self.test_internal_account_id,
            amount=Decimal(10),
            denomination=self.denomination,
        )
        inbound_authorisation = InboundAuthorisation(
            client_transaction_id=self.client_transaction_id,
            target_account_id=self.test_account_id,
            internal_account_id=self.test_internal_account_id,
            amount=Decimal(10),
            denomination=self.denomination,
        )
        outbound_hard_settlement = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id=self.test_internal_account_id,
            amount=Decimal(10),
            denomination=self.denomination,
            advice=True,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        inbound_hard_settlement = InboundHardSettlement(
            target_account_id=self.test_account_id,
            internal_account_id=self.test_internal_account_id,
            amount=Decimal(10),
            denomination=self.denomination,
            advice=True,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        authorisation_adjustment = AuthorisationAdjustment(
            client_transaction_id=self.client_transaction_id,
            adjustment_amount=AdjustmentAmount(amount=Decimal(10)),
            advice=True,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        settlement = Settlement(
            client_transaction_id=self.client_transaction_id,
            final=True,
            amount=Decimal(10),
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        release = Release(
            client_transaction_id=self.client_transaction_id,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        transfer = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id=self.test_internal_account_id,
            amount=Decimal(10),
            denomination=self.denomination,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        # This list does not contain custom instructions. CustomInstructions must have their own
        # tests since the committed_postings are inherited from the postings attribute passed into
        # the constructor, so the setup has to be slightly different.
        self.posting_instructions = [
            outbound_authorisation,
            inbound_authorisation,
            outbound_hard_settlement,
            inbound_hard_settlement,
            authorisation_adjustment,
            settlement,
            release,
            transfer,
        ]
        

    
    def test_balances_errors_if_no_account_id_filter_provided(self):
        for pi in self.posting_instructions:
            with self.subTest(pi=pi.__class__.__name__):
                pi._set_output_attributes(  # noqa: SLF001
                    committed_postings=[],
                    tside=Tside.ASSET,
                )

                # Neither account_id or self._own_account_id are provided, so error.
                with self.assertRaisesRegex(
                    InvalidSmartContractError,
                    "An account_id must be specified for the balances calculation.",
                ):
                    pi.balances()

    

    
    def test_balances_defaults_to_own_account_id_when_no_account_id_provided(
        self,
    ):
        for pi in self.posting_instructions:
            with self.subTest(pi=pi.__class__.__name__):
                committed_postings = [
                    Posting(
                        account_id=self.test_account_id,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=False,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(10),
                        denomination=self.denomination,
                    ),
                    Posting(
                        account_id="filter-out-this-account-pls",
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=True,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(1984),
                        denomination=self.denomination,
                    ),
                ]

                pi._set_output_attributes(  # noqa: SLF001
                    # account_id arg should be set to this.
                    own_account_id=self.test_account_id,
                    committed_postings=committed_postings,
                    tside=Tside.ASSET,
                )

                # account_id not provided in args.
                balances = pi.balances()
                self.assertEqual(
                    {
                        BalanceCoordinate(
                            account_address="DEFAULT",
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination=self.denomination,
                            phase=Phase.PENDING_OUT,
                        ): Balance(
                            credit=Decimal(0),
                            debit=Decimal(10),
                            net=Decimal(10),
                        ),
                    },
                    balances,
                )

    
    def test_balances_filters_on_account_id_when_provided(self):
        for pi in self.posting_instructions:
            with self.subTest(pi=pi.__class__.__name__):
                committed_postings = [
                    Posting(
                        # Matching account_id.
                        account_id=self.test_account_id,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=False,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(10),
                        denomination=self.denomination,
                    ),
                    Posting(
                        # Non-matching account_id.
                        account_id="filter-out-this-account-pls",
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        credit=True,
                        phase=Phase.PENDING_OUT,
                        amount=Decimal(1984),
                        denomination=self.denomination,
                    ),
                ]

                pi._set_output_attributes(  # noqa: SLF001
                    committed_postings=committed_postings,
                    tside=Tside.ASSET,
                )

                # Only account_id provided in args.
                balances = pi.balances(account_id=self.test_account_id)
                self.assertEqual(
                    {
                        BalanceCoordinate(
                            account_address="DEFAULT",
                            asset="COMMERCIAL_BANK_MONEY",
                            denomination=self.denomination,
                            phase=Phase.PENDING_OUT,
                        ): Balance(
                            credit=Decimal(0),
                            debit=Decimal(10),
                            net=Decimal(10),
                        ),
                    },
                    balances,
                )

    

    
    def test_custom_instruction_balances_errors_if_no_account_id_filter_provided(self):
        pi = CustomInstruction(
            postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_OUT,
                    amount=Decimal(10),
                    denomination=self.denomination,
                ),
            ],
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )
        pi._set_output_attributes(  # noqa: SLF001
            tside=Tside.ASSET,
        )

        # Neither account_id or self._own_account_id are provided, so error.
        with self.assertRaisesRegex(
            InvalidSmartContractError,
            "An account_id must be specified for the balances calculation.",
        ):
            pi.balances()

    
    def test_custom_instruction_balances_defaults_to_own_account_id_when_no_account_id_provided(
        self,
    ):
        postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination=self.denomination,
            ),
            Posting(
                account_id="filter-out-this-account-pls",
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(1984),
                denomination=self.denomination,
            ),
        ]
        pi = CustomInstruction(
            postings=postings,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )

        pi._set_output_attributes(  # noqa: SLF001
            # account_id arg should be set to this.
            own_account_id=self.test_account_id,
            tside=Tside.ASSET,
        )

        # account_id not provided in args.
        balances = pi.balances()
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination=self.denomination,
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    
    def test_custom_instruction_balances_filters_on_account_id_when_provided(
        self,
    ):
        postings = [
            Posting(
                # Matching account_id.
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(10),
                denomination=self.denomination,
            ),
            Posting(
                # Non-matching account_id.
                account_id="filter-out-this-account-pls",
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_OUT,
                amount=Decimal(1984),
                denomination=self.denomination,
            ),
        ]
        pi = CustomInstruction(
            postings=postings,
            override_all_restrictions=True,
            transaction_code=self.transaction_code,
            instruction_details=self.instruction_details,
        )

        pi._set_output_attributes(  # noqa: SLF001
            tside=Tside.ASSET,
        )

        # Only account_id provided in args.
        balances = pi.balances(account_id=self.test_account_id)
        self.assertEqual(
            {
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination=self.denomination,
                    phase=Phase.PENDING_OUT,
                ): Balance(
                    credit=Decimal(0),
                    debit=Decimal(10),
                    net=Decimal(10),
                ),
            },
            balances,
        )

    



