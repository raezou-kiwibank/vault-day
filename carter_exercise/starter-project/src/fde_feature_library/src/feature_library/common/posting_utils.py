__smart_contract_feature__ = True

# standard libs
from decimal import Decimal

import feature_library.common.utils as utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AuthorisationAdjustment,
    BalanceDefaultDict,
    CustomInstruction,
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

PostingInstructionTypeAlias = (
    AuthorisationAdjustment
    | CustomInstruction
    | InboundAuthorisation
    | InboundHardSettlement
    | OutboundAuthorisation
    | OutboundHardSettlement
    | Release
    | Settlement
    | Transfer
)

PostingInstructionListAlias = list[PostingInstructionTypeAlias]

VALID_DAYS_IN_YEAR = ["360", "365", "366", "actual"]
DEFAULT_DAYS_IN_YEAR = "actual"
RATE_DECIMAL_PLACES = 10


## Posting helpers
def create_postings(
    amount: Decimal,
    debit_account: str,
    credit_account: str,
    denomination: str,
    debit_address: str = DEFAULT_ADDRESS,
    credit_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
) -> list[Posting]:
    """Creates a pair of postings to debit the debit_address on debit_account.

    The postings will credit the credit_address on credit_account by the specified amount.


    Args:
        amount (Decimal): The amount to pay. If the amount is < 0, debit and credit postings are
            swapped.
        debit_account (str): The account from which to debit the amount.
        credit_account (str): The account to which to credit the amount.
        denomination (str): The denomination of the postings.
        debit_address (str, optional): The address from which to move the amount. Defaults to
            DEFAULT_ADDRESS.
        credit_address (str, optional): The address to which to move the amount. Defaults to
            DEFAULT_ADDRESS.
        asset (str, optional): The asset of the postings. Defaults to DEFAULT_ASSET.

    Returns:
        list[Posting]: The credit-debit pair of postings.
    """
    is_credit: bool = amount > Decimal(0)
    abs_amt = abs(amount)
    return (
        [
            Posting(
                credit=not is_credit,
                amount=abs_amt,
                denomination=denomination,
                account_id=debit_account,
                account_address=debit_address,
                asset=asset,
                phase=Phase.COMMITTED,
            ),
            Posting(
                credit=is_credit,
                amount=abs_amt,
                denomination=denomination,
                account_id=credit_account,
                account_address=credit_address,
                asset=asset,
                phase=Phase.COMMITTED,
            ),
        ]
        if amount != 0
        else []
    )


def get_posting_instructions_balances(
    posting_instructions: PostingInstructionListAlias,
    account_id: str | None = None,
    tside: Tside | None = None,
) -> BalanceDefaultDict:
    """Gets the combined balances for a list of posting instructions.

    You MUST supply the 'account_id' and 'tside' if calling this function for contract-generated
    posting instructions. Fetched or hook argument postings will have the required
    attributes (_tside and _own_account_id) already and so these arguments do not have to be
    specified for them.

    Args:
        posting_instructions (PostingInstructionListAlias): list of posting instructions.
        account_id (str | None, optional): id of the vault account, required for contract-generated
            posting instructions. Defaults to None.
        tside (Tside | None, optional): tside of the account, required for contract-generated
            posting instructions. Defaults to None.

    Returns:
        BalanceDefaultDict: populated with the balances from the provided posting instructions.
    """

    return sum(
        (pi.balances(account_id=account_id, tside=tside) for pi in posting_instructions),
        BalanceDefaultDict(),
    )


def standard_instruction_details(
    description: str,
    event_type: str,
    gl_impacted: bool = False,
    account_type: str = "",
) -> dict[str, str]:
    """Generates standard posting instruction details.

    Args:
        description (str): a description of the instruction, usually for human consumption.
        event_type (str): event type name that resulted in the instruction (e.g.,
            "ACCRUE_INTEREST").
        gl_impacted (bool, optional): indicates if this posting instruction has GL implications.
            Defaults to False.
        account_type (str, optional): the account type for GL purposes (e.g. to identify postings
            pertaining to current accounts vs savings accounts). Defaults to "".

    Returns:
        dict[str, str]: the instruction details.
    """

    return {
        "description": description,
        "event": event_type,
        "gl_impacted": str(gl_impacted),
        "account_type": account_type,
    }


def is_key_in_instruction_details(
    *, key: str, posting_instructions: PostingInstructionListAlias
) -> bool:
    """Checks if a key is present and evaluates to true.

    The check is performed in the instruction details of all provided posting instructions.


    Args:
        key (str): The key to check in instruction_details.
        posting_instructions (PostingInstructionListAlias): The list of posting instructions to
            examine.

    Returns:
        bool: True if the key is present and true for all instructions, False otherwise.
    """
    return all(
        utils.str_to_bool(posting_instruction.instruction_details.get(key, "false"))
        for posting_instruction in posting_instructions
    )


def is_force_override(posting_instructions: PostingInstructionListAlias) -> bool:
    """Checks if 'force_override' is set to true.

    The check is performed in the instruction details of all provided posting instructions.


    Args:
        posting_instructions (PostingInstructionListAlias): The list of posting instructions to
            examine.

    Returns:
        bool: True if 'force_override' is true for all instructions, False otherwise.
    """
    return is_key_in_instruction_details(
        key="force_override", posting_instructions=posting_instructions
    )
