from unittest import TestCase
from unittest.mock import call
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from unittest.mock import patch, Mock
from zoneinfo import ZoneInfo

from ..types import (
    AdjustmentAmount,
    AuthorisationAdjustment,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    ClientTransaction,
    ClientTransactionEffects,
    CustomInstruction,
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Phase,
    Posting,
    Release,
    Settlement,
    Transfer,
    Tside,
)
from ..types.postings import (
    BalancesCacheKey,
    EffectsCacheKey,
)
from .....utils.exceptions import (
    StrongTypingError,
    InvalidSmartContractError,
    InvalidPostingInstructionException,
)
from .....utils.types_utils import (
    ContractsLanguageDunderMixin,
)
from .....utils import timezone_utils







class TestClientTransactionsBase(TestCase):
    test_account_id = "test_account_id"
    posting_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))

    def _create_uniform_client_transaction(self) -> ClientTransaction:
        pi_committed_postings = [
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
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=self.posting_datetime,
            value_datetime=self.posting_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        client_transaction = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        return client_transaction

    


class TestClientTransactionsDunders(TestClientTransactionsBase):
    

    def test_client_transaction_repr_inherited_from_mixin(self):
        tx = self._create_uniform_client_transaction()
        self.assertTrue(issubclass(ClientTransaction, ContractsLanguageDunderMixin))
        self.assertIn("ClientTransaction", repr(tx))

    def test_instances_equality(self):
        transaction_1 = self._create_uniform_client_transaction()
        transaction_2 = self._create_uniform_client_transaction()
        self.assertNotEqual(id(transaction_1), id(transaction_2))
        self.assertEqual(transaction_1, transaction_2)

    def test_instances_unequal_posting_instructions(self):
        transaction_1 = self._create_uniform_client_transaction()
        transaction_2 = self._create_uniform_client_transaction()
        transaction_1.posting_instructions[0].amount = Decimal(10)
        transaction_2.posting_instructions[0].amount = Decimal(45789)
        self.assertNotEqual(transaction_1, transaction_2)

    def test_instances_unequal_tside(self):
        transaction_1 = self._create_uniform_client_transaction()
        transaction_2 = self._create_uniform_client_transaction()
        transaction_1.tside = Tside.LIABILITY
        transaction_2.tside = Tside.ASSET
        self.assertNotEqual(transaction_1, transaction_2)

    def test_attributes_that_are_compared(self):
        """Check that there are no additional attributes in the class that the __eq__ method does
        not check against.
        """
        expected_public_attributes = {
            "client_transaction_id",
            "account_id",
            "posting_instructions",
            "client_id",
            "tside",
        }
        transaction = self._create_uniform_client_transaction()
        actual_public_attributes = {i for i in transaction.__dict__.keys() if i[:1] != "_"}
        self.assertEqual(actual_public_attributes, expected_public_attributes)

    


class TestClientTransaction(TestClientTransactionsBase):
    
    test_denomination = "GBP"

    def test_client_transaction_transfer(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
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
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "GBP")
        self.assertEqual(ctx.client_id, "CoreContracts")
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
            ctx.balances(),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("0"),
                settled=Decimal("-10"),
                unsettled=Decimal("0"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_inbound_authorisation(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(3),
                denomination="STONKS",
            ),
        ]
        pi = InboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(3),
            denomination="STONKS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "STONKS")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(
            {
                ("DEFAULT", "COMMERCIAL_BANK_MONEY", "STONKS", Phase.PENDING_IN): Balance(
                    credit=Decimal(3),
                    debit=Decimal(0),
                    net=Decimal(3),
                ),
            },
            ctx.balances(),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("3"),
                settled=Decimal("0"),
                unsettled=Decimal("3"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_outbound_authorisation(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "CAMELS")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(
            {
                ("DEFAULT", "COMMERCIAL_BANK_MONEY", "CAMELS", Phase.PENDING_OUT): Balance(
                    credit=Decimal(0),
                    debit=Decimal(40),
                    net=Decimal(-40),
                ),
            },
            ctx.balances(),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("-40"),
                settled=Decimal("0"),
                unsettled=Decimal("-40"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_authorisation_adjustment(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        post_two_datetime = datetime(2019, 12, 13, tzinfo=ZoneInfo("UTC"))
        pi1_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi1 = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi1._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi1_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        pi2_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(7),
                denomination="CAMELS",
            ),
        ]
        pi2 = AuthorisationAdjustment(
            client_transaction_id="ctxid", adjustment_amount=AdjustmentAmount(amount=7)
        )
        pi2._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_two_datetime,
            value_datetime=post_two_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi2_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )

        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi1, pi2],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "CAMELS")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(
            {
                ("DEFAULT", "COMMERCIAL_BANK_MONEY", "CAMELS", Phase.PENDING_OUT): Balance(
                    credit=Decimal(0),
                    debit=Decimal(40),
                    net=Decimal(-40),
                ),
            },
            ctx.balances(effective_datetime=post_one_datetime),
        )
        self.assertEqual(
            {
                ("DEFAULT", "COMMERCIAL_BANK_MONEY", "CAMELS", Phase.PENDING_OUT): Balance(
                    credit=Decimal(0),
                    debit=Decimal(47),
                    net=Decimal(-47),
                ),
            },
            ctx.balances(effective_datetime=post_two_datetime),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("-40"),
                settled=Decimal("0"),
                unsettled=Decimal("-40"),
            ),
            ctx.effects(effective_datetime=post_one_datetime),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("-47"),
                settled=Decimal("0"),
                unsettled=Decimal("-47"),
            ),
            ctx.effects(effective_datetime=post_two_datetime),
        )
        self.assertEqual("ClientTransaction(2 posting instruction(s))", str(ctx))

    def test_client_transaction_inbound_hard_settlement(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal(7),
                denomination=self.test_denomination,
            ),
        ]
        pi = InboundHardSettlement(
            target_account_id=self.test_account_id,
            amount=Decimal(7),
            denomination=self.test_denomination,
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, self.test_denomination)
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(
            {
                (
                    "DEFAULT",
                    "COMMERCIAL_BANK_MONEY",
                    self.test_denomination,
                    Phase.COMMITTED,
                ): Balance(
                    credit=Decimal(7),
                    debit=Decimal(0),
                    net=Decimal(7),
                ),
            },
            ctx.balances(),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("0"),
                settled=Decimal("7"),
                unsettled=Decimal("0"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_outbound_hard_settlement(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(666),
                denomination="APPLES",
            ),
        ]
        pi = OutboundHardSettlement(
            target_account_id=self.test_account_id,
            amount=Decimal(666),
            denomination="APPLES",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "APPLES")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(
            {
                ("DEFAULT", "COMMERCIAL_BANK_MONEY", "APPLES", Phase.COMMITTED): Balance(
                    credit=Decimal(0),
                    debit=Decimal(666),
                    net=Decimal(-666),
                ),
            },
            ctx.balances(),
        )
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("0"),
                settled=Decimal("-666"),
                unsettled=Decimal("0"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_custom_instruction(self):
        post_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address="SOME_ADDRESS",
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(10),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address="SOME_ADDRESS",
                asset="GOLD",
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(100),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address="SOME_ADDRESS",
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal(30),
                denomination="GBP",
            ),
        ]
        pi = CustomInstruction(postings=pi_committed_postings)
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_datetime,
            value_datetime=post_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertTrue(ctx.is_custom)
        self.assertIsNone(ctx.denomination)
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertIsNone(ctx.effects())
        self.assertEqual(ctx.start_datetime, post_datetime)
        self.assertFalse(ctx.completed())
        self.assertFalse(ctx.released())

        self.assertEqual(
            Balance(
                credit=Decimal(0),
                debit=Decimal(10),
                net=Decimal(-10),
            ),
            ctx.balances()[
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
                credit=Decimal(30),
                debit=Decimal(10),
                net=Decimal(20),
            ),
            ctx.balances()[
                BalanceCoordinate(
                    account_address="SOME_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                )
            ],
        )
        self.assertEqual(
            Balance(
                credit=Decimal(0),
                debit=Decimal(100),
                net=Decimal(-100),
            ),
            ctx.balances()[
                BalanceCoordinate(
                    account_address="SOME_ADDRESS",
                    asset="GOLD",
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                )
            ],
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_outbound_authorisation_and_secondaries_with_mixed_timestamps(self):
        """
        Given a ClientTransaction object from the following instructions:
        +-------------+------------------+----------+------------+--------+------+
        | Instruction | Instruction Type | Value Ts | Booking Ts | Amount | PIB  |
        +-------------+------------------+----------+------------+--------+------+
        | I1          | Outbound Auth    | T1       | T1         | 10     | PIB1 |
        | I2          | Auth Adjustment  | T1       | T2         | 1      | PIB1 |
        | I3          | Settlement       | T1       | T2         | 2      | PIB2 |
        | I4          | Release          | T2       | T2         | -      | PIB2 |
        +-------------+------------------+----------+------------+--------+------+
        """
        t1 = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        t2 = datetime(2019, 12, 13, tzinfo=ZoneInfo("UTC"))

        batch_id_1 = "batch_id_1"
        batch_id_2 = "batch_id_2"

        # I1: Inbound Authorisation
        pi1 = InboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(10),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi1._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t1,
            value_datetime=t1,
            booking_datetime=t1,
            client_batch_id="client_batch_id",
            batch_id=batch_id_1,
            committed_postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.PENDING_IN,
                    amount=Decimal(10),
                    denomination="CAMELS",
                ),
            ],
            instruction_id="instruction_id_1",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        # I2: Authorisation Adjustment
        pi2 = AuthorisationAdjustment(
            client_transaction_id="ctxid", adjustment_amount=AdjustmentAmount(amount=1)
        )
        pi2._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t1,
            value_datetime=t1,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_1,
            committed_postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.PENDING_IN,
                    amount=Decimal(1),
                    denomination="CAMELS",
                ),
            ],
            instruction_id="instruction_id_2",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        # I3: Settlement
        pi3 = Settlement(client_transaction_id="ctxid", amount=Decimal("2"))
        pi3._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t2,
            value_datetime=t1,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_2,
            committed_postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=True,
                    phase=Phase.COMMITTED,
                    amount=Decimal("2"),
                    denomination="CAMELS",
                ),
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_IN,
                    amount=Decimal("2"),
                    denomination="CAMELS",
                ),
            ],
            instruction_id="instruction_id_3",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="CAMELS",
        )
        # I4: Release
        pi4 = Release(client_transaction_id="ctxid")
        pi4._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t2,
            value_datetime=t2,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_2,
            committed_postings=[
                Posting(
                    account_id=self.test_account_id,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    credit=False,
                    phase=Phase.PENDING_IN,
                    amount=Decimal("9"),
                    denomination="CAMELS",
                ),
            ],
            instruction_id="instruction_id_4",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="CAMELS",
        )

        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi1, pi2, pi3, pi4],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )

        # assert on fields
        self.assertEqual(ctx.start_datetime, t1)
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "CAMELS")
        self.assertEqual(ctx.client_id, "CoreContracts")

        # assert on completed()
        self.assertFalse(ctx.completed())

        # assert on released()
        self.assertTrue(ctx.released())
        self.assertFalse(ctx.released(effective_datetime=t1))

        # assert on effects()
        # assertion with no ts
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("11"), settled=Decimal("2"), unsettled=Decimal("0")
            ),
            ctx.effects(),
        )
        # assertion at t1
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("11"), settled=Decimal("2"), unsettled=Decimal("9")
            ),
            ctx.effects(effective_datetime=t1),
        )

        # assert on balances()
        coord_committed = BalanceCoordinate(
            account_address="DEFAULT",
            asset="COMMERCIAL_BANK_MONEY",
            denomination="CAMELS",
            phase=Phase.COMMITTED,
        )
        coord_pending_in = BalanceCoordinate(
            account_address="DEFAULT",
            asset="COMMERCIAL_BANK_MONEY",
            denomination="CAMELS",
            phase=Phase.PENDING_IN,
        )
        # assertion with no ts
        self.assertEqual(
            Balance(credit=Decimal("2"), debit=Decimal("0"), net=Decimal("2")),
            ctx.balances()[coord_committed],
        )
        self.assertEqual(
            Balance(credit=Decimal(11), debit=Decimal(11), net=Decimal(0)),
            ctx.balances()[coord_pending_in],
        )
        # assertion at t1
        self.assertEqual(
            Balance(credit=Decimal("2"), debit=Decimal("0"), net=Decimal("2")),
            ctx.balances(effective_datetime=t1)[coord_committed],
        )
        self.assertEqual(
            Balance(credit=Decimal(11), debit=Decimal(2), net=Decimal(9)),
            ctx.balances(effective_datetime=t1)[coord_pending_in],
        )

        self.assertEqual("ClientTransaction(4 posting instruction(s))", str(ctx))

    def test_client_transaction_custom_instructions_with_mixed_timestamps(self):
        """
        Given a ClientTransaction object from the following custom instructions:
        +-------------+--------------------+----------+------------+--------+------+
        | Instruction | Instruction Type   | Value Ts | Booking Ts | Amount | PIB  |
        +-------------+--------------------+----------+------------+--------+------+
        | I1          | Custom Instruction | T1       | T1         | 1      | PIB1 |
        | I2          | Custom Instruction | T1       | T2         | 20     | PIB1 |
        | I3          | Custom Instruction | T1       | T2         | 300    | PIB2 |
        | I4          | Custom Instruction | T2       | T2         | 4000   | PIB2 |
        +-------------+--------------------+----------+------------+--------+------+
        """
        t1 = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        t2 = datetime(2019, 12, 13, tzinfo=ZoneInfo("UTC"))

        batch_id_1 = "batch_id_1"
        batch_id_2 = "batch_id_2"

        # I1
        pi1_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(1),
                denomination="GBP",
            )
        ]
        pi1 = CustomInstruction(postings=pi1_committed_postings)
        pi1._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t1,
            value_datetime=t1,
            booking_datetime=t1,
            client_batch_id="client_batch_id",
            batch_id=batch_id_1,
            committed_postings=pi1_committed_postings,
            instruction_id="instruction_id_1",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        # I2
        pi2_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(20),
                denomination="GBP",
            )
        ]
        pi2 = CustomInstruction(postings=pi2_committed_postings)
        pi2._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t1,
            value_datetime=t1,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_2,
            committed_postings=pi2_committed_postings,
            instruction_id="instruction_id_2",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        # I3
        pi3_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(300),
                denomination="GBP",
            )
        ]
        pi3 = CustomInstruction(postings=pi3_committed_postings)
        pi3._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t2,
            value_datetime=t1,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_2,
            committed_postings=pi3_committed_postings,
            instruction_id="instruction_id_3",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        # I4
        pi4_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.COMMITTED,
                amount=Decimal(4000),
                denomination="GBP",
            )
        ]
        pi4 = CustomInstruction(postings=pi4_committed_postings)
        pi4._set_output_attributes(  # noqa: SLF001
            insertion_datetime=t2,
            value_datetime=t2,
            booking_datetime=t2,
            client_batch_id="client_batch_id",
            batch_id=batch_id_2,
            committed_postings=pi4_committed_postings,
            instruction_id="instruction_id_4",
            unique_client_transaction_id="CoreContracts_ctxid",
        )

        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi1, pi2, pi3, pi4],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )

        # assert on fields
        self.assertEqual(ctx.start_datetime, t1)
        self.assertTrue(ctx.is_custom)
        self.assertIsNone(ctx.denomination)
        self.assertEqual(ctx.client_id, "CoreContracts")

        # assert on completed()
        self.assertFalse(ctx.completed())

        # assert on released()
        self.assertFalse(ctx.released())

        # assert on effects()
        self.assertIsNone(ctx.effects())

        # assert on balances()
        coord_committed = BalanceCoordinate(
            account_address="DEFAULT",
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            phase=Phase.COMMITTED,
        )

        # assertion with no ts
        self.assertEqual(
            Balance(credit=Decimal("0"), debit=Decimal("4321"), net=Decimal("-4321")),
            ctx.balances()[coord_committed],
        )
        # assertion at t1
        self.assertEqual(
            Balance(credit=Decimal("0"), debit=Decimal("321"), net=Decimal("-321")),
            ctx.balances(effective_datetime=t1)[coord_committed],
        )

        self.assertEqual("ClientTransaction(4 posting instruction(s))", str(ctx))

    def test_client_transaction_balances_raises_with_naive_datetime(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        with self.assertRaises(InvalidSmartContractError) as ex:
            ctx.balances(effective_datetime=datetime(2022, 1, 1))

        self.assertEqual(
            "'effective_datetime' of ClientTransaction.balances() is not timezone aware.",
            str(ex.exception),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_balances_returns_default_balance_object_before_value_datetime(self):
        before_value_datetime = datetime(2019, 12, 11, tzinfo=ZoneInfo("UTC"))
        value_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=value_datetime,
            value_datetime=value_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(
            BalanceDefaultDict(),
            ctx.balances(effective_datetime=before_value_datetime),
        )
        self.assertEqual(
            Balance(),
            ctx.balances(effective_datetime=before_value_datetime)[
                BalanceCoordinate(
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    denomination="CAMELS",
                    phase=Phase.PENDING_OUT,
                )
            ],
        )

    def test_client_transaction_effects_raises_with_naive_datetime(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        with self.assertRaises(InvalidSmartContractError) as ex:
            ctx.effects(effective_datetime=datetime(2022, 1, 1))

        self.assertEqual(
            "'effective_datetime' of ClientTransaction.effects() is not timezone aware.",
            str(ex.exception),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_effects_default_object_before_value_datetime(self):
        before_value_datetime = datetime(2019, 12, 11, tzinfo=ZoneInfo("UTC"))
        value_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=value_datetime,
            value_datetime=value_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(
            ClientTransactionEffects(),
            ctx.effects(effective_datetime=before_value_datetime),
        )

    def test_client_transaction_effects_raises_with_non_zoneinfo_timezone(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_OUT,
                amount=Decimal(40),
                denomination="CAMELS",
            ),
        ]
        pi = OutboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(40),
            denomination="CAMELS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        with self.assertRaises(InvalidSmartContractError) as ex:
            ctx.effects(effective_datetime=datetime.fromtimestamp(1, timezone.utc))

        self.assertEqual(
            "'effective_datetime' of ClientTransaction.effects() must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_released(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(10),
                denomination="HKK",
            ),
        ]
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="HKK",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        post_two_datetime = datetime(2020, 12, 12, tzinfo=ZoneInfo("UTC"))
        settlement_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal("0.1"),
                denomination="HKK",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("0.1"),
                denomination="HKK",
            ),
        ]
        post_two = Settlement(client_transaction_id="ctxid", amount=Decimal("0.1"))
        post_two._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_two_datetime,
            value_datetime=post_two_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_2",
            committed_postings=settlement_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="HKK",
        )
        post_three_datetime = datetime(2021, 12, 12, tzinfo=ZoneInfo("UTC"))
        release_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("9.9"),
                denomination="HKK",
            ),
        ]
        post_three = Release(client_transaction_id="ctxid")
        post_three._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_three_datetime,
            value_datetime=post_three_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_3",
            committed_postings=release_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="HKK",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one, post_two, post_three],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(False, ctx.completed())
        self.assertEqual(True, ctx.released())
        self.assertEqual(
            False, ctx.released(effective_datetime=datetime(2021, 1, 1, tzinfo=ZoneInfo("UTC")))
        )
        self.assertEqual(
            Balance(
                credit=Decimal("0.1"),
                debit=Decimal("0"),
                net=Decimal("0.1"),
            ),
            ctx.balances()[
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="HKK",
                    phase=Phase.COMMITTED,
                )
            ],
        )
        self.assertEqual(
            Balance(
                credit=Decimal(10),
                debit=Decimal(10),
                net=Decimal(0),
            ),
            ctx.balances()[
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="HKK",
                    phase=Phase.PENDING_IN,
                )
            ],
        )
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "HKK")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("10"),
                settled=Decimal("0.1"),
                unsettled=Decimal("0"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(3 posting instruction(s))", str(ctx))

    def test_client_transaction_completed(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        post_two_datetime = datetime(2020, 12, 12, tzinfo=ZoneInfo("UTC"))
        settlement_committed_postings_1 = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal("0.1"),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("0.1"),
                denomination="GBP",
            ),
        ]
        post_two = Settlement(client_transaction_id="ctxid", amount=Decimal("0.1"))
        post_two._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_two_datetime,
            value_datetime=post_two_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_2",
            committed_postings=settlement_committed_postings_1,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="GBP",
        )
        post_three_datetime = datetime(2021, 12, 12, tzinfo=ZoneInfo("UTC"))
        settlement_committed_postings_2 = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal("9.9"),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("9.9"),
                denomination="GBP",
            ),
        ]
        post_three = Settlement(client_transaction_id="ctxid", final=True)
        post_three._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_three_datetime,
            value_datetime=post_three_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_3",
            committed_postings=settlement_committed_postings_2,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="GBP",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one, post_two, post_three],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        self.assertEqual(False, ctx.released())
        self.assertEqual(True, ctx.completed())
        self.assertEqual(
            False, ctx.completed(effective_datetime=datetime(2021, 1, 1, tzinfo=ZoneInfo("UTC")))
        )
        self.assertEqual(
            Balance(
                credit=Decimal("10"),
                debit=Decimal("0"),
                net=Decimal("10"),
            ),
            ctx.balances()[
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
                credit=Decimal(10),
                debit=Decimal(10),
                net=Decimal(0),
            ),
            ctx.balances()[
                BalanceCoordinate(
                    account_address="DEFAULT",
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=Phase.PENDING_IN,
                )
            ],
        )
        self.assertFalse(ctx.is_custom)
        self.assertEqual(ctx.denomination, "GBP")
        self.assertEqual(ctx.client_id, "CoreContracts")
        self.assertEqual(ctx.start_datetime, post_one_datetime)
        self.assertEqual(
            ClientTransactionEffects(
                authorised=Decimal("10"),
                settled=Decimal("10"),
                unsettled=Decimal("0"),
            ),
            ctx.effects(),
        )
        self.assertEqual("ClientTransaction(3 posting instruction(s))", str(ctx))

    def test_client_transaction_invalid_committed_postings_inconsistent_ct(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        post_two_datetime = datetime(2020, 12, 12, tzinfo=ZoneInfo("UTC"))
        settlement_committed_postings_1 = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal("0.1"),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("0.1"),
                denomination="HKK",
            ),
        ]
        post_two = Settlement(client_transaction_id="ctxid", amount=Decimal("0.1"))
        post_two._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_two_datetime,
            value_datetime=post_two_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_2",
            committed_postings=settlement_committed_postings_1,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="GBP",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one, post_two],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )
        with self.assertRaises(InvalidPostingInstructionException) as ex:
            ctx.effects()
        self.assertEqual(
            str(ex.exception),
            "ClientTransaction only supports posting instructions with the same "
            "account_address, denomination and asset attributes.",
        )
        self.assertEqual("ClientTransaction(2 posting instruction(s))", str(ctx))

    def test_client_transaction_raises_with_no_posting_instructions(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            ClientTransaction(
                client_transaction_id="ctxid",
                account_id=self.test_account_id,
                posting_instructions=[],
                client_id="CoreContracts",
            )
        self.assertEqual(
            "'ClientTransaction.posting_instructions' must be a non empty list, got []",
            str(ex.exception),
        )

    def test_client_transaction_raises_for_posting_instruction_with_no_value_datetime(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi_committed_postings = [
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
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        # No value_datetime is set.
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        with self.assertRaises(InvalidPostingInstructionException) as ex:
            ClientTransaction(
                client_transaction_id="ctxid",
                account_id=self.test_account_id,
                posting_instructions=[pi],
                client_id="CoreContracts",
                tside=Tside.LIABILITY,
            )
        self.assertEqual(
            "'ClientTransaction.posting_instructions[0]' has its value_datetime attribute set "
            "to None. Expected value_datetime to be set.",
            str(ex.exception),
        )

    def test_client_transaction_raises_for_posting_instruction_with_no_committed_postings(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=None,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        with self.assertRaises(InvalidSmartContractError) as ex:
            ClientTransaction(
                client_transaction_id="ctxid",
                account_id=self.test_account_id,
                posting_instructions=[pi],
                client_id="CoreContracts",
                tside=Tside.LIABILITY,
            )
        self.assertEqual(
            "'ClientTransaction.posting_instructions[0]._committed_postings' "
            "must be a non empty list, got None",
            str(ex.exception),
        )

    def test_client_transaction_raises_for_posting_instruction_with_committed_postings_type(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        pi = Transfer(
            debtor_target_account_id=self.test_account_id,
            creditor_target_account_id="1",
            amount=Decimal(10),
            denomination="GBP",
        )
        pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=[0],
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        with self.assertRaises(StrongTypingError) as ex:
            ClientTransaction(
                client_transaction_id="ctxid",
                account_id=self.test_account_id,
                posting_instructions=[pi],
                client_id="CoreContracts",
                tside=Tside.LIABILITY,
            )
        self.assertEqual(
            "'ClientTransaction.posting_instructions[0]._committed_postings[0]' "
            "expected Posting, got '0' of type int",
            str(ex.exception),
        )

    def test_client_transaction_raises_for_settlement_attribute_final_set_to_none(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        post_two_datetime = datetime(2020, 12, 12, tzinfo=ZoneInfo("UTC"))
        settlement_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.COMMITTED,
                amount=Decimal("10"),
                denomination="GBP",
            ),
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=False,
                phase=Phase.PENDING_IN,
                amount=Decimal("10"),
                denomination="GBP",
            ),
        ]
        post_two = Settlement(client_transaction_id="ctxid", amount=Decimal("10"), final=None)
        post_two._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_two_datetime,
            value_datetime=post_two_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_2",
            committed_postings=settlement_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
            target_account_id=self.test_account_id,
            denomination="GBP",
        )
        with self.assertRaises(InvalidPostingInstructionException) as ex:
            ClientTransaction(
                client_transaction_id="ctxid",
                account_id=self.test_account_id,
                posting_instructions=[post_one, post_two],
                client_id="CoreContracts",
                tside=Tside.LIABILITY,
            )
        self.assertEqual(
            "'ClientTransaction.posting_instructions[1]' Settlement instruction "
            "has its final attribute set to None. Expected True or False.",
            str(ex.exception),
        )

    def test_client_transaction_with_no_tside_balances(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one],
            client_id="CoreContracts",
        )
        with self.assertRaises(InvalidSmartContractError) as ex:
            ctx.balances()
        self.assertEqual(
            str(ex.exception), "A tside must be specified for the balances calculation."
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    def test_client_transaction_with_no_client_id_backwards_compatible(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one],
        )
        self.assertEqual("", ctx.client_id)

    def test_client_transaction_effects_with_no_committed_postings(self):
        post_one_datetime = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        inbound_committed_postings = [
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
        post_one = InboundAuthorisation(
            amount=Decimal(10),
            target_account_id=self.test_account_id,
            denomination="GBP",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        post_one._set_output_attributes(  # noqa: SLF001
            insertion_datetime=post_one_datetime,
            value_datetime=post_one_datetime,
            client_batch_id="client_batch_id",
            batch_id="batch_id_1",
            committed_postings=inbound_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[post_one],
            client_id="CoreContracts",
        )
        ctx.posting_instructions[0]._committed_postings = None
        with self.assertRaises(InvalidSmartContractError) as ex:
            ctx.effects()
        self.assertEqual(
            str(ex.exception),
            "ClientTransaction only supports posting instructions with"
            "non empty committed postings.",
        )
        self.assertEqual("ClientTransaction(1 posting instruction(s))", str(ctx))

    @patch.object(ClientTransaction, "_validate_account_helper_preconditions")
    def test_client_transaction_balances_calls_validate_account_helper_preconditions(
        self, mock_validate_account_helper_preconditions: Mock
    ):
        ctxn = self._create_uniform_client_transaction()
        ctxn.balances(effective_datetime=self.posting_datetime)
        mock_validate_account_helper_preconditions.assert_called_once_with(
            "balances",
            self.posting_datetime,
        )

    @patch.object(ClientTransaction, "_validate_account_helper_preconditions")
    def test_client_transaction_effects_calls_validate_account_helper_preconditions(
        self, mock_validate_account_helper_preconditions: Mock
    ):
        ctxn = self._create_uniform_client_transaction()
        ctxn.effects(effective_datetime=self.posting_datetime)
        mock_validate_account_helper_preconditions.assert_has_calls(
            [
                call("effects", self.posting_datetime),
                # effects also calls balances.
                call("balances", self.posting_datetime),
            ]
        )

    @patch.object(timezone_utils, "validate_timezone_is_utc")
    def test_validate_account_helper_preconditions_validates_effective_datetime(
        self, mock_validate_timezone_is_utc
    ):
        ctxn = self._create_uniform_client_transaction()
        helper_name = "account_balances"
        ctxn._validate_account_helper_preconditions(  # noqa:SLF001
            helper_name,
            self.posting_datetime,
        )

        mock_validate_timezone_is_utc.assert_called_once_with(
            self.posting_datetime,
            "effective_datetime",
            f"ClientTransaction.{helper_name}()",
        )

    






class TestClientTransactionEffects(TestCase):
    def test_client_transaction_effect_authorised_attribute_set(self):
        effect = ClientTransactionEffects(authorised=Decimal("40"))
        self.assertEqual(effect.authorised, Decimal("40"))
        self.assertEqual(effect.settled, Decimal("0"))
        self.assertEqual(effect.unsettled, Decimal("0"))

    def test_client_transaction_effect_settled_attribute_set(self):
        effect = ClientTransactionEffects(settled=Decimal("7"))
        self.assertEqual(effect.authorised, Decimal("0"))
        self.assertEqual(effect.settled, Decimal("7"))
        self.assertEqual(effect.unsettled, Decimal("0"))

    def test_client_transaction_effect_unsettled_attribute_set(self):
        effect = ClientTransactionEffects(unsettled=Decimal("3"))
        self.assertEqual(effect.authorised, Decimal("0"))
        self.assertEqual(effect.settled, Decimal("0"))
        self.assertEqual(effect.unsettled, Decimal("3"))

    def test_client_transaction_effect_all_attributes_set(self):
        effect = ClientTransactionEffects(
            authorised=Decimal("40"),
            settled=Decimal("7"),
            unsettled=Decimal("3"),
        )
        self.assertEqual(effect.authorised, Decimal("40"))
        self.assertEqual(effect.settled, Decimal("7"))
        self.assertEqual(effect.unsettled, Decimal("3"))

    def test_client_transaction_effect_repr(self):
        effect = ClientTransactionEffects(
            authorised=Decimal("40"),
            settled=Decimal("7"),
            unsettled=Decimal("3"),
        )
        expected = (
            "ClientTransactionEffects(authorised=Decimal('40'), settled=Decimal('7'), "
            + "unsettled=Decimal('3'))"
        )
        self.assertEqual(expected, repr(effect))

    def test_client_transaction_effect_equality(self):
        effect = ClientTransactionEffects(authorised=Decimal("40"))
        other_effect = ClientTransactionEffects(authorised=Decimal("40"))
        self.assertEqual(effect, other_effect)

    def test_client_transaction_effect_unequal_authorised(self):
        effect = ClientTransactionEffects(authorised=Decimal("40"))
        other_effect = ClientTransactionEffects(authorised=Decimal("42"))
        self.assertNotEqual(effect, other_effect)


class TestClientTransactionBalancesCaching(TestCase):
    test_account_id = "test_account_id"
    
    mocked_balances_1 = {
        ("DEFAULT", "COMMERCIAL_BANK_MONEY", "STONKS", Phase.PENDING_IN): Balance(
            credit=Decimal(3),
            debit=Decimal(0),
            net=Decimal(3),
        )
    }
    mocked_balances_2 = {
        ("DEFAULT", "COMMERCIAL_BANK_MONEY", "GBP", Phase.COMMITTED): Balance(
            credit=Decimal(25),
            debit=Decimal(0),
            net=Decimal(25),
        )
    }

    def setUp(self) -> None:
        self.datetime_1 = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        self.datetime_2 = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(3),
                denomination="STONKS",
            ),
        ]
        self.pi = InboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(3),
            denomination="STONKS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        self.pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=self.datetime_1,
            value_datetime=self.datetime_1,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=self.pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        self.ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[self.pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )

    @patch.object(ClientTransaction, "_balances")
    def test_client_transaction_balances_cache(self, mock_private_balances: Mock):
        for test_number, (effective_datetime, tside) in enumerate(
            [
                (None, None),
                (self.datetime_1, None),
                (None, Tside.ASSET),
                (self.datetime_1, Tside.ASSET),
            ]
        ):
            with self.subTest(effective_datetime=effective_datetime, tside=tside):
                balance_cache_key = BalancesCacheKey(
                    effective_datetime=effective_datetime,
                    tside=tside,
                )
                mock_private_balances.side_effect = [
                    self.mocked_balances_1,
                    self.mocked_balances_2,
                ]

                # First call of balances(...) adds `balance_cache_key` to the cache.
                self.assertEqual(
                    self.ctx.balances(effective_datetime=effective_datetime, tside=tside),
                    self.mocked_balances_1,
                )
                self.assertTrue(
                    balance_cache_key in self.ctx._balances_cache.keys()  # noqa: SLF001
                )
                mock_private_balances.assert_called_once_with(
                    effective_datetime=effective_datetime,
                    tside=tside,
                )

                # Second call of balances(...) accesses the cache,
                # so mock_private_balances should still only be called once.
                self.assertEqual(
                    self.ctx.balances(effective_datetime=effective_datetime, tside=tside),
                    self.mocked_balances_1,
                )
                self.assertTrue(
                    balance_cache_key in self.ctx._balances_cache.keys()  # noqa: SLF001
                )
                mock_private_balances.assert_called_once_with(
                    effective_datetime=effective_datetime,
                    tside=tside,
                )

                # Third call of balances(...) with new set of args does not access cache and
                # should add the `different_balance_cache_key` to the cache.
                different_balance_cache_key = BalancesCacheKey(
                    effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                    tside=Tside.LIABILITY,
                )
                self.assertEqual(
                    self.ctx.balances(
                        effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                        tside=Tside.LIABILITY,
                    ),
                    self.mocked_balances_2,
                )
                self.assertTrue(
                    different_balance_cache_key in self.ctx._balances_cache.keys()  # noqa: SLF001
                )
                self.assertEqual(mock_private_balances.call_count, 2)
                mock_private_balances.assert_called_with(
                    effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                    tside=Tside.LIABILITY,
                )

                self.assertEqual("ClientTransaction(1 posting instruction(s))", str(self.ctx))
                mock_private_balances.reset_mock(side_effect=True)

    


class TestClientTransactionEffectsCaching(TestCase):
    test_account_id = "test_account_id"
    
    mocked_effects_1 = ClientTransactionEffects(
        authorised=Decimal("0"),
        settled=Decimal("10"),
        unsettled=Decimal("0"),
    )
    mocked_effects_2 = ClientTransactionEffects(
        authorised=Decimal("40"),
        settled=Decimal("7"),
        unsettled=Decimal("33"),
    )

    def setUp(self) -> None:
        self.datetime_1 = datetime(2019, 12, 12, tzinfo=ZoneInfo("UTC"))
        self.datetime_2 = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.pi_committed_postings = [
            Posting(
                account_id=self.test_account_id,
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                credit=True,
                phase=Phase.PENDING_IN,
                amount=Decimal(3),
                denomination="STONKS",
            ),
        ]
        self.pi = InboundAuthorisation(
            target_account_id=self.test_account_id,
            amount=Decimal(3),
            denomination="STONKS",
            client_transaction_id="ctxid",
            internal_account_id="1",
        )
        self.pi._set_output_attributes(  # noqa: SLF001
            insertion_datetime=self.datetime_1,
            value_datetime=self.datetime_1,
            client_batch_id="client_batch_id",
            batch_id="batch_id",
            committed_postings=self.pi_committed_postings,
            instruction_id="instruction_id",
            unique_client_transaction_id="CoreContracts_ctxid",
        )
        self.ctx = ClientTransaction(
            client_transaction_id="ctxid",
            account_id=self.test_account_id,
            posting_instructions=[self.pi],
            client_id="CoreContracts",
            tside=Tside.LIABILITY,
        )

    @patch.object(ClientTransaction, "_effects")
    def test_client_transaction_effects_cache(self, mock_private_effects: Mock):
        for test_number, effective_datetime in enumerate(
            [
                None,
                self.datetime_1,
            ]
        ):
            with self.subTest(effective_datetime=effective_datetime):
                balance_cache_key = EffectsCacheKey(
                    effective_datetime=effective_datetime,
                )
                mock_private_effects.side_effect = [
                    self.mocked_effects_1,
                    self.mocked_effects_2,
                ]

                # First call of effects(...) adds `balance_cache_key` to the cache.
                self.assertEqual(
                    self.ctx.effects(effective_datetime=effective_datetime),
                    self.mocked_effects_1,
                )
                self.assertTrue(balance_cache_key in self.ctx._effects_cache.keys())  # noqa: SLF001
                mock_private_effects.assert_called_once_with(
                    effective_datetime=effective_datetime,
                )

                # Second call of effects(...) accesses the cache,
                # so mock_private_effects should still only be called once.
                self.assertEqual(
                    self.ctx.effects(effective_datetime=effective_datetime),
                    self.mocked_effects_1,
                )
                self.assertTrue(balance_cache_key in self.ctx._effects_cache.keys())  # noqa: SLF001
                mock_private_effects.assert_called_once_with(
                    effective_datetime=effective_datetime,
                )

                # Third call of effects(...) with new set of args does not access cache and
                # should add the `different_balance_cache_key` to the cache.
                different_balance_cache_key = EffectsCacheKey(
                    effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                )
                self.assertEqual(
                    self.ctx.effects(
                        effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                    ),
                    self.mocked_effects_2,
                )
                self.assertTrue(
                    different_balance_cache_key in self.ctx._effects_cache.keys()  # noqa: SLF001
                )
                self.assertEqual(mock_private_effects.call_count, 2)
                mock_private_effects.assert_called_with(
                    effective_datetime=self.datetime_2 + relativedelta(days=test_number),
                )

                self.assertEqual("ClientTransaction(1 posting instruction(s))", str(self.ctx))
                mock_private_effects.reset_mock(side_effect=True)

    



