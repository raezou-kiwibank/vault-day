# standard libs
from datetime import datetime
from decimal import Decimal
from unittest import TestCase

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.pydantic_types import OneOfException
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateOutboundAuthPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp="2024-12-31T12:00:00+00:00",
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=dict(
                        advice=True,
                        amount="1.23",
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=dict(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                        target_sub_account_id=None,
                    ),
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=["a", "b"],
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    # deprecated as of Vault 4.0.0
                    pics=["a", "b"],
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=sim.OutboundAuthorisation(
                        advice=True,
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=sim.TargetAccount(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateInboundAuthPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp="2024-12-31T12:00:00+00:00",
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=dict(
                        advice=True,
                        amount="1.23",
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=dict(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                        target_sub_account_id=None,
                    ),
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=["a", "b"],
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    pics=["a", "b"],
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=sim.InboundAuthorisation(
                        advice=True,
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=sim.TargetAccount(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                    ),
                    instruction_details=dict(a="1", b="2"),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateAuthAdjustmentPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=dict(
                        advice=True,
                        amount="1.23",
                        replacement_amount="2.34",
                    ),
                    batch_details=None,
                    booking_timestamp=None,
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=None,
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    authorisation_adjustment=sim.AuthorisationAdjustment(
                        advice=True,
                        amount=Decimal("1.23"),
                        replacement_amount=Decimal("2.34"),
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateSettlementPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=None,
                    booking_timestamp=None,
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=None,
                    release=None,
                    settlement=dict(
                        amount="1.23",
                        final=True,
                        require_pre_posting_hook_execution=True,
                    ),
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    release=None,
                    settlement=sim.Settlement(
                        amount=Decimal("1.23"),
                        final=True,
                        require_pre_posting_hook_execution=True,
                    ),
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateReleasePibInstruction(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=None,
                    booking_timestamp=None,
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=None,
                    release=dict(
                        require_pre_posting_hook_execution=True,
                    ),
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    release=sim.Release(
                        require_pre_posting_hook_execution=True,
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateInboundHardSettlementPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=None,
                    booking_timestamp=None,
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=dict(
                        advice=True,
                        amount="1.23",
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=dict(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                        target_sub_account_id=None,
                    ),
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=None,
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    inbound_hard_settlement=sim.InboundHardSettlement(
                        advice=True,
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=sim.TargetAccount(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateOutboundHardSettlementPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=None,
                    booking_timestamp=None,
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=dict(
                        advice=True,
                        amount="1.23",
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=dict(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                        target_sub_account_id=None,
                    ),
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    pics=None,
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    outbound_hard_settlement=sim.OutboundHardSettlement(
                        advice=True,
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        internal_account_id="4",
                        target_account=sim.TargetAccount(
                            account_id="5",
                        ),
                        target_account_address="DEFAULT_ADDRESS",
                        asset="COMMERCIAL_BANK_MONEY",
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["7", "8"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="9",
                        family="10",
                        subfamily="11",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateTransferPibInstruction(TestPydanticModelOutputForSimulation.Base[sim.Instruction]):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp="2024-12-31T00:00:00+00:00",
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    release=None,
                    settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["9", "10"],
                        )
                    ),
                    pics=None,
                    transaction_code=dict(
                        domain="11",
                        family="12",
                        subfamily="13",
                    ),
                    transfer=dict(
                        amount="1.23",
                        creditor_target_account_address=None,
                        creditor_target_sub_account_id=None,
                        debtor_target_account_address=None,
                        debtor_target_sub_account_id=None,
                        denomination="AUD",
                        debtor_target_account=dict(
                            account_id="4",
                        ),
                        creditor_target_account=dict(
                            account_id="6",
                        ),
                    ),
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    transfer=sim.Transfer(
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        debtor_target_account=sim.TargetAccount(
                            account_id="4",
                        ),
                        creditor_target_account=sim.TargetAccount(
                            account_id="6",
                        ),
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["9", "10"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="11",
                        family="12",
                        subfamily="13",
                    ),
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestCreateCustomInstructionPibInstruction(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp="2024-12-31T00:00:00+00:00",
                    client_transaction_id="3",
                    custom_instruction=dict(
                        postings=[
                            dict(
                                credit=False,
                                amount="1.23",
                                denomination="AUD",
                                account_id="4",
                                account_address="5",
                                asset="6",
                                phase="POSTING_PHASE_COMMITTED",
                                sub_account_id="",
                            ),
                            dict(
                                credit=True,
                                amount="1.23",
                                denomination="AUD",
                                account_id="7",
                                account_address="8",
                                asset="9",
                                phase="POSTING_PHASE_COMMITTED",
                                sub_account_id="",
                            ),
                        ],
                    ),
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["10", "11"],
                        )
                    ),
                    pics=None,
                    release=None,
                    settlement=None,
                    transaction_code=dict(
                        domain="12",
                        family="13",
                        subfamily="14",
                    ),
                    transfer=None,
                    value_timestamp="2024-12-31T12:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    custom_instruction=sim.CustomInstruction(
                        postings=[
                            sim.Posting(
                                credit=False,
                                amount=Decimal("1.23"),
                                denomination="AUD",
                                account_id="4",
                                account_address="5",
                                asset="6",
                                phase=core_api.PostingPhase.COMMITTED,
                            ),
                            sim.Posting(
                                credit=True,
                                amount=Decimal("1.23"),
                                denomination="AUD",
                                account_id="7",
                                account_address="8",
                                asset="9",
                                phase=core_api.PostingPhase.COMMITTED,
                            ),
                        ],
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["10", "11"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="12",
                        family="13",
                        subfamily="14",
                    ),
                    transfer=None,
                    value_timestamp=datetime(2024, 12, 31, 12, tzinfo=UTC),
                )
            ],
        ),
    )


class TestValidatePostingInstruction(TestCase):

    posting_instruction_validation_error = (
        "1 validation error for PostingInstruction\n  Value error, A Posting Instruction must "
        'specify exactly one of "outbound_authorisation", "inbound_authorisation", '
        '"authorisation_adjustment", "settlement", "release", "inbound_hard_settlement", '
        '"outbound_hard_settlement", "transfer", "custom_instruction".'
    )

    def test_incomplete_posting_instruction(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(client_transaction_id="1")

    def test_overloaded_posting_instruction_1(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                inbound_hard_settlement=sim.InboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
            )

    def test_overloaded_posting_instruction_2(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                authorisation_adjustment=sim.AuthorisationAdjustment(
                    advice=True,
                    amount=Decimal("1.23"),
                    replacement_amount=Decimal("2.34"),
                ),
            )

    def test_overloaded_posting_instruction_3(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                settlement=sim.Settlement(
                    amount=Decimal("1.23"),
                    final=True,
                    require_pre_posting_hook_execution=True,
                ),
            )

    def test_overloaded_posting_instruction_4(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                release=sim.Release(
                    require_pre_posting_hook_execution=True,
                ),
            )

    def test_overloaded_posting_instruction_5(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                outbound_authorisation=sim.OutboundAuthorisation(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
            )

    def test_overloaded_posting_instruction_6(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                inbound_authorisation=sim.InboundAuthorisation(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
            )

    def test_overloaded_posting_instruction_7(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="DEFAULT_ADDRESS",
                    asset="COMMERCIAL_BANK_MONEY",
                ),
                transfer=sim.Transfer(
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    debtor_target_account=sim.TargetAccount(
                        account_id="4",
                    ),
                    creditor_target_account=sim.TargetAccount(
                        account_id="6",
                    ),
                ),
            )

    def test_overloaded_posting_instruction_8(self):
        with self.assertRaises(OneOfException):
            sim.PostingInstruction(
                client_transaction_id="1",
                outbound_hard_settlement=sim.OutboundHardSettlement(
                    advice=True,
                    amount=Decimal("1.23"),
                    denomination="AUD",
                    internal_account_id="4",
                    target_account=sim.TargetAccount(
                        account_id="5",
                    ),
                    target_account_address="8",
                    asset="9",
                ),
                custom_instruction=sim.CustomInstruction(
                    postings=[
                        sim.Posting(
                            credit=False,
                            amount=Decimal("1.23"),
                            denomination="AUD",
                            account_id="4",
                            account_address="5",
                            asset="6",
                            phase=core_api.PostingPhase.COMMITTED,
                        ),
                        sim.Posting(
                            credit=True,
                            amount=Decimal("1.23"),
                            denomination="AUD",
                            account_id="7",
                            account_address="8",
                            asset="9",
                            phase=core_api.PostingPhase.COMMITTED,
                        ),
                    ],
                ),
            )


class TestCreateTransferPibInstructionWithSubAccounts(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2026-01-01T00:00:00+00:00",
        create_posting_instruction_batch=dict(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                dict(
                    authorisation_adjustment=None,
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp="2026-01-01T00:00:00+00:00",
                    client_transaction_id="3",
                    custom_instruction=None,
                    inbound_authorisation=None,
                    inbound_hard_settlement=None,
                    instruction_details=dict(a="1", b="2"),
                    outbound_authorisation=None,
                    outbound_hard_settlement=None,
                    release=None,
                    settlement=None,
                    override=dict(
                        restrictions=dict(
                            all=False,
                            restriction_set_ids=["9", "10"],
                        )
                    ),
                    pics=None,
                    transaction_code=dict(
                        domain="11",
                        family="12",
                        subfamily="13",
                    ),
                    transfer=dict(
                        amount="1.23",
                        creditor_target_account_address="CREDITOR_ADDR",
                        creditor_target_sub_account_id="creditor-sub-id",
                        debtor_target_account_address="DEBTOR_ADDR",
                        debtor_target_sub_account_id="debtor-sub-id",
                        denomination="AUD",
                        debtor_target_account=dict(
                            account_id="4",
                        ),
                        creditor_target_account=dict(
                            account_id="6",
                        ),
                    ),
                    value_timestamp="2026-01-01T00:00:00+00:00",
                )
            ],
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        instruction=sim.CreatePostingInstructionBatch(
            client_batch_id="1",
            client_id="2",
            posting_instructions=[
                sim.PostingInstruction(
                    batch_details=dict(a="1", b="2"),
                    booking_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                    client_transaction_id="3",
                    instruction_details=dict(a="1", b="2"),
                    transfer=sim.Transfer(
                        amount=Decimal("1.23"),
                        denomination="AUD",
                        debtor_target_account=sim.TargetAccount(
                            account_id="4",
                        ),
                        creditor_target_account=sim.TargetAccount(
                            account_id="6",
                        ),
                        debtor_target_sub_account_id="debtor-sub-id",
                        creditor_target_sub_account_id="creditor-sub-id",
                        debtor_target_account_address="DEBTOR_ADDR",
                        creditor_target_account_address="CREDITOR_ADDR",
                    ),
                    override=sim.Override(
                        restrictions=sim.Restrictions(
                            all=False,
                            restriction_set_ids=["9", "10"],
                        )
                    ),
                    release=None,
                    settlement=None,
                    transaction_code=sim.TransactionCode(
                        domain="11",
                        family="12",
                        subfamily="13",
                    ),
                    value_timestamp=datetime(2026, 1, 1, 0, tzinfo=UTC),
                )
            ],
        ),
    )
