from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, Optional

from .exceptions import InvalidPostingInstructionException
from .symbols import DEFAULT_ADDRESS, DEFAULT_ASSET, PostingInstructionType



SECONDARY_POSTING_INSTRUCTIONS = {
    PostingInstructionType.AUTHORISATION_ADJUSTMENT,
    PostingInstructionType.SETTLEMENT,
    PostingInstructionType.RELEASE,
}
PRIMARY_POSTING_INSTRUCTIONS = {
    PostingInstructionType.INBOUND_AUTHORISATION,
    PostingInstructionType.OUTBOUND_AUTHORISATION,
}
NON_CHAINABLE_INSTRUCTIONS = {
    PostingInstructionType.INBOUND_HARD_SETTLEMENT,
    PostingInstructionType.OUTBOUND_HARD_SETTLEMENT,
    PostingInstructionType.TRANSFER,
}

CUSTOM_INSTRUCTIONS = {PostingInstructionType.CUSTOM_INSTRUCTION}





# Below data classes are internal data types used only in the scope of this posting logic
# module. Final results will be converted to a versioned
# public data types defined in the Contracts API.
class CommittedPosting(NamedTuple):
    account_id: str
    amount: Decimal
    denomination: str
    credit: bool
    phase: int
    account_address: str = DEFAULT_ADDRESS
    asset: str = DEFAULT_ASSET
    


class BalanceKey(NamedTuple):
    account_address: str
    asset: str
    denomination: str
    phase: int


class BalanceValue(NamedTuple):
    debit: Decimal
    credit: Decimal


class ClientTransactionUpdate(NamedTuple):
    at_datetime: datetime
    committed_postings: list[CommittedPosting]
    balances: dict[BalanceKey, BalanceValue]
    completed: bool
    released: bool


class SingleAccountClientTransaction:
    """
    Stores all the CommittedPostings for a given account_id and client_transaction_id.
    Keeps track of the overall balance of the Transaction and its state.
    """

    _client_transaction_id: str
    _account_id: str
    _updates: list[ClientTransactionUpdate]

    

    # These private attributes are used to track the state of the ClientTransaction.
    _first_type: Optional[str] = None
    _latest_at_datetime: Optional[datetime] = None
    # True if and only if the ctx has ended with RELEASE.
    _released: bool = False
    # True if and only if the ctx has ended with SETTLEMENT with flag final=True.
    _completed: bool = False

    def __init__(
        self,
        client_transaction_id: str,
        account_id: str,
    ) -> None:
        self._client_transaction_id = client_transaction_id

        self._account_id = account_id
        self._updates = []

        

    @property
    def last_update(self) -> Optional[ClientTransactionUpdate]:
        """
        Returns the latest ClientTransactionUpdate affecting the Account.
        """
        return self._updates[-1] if self._updates else None

    def _get_latest_account_update(self) -> Optional[ClientTransactionUpdate]:
        return self._updates[-1] if self._updates else None

    def _get_latest_account_balances(self) -> dict[BalanceKey, BalanceValue]:
        if latest_update := self._get_latest_account_update():
            return latest_update.balances
        return {}

    

    def balances(
        self,
        *,
        at_datetime: Optional[datetime] = None,
    ) -> dict[BalanceKey, BalanceValue]:
        """
        Returns the balances state of the client transaction for the Account with account_id
        set in `self.account_id`.

        
        """
        return self._balances(updates=self._updates, at_datetime=at_datetime)

    

    def _balances(
        self,
        *,
        updates: list[ClientTransactionUpdate],
        at_datetime: Optional[datetime] = None,
    ) -> dict[BalanceKey, BalanceValue]:
        """
        Returns the balances state of the client transaction for the provided datetime.

        :param updates:
        :param at_datetime:
        :return: the balance state
        """
        if not updates:
            return {}

        if not at_datetime:
            # Return latest.
            return updates[-1].balances

        index = next(
            (i for i, update in enumerate(updates) if update.at_datetime > at_datetime),
            len(updates),
        )
        return updates[index - 1].balances if index else {}

    def add_committed_postings(
        self,
        at_datetime: datetime,
        committed_postings: list[CommittedPosting],
        instruction_type: str,
        # Only used for Settlement PIs.
        final: bool = False,
    ) -> None:
        # Validate the committed postings for the Posting Instruction.
        self._validate_committed_postings(committed_postings, instruction_type, final=final)

        # Validate that datetime is set - None is not supported.
        if not at_datetime:
            raise InvalidPostingInstructionException(
                "All posting instructions within a ClientTransaction have to "
                "have a value_datetime set."
            )

        if self._first_type is not None:
            # We already have at least one instruction for the same ClientTransaction.
            self._validate_secondary_instruction(at_datetime, instruction_type)
        else:
            self._first_type = instruction_type
            self._latest_at_datetime = at_datetime

            # This is the first instruction within the Client Transaction.
            self._validate_primary_instruction(instruction_type)

        completed = released = False
        if instruction_type == PostingInstructionType.SETTLEMENT:
            self._completed = completed = final
        elif instruction_type == PostingInstructionType.RELEASE:
            self._released = released = True

        account_balances_diff, sub_account_balances_diff = self._process_committed_postings(
            committed_postings=committed_postings
        )

        if account_balances_diff:
            updated_balances = self._merge_balances(
                latest_balances=self._get_latest_account_balances(),
                new_balances_diff=account_balances_diff,
            )
            self._updates.append(
                ClientTransactionUpdate(
                    at_datetime=at_datetime,
                    committed_postings=committed_postings,
                    balances=updated_balances,
                    completed=completed,
                    released=released,
                )
            )

        

    def _validate_committed_postings(
        self, committed_postings: list[CommittedPosting], instruction_type: str, final: bool = False
    ):
        if not committed_postings:
            raise InvalidPostingInstructionException("Committed Postings required")

        if final and instruction_type != PostingInstructionType.SETTLEMENT:
            raise InvalidPostingInstructionException(
                "Final flag can only be used with Settlement Posting Instructions"
            )

        for committed_posting in committed_postings:
            if committed_posting.account_id != self._account_id:
                raise InvalidPostingInstructionException(
                    "Cannot add this Committed Posting with account ID "
                    f"{committed_posting.account_id} to the Client Transaction "
                    f"for account ID {self._account_id}"
                )

    @staticmethod
    def _validate_primary_instruction(instruction_type: str) -> None:
        if instruction_type in SECONDARY_POSTING_INSTRUCTIONS:
            raise InvalidPostingInstructionException(
                f"A ClientTransaction cannot start with {instruction_type}"
            )

    def _validate_secondary_instruction(self, at_datetime: datetime, instruction_type: str) -> None:
        if not self._latest_at_datetime:
            raise InvalidPostingInstructionException(
                "Secondary instruction cannot be added to an empty ClientTransaction"
            )

        if at_datetime < self._latest_at_datetime:
            raise InvalidPostingInstructionException(
                "ClientTransaction does not support backdating"
            )

        if self._completed or self._released:
            raise InvalidPostingInstructionException(
                f"Client Transaction (id {self._client_transaction_id}) has already been finalised"
            )

        if instruction_type in {*PRIMARY_POSTING_INSTRUCTIONS, *NON_CHAINABLE_INSTRUCTIONS}:
            raise InvalidPostingInstructionException(
                f"Cannot add {instruction_type} to existing "
                f"ClientTransaction (id {self._client_transaction_id})"
            )
        elif instruction_type in SECONDARY_POSTING_INSTRUCTIONS:
            if self._first_type not in PRIMARY_POSTING_INSTRUCTIONS:
                raise InvalidPostingInstructionException(
                    f"Cannot add {instruction_type} "
                    f"for an existing ClientTransaction (id {self._client_transaction_id}) "
                    f"that did not start with an {PostingInstructionType.INBOUND_AUTHORISATION}"
                    f" or an {PostingInstructionType.OUTBOUND_AUTHORISATION}"
                )
        elif instruction_type in CUSTOM_INSTRUCTIONS:
            if self._first_type not in CUSTOM_INSTRUCTIONS:
                raise InvalidPostingInstructionException(
                    f"Cannot add {instruction_type} "
                    f"for an existing ClientTransaction (id {self._client_transaction_id}) "
                    f"that did not start with a {PostingInstructionType.CUSTOM_INSTRUCTION}"
                )

    def _process_committed_postings(
        self, *, committed_postings: list[CommittedPosting]
    ) -> tuple[dict[BalanceKey, BalanceValue], dict[str, dict[BalanceKey, BalanceValue]]]:
        account_balances: dict[BalanceKey, BalanceValue] = defaultdict(
            lambda: BalanceValue(Decimal(0), Decimal(0))
        )
        sub_account_balances: dict[str, dict[BalanceKey, BalanceValue]] = defaultdict(
            lambda: defaultdict(lambda: BalanceValue(Decimal(0), Decimal(0)))
        )

        for committed_posting in committed_postings:
            coordinate = BalanceKey(
                account_address=committed_posting.account_address,
                asset=committed_posting.asset,
                denomination=committed_posting.denomination,
                phase=committed_posting.phase,
            )

            

            account_balances[coordinate] = self._update_balance_value_with_committed_posting(
                current_balance_value=account_balances[coordinate],
                committed_posting=committed_posting,
            )
        return account_balances, sub_account_balances

    @staticmethod
    def _update_balance_value_with_committed_posting(
        *, current_balance_value: BalanceValue, committed_posting: CommittedPosting
    ) -> BalanceValue:
        debit, credit = current_balance_value
        if committed_posting.credit:
            credit += Decimal(committed_posting.amount)
        else:
            debit += Decimal(committed_posting.amount)
        return BalanceValue(debit=debit, credit=credit)

    @staticmethod
    def _merge_balances(
        latest_balances: dict[BalanceKey, BalanceValue],
        new_balances_diff: dict[BalanceKey, BalanceValue],
    ) -> dict[BalanceKey, BalanceValue]:
        # Merge current balances with balances changes.
        balances = dict(latest_balances)  # Shallow copy.
        for key, value in new_balances_diff.items():
            if key in balances:
                # Update existing key.
                balances[key] = BalanceValue(
                    debit=(balances[key].debit + value.debit),
                    credit=(balances[key].credit + value.credit),
                )
            else:
                # Add key-value entry.
                balances[key] = value

        return balances


def derive_balance_diff_from_committed_postings(
    committed_postings: list[CommittedPosting],
) -> dict[BalanceKey, BalanceValue]:
    balance_diff: dict[BalanceKey, BalanceValue] = {}
    for committed_posting in committed_postings:
        balance_diff_key = BalanceKey(
            account_address=committed_posting.account_address,
            asset=committed_posting.asset,
            denomination=committed_posting.denomination,
            phase=committed_posting.phase,
        )

        debit, credit = Decimal(0), Decimal(0)
        if balance_diff_key in balance_diff:
            credit = balance_diff[balance_diff_key].credit
            debit = balance_diff[balance_diff_key].debit

        if committed_posting.credit:
            credit += Decimal(committed_posting.amount)
        else:
            debit += Decimal(committed_posting.amount)
        balance_diff[balance_diff_key] = BalanceValue(debit=debit, credit=credit)

    return balance_diff
