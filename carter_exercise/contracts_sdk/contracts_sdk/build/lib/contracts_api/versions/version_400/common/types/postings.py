from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, NamedTuple, Optional, List, Dict, Union, get_args
from zoneinfo import ZoneInfo

from . import enums

from ...common.docs import _common_docs_path
from .....utils import exceptions, symbols, types_utils
from ....version_400.common.types import (
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    Phase,
    PostingInstructionType,
    Tside,
)
from .....utils.exceptions import (
    InvalidSmartContractError,
    InvalidPostingInstructionException,
    StrongTypingError,
)
from .....utils.posting_logic import (
    derive_balance_diff_from_committed_postings,
    
    SingleAccountClientTransaction,
)
from .....utils import timezone_utils
from .....utils.feature_flags import (
    is_fflag_enabled,
    
    ENRICH_POSTING_INSTRUCTIONS,
    POSTINGS_TARGET_ADDRESS,
    
    RELAX_CLIENT_TRANSACTION_TIMESTAMP_CONSTRAINT,
    
)





class PostingInstructionEnrichment(types_utils.ContractsLanguageDunderMixin):
    MAX_LENGTH = 1200

    def __init__(
        self,
        *,
        details: dict[str, str],
    ):
        self.details = details
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.details,
            dict,
            hint="dict[str, str]",
            prefix="PostingInstructionEnrichment.details",
        )

        total_length = 0
        for key, value in self.details.items():
            types_utils.validate_type(key, str)
            types_utils.validate_type(value, str)
            if not key.isascii() or not value.isascii():
                raise InvalidSmartContractError(
                    f"Cannot enrich Posting Instruction with non ASCII characters: "
                    f"{key}: {value}"
                )
            total_length += len(key) + len(value)

        if total_length > PostingInstructionEnrichment.MAX_LENGTH:
            raise InvalidSmartContractError(
                f"Cannot enrich Posting Instruction with {total_length} key/values, "
                f"maximum length is {PostingInstructionEnrichment.MAX_LENGTH}"
            )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="details",
                type="dict[str, str]",
                docstring=f"""
                   A dictionary of key/value pairs that will be used to enrich a Posting
                   Instruction. Up to {PostingInstructionEnrichment.MAX_LENGTH} bytes of ASCII
                   characters are allowed.
                """,
            )
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="PostingInstructionEnrichment",
            docstring=f"""
                `PostingInstructionEnrichment` objects describe the key/value pairs that make up the
                enrichment of a Posting Instruction. Posting Instructions that will be accepted may
                be enriched with up to {PostingInstructionEnrichment.MAX_LENGTH} bytes of ASCII
                key/value pairs in pre-posting. The latency for postings with larger amounts of
                enriched bytes will be higher than ones with smaller enrichments.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new `PostingInstructionEnrichment` object",
                args=cls._public_attributes(language_code),
            ),
        )


class Posting(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        credit: bool,
        amount: Union[Decimal, int],
        denomination: str,
        account_id: Optional[str] = None,
        
        internal_account_processing_label: Optional[str] = None,
        account_address: str,
        asset: str,
        phase: Phase,
        _from_proto: bool = False,
    ):
        self.denomination = denomination
        self.account_id = account_id
        
        self.internal_account_processing_label = internal_account_processing_label
        self.account_address = account_address
        self.asset = asset
        self.credit = credit
        self.amount = amount
        self.phase = phase
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        # As this is now used when instructing CustomInstruction directive ensure that all
        # validation previously existing in vault method exist.
        str_args = {
            "denomination": self.denomination,
            "account_address": self.account_address,
            "asset": self.asset,
        }

        missing = [k for k, v in str_args.items() if not v]
        if self.account_id == "":
            # account_id cannot be an empty string, but is permitted to be None, hence the
            # falsey check in the missing dictionary is not suitable.
            missing.append("account_id")

        if missing:
            raise InvalidSmartContractError(f"Postings missing required argument(s): {missing}")
        if self.amount <= 0:
            raise InvalidSmartContractError(f"Amount must be greater than 0, {self.amount}")
        try:
            self.phase = Phase(self.phase)
        except ValueError:
            raise StrongTypingError("'phase' must be set to a Phase value")

        if self.account_id is None and self.internal_account_processing_label is None:
            raise InvalidSmartContractError(
                "At least one of account_id and internal_account_processing_label must be provided"
            )

        types_utils.validate_type(
            self.internal_account_processing_label,
            str,
            is_optional=True,
            check_empty=True,
            prefix="Posting.internal_account_processing_label",
        )

        

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="Posting",
            docstring="""
                Posting ledger entry that represents a financial movement
                that resulted from each different Posting Instruction type intent.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new Posting",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        public_attributes = [
            types_utils.ValueSpec(
                name="credit",
                type="bool",
                docstring="""
                    Represents the direction of the financial movement.
                """,
            ),
            types_utils.ValueSpec(
                name="amount",
                type="Union[Decimal, int]",
                docstring="""
                    Represents the value of the financial movement.
                """,
            ),
            types_utils.ValueSpec(
                name="denomination",
                type="str",
                docstring="""
                    The denomination of the Posting.
                """,
            ),
        ]
        account_id_value_spec = types_utils.ValueSpec(
            name="account_id",
            type="Optional[str]",
            docstring="""
                The Account ID that is targeted by the financial movement. When creating
                a `Posting` within a Contract, this should only be populated if
                `internal_account_processing_label` is not provided.
            """,
        )

        
        public_attributes.append(account_id_value_spec)

        

        internal_account_processing_label_value_spec = types_utils.ValueSpec(
            name="internal_account_processing_label",
            type="Optional[str]",
            docstring="""
                A label for a Posting Instruction to use to reference an Internal
                Account without a need to identify the Processing Group it belongs to.
                Use `internal_account_processing_label` in place of the
                `account_id` in order to instruct Posting Instructions
                for an Internal Account with a matching processing label
                belonging to the same Processing Group as the target Account.

                For fetched Posting Instructions, if `internal_account_processing_label`
                is set, then `account_id` is already resolved by Vault
                and set on the instruction.
            """,
        )

        
        public_attributes.append(internal_account_processing_label_value_spec)

        account_address_value_spec = types_utils.ValueSpec(
            name="account_address",
            type="str",
            docstring="""
                        The address of the Account that is targeted by the financial movement.
                        It is equivalent to the `target_account_address` in the Posting Instruction types,
                        except for `CustomInstruction` and `Transfer`.
                    """,
        )

        
        public_attributes.append(account_address_value_spec)

        public_attributes.extend(
            [
                types_utils.ValueSpec(
                    name="asset",
                    type="str",
                    docstring="""
                        Represents the asset type of the financial movement.
                    """,
                ),
                types_utils.ValueSpec(
                    name="phase",
                    type="Phase",
                    docstring="""
                        Represents the phase of the financial movement.
                    """,
                ),
            ]
        )
        return public_attributes


class TransactionCode(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self, *, domain: str, family: str, subfamily: str, _from_proto: Optional[bool] = False
    ):
        self.domain = domain
        self.family = family
        self.subfamily = subfamily
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.domain, str, check_empty=True, prefix="TransactionCode.domain"
        )
        types_utils.validate_type(
            self.family, str, check_empty=True, prefix="TransactionCode.family"
        )
        types_utils.validate_type(
            self.subfamily, str, check_empty=True, prefix="TransactionCode.subfamily"
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="TransactionCode",
            docstring="""
                ISO20022 Bank Transaction Code with information about payment domain, family and subfamily.
                For further information, see [Posting Instruction](/reference/postings/#posting_instruction)..
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new TransactionCode",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="domain",
                type="str",
                docstring="""
                    Business area of the transaction.
                """,
            ),
            types_utils.ValueSpec(
                name="family",
                type="str",
                docstring="""
                    A family within the domain.
                """,
            ),
            types_utils.ValueSpec(
                name="subfamily",
                type="str",
                docstring="""
                    Sub-product family within a specific family.
                """,
            ),
        ]


class PostingInstructionBase(types_utils.ContractsLanguageDunderMixin):
    _balance_class = Balance
    _balance_coordinate_class = BalanceCoordinate
    _balance_default_dict_class = BalanceDefaultDict

    # The below attributes are set on a class instance and are either
    # output fields or other indirect attributes
    _insertion_datetime: Optional[datetime] = None
    _value_datetime: Optional[datetime] = None
    _booking_datetime: Optional[datetime] = None
    
    _client_batch_id: Optional[str] = None
    _batch_id: Optional[str] = None
    _committed_postings: Optional[List[Posting]] = None
    _instruction_id: Optional[str] = None
    _unique_client_transaction_id: Optional[str] = None
    _client_transaction_id: Optional[str] = None
    _own_account_id: Optional[str] = None
    
    _tside: Optional[Tside] = None
    _batch_details: Optional[Dict[str, str]] = None
    _client_id: Optional[str] = None
    _localised_booking_datetime = None
    _enrichment_details: dict[str, PostingInstructionEnrichment]
    
    # Appended to each class doc-string
    _class_docs_note = """
        To enable Posting Instruction methods that return indirect or output attributes
        to work in unit tests, you must set private Posting Instruction attributes when
        mocking Vault data. You can do this by calling `_set_output_attributes()` method
        on the Posting Instruction class instance. To see an example, see
        [Supervisor Contract example unit test](/reference/contracts/contracts_api_4xx/development_and_testing#supervisor_contract_example_unit_test).
    """
    
    # Public attribute that returns the Posting Instruction type - set on each sub-class
    type: Optional[PostingInstructionType] = None

    def __init__(
        self,
        *,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        self.instruction_details = instruction_details or {}
        self.transaction_code = transaction_code
        self.override_all_restrictions = override_all_restrictions
        if is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
            self._enrichment_details = dict()
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.transaction_code,
            TransactionCode,
            hint="TransactionCode",
            is_optional=True,
            prefix=f"{self.type.value}.transaction_code",
        )

        # Avoids iterable errors in the native_to_proto.
        types_utils.validate_type(
            self.instruction_details,
            dict,
            hint="Dict[str, str]",
            is_optional=True,
            prefix=f"{self.type.value}.instruction_details",
        )

    def _set_output_attributes(
        self,
        insertion_datetime: Optional[datetime] = None,
        value_datetime: Optional[datetime] = None,
        booking_datetime: Optional[datetime] = None,
        
        client_batch_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        committed_postings: Optional[List[Posting]] = None,
        instruction_id: Optional[str] = None,
        unique_client_transaction_id: Optional[str] = None,
        client_transaction_id: Optional[str] = None,
        own_account_id: Optional[str] = None,
        
        tside: Optional[Tside] = None,
        batch_details: Optional[Dict[str, str]] = None,
        client_id: Optional[str] = None,
        localised_booking_datetime: Optional[datetime] = None,
        enrichment_details: Optional[dict[str, PostingInstructionEnrichment]] = None,
        
    ):
        """
        This method could be used in Contracts unit tests when mocking Posting Instruction
        data to set output attributes that are needed for `.balances()`, `.value_datetime()`
        and similar methods to work.

        Note that this method never needs to be called in the Contract code itself - just in
        unit tests when mocking Posting Instruction data.

        In the Contracts simulation and real Vault Contracts execution, all Posting Instruction
        objects that the Contract receives from Vault (via hook arguments or vault historical data
        methods) already have the output attributes set.

        Since this method sets output only attributes, and is populated by Contracts simulation
        or real Vault data, no validation is done on the attributes values.
        """
        if insertion_datetime is not None:
            self._insertion_datetime = insertion_datetime
        if value_datetime is not None:
            self._value_datetime = value_datetime
        if booking_datetime is not None:
            self._booking_datetime = booking_datetime
        
        if client_batch_id is not None:
            self._client_batch_id = client_batch_id
        if batch_id is not None:
            self._batch_id = batch_id
        # Make sure the committed_postings are not reset to empty list for the
        # Smart Contract-instructed Custom Instructions that are sent to Supervisor Contracts
        if committed_postings is not None and not self._committed_postings:
            self._committed_postings = committed_postings
        if instruction_id is not None:
            self._instruction_id = instruction_id
        if unique_client_transaction_id is not None:
            self._unique_client_transaction_id = unique_client_transaction_id
        if client_transaction_id is not None:
            self._client_transaction_id = client_transaction_id
        if own_account_id is not None:
            self._own_account_id = own_account_id
        
        if tside is not None:
            self._tside = tside
        if batch_details is not None:
            self._batch_details = batch_details
        if client_id is not None:
            self._client_id = client_id
        self._localised_booking_datetime = localised_booking_datetime
        if is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
            self._enrichment_details = enrichment_details or dict()
        

    @property
    def id(self) -> Optional[str]:
        # Could be None for the proposed PIs
        return self._instruction_id

    @property
    def batch_id(self) -> Optional[str]:
        return self._batch_id

    @property
    def client_batch_id(self) -> Optional[str]:
        return self._client_batch_id

    @property
    def unique_client_transaction_id(self) -> Optional[str]:
        return self._unique_client_transaction_id

    @property
    def insertion_datetime(self) -> Optional[datetime]:
        # Could be None for the proposed PIs
        return self._insertion_datetime

    @property
    def value_datetime(self) -> Optional[datetime]:
        return self._value_datetime

    @property
    def booking_datetime(self) -> Optional[datetime]:
        return self._booking_datetime

    
    @property
    def localised_booking_datetime(self) -> Optional[datetime]:
        return self._localised_booking_datetime

    @property
    def batch_details(self) -> Optional[Dict[str, str]]:
        return self._batch_details or {}

    @property
    def client_id(self) -> Optional[str]:
        return self._client_id

    @property
    def enrichment_details(self) -> dict[str, PostingInstructionEnrichment]:
        if not is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute enrichment_details"
            )
        return self._enrichment_details

    

    def _transform_postings_to_balances(
        self,
        postings: list[Posting],
        tside: Tside,
    ) -> BalanceDefaultDict:
        balance_diffs = derive_balance_diff_from_committed_postings(postings)  # type: ignore

        def _transform_balance_to_versioned_balance(balance_value):
            result = self._balance_class()
            result._adjust(  # noqa: SLF001
                credit=balance_value.credit,
                debit=balance_value.debit,
                tside=tside,
            )
            return result

        def _transform_balance_key(balance_key):
            return self._balance_coordinate_class(
                account_address=balance_key.account_address,
                asset=balance_key.asset,
                denomination=balance_key.denomination,
                phase=balance_key.phase,
            )

        balances = self._balance_default_dict_class(
            # defaults to 0 net, credit and debit
            lambda *_: self._balance_class(),
            {
                _transform_balance_key(balance_key): _transform_balance_to_versioned_balance(
                    balance_value
                )
                for balance_key, balance_value in balance_diffs.items()
            },
        )

        return balances

    def balances(
        self,
        account_id: Optional[str] = None,
        tside: Optional[Tside] = None,
    ) -> BalanceDefaultDict:
        tside = tside or self._tside
        if not tside:
            raise InvalidSmartContractError(
                "A tside must be specified for the balances calculation."
            )

        instruction_type = self.type.value if self.type else "unknown"

        

        if self._committed_postings is None:
            raise InvalidSmartContractError(
                f"The {instruction_type} posting instruction type does not support the balances "
                f"method for the non-historical data as committed_postings are not available."
            )

        return self._balances(account_id=account_id, tside=tside)

    def _balances(
        self,
        tside: Tside,
        account_id: Optional[str] = None,
    ) -> BalanceDefaultDict:
        account_id = account_id or self._own_account_id
        if not account_id:
            raise InvalidSmartContractError(
                "An account_id must be specified for the balances calculation."
            )

        filtered_postings: list[Posting] = []
        for committed_postings in self._committed_postings:  # type: ignore
            if committed_postings.account_id == account_id:
                
                filtered_postings.append(committed_postings)

        return self._transform_postings_to_balances(postings=filtered_postings, tside=tside)

    

    @classmethod
    def _public_methods(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_methods = [
            types_utils.MethodSpec(
                name="balances",
                docstring="""
                    Returns the net balance changes to the Account caused by this Posting Instruction.
                """,
                args=[
                    types_utils.ValueSpec(
                        name="account_id",
                        type="Optional[str]",
                        docstring="""
                            The ID of an Account for which the balance changes should be returned.
                            Does not need to be provided for historical Posting Instructions
                            returned via `vault` methods or new Posting Instructions that the hook
                            receives via arguments in `pre_posting_hook` and `post_posting_hook`.
                            In these cases, the argument defaults to the `account_id` of the Smart Contract
                            or the ID of the supervisee Account in Supervisor Contract.
                            Only required when creating a Posting Instruction within a Contract, as
                            these might contain instructions for multiple accounts. This also
                            applies for PostingInstructionDirectives accessible in a Supervisor
                            Contract via `get_hook_result()` method.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="tside",
                        type="Optional[Tside]",
                        docstring="""
                            The T-side of an Account which is used to calculate net balances.
                            It is not required for PostingInstructionDirectives accessible in a Supervisor
                            Contract via the `get_hook_result()` method and defaults to the `tside`
                            of the supervisee Account. It does not need to be provided for historical
                            Posting Instructions returned via `vault` methods or new Posting Instructions
                            that the hook receives via arguments in `pre_posting_hook` and `post_posting_hook`.
                            In these cases, the argument defaults to the `tside` of the Smart Contract
                            or the `tside` of the supervisee Account in Supervisor Contract.
                            Only required when creating a Posting Instruction within a Contract, as
                            these might contain instructions for multiple accounts.
                        """,
                    ),
                ],
                return_value=types_utils.ReturnValueSpec(
                    type="BalanceDefaultDict",
                    docstring=f"""
                        The default balance dictionary where the key is the
                        [BalanceCoordinate]({_common_docs_path}classes/#BalanceCoordinate) and the value is
                        a [Balance]({_common_docs_path}classes/#Balance) object which contains the debit,
                        credit and net balance changes for the Account. Accessing a non-existent key will
                        return a `Balance` object with zero debit, credit, and net balance changes.
                    """,
                ),
            ),
        ]
        
        return public_methods

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        return [
            types_utils.ValueSpec(
                name="instruction_details",
                type="Optional[Dict[str, str]]",
                docstring="""
                    An optional mapping containing instruction-level metadata.
                """,
            ),
            types_utils.ValueSpec(
                name="transaction_code",
                type="Optional[TransactionCode]",
                docstring="""
                    ISO20022 Bank Transaction Code field; a set of properties to identify the
                    underlying transaction.
                """,
            ),
            types_utils.ValueSpec(
                name="override_all_restrictions",
                type="bool",
                docstring="""
                    Specifies whether to ignore all restrictions.
                """,
            ),
        ]

    @classmethod
    def _output_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        output_attributes = [
            types_utils.ValueSpec(
                name="type",
                type="PostingInstructionType",
                docstring="""
                    The Posting Instruction type, such as CustomInstruction or Transfer.
                """,
            ),
            types_utils.ValueSpec(
                name="id",
                type="Optional[str]",
                docstring="""
                    Uniquely identifies the Posting Instruction in Vault.
                """,
            ),
            types_utils.ValueSpec(
                name="client_batch_id",
                type="str",
                docstring="""
                    The ID which allows related Posting Instructions (for example,
                    interest accrual payments) to be associated with each other.
                """,
            ),
            types_utils.ValueSpec(
                name="unique_client_transaction_id",
                type="str",
                docstring="""
                    The globally unique ID of the ClientTransaction that this Posting
                    Instruction is a part of. This value is not deterministic and therefore is
                    not guaranteed to be consistent between different Contract executions for
                    the same ClientTransaction.
                    A Posting Instruction may be viewed as a change of state to a ClientTransaction.
                    Note: This value will be used as a key in the map returned in the
                    [get_client_transactions](/reference/contracts/contracts_api_4xx/smart_contracts_api_reference4xx/vault/#methods-get_client_transactions)
                    Vault method.
                """,
            ),
            types_utils.ValueSpec(
                name="insertion_datetime",
                type="Optional[datetime]",
                docstring="""
                    The datetime indicating when the Posting Instruction was inserted into the
                    posting ledger (unless migrated into Vault Core from another core banking
                    system, when this represents the time at which this Posting Instruction
                    batch was inserted into the source core banking system). This field has the
                    same value as the `source_insertion_timestamp` of the Posting Instruction batch,
                    and the same value as the `insertion_timestamp` (unless migrated from another
                    core banking system). See [source_insertion_timestamp](/api/core_api/#Posting_instruction_batches-PostingInstructionBatch).
                    It is a timezone-aware UTC datetime using the ZoneInfo class.
                """,
            ),
            types_utils.ValueSpec(
                name="value_datetime",
                type="Optional[datetime]",
                docstring="""
                    An optional datetime that specifies the time at which the Posting Instruction
                    will affect balances. Only use for backdated and future-dated instructions. Set
                    between 1970-01-01T00:00:00Z and the current time + 90 days, inclusive.
                    It is a timezone-aware UTC datetime using the ZoneInfo class.
                """,
            ),
            types_utils.ValueSpec(
                name="batch_id",
                type="Optional[str]",
                docstring="""
                    The ID of the batch of Posting Instructions that get atomically
                    inserted into the ledger.
                """,
            ),
            types_utils.ValueSpec(
                name="batch_details",
                type="Optional[Dict[str, str]]",
                docstring="""
                    An optional mapping containing batch-level metadata attached to the list of
                    Posting Instructions that get atomically accepted or rejected.
                """,
            ),
            types_utils.ValueSpec(
                name="client_id",
                type="str",
                docstring="""
                    Uniquely identifies a client of the Posting API. Used to publish responses
                    to the specified Kafka response topic. Together with the
                    `client_transaction_id`, this forms a `unique_client_transaction_id`,
                    which is used when accessing `ClientTransaction` objects in the Contract code.
                """,
            ),
            types_utils.ValueSpec(
                name="booking_datetime",
                type="Optional[datetime]",
                docstring="""
                    An optional datetime that specifies that time at which the Posting Instruction
                    will be booked. Only use for back-booked or future-booked instructions. Set between
                    1970-01-01T00:00:00Z and the current time + 90 days, inclusive.
                    It is a timezone-aware UTC datetime using the ZoneInfo class.
                """,
            ),
            types_utils.ValueSpec(
                name="localised_booking_datetime",
                type="Optional[datetime]",
                docstring="""
                    The localised datetime indicating when the Posting Instruction was booked.
                """,
            ),
        ]

        
        if is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
            output_attributes.extend(
                [
                    types_utils.ValueSpec(
                        name="enrichment_details",
                        type="Optional[dict[str, PostingInstructionEnrichment]]",
                        docstring="""
                            The enrichment added to this instruction in pre-posting, if it was
                            enriched.
                        """,
                    ),
                ]
            )
        
        return output_attributes

    @classmethod
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        public_attributes = cls._constructor_args(language_code=language_code)
        public_attributes.extend(cls._output_attributes(language_code=language_code))
        return public_attributes


class Authorisation(PostingInstructionBase):
    def __init__(
        self,
        *,
        client_transaction_id: str,
        amount: Union[Decimal, int],
        denomination: str,
        target_account_id: str,
        internal_account_id: str,
        internal_account_processing_label: Optional[str] = None,
        target_account_address: Optional[str] = None,
        asset: Optional[str] = None,
        
        advice: Optional[bool] = False,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.client_transaction_id = client_transaction_id
        self.amount = amount
        self.denomination = denomination
        self.target_account_id = target_account_id
        self.internal_account_id = internal_account_id
        self.internal_account_processing_label = internal_account_processing_label
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            self.target_account_address = target_account_address
            self.asset = asset
        
        self.advice = advice
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="client_transaction_id",
                    type="str",
                    docstring="""
                        The ID of the ClientTransaction that this Posting Instruction is a
                        part of. A Posting Instruction may be viewed as a change of state to a
                        ClientTransaction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The amount moved by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the amount moved by the Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="target_account_id",
                    type="str",
                    docstring="""
                        The Account ID targeted by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_id",
                    type="str",
                    docstring="""
                        The Internal Account ID targeted by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_processing_label",
                    type="Optional[str]",
                    docstring="""
                        A label for a Posting Instruction to use to reference an Internal
                        Account without a need to identify the Processing Group it belongs to.
                        Use `internal_account_processing_label` in place of the
                        `internal_account_id` in order to instruct Posting Instructions
                        for an Internal Account with a matching processing label
                        belonging to the same Processing Group as the target Account.

                        For fetched Posting Instructions, if `internal_account_processing_label`
                        is set, then `internal_account_id` is already resolved by Vault
                        and set on the instruction.
                    """,
                ),
            ]
        )
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            constructor_args.extend(
                [
                    types_utils.ValueSpec(
                        name="target_account_address",
                        type="str",
                        docstring="""
                            The address of the Account that is targeted by the Posting Instruction.
                            It is equivalent to the `account_address` in the `Posting` type.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="asset",
                        type="str",
                        docstring="""
                            The asset type targeted by the Posting Instruction.
                        """,
                    ),
                ]
            )
        
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="advice",
                    type="Optional[bool]",
                    docstring="""
                        This indicates that the Contract should skip
                        balance checks for this Posting Instruction. For the advice flag to be
                        set in the Posting Instruction object, it must be supported in the
                        specific type Posting Instruction object in the Core API. This
                        defaults to false if supported by the PostingInstructionType but not
                        supplied.
                    """,
                ),
            ]
        )
        return constructor_args


class OutboundAuthorisation(Authorisation):
    type = PostingInstructionType.OUTBOUND_AUTHORISATION

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        public_methods = super()._public_methods(language_code)
        class_docstring = """
        [Outbound authorisation](/reference/postings#outbound_authorisation_chainable)
        is a chainable Posting Instruction that creates an outgoing funds hold (ring-fence the
        funds) on the target Account
        """
        
        class_docstring += cls._class_docs_note

        return types_utils.ClassSpec(
            name="OutboundAuthorisation",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new OutboundAuthorisation
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )


class InboundAuthorisation(Authorisation):
    type = PostingInstructionType.INBOUND_AUTHORISATION

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_methods = super()._public_methods(language_code)
        class_docstring = """
        [Inbound authorisation](/reference/postings#inbound_authorisation_chainable)
        is a chainable Posting Instruction that authorises incoming funds into the target
        Account
        """
        

        return types_utils.ClassSpec(
            name="InboundAuthorisation",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new InboundAuthorisation
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )


class CustomInstruction(PostingInstructionBase):
    type = PostingInstructionType.CUSTOM_INSTRUCTION

    def __init__(
        self,
        *,
        postings: List[Posting],
        value_datetime: Optional[datetime] = None,
        booking_datetime: Optional[datetime] = None,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.postings = postings
        self.value_datetime = value_datetime
        self.booking_datetime = booking_datetime

        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )
        # This allows in-flight balances to work for new CustomInstruction directives
        # that are not yet committed.
        self._set_output_attributes(
            committed_postings=postings,
            value_datetime=value_datetime,
            booking_datetime=booking_datetime,
        )

    @property
    def value_datetime(self) -> Optional[datetime]:
        return self._value_datetime

    @value_datetime.setter
    def value_datetime(self, value):
        self._value_datetime = value

    @property
    def booking_datetime(self) -> Optional[datetime]:
        return self._booking_datetime

    @booking_datetime.setter
    def booking_datetime(self, value):
        self._booking_datetime = value

    def _validate_attributes(self):
        super()._validate_attributes()
        iterator = types_utils.get_iterator(
            self.postings, "Posting", name="CustomInstruction.postings", check_empty=True
        )

        

        for index, posting in enumerate(iterator):
            types_utils.validate_type(
                posting,
                Posting,
                hint="Posting",
                prefix=f"CustomInstruction.postings[{index}]",
            )

            

        

        types_utils.validate_type(self.value_datetime, datetime, is_optional=True)
        if self.value_datetime is not None:
            timezone_utils.validate_timezone_is_utc(
                self.value_datetime,
                "value_datetime",
                self.type.value if self.type else "posting instruction",
            )

        types_utils.validate_type(self.booking_datetime, datetime, is_optional=True)
        if self.booking_datetime is not None:
            timezone_utils.validate_timezone_is_utc(
                self.booking_datetime,
                "booking_datetime",
                self.type.value if self.type else "posting instruction",
            )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_methods = super()._public_methods(language_code)
        class_docstring = """
        [Custom Instruction](/reference/postings#custom_instruction) is a type of Posting
        Instruction that specifies a list of credits and debits to be written to the ledger.
        """
        class_docstring += cls._class_docs_note

        return types_utils.ClassSpec(
            name="CustomInstruction",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new CustomInstruction.",
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )

    def _validate_postings_and_zero_net_sum(self):
        if len(self.postings) > 64:
            raise InvalidSmartContractError(
                f"Too many postings submitted in the {self.type.value}. "
                f"Number submitted: {len(self.postings)}. Limit: 64.",
            )

        balance_dict = {}
        for p in self.postings:
            balance_key = tuple([p.asset, p.denomination, p.phase])
            if balance_key not in balance_dict.keys():
                balance_dict[balance_key] = {"credit": 0, "debit": 0}
            if p.credit:
                balance_dict[balance_key]["credit"] += p.amount
            else:
                balance_dict[balance_key]["debit"] += p.amount

        for balance_key, balance_value in balance_dict.items():
            if balance_value["credit"] != balance_value["debit"]:
                net_sum = abs(balance_value["credit"] - balance_value["debit"])
                raise InvalidSmartContractError(
                    f"Net of balance coordinate {balance_key} in the "
                    f"CustomInstruction: {net_sum}, Expected: 0.",
                )

    def _validate_postings_internal_account_id_and_processing_label(self):
        for p in self.postings:
            if p.account_id and p.internal_account_processing_label:
                raise InvalidSmartContractError(
                    f"Either account_id or internal_account_processing_label must be provided, not both. "
                    f"Got account_id '{p.account_id}' and "
                    f"internal_account_processing_label '{p.internal_account_processing_label}'"
                )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="postings",
                    type="List[Posting]",
                    docstring="""
                        A list of Postings (credits and debits).
                        When instructed via a `PostingInstructionDirective`, each
                        `CustomInstruction` can have up to 64 `Posting`s and must have a zero net
                        sum. The zero net sum means that for each unique (asset, denomination,
                        phase) combination, the sum of `Posting` credits must equal the sum of
                        `Posting` debits.
                    """,
                ),
                types_utils.ValueSpec(
                    name="value_datetime",
                    type="Optional[datetime]",
                    docstring="""
                        An optional datetime that specifies the time at which the Posting Instruction
                        will affect balances. Only use for backdated and future-dated instructions. Set
                        between 1970-01-01T00:00:00Z and the current time + 90 days, inclusive.
                    """,
                ),
                types_utils.ValueSpec(
                    name="booking_datetime",
                    type="Optional[datetime]",
                    docstring="""
                        An optional datetime that specifies that time at which the Posting Instruction
                        will be booked. Only use for back-booked or future-booked instructions. Set between
                        1970-01-01T00:00:00Z and the current time + 90 days, inclusive.
                    """,
                ),
            ]
        )
        return constructor_args


class AdjustmentAmount(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        amount: Optional[Union[Decimal, int]] = None,
        replacement_amount: Optional[Union[Decimal, int]] = None,
        _from_proto: bool = False,
    ):
        self.amount = amount
        self.replacement_amount = replacement_amount
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        if (self.amount is None and self.replacement_amount is None) or (
            self.amount and self.replacement_amount
        ):
            raise InvalidSmartContractError(
                "Either amount or replacement amount argument must be set, not both."
            )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="AdjustmentAmount",
            docstring="""
                Used in the AuthorisationAdjustment Posting Instructions to adjust an
                authorised amount of a ClientTransaction.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new AdjustmentAmount",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        return [
            types_utils.ValueSpec(
                name="amount",
                type="Optional[Union[Decimal, int]]",
                docstring="""
                    Signed delta amount.
                """,
            ),
            types_utils.ValueSpec(
                name="replacement_amount",
                type="Optional[Union[Decimal, int]]",
                docstring="""
                    A new amount to replace an existing authorised amount.
                """,
            ),
        ]

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.amount == other.amount
            and self.replacement_amount == other.replacement_amount
        )


class AuthorisationAdjustment(PostingInstructionBase):
    _authorised_amount: Optional[Union[Decimal, int]] = None
    _delta_amount: Optional[Union[Decimal, int]] = None
    _denomination: Optional[str] = None
    _target_account_id: Optional[str] = None
    _internal_account_id: Optional[str] = None
    _internal_account_processing_label: Optional[str] = None
    _target_account_address: Optional[str] = None
    _asset: Optional[str] = None
    _target_sub_account_id: Optional[str] = None
    type = PostingInstructionType.AUTHORISATION_ADJUSTMENT

    def __init__(
        self,
        *,
        client_transaction_id: str,
        adjustment_amount: AdjustmentAmount,
        advice: Optional[bool] = False,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.client_transaction_id = client_transaction_id
        self.adjustment_amount = adjustment_amount
        self.advice = advice
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    def _validate_attributes(self):
        super()._validate_attributes()
        if self.adjustment_amount is None:
            raise exceptions.StrongTypingError(
                f"{self.type.value} 'adjustment_amount' must be populated",
            )

        types_utils.validate_type(
            self.adjustment_amount,
            AdjustmentAmount,
            hint="AdjustmentAmount",
            prefix="AuthorisationAdjustment.adjustment_amount",
        )

    def _set_output_attributes(
        self,
        insertion_datetime: Optional[datetime] = None,
        value_datetime: Optional[datetime] = None,
        booking_datetime: Optional[datetime] = None,
        
        client_batch_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        committed_postings: Optional[List[Posting]] = None,
        instruction_id: Optional[str] = None,
        unique_client_transaction_id: Optional[str] = None,
        client_transaction_id: Optional[str] = None,
        own_account_id: Optional[str] = None,
        
        tside: Optional[Tside] = None,
        batch_details: Optional[Dict[str, str]] = None,
        client_id: Optional[str] = None,
        localised_booking_datetime: Optional[datetime] = None,
        enrichment_details: Optional[dict[str, PostingInstructionEnrichment]] = None,
        
        # Additional class attributes
        authorised_amount: Optional[Union[Decimal, int]] = None,
        delta_amount: Optional[Union[Decimal, int]] = None,
        denomination: Optional[str] = None,
        target_account_id: Optional[str] = None,
        internal_account_id: Optional[str] = None,
        internal_account_processing_label: Optional[str] = None,
        target_account_address: Optional[str] = None,
        asset: Optional[str] = None,
        
    ):
        """
        This method could be used in Contracts unit tests when mocking Posting Instruction
        data to set output attributes that are needed for `.balances()`, `.value_datetime`
        and similar methods to work.
        Note that this method never needs to be called in the Contract code itself - just in
        unit tests when mocking Posting Instruction data.
        In the Contracts simulation and real Vault Contracts execution, all Posting Instruction
        objects that the Contract receives from Vault (via hook arguments or vault historical data
        methods) already have the output attributes set.
        """
        super()._set_output_attributes(
            insertion_datetime=insertion_datetime,
            value_datetime=value_datetime,
            booking_datetime=booking_datetime,
            
            client_batch_id=client_batch_id,
            batch_id=batch_id,
            committed_postings=committed_postings,
            instruction_id=instruction_id,
            unique_client_transaction_id=unique_client_transaction_id,
            client_transaction_id=client_transaction_id,
            own_account_id=own_account_id,
            
            tside=tside,
            batch_details=batch_details,
            client_id=client_id,
            localised_booking_datetime=localised_booking_datetime,
            enrichment_details=enrichment_details,
            
        )
        if authorised_amount is not None:
            self._authorised_amount = authorised_amount
        if delta_amount is not None:
            self._delta_amount = delta_amount
        if denomination is not None:
            self._denomination = denomination
        if target_account_id is not None:
            self._target_account_id = target_account_id
        if internal_account_id is not None:
            self._internal_account_id = internal_account_id
        if internal_account_processing_label is not None:
            self._internal_account_processing_label = internal_account_processing_label
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            if target_account_address is not None:
                self._target_account_address = target_account_address
            if asset is not None:
                self._asset = asset
        

    @property
    def authorised_amount(self) -> Optional[Union[Decimal, int]]:
        return self._authorised_amount

    @property
    def delta_amount(self) -> Optional[Union[Decimal, int]]:
        return self._delta_amount

    @property
    def denomination(self) -> Optional[str]:
        return self._denomination

    @property
    def target_account_id(self) -> Optional[str]:
        return self._target_account_id

    @property
    def internal_account_id(self) -> Optional[str]:
        return self._internal_account_id

    @property
    def internal_account_processing_label(self) -> Optional[str]:
        return self._internal_account_processing_label

    @property
    def target_account_address(self) -> Optional[str]:
        return self._target_account_address

    @property
    def asset(self) -> Optional[str]:
        return self._asset

    @property
    def target_sub_account_id(self) -> Optional[str]:
        return self._target_sub_account_id

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        class_docstring = """
        [Authorisation adjustment](/reference/postings#authorisation_adjustment_chainable) is a
        chainable Posting Instruction that can be used to change the amount that is ring-fenced
        by a [ClientTransaction](#ClientTransaction). The Client Transaction being adjusted is
        identified by the `client_transaction_id` attribute.
        """
        
        class_docstring += cls._class_docs_note

        return types_utils.ClassSpec(
            name="AuthorisationAdjustment",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new AuthorisationAdjustment",
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=cls._public_methods(language_code=language_code),
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="client_transaction_id",
                    type="str",
                    docstring="""
                        The ID of the ClientTransaction that this Posting Instruction is a
                        part of. A Posting Instruction may be viewed as a change of state to a
                        ClientTransaction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="adjustment_amount",
                    type="AdjustmentAmount",
                    docstring="""
                        The amount of the AuthorisationAdjustment, which can be specified as a delta
                        (the difference between previous amount and the new amount) or as a new
                        total authorised amount.
                    """,
                ),
                types_utils.ValueSpec(
                    name="advice",
                    type="Optional[bool]",
                    docstring="""
                        This indicates that the Contract should skip
                        balance checks for this Posting Instruction. For the advice flag to be
                        set in the Posting Instruction object, it must be supported in the
                        specific type Posting Instruction object in the Core API. This
                        defaults to false if supported by the PostingInstructionType but not
                        supplied.
                    """,
                ),
            ]
        )
        return constructor_args

    @classmethod
    def _output_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        output_attributes = super()._output_attributes(language_code=language_code)
        output_attributes.extend(
            [
                types_utils.ValueSpec(
                    name="authorised_amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The total amount authorised for this ClientTransaction after
                        this instruction has been accepted. Note that this is output only
                        information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="delta_amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The change that this accepted instruction has made to the amount authorised
                        for this ClientTransaction. Note that this is output only information,
                        which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the Posting Instruction. Note that this is output only
                        information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="target_account_id",
                    type="str",
                    docstring="""
                        The Account ID targeted by this Posting Instruction. Note that this is
                        output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_id",
                    type="str",
                    docstring="""
                        The Internal Account ID targeted by this posted instruction. Note that this
                        is output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_processing_label",
                    type="Optional[str]",
                    docstring="""
                        A label for a Posting Instruction to use to reference an Internal
                        Account without a need to identify the Processing Group it belongs to.
                        Use `internal_account_processing_label` in place of the
                        `internal_account_id` in order to instruct Posting Instructions
                        for an Internal Account with a matching processing label
                        belonging to the same Processing Group as the target Account.

                        For fetched Posting Instructions, if `internal_account_processing_label`
                        is set, then `internal_account_id` is already resolved by Vault
                        and set on the instruction.

                        Note that this is output only information,
                        which is derived by the ledger.
                    """,
                ),
            ]
        )
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            output_attributes.extend(
                [
                    types_utils.ValueSpec(
                        name="target_account_address",
                        type="str",
                        docstring="""
                            The address of the Account that is targeted by the Posting Instruction.
                            It is equivalent to the `account_address` in the `Posting` type.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="asset",
                        type="str",
                        docstring="""
                            The asset type targeted by the Posting Instruction.
                        """,
                    ),
                ]
            )
        
        return output_attributes


class Settlement(PostingInstructionBase):
    _denomination: Optional[str] = None
    _target_account_id: Optional[str] = None
    _internal_account_id: Optional[str] = None
    _internal_account_processing_label: Optional[str] = None
    _target_account_address: Optional[str] = None
    _asset: Optional[str] = None
    _target_sub_account_id: Optional[str] = None
    type = PostingInstructionType.SETTLEMENT

    def __init__(
        self,
        *,
        client_transaction_id: str,
        amount: Optional[Union[Decimal, int]] = None,
        final: Optional[bool] = False,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.client_transaction_id = client_transaction_id
        self.amount = amount
        self.final = final
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    def _set_output_attributes(
        self,
        insertion_datetime: Optional[datetime] = None,
        value_datetime: Optional[datetime] = None,
        booking_datetime: Optional[datetime] = None,
        
        client_batch_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        committed_postings: Optional[List[Posting]] = None,
        instruction_id: Optional[str] = None,
        unique_client_transaction_id: Optional[str] = None,
        client_transaction_id: Optional[str] = None,
        own_account_id: Optional[str] = None,
        
        tside: Optional[Tside] = None,
        batch_details: Optional[Dict[str, str]] = None,
        client_id: Optional[str] = None,
        localised_booking_datetime: Optional[datetime] = None,
        enrichment_details: Optional[dict[str, PostingInstructionEnrichment]] = None,
        
        # Additional class attributes
        denomination: Optional[str] = None,
        target_account_id: Optional[str] = None,
        internal_account_id: Optional[str] = None,
        internal_account_processing_label: Optional[str] = None,
        target_account_address: Optional[str] = None,
        asset: Optional[str] = None,
        
    ):
        """
        This method could be used in Contracts unit tests when mocking Posting Instruction
        data to set output attributes that are needed for `.balances()`, `.value_datetime`
        and similar methods to work.
        Note that this method never needs to be called in the Contract code itself - just in
        unit tests when mocking Posting Instruction data.
        In the Contracts simulation and real Vault Contracts execution, all Posting Instruction
        objects that the Contract receives from Vault (via hook arguments or vault historical data
        methods) already have the output attributes set.
        """
        super()._set_output_attributes(
            insertion_datetime=insertion_datetime,
            value_datetime=value_datetime,
            booking_datetime=booking_datetime,
            
            client_batch_id=client_batch_id,
            batch_id=batch_id,
            committed_postings=committed_postings,
            instruction_id=instruction_id,
            unique_client_transaction_id=unique_client_transaction_id,
            client_transaction_id=client_transaction_id,
            own_account_id=own_account_id,
            
            tside=tside,
            batch_details=batch_details,
            client_id=client_id,
            localised_booking_datetime=localised_booking_datetime,
            enrichment_details=enrichment_details,
            
        )
        if denomination is not None:
            self._denomination = denomination
        if target_account_id is not None:
            self._target_account_id = target_account_id
        if internal_account_id is not None:
            self._internal_account_id = internal_account_id
        if internal_account_processing_label is not None:
            self._internal_account_processing_label = internal_account_processing_label
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            if target_account_address is not None:
                self._target_account_address = target_account_address
            if asset is not None:
                self._asset = asset
        

    @property
    def denomination(self) -> Optional[str]:
        return self._denomination

    @property
    def target_account_id(self) -> Optional[str]:
        return self._target_account_id

    @property
    def internal_account_id(self) -> Optional[str]:
        return self._internal_account_id

    @property
    def internal_account_processing_label(self) -> Optional[str]:
        return self._internal_account_processing_label

    @property
    def target_account_address(self) -> Optional[str]:
        return self._target_account_address

    @property
    def asset(self) -> Optional[str]:
        return self._asset

    @property
    def target_sub_account_id(self) -> Optional[str]:
        return self._target_sub_account_id

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        class_docstring = """
        [Settlement](/reference/postings#settlement_chainable) is a chainable Posting Instruction
        that clears funds that have been previously authorised in a
        [ClientTransaction](#ClientTransaction). The Client Transaction being cleared is identified
        by the `client_transaction_id` attribute.
        """
        
        class_docstring += cls._class_docs_note

        return types_utils.ClassSpec(
            name="Settlement",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new Settlement",
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=cls._public_methods(language_code=language_code),
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="client_transaction_id",
                    type="str",
                    docstring="""
                        The ID of the ClientTransaction that this Posting Instruction is a
                        part of. A Posting Instruction may be viewed as a change of state to a
                        ClientTransaction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="amount",
                    type="Optional[Union[Decimal, int]]",
                    docstring="""
                        The amount to be cleared for a ClientTransaction. Defaults to the total
                        amount authorised for the ClientTransaction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="final",
                    type="Optional[bool]",
                    docstring="""
                        If set to true, any remaining amount authorised for the ClientTransaction
                        will be released. No Posting Instructions may mutate the ClientTransaction
                        once a final Settlement has been accepted.
                    """,
                ),
            ]
        )
        return constructor_args

    @classmethod
    def _output_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        output_attributes = super()._output_attributes(language_code=language_code)
        output_attributes.extend(
            [
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the Posting Instruction. Note that this is output only
                        information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="target_account_id",
                    type="str",
                    docstring="""
                        The Account ID targeted by this Posting Instruction. Note that this is
                        output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_id",
                    type="str",
                    docstring="""
                        The Internal Account ID targeted by this posted instruction. Note that this
                        is output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_processing_label",
                    type="Optional[str]",
                    docstring="""
                        A label for a Posting Instruction to use to reference an Internal
                        Account without a need to identify the Processing Group it belongs to.
                        Use `internal_account_processing_label` in place of the
                        `internal_account_id` in order to instruct Posting Instructions
                        for an Internal Account with a matching processing label
                        belonging to the same Processing Group as the target Account.

                        For fetched Posting Instructions, if `internal_account_processing_label`
                        is set, then `internal_account_id` is already resolved by Vault
                        and set on the instruction.

                        Note that this is output only information,
                        which is derived by the ledger.
                    """,
                ),
            ]
        )
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            output_attributes.extend(
                [
                    types_utils.ValueSpec(
                        name="target_account_address",
                        type="str",
                        docstring="""
                            The address of the Account that is targeted by the Posting Instruction.
                            It is equivalent to the `account_address` in the `Posting` type.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="asset",
                        type="str",
                        docstring="""
                            The asset type targeted by the Posting Instruction.
                        """,
                    ),
                ]
            )
        
        return output_attributes


class Release(PostingInstructionBase):
    _amount: Optional[Union[Decimal, int]] = None
    _denomination: Optional[str] = None
    _target_account_id: Optional[str] = None
    _internal_account_id: Optional[str] = None
    _internal_account_processing_label: Optional[str] = None
    _target_account_address: Optional[str] = None
    _asset: Optional[str] = None
    _target_sub_account_id: Optional[str] = None
    type = PostingInstructionType.RELEASE

    def __init__(
        self,
        *,
        client_transaction_id: str,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.client_transaction_id = client_transaction_id
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    def _set_output_attributes(
        self,
        insertion_datetime: Optional[datetime] = None,
        value_datetime: Optional[datetime] = None,
        booking_datetime: Optional[datetime] = None,
        
        client_batch_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        committed_postings: Optional[List[Posting]] = None,
        instruction_id: Optional[str] = None,
        unique_client_transaction_id: Optional[str] = None,
        client_transaction_id: Optional[str] = None,
        own_account_id: Optional[str] = None,
        
        tside: Optional[Tside] = None,
        batch_details: Optional[Dict[str, str]] = None,
        client_id: Optional[str] = None,
        localised_booking_datetime: Optional[datetime] = None,
        enrichment_details: Optional[dict[str, PostingInstructionEnrichment]] = None,
        
        # Additional class attributes
        amount: Optional[Union[Decimal, int]] = None,
        denomination: Optional[str] = None,
        target_account_id: Optional[str] = None,
        internal_account_id: Optional[str] = None,
        internal_account_processing_label: Optional[str] = None,
        target_account_address: Optional[str] = None,
        asset: Optional[str] = None,
        
    ):
        """
        This method could be used in Contracts unit tests when mocking Posting Instruction
        data to set output attributes that are needed for `.balances()`, `.value_datetime`
        and similar methods to work.
        Note that this method never needs to be called in the Contract code itself - just in
        unit tests when mocking Posting Instruction data.
        In the Contracts simulation and real Vault Contracts execution, all Posting Instruction
        objects that the Contract receives from Vault (via hook arguments or vault historical data
        methods) already have the output attributes set.
        """
        super()._set_output_attributes(
            insertion_datetime=insertion_datetime,
            value_datetime=value_datetime,
            booking_datetime=booking_datetime,
            
            client_batch_id=client_batch_id,
            batch_id=batch_id,
            committed_postings=committed_postings,
            instruction_id=instruction_id,
            unique_client_transaction_id=unique_client_transaction_id,
            client_transaction_id=client_transaction_id,
            own_account_id=own_account_id,
            
            tside=tside,
            batch_details=batch_details,
            client_id=client_id,
            localised_booking_datetime=localised_booking_datetime,
            enrichment_details=enrichment_details,
            
        )
        if amount is not None:
            self._amount = amount
        if denomination is not None:
            self._denomination = denomination
        if target_account_id is not None:
            self._target_account_id = target_account_id
        if internal_account_id is not None:
            self._internal_account_id = internal_account_id
        if internal_account_processing_label is not None:
            self._internal_account_processing_label = internal_account_processing_label
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            if target_account_address is not None:
                self._target_account_address = target_account_address
            if asset is not None:
                self._asset = asset
        

    @property
    def amount(self) -> Optional[Union[Decimal, int]]:
        return self._amount

    @property
    def denomination(self) -> Optional[str]:
        return self._denomination

    @property
    def target_account_id(self) -> Optional[str]:
        return self._target_account_id

    @property
    def internal_account_id(self) -> Optional[str]:
        return self._internal_account_id

    @property
    def internal_account_processing_label(self) -> Optional[str]:
        return self._internal_account_processing_label

    @property
    def target_account_address(self) -> Optional[str]:
        return self._target_account_address

    @property
    def asset(self) -> Optional[str]:
        return self._asset

    @property
    def target_sub_account_id(self) -> Optional[str]:
        return self._target_sub_account_id

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        class_docstring = """
        [Release](/reference/postings#release_chainable) is a chainable Posting Instruction that
        removes an authorisation hold from a ClientTransaction. The ClientTransaction being
        released is identified by the client_transaction_id attribute.
        """
        
        class_docstring += cls._class_docs_note

        return types_utils.ClassSpec(
            name="Release",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new Release
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=cls._public_methods(language_code=language_code),
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="client_transaction_id",
                    type="str",
                    docstring="""
                        The ID of the ClientTransaction that this Posting Instruction is a
                        part of. A Posting Instruction may be viewed as a change of state to a
                        ClientTransaction.
                    """,
                ),
            ]
        )
        return constructor_args

    @classmethod
    def _output_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        output_attributes = super()._output_attributes(language_code=language_code)
        output_attributes.extend(
            [
                types_utils.ValueSpec(
                    name="amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The amount released. Note that this is output only information, which is
                        calculated by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the Posting Instruction. Note that this is output only
                        information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="target_account_id",
                    type="str",
                    docstring="""
                        The Account ID targeted by this Posting Instruction. Note that this is
                        output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_id",
                    type="str",
                    docstring="""
                        The Internal Account ID targeted by this posted instruction. Note that this
                        is output only information, which is derived by the ledger.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_processing_label",
                    type="Optional[str]",
                    docstring="""
                        A label for a Posting Instruction to use to reference an Internal
                        Account without a need to identify the Processing Group it belongs to.
                        Use `internal_account_processing_label` in place of the
                        `internal_account_id` in order to instruct Posting Instructions
                        for an Internal Account with a matching processing label
                        belonging to the same Processing Group as the target Account.

                        For fetched Posting Instructions, if `internal_account_processing_label`
                        is set, then `internal_account_id` is already resolved by Vault
                        and set on the instruction.

                        Note that this is output only information,
                        which is derived by the ledger.
                    """,
                ),
            ]
        )
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            output_attributes.extend(
                [
                    types_utils.ValueSpec(
                        name="target_account_address",
                        type="str",
                        docstring="""
                            The address of the Account that is targeted by the Posting Instruction.
                            It is equivalent to the `account_address` in the `Posting` type.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="asset",
                        type="str",
                        docstring="""
                            The asset type targeted by the Posting Instruction.
                        """,
                    ),
                ]
            )
        
        return output_attributes


class HardSettlement(PostingInstructionBase):
    def __init__(
        self,
        *,
        amount: Union[Decimal, int],
        denomination: str,
        target_account_id: str,
        internal_account_id: str,
        internal_account_processing_label: Optional[str] = None,
        target_account_address: Optional[str] = None,
        asset: Optional[str] = None,
        
        advice: Optional[bool] = False,
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.amount = amount
        self.denomination = denomination
        self.target_account_id = target_account_id
        self.internal_account_id = internal_account_id
        self.internal_account_processing_label = internal_account_processing_label
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            self.target_account_address = target_account_address
            self.asset = asset
        
        self.advice = advice
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The amount moved by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the amount moved by the Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="target_account_id",
                    type="str",
                    docstring="""
                        The Account ID targeted by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_id",
                    type="str",
                    docstring="""
                        The Internal Account ID targeted by this posted instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="internal_account_processing_label",
                    type="Optional[str]",
                    docstring="""
                        A label for a Posting Instruction to use to reference an Internal
                        Account without a need to identify the Processing Group it belongs to.
                        Use `internal_account_processing_label` in place of the
                        `internal_account_id` in order to instruct Posting Instructions
                        for an Internal Account with a matching processing label
                        belonging to the same Processing Group as the target Account.

                        For fetched Posting Instructions, if `internal_account_processing_label`
                        is set, then `internal_account_id` is already resolved by Vault
                        and set on the instruction.
                    """,
                ),
            ]
        )
        if is_fflag_enabled(POSTINGS_TARGET_ADDRESS):
            constructor_args.extend(
                [
                    types_utils.ValueSpec(
                        name="target_account_address",
                        type="str",
                        docstring="""
                            The address of the Account that is targeted by the Posting Instruction.
                            It is equivalent to the `account_address` in the `Posting` type.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="asset",
                        type="str",
                        docstring="""
                            The asset type targeted by the Posting Instruction.
                        """,
                    ),
                ]
            )
        
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="advice",
                    type="Optional[bool]",
                    docstring="""
                        This indicates that the Contract should skip
                        balance checks for this Posting Instruction. For the advice flag to be
                        set in the Posting Instruction object, it must be supported in the
                        specific type Posting Instruction object in the Core API. This
                        defaults to false if supported by the PostingInstructionType but not
                        supplied.
                    """,
                ),
            ]
        )
        return constructor_args


class OutboundHardSettlement(HardSettlement):
    type = PostingInstructionType.OUTBOUND_HARD_SETTLEMENT

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        class_docstring = (
            """
        [Outbound hard settlement](/reference/postings#outbound_hard_settlement_standalone)
        is a non-chainable Posting Instruction that authorises
        and settles outgoing funds from a target Account.
        """
            + cls._class_docs_note
        )
        public_methods = super()._public_methods(language_code)
        return types_utils.ClassSpec(
            name="OutboundHardSettlement",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new OutboundHardSettlement
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )


class InboundHardSettlement(HardSettlement):
    type = PostingInstructionType.INBOUND_HARD_SETTLEMENT

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        class_docstring = (
            """
        [Inbound hard settlement](/reference/postings#inbound_hard_settlement_standalone)
        is a non-chainable Posting Instruction that authorises
        and settles incoming funds into a target Account.
        """
            + cls._class_docs_note
        )
        public_methods = super()._public_methods(language_code)
        return types_utils.ClassSpec(
            name="InboundHardSettlement",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new InboundHardSettlement
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )


class Transfer(PostingInstructionBase):
    type = PostingInstructionType.TRANSFER

    def __init__(
        self,
        *,
        amount: Union[Decimal, int],
        denomination: str,
        debtor_target_account_id: str,
        creditor_target_account_id: str,
        
        instruction_details: Optional[Dict[str, str]] = None,
        transaction_code: Optional[TransactionCode] = None,
        override_all_restrictions: Optional[bool] = False,
        _from_proto: bool = False,
    ):
        # Subclass only attributes settable on the particular PostingInstructionType only
        self.amount = amount
        self.denomination = denomination
        self.debtor_target_account_id = debtor_target_account_id
        self.creditor_target_account_id = creditor_target_account_id
        
        # The init of the base PostingInstructionBase class
        super().__init__(
            instruction_details=instruction_details,
            transaction_code=transaction_code,
            override_all_restrictions=override_all_restrictions,
            _from_proto=_from_proto,
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        transfer_description = (
            "[Transfer](/reference/postings#transfer_standalone)"
            " is a non-chainable Posting Instruction that moves funds from a"
            " debtor to a creditor target Account."
        )

        class_docstring = f"""
        {transfer_description}

        [NOTE]
        ====
        When accessing `Transfer` attributes from within a hook, only one of the `debtor_target_account_id`
        or `creditor_target_account_id` attributes is populated. This applies to Transfers in `hook_arguments`
        as well as those fetched via an [Account Vault object](/reference/contracts/contracts_api_4xx/smart_contracts_api_reference4xx/vault).

        Only the attribute corresponding to the relevant Account is populated. The relevant Account is defined as:
        * For Smart Contracts: The Account executing the hook.
        * For Supervisor Contracts:
        ** For Transfers in `hook_arguments`: The supervisee Account with the ID in the dictionary
            of the `posting_instructions` or `client_transactions` fields of
            [SupervisorPrePostingHookArguments]({_common_docs_path}classes#supervisorprepostinghookarguments)
            or
            [SupervisorPostPostingHookArguments]({_common_docs_path}classes#supervisorpostpostinghookarguments)
            objects.
        ** For Transfers fetched via a supervisee Account Vault object: The supervisee Account associated with
            that supervisee Vault object.

        If the relevant Account is the debtor, the debtor attribute is populated. If the relevant Account is the creditor,
        the creditor attribute is populated. The other attribute is set as an empty string, and the Contract must not make
        financial decisions based on its value.
        ====
        {cls._class_docs_note}
        """
        public_methods = super()._public_methods(language_code)
        return types_utils.ClassSpec(
            name="Transfer",
            docstring=class_docstring,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new Transfer
                """,
                args=cls._constructor_args(language_code=language_code),  # noqa: SLF001
            ),
            public_methods=public_methods,
        )

    @classmethod
    def _constructor_args(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        constructor_args = super()._constructor_args(language_code=language_code)
        constructor_args.extend(
            [
                types_utils.ValueSpec(
                    name="amount",
                    type="Union[Decimal, int]",
                    docstring="""
                        The amount moved by this Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="denomination",
                    type="str",
                    docstring="""
                        The denomination of the amount moved by the Posting Instruction.
                    """,
                ),
                types_utils.ValueSpec(
                    name="debtor_target_account_id",
                    type="str",
                    docstring="""
                        The ID of the Account being debited.
                    """,
                ),
                types_utils.ValueSpec(
                    name="creditor_target_account_id",
                    type="str",
                    docstring="""
                        The ID Account being credited.
                    """,
                ),
            ]
        )
        
        return constructor_args


PITypesUnion = Union[
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Release,
    Settlement,
    Transfer,
]
PITypesList = list[PITypesUnion]

_AllPITypes = get_args(PITypesUnion)
_PI_TYPES_UNION_STR = f"Union[{', '.join(sorted([pi.type.value for pi in _AllPITypes]))}]"
_PI_TYPES_LIST_STR = f"List[{_PI_TYPES_UNION_STR}]"


class ClientTransactionEffects(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        authorised: Union[Decimal, int] = Decimal(0),
        settled: Union[Decimal, int] = Decimal(0),
        unsettled: Union[Decimal, int] = Decimal(0),
    ):
        self.authorised = authorised
        self.settled = settled
        self.unsettled = unsettled

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="ClientTransactionEffects",
            docstring="""
                The "effects" that a ClientTransaction has had on the balances of
                an Account, or the "current state" of the ClientTransaction.
                Note: This method is not implemented for ClientTransaction
                with CustomInstruction type - None will be returned
                for such ClientTransaction effects instead.
            """,
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            public_methods=[],
            constructor=types_utils.ConstructorSpec(
                docstring="""
                    Constructs a new ClientTransactionEffects
                """,
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="authorised",
                type="Union[Decimal, int]",
                docstring="""
                    The total amount that has been authorised.
                    Note: value is updated on Adjustment instructions,
                    however, is not updated on Settlement or Release instructions.
                """,
            ),
            types_utils.ValueSpec(
                name="settled",
                type="Union[Decimal, int]",
                docstring="""
                    The total amount that has been settled.
                """,
            ),
            types_utils.ValueSpec(
                name="unsettled",
                type="Union[Decimal, int]",
                docstring="""
                    The total amount that has been authorised (including adjustments)
                    but is yet to be released or settled.
                """,
            ),
        ]


class BalancesCacheKey(NamedTuple):
    """
    BalancesCacheKey is a NamedTuple that is used to key the balances cache.

    
    """

    effective_datetime: Optional[datetime]
    tside: Optional[Tside]
    


class EffectsCacheKey(NamedTuple):
    """
    EffectsCacheKey is a NamedTuple that is used to key the effects cache.

    
    """

    effective_datetime: Optional[datetime]
    


class ClientTransaction(types_utils.ContractsLanguageDunderMixin):
    _balance_class = Balance
    _balance_coordinate_class = BalanceCoordinate
    _balance_defaultdict_class = BalanceDefaultDict
    _client_transaction_effects_class = ClientTransactionEffects
    

    def __init__(
        self,
        *,
        client_transaction_id: str,
        account_id: str,
        posting_instructions: PITypesList,
        client_id: str = "",
        tside: Optional[Tside] = None,
        _from_proto: bool = False,
    ):
        self._balances_cache: dict[BalancesCacheKey, BalanceDefaultDict] = {}
        
        self._effects_cache: dict[EffectsCacheKey, Optional[ClientTransactionEffects]] = {}
        
        self.posting_instructions = posting_instructions
        self.client_transaction_id = client_transaction_id
        self.client_id = client_id
        self.account_id = account_id
        self.tside = tside
        if not _from_proto:
            self._validate_attributes()

        # Construct an internal Client Transaction object which is used for the calculation of
        # balances and effects. This validates that the sequence of Posting Instructions in a
        # Client Transaction is valid.
        _client_transaction_kwargs: dict[str, Any] = {
            "client_transaction_id": client_transaction_id,
            "account_id": account_id,
        }
        self._client_transaction = SingleAccountClientTransaction(**_client_transaction_kwargs)
        for pi in posting_instructions:
            value_datetime = pi.value_datetime
            if value_datetime and pi._committed_postings:  # noqa: SLF001
                final = pi.final if isinstance(pi, Settlement) else False
                if final is not None:
                    committed_postings = pi._committed_postings  # noqa: SLF001
                    self._client_transaction.add_committed_postings(
                        value_datetime,
                        committed_postings,  # type: ignore[arg-type]
                        pi.type.value,
                        final,
                    )

    def _validate_attributes(self):
        types_utils.validate_type(
            self.posting_instructions,
            list,
            hint=_PI_TYPES_LIST_STR,
            prefix="ClientTransaction.posting_instructions",
        )

        type_hint = _PI_TYPES_UNION_STR
        iterator = types_utils.get_iterator(
            self.posting_instructions,
            hint=type_hint,
            name="ClientTransaction.posting_instructions",
            check_empty=True,
        )
        expected_type = _AllPITypes
        for index, item in enumerate(iterator):
            types_utils.validate_type(
                item,
                expected_type,
                hint=type_hint,
                prefix="ClientTransaction.posting_instructions",
            )

            if not item.value_datetime:
                raise InvalidPostingInstructionException(
                    f"'ClientTransaction.posting_instructions[{index}]' has its value_datetime "
                    f"attribute set to {item.value_datetime}. Expected value_datetime to be set."
                )
            if isinstance(item, Settlement) and item.final is None:
                raise InvalidPostingInstructionException(
                    f"'ClientTransaction.posting_instructions[{index}]' Settlement instruction "
                    f"has its final attribute set to {item.final}. Expected True or False."
                )

            postings_iterator = types_utils.get_iterator(
                item._committed_postings,  # noqa: SLF001
                hint="List[Posting]",
                name=f"ClientTransaction.posting_instructions[{index}]._committed_postings",
                check_empty=True,
            )
            for posting_index, posting_item in enumerate(postings_iterator):
                types_utils.validate_type(
                    posting_item,
                    Posting,
                    hint="Posting",
                    prefix=f"ClientTransaction.posting_instructions[{index}]."
                    f"_committed_postings[{posting_index}]",
                )

    def __eq__(self, other):
        """Checks equality of the public attributes. If another attribute is added to the class it
        must be added to the `attributes` or `ignored_attributes`.
        """
        if type(other) is type(self):
            attributes = {
                "client_transaction_id",
                "account_id",
                "posting_instructions",
                "client_id",
                "tside",
            }

            ignored_attributes = {
                "_client_transaction",
                "_balances_cache",
                "_effects_cache",
                
            }
            
            if len(self.__dict__) != len(attributes) + len(ignored_attributes):
                raise NotImplementedError(
                    f"__eq__ operator for {self.__class__} is broken. Please, specify whether your "
                    f"new attribute will be ignored or not."
                )

            return all(getattr(self, attr) == getattr(other, attr) for attr in attributes)
        return False

    def released(self, *, effective_datetime: Optional[datetime] = None):
        effective_datetime = effective_datetime or datetime.max.replace(tzinfo=ZoneInfo("UTC"))
        timezone_utils.validate_timezone_is_utc(
            effective_datetime,
            "effective_datetime",
            "ClientTransaction.released()",
        )
        return any(
            isinstance(posting_instruction, Release) and value_datetime < effective_datetime
            for posting_instruction in self.posting_instructions
            if (value_datetime := posting_instruction.value_datetime) and value_datetime is not None
        )

    def completed(self, *, effective_datetime: Optional[datetime] = None):
        effective_datetime = effective_datetime or datetime.max.replace(tzinfo=ZoneInfo("UTC"))
        timezone_utils.validate_timezone_is_utc(
            effective_datetime,
            "effective_datetime",
            "ClientTransaction.completed()",
        )
        return any(
            isinstance(posting_instruction, Settlement)
            and posting_instruction.final is True
            and value_datetime < effective_datetime
            for posting_instruction in self.posting_instructions
            if (value_datetime := posting_instruction.value_datetime) and value_datetime is not None
        )

    

    @property
    def denomination(self) -> Optional[str]:
        posting_instruction = self.posting_instructions[0]
        if (
            isinstance(posting_instruction, InboundAuthorisation)
            or isinstance(posting_instruction, OutboundAuthorisation)
            or isinstance(posting_instruction, InboundHardSettlement)
            or isinstance(posting_instruction, OutboundHardSettlement)
            or isinstance(posting_instruction, Transfer)
        ):
            return posting_instruction.denomination
        else:
            return None

    @property
    def is_custom(self) -> bool:
        return self.posting_instructions[0].type == enums.PostingInstructionType.CUSTOM_INSTRUCTION

    @property
    def start_datetime(self) -> Optional[datetime]:
        return self.posting_instructions[0].value_datetime

    def balances(
        self,
        *,
        effective_datetime: Optional[datetime] = None,
        tside: Optional[Tside] = None,
    ) -> BalanceDefaultDict:
        self._validate_account_helper_preconditions("balances", effective_datetime)

        caching_key = BalancesCacheKey(
            effective_datetime=effective_datetime,
            tside=tside,
        )

        if caching_key in self._balances_cache:
            return self._balances_cache[caching_key]

        self._balances_cache[caching_key] = result = self._balances(
            effective_datetime=effective_datetime,
            tside=tside,
        )

        return result

    def _balances(
        self,
        *,
        effective_datetime: Optional[datetime] = None,
        tside: Optional[Tside] = None,
    ) -> BalanceDefaultDict:
        tside = tside or self.tside
        if not tside:
            raise InvalidSmartContractError(
                "A tside must be specified for the balances calculation."
            )

        # Get balances for client transaction object from postings logic module.
        balances = self._client_transaction.balances(at_datetime=effective_datetime)

        return self._transform_balance_default_dict_to_versioned_object(balances, tside)

    

    def _transform_balance_default_dict_to_versioned_object(self, balances: dict, tside: Tside):
        """
        Transforms the balances returned from the postings logic module
        to the versioned BalanceDefaultDict class, containing the transformed
        versioned BalanceCoordinate and Balance objects.
        """

        def _transform_balance_to_versioned_balance(balance_value):
            result = self._balance_class()
            result._adjust(  # noqa: SLF001
                credit=balance_value.credit,
                debit=balance_value.debit,
                tside=tside,
            )
            return result

        def _transform_balance_key(balance_key):
            return self._balance_coordinate_class(
                account_address=balance_key.account_address,
                asset=balance_key.asset,
                denomination=balance_key.denomination,
                phase=balance_key.phase,
            )

        return self._balance_defaultdict_class(
            # defaults to 0 net, credit and debit
            lambda *_: self._balance_class(),
            {
                _transform_balance_key(balance_key): _transform_balance_to_versioned_balance(
                    balance_value
                )
                for balance_key, balance_value in balances.items()
            },
        )

    def effects(
        self,
        *,
        effective_datetime: Optional[datetime] = None,
    ) -> Optional[ClientTransactionEffects]:
        self._validate_account_helper_preconditions("effects", effective_datetime)

        caching_key = EffectsCacheKey(
            effective_datetime=effective_datetime,
        )

        if caching_key in self._effects_cache:
            return self._effects_cache[caching_key]

        self._effects_cache[caching_key] = result = self._effects(
            effective_datetime=effective_datetime,
        )

        return result

    def _effects(
        self,
        effective_datetime: Optional[datetime] = None,
    ) -> Optional[ClientTransactionEffects]:
        if self.is_custom:
            return None

        # Note: tside does not influence calculating effects() so use Tside.LIABILITY when
        # calculating balances(), since it is calculating the absolute authorised, settled and
        # unsettled amounts, which are independent of tside.
        balances = self.balances(
            effective_datetime=effective_datetime,
            tside=Tside.LIABILITY,
        )
        if not balances:
            return self._client_transaction_effects_class()

        targeted_balance_keys = set(
            (key.account_address, key.asset, key.denomination) for key in balances.keys()
        )
        if len(targeted_balance_keys) != 1:
            raise InvalidPostingInstructionException(
                "ClientTransaction only supports posting instructions with "
                "the same account_address, denomination and asset attributes."
            )
        balance_key = targeted_balance_keys.pop()

        committed_postings = self.posting_instructions[0]._committed_postings
        if not committed_postings:
            raise InvalidSmartContractError(
                "ClientTransaction only supports posting instructions with"
                "non empty committed postings."
            )

        # All PI types except CustomInstructions have one committed posting in the primary
        # Posting Instruction.
        is_credit: bool = committed_postings[0].credit

        if is_credit:
            return self._make_inbound_effects(
                balances, *balance_key, effective_datetime=effective_datetime
            )
        else:
            return self._make_outbound_effects(
                balances, *balance_key, effective_datetime=effective_datetime
            )

    

    def _make_inbound_effects(
        self, balances, address, asset, denomination, effective_datetime=None
    ):
        # This is either authorised, released or settled transaction
        return self._client_transaction_effects_class(
            authorised=balances[
                self._balance_coordinate_class(
                    account_address=address,
                    asset=asset,
                    denomination=denomination,
                    phase=Phase.PENDING_IN,
                )
            ].credit,
            settled=balances[
                self._balance_coordinate_class(
                    account_address=address,
                    asset=asset,
                    denomination=denomination,
                    phase=Phase.COMMITTED,
                )
            ].credit,
            unsettled=(
                Decimal(0)
                if self.released(effective_datetime=effective_datetime)
                else abs(
                    balances[
                        self._balance_coordinate_class(
                            account_address=address,
                            asset=asset,
                            denomination=denomination,
                            phase=Phase.PENDING_IN,
                        )
                    ].net
                )
            ),
        )

    def _make_outbound_effects(
        self, balances, address, asset, denomination, effective_datetime=None
    ):
        # This is either authorised or released or settled transaction
        return self._client_transaction_effects_class(
            authorised=-balances[
                self._balance_coordinate_class(
                    account_address=address,
                    asset=asset,
                    denomination=denomination,
                    phase=Phase.PENDING_OUT,
                )
            ].debit,
            settled=-balances[
                self._balance_coordinate_class(
                    account_address=address,
                    asset=asset,
                    denomination=denomination,
                    phase=Phase.COMMITTED,
                )
            ].debit,
            unsettled=(
                Decimal(0)
                if self.released(effective_datetime=effective_datetime)
                else -abs(
                    balances[
                        self._balance_coordinate_class(
                            account_address=address,
                            asset=asset,
                            denomination=denomination,
                            phase=Phase.PENDING_OUT,
                        )
                    ].net
                )
            ),
        )

    def _validate_account_helper_preconditions(
        self, method_name: str, effective_datetime: Optional[datetime]
    ) -> None:
        # effective_datetime
        if effective_datetime:
            timezone_utils.validate_timezone_is_utc(
                effective_datetime,
                "effective_datetime",
                f"ClientTransaction.{method_name}()",
            )

        

    

    def __str__(self):
        return f"ClientTransaction({len(self.posting_instructions)} posting instruction(s))"

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        posting_instructions_docstring = """
            Ordered list of Posting Instructions with the same `client_transaction_id`
            for this `ClientTransaction`. Sorted ascending by `value_datetime`.
        """

        if is_fflag_enabled(RELAX_CLIENT_TRANSACTION_TIMESTAMP_CONSTRAINT):
            posting_instructions_docstring = """
               Ordered list of Posting Instructions with the same `client_transaction_id`
               for this `ClientTransaction`. Sorted ascending by priority: `value_datetime`,
               `insertion_datetime`, then `booking_datetime`.
            """

        constructor_spec_args = [
            types_utils.ValueSpec(
                name="client_transaction_id",
                type="str",
                docstring="""
                    The unique ID of this `ClientTransaction`.
                """,
            ),
            types_utils.ValueSpec(
                name="account_id",
                type="str",
                docstring="""
                    The ID of the Account which is the target Account for this `ClientTransaction`.
                    Note that for a `ClientTransaction` that consists of Custom Instructions
                    that have different target accounts, each `ClientTransaction` represents
                    the single Account client transaction - therefore consists only of
                    `CustomInstruction` Postings for a single Account ID.
                """,
            ),
            types_utils.ValueSpec(
                name="posting_instructions",
                type=_PI_TYPES_LIST_STR,
                docstring=posting_instructions_docstring,
            ),
            types_utils.ValueSpec(
                name="client_id",
                type="str",
                docstring="""
                        Uniquely identifies a client of the Posting API. Used to publish
                        responses to the specified Kafka response topic. Together with the
                        `client_transaction_id`, this forms a `unique_client_transaction_id`,
                        which is used when accessing `ClientTransaction` objects in the Contract
                        code. If not provided, defaults to an empty string.
                    """,
            ),
            types_utils.ValueSpec(
                name="tside",
                type="Optional[Tside]",
                docstring="""
                        The treasury side of the target Account.
                        Determines the Account Balance net sign.
                    """,
            ),
        ]

        public_attributes = [
            types_utils.ValueSpec(
                name="client_transaction_id",
                type="str",
                docstring="""
                    The unique ID of this `ClientTransaction`.
                """,
            ),
            types_utils.ValueSpec(
                name="client_id",
                type="str",
                docstring="""
                    Uniquely identifies a client of the Posting API. Used to publish responses
                    to the specified Kafka response topic. Together with the
                    `client_transaction_id`, this forms a `unique_client_transaction_id`,
                    which is used when accessing `ClientTransaction` objects in the Contract
                    code.
                """,
            ),
            types_utils.ValueSpec(
                name="account_id",
                type="str",
                docstring="""
                    The ID of the Account which is the target Account for this `ClientTransaction`.
                    Note that for a `ClientTransaction` that consists of Custom Instructions
                    that have different target accounts, each `ClientTransaction` represents
                    the single Account client transaction - therefore consists only of
                    `CustomInstruction` Postings for a single Account ID.
                """,
            ),
            types_utils.ValueSpec(
                name="denomination",
                type="str",
                docstring="""
                    The denomination of the `ClientTransaction` which is determined by the
                    denomination of the first Posting Instruction within the `ClientTransaction`.
                """,
            ),
            types_utils.ValueSpec(
                name="is_custom",
                type="bool",
                docstring="""
                    The value will be True if and only if all Posting Instruction objects are of
                    type `PostingInstructionType.CUSTOM_INSTRUCTION`.
                """,
            ),
            types_utils.ValueSpec(
                name="start_datetime",
                type="datetime",
                docstring="""
                    This value is the `value_datetime` of the first Posting Instruction within the
                    `ClientTransaction`. Must be a timezone-aware UTC datetime using the
                    ZoneInfo class.
                """,
            ),
            types_utils.ValueSpec(
                name="posting_instructions",
                type=_PI_TYPES_LIST_STR,
                docstring=posting_instructions_docstring,
            ),
            types_utils.ValueSpec(
                name="tside",
                type="Optional[Tside]",
                docstring="""
                    The treasury side of the target Account.
                    Determines the Account Balance net sign.
                """,
            ),
        ]
        

        public_methods = [
            types_utils.MethodSpec(
                name="released",
                docstring="""
                    This value will be `True` if and only if the `ClientTransaction` has ended with
                    a Posting Instruction of type `RELEASE` at given `effective_datetime`.
                """,
                args=[
                    types_utils.ValueSpec(
                        name="effective_datetime",
                        type="Optional[datetime]",
                        docstring="""
                            If set, only Posting Instructions that happened before or on the
                            datetime are included in the result. Must be a timezone-aware
                            UTC datetime. Must be a timezone-aware UTC datetime using the
                            ZoneInfo class.
                        """,
                    )
                ],
                return_value=types_utils.ReturnValueSpec(
                    type="bool",
                    docstring="""
                        This value will be `True` if and only if the `ClientTransaction` has ended with
                        a Posting Instruction of type `RELEASE` at given `effective_datetime`.
                    """,
                ),
            ),
            types_utils.MethodSpec(
                name="completed",
                docstring="""
                    This value will be `True` if and only if the `ClientTransaction` has ended with
                    a Posting Instruction of type `SETTLEMENT` and flag final.
                """,
                args=[
                    types_utils.ValueSpec(
                        name="effective_datetime",
                        type="Optional[datetime]",
                        docstring="""
                            If set, only Posting Instructions that happened before or on the
                            datetime are included in the result. Must be a timezone-aware
                            UTC datetime.
                        """,
                    )
                ],
                return_value=types_utils.ReturnValueSpec(
                    type="bool",
                    docstring="""
                        This value will be `True` if and only if the `ClientTransaction` has ended with
                        a Posting Instruction of type `SETTLEMENT` and flag final.
                    """,
                ),
            ),
            types_utils.MethodSpec(
                name="effects",
                docstring="""
                    Returns the net "effects" that the `ClientTransaction` has had on the Account.
                    Note: This method is not implemented for Client Transactions with
                    Custom Instructions.
                """,
                args=[
                    types_utils.ValueSpec(
                        name="effective_datetime",
                        type="Optional[datetime]",
                        docstring="""
                            If set, only Posting Instructions that happened before or on the
                            datetime are included in the result. Must be a timezone-aware UTC
                            datetime.
                        """,
                    )
                ],
                return_value=types_utils.ReturnValueSpec(
                    type="Optional[ClientTransactionEffects]",
                    docstring="""
                        The "effects" that a`ClientTransaction` has had on the balances of an Account,
                        or the "current state" of the `ClientTransaction`. Returns `None`
                        for Client Transactions with Custom Instructions.
                    """,
                ),
            ),
        ]
        
        public_methods.append(
            types_utils.MethodSpec(
                name="balances",
                docstring="Returns the net balance changes to the Account caused by this `ClientTransaction`.",
                args=[
                    types_utils.ValueSpec(
                        name="effective_datetime",
                        type="Optional[datetime]",
                        docstring="""
                            If set, only Posting Instructions that happened before or on the
                            datetime are included in the result. Must be a timezone-aware UTC
                            datetime.
                        """,
                    ),
                    types_utils.ValueSpec(
                        name="tside",
                        type="Optional[Tside]",
                        docstring="""
                            The T-side of an Account which is used to calculate net balances.
                            It is only required when creating a Client Transaction object within a
                            Contract, as these might contain instructions for multiple Accounts.
                            It does not need to be provided for historical Client Transactions
                            returned via `vault` methods or Client Transactions that the hook
                            receives via arguments in `pre_posting_hook` and `post_posting_hook`.
                            In these cases, the argument defaults to the `tside` of the Smart Contract
                            or the `tside` of the supervisee Account in a Supervisor Contract.
                        """,
                    ),
                ],
                return_value=types_utils.ReturnValueSpec(
                    type="BalanceDefaultDict",
                    docstring=f"""
                        The default balance dictionary where the key is the
                        [BalanceCoordinate]({_common_docs_path}classes/#BalanceCoordinate) and the value is
                        a [Balance]({_common_docs_path}classes/#Balance) object which contains the debit,
                        credit and net balance changes. Accessing a non-existent key will return a
                        `Balance` object with zero debit, credit, and net balance changes.
                    """,
                ),
            ),
        )
        
        docstring = f"""
            A sequence of Posting Instruction objects with the same `client_transaction_id`
            field.

            This object represents the lifecycle of a single transaction. The lifecycle may be
            as trivial as a single "hard settlement" (immediate movement of funds), or contain
            any combination of authorisation, reauthorisation, and so on (see
            [PostingInstructionType]({_common_docs_path}enums/#PostingInstructionType)).

            Each Posting Instruction in this sequence represents a change in state in the
            transaction's lifecycle.

            Although the object schema allows for Posting Instruction objects within the same
            [ClientTransaction]({_common_docs_path}classes/#ClientTransaction)
            to have differing `account_id`, `asset`, and `denomination` fields, by convention they
            should all be the same, in which case the Posting Instruction only represents a
            change to the net amount and/or [Phase]({_common_docs_path}enums/#Phase)
            of its parent transaction."""
        
        

        public_methods.append(
            types_utils.MethodSpec(
                name="__str__",
                docstring="Python dunder method. Returns a string representation of the class name and the number of posting instructions.",
                args=[],
                return_value=types_utils.ValueSpec(
                    name=None,
                    type="str",
                    docstring="A string representation. Example: `ClientTransaction(2 posting instruction(s))`",
                ),
            )
        )
        return types_utils.ClassSpec(
            name="ClientTransaction",
            docstring=docstring,
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=constructor_spec_args,
            ),
            public_attributes=public_attributes,
            public_methods=public_methods,
        )

    
