__smart_contract_feature__ = True

# standard libs
from decimal import Decimal

# library
import feature_library.common.posting_utils as posting_utils

# contracts api
from contracts_api import DEFAULT_ADDRESS, CustomInstruction, Posting


def create_payable_accrual_custom_instruction(
    customer_account: str,
    customer_address: str,
    denomination: str,
    amount: Decimal,
    internal_account: str,
    instruction_details: dict[str, str] | None = None,
    reversal: bool = False,
) -> list[CustomInstruction]:
    """Create a Custom Instruction for accruing a charge.

    Accepts negative amounts, will flip what is debited/credited in this scenario.

    Args:
        customer_account (str): The customer's account id
        customer_address (str): The customer's address
        denomination (str): The denomination
        amount (Decimal): The accrual amount
        internal_account (str): The internal account id
        instruction_details (dict[str, str] | None, optional): instruction details to add to the
            postings. Defaults to None.
        reversal (bool, optional): set to True if reversing the accrual, or False otherwise.
            Defaults to False.

    Returns:
        list[CustomInstruction]: List of custom instructions for accrual
    """
    if amount == 0:
        return []

    debit_account = internal_account
    credit_account = customer_account
    debit_address = DEFAULT_ADDRESS
    credit_address = customer_address

    if reversal:
        debit_account, credit_account = credit_account, debit_account
        debit_address, credit_address = credit_address, debit_address

    postings = posting_utils.create_postings(
        amount=amount,
        debit_account=debit_account,
        credit_account=credit_account,
        denomination=denomination,
        debit_address=debit_address,
        credit_address=credit_address,
    )

    return (
        [
            CustomInstruction(
                postings=postings,
                instruction_details=instruction_details,
                override_all_restrictions=True,
            )
        ]
        if postings
        else []
    )


def create_payable_accrual_application_postings(
    customer_account: str,
    denomination: str,
    application_amount: Decimal,
    accrual_amount: Decimal,
    accrual_customer_address: str,
    accrual_internal_account: str,
    application_customer_address: str,
    application_internal_account: str,
) -> list[Posting]:
    """Create a list of Postings for applying an accrued charge.

    Accepts negative amounts, will flip what is debited/credited in this scenario.

    Args:
        customer_account (str): The customer's account id
        denomination (str): The denomination
        application_amount (Decimal): The application amount
        accrual_amount (Decimal): The accrual amount
        accrual_customer_address (str): The accrual address on the customer account
        accrual_internal_account (str): The accrual internal account
        application_customer_address (str): The application address on the customer account
        application_internal_account (str): The application internal account

    Returns:
        list[Posting]: List of postings for the application
    """
    if application_amount == 0:
        return []

    # 1. Application postings (Move money from internal to customer or vice-versa)
    postings = posting_utils.create_postings(
        amount=application_amount,
        debit_account=application_internal_account,
        credit_account=customer_account,
        denomination=denomination,
        debit_address=DEFAULT_ADDRESS,
        credit_address=application_customer_address,
    )

    # 2. Zero out all accrued interest (Reversal of the accrual addresses)
    if accrual_amount != 0:
        postings.extend(
            posting_utils.create_postings(
                amount=accrual_amount,
                debit_account=customer_account,
                credit_account=accrual_internal_account,
                denomination=denomination,
                debit_address=accrual_customer_address,
                credit_address=DEFAULT_ADDRESS,
            )
        )

    return postings


def create_payable_accrual_application_custom_instruction(
    customer_account: str,
    denomination: str,
    application_amount: Decimal,
    accrual_amount: Decimal,
    instruction_details: dict[str, str],
    accrual_customer_address: str,
    accrual_internal_account: str,
    application_customer_address: str,
    application_internal_account: str,
) -> list[CustomInstruction]:
    """Create a Custom Instruction for applying an accrued charge.

    Accepts negative amounts, will flip what is debited/credited in this scenario.

    Args:
        customer_account (str): The customer's account id
        denomination (str): The denomination
        application_amount (Decimal): The application amount
        accrual_amount (Decimal): The accrual amount
        instruction_details (dict[str, str]): The instruction details
        accrual_customer_address (str): The accrual address on the customer account
        accrual_internal_account (str): The accrual internal account
        application_customer_address (str): The application address on the customer account
        application_internal_account (str): The application internal account

    Returns:
        list[CustomInstruction]: List of custom instructions for the application
    """
    postings = create_payable_accrual_application_postings(
        customer_account=customer_account,
        denomination=denomination,
        application_amount=application_amount,
        accrual_amount=accrual_amount,
        accrual_customer_address=accrual_customer_address,
        accrual_internal_account=accrual_internal_account,
        application_customer_address=application_customer_address,
        application_internal_account=application_internal_account,
    )

    return (
        [
            CustomInstruction(
                postings=postings,
                instruction_details=instruction_details,
                override_all_restrictions=True,
            )
        ]
        if postings
        else []
    )


def create_receivable_accrual_custom_instruction(
    customer_account: str,
    denomination: str,
    amount: Decimal,
    internal_account: str,
    customer_address: str,
    reversal: bool = False,
    instruction_details: dict[str, str] | None = None,
) -> list[CustomInstruction]:
    """Create a Custom Instruction for a receivable accrual (customer pays)."""
    if amount == 0:
        return []

    debit_account = customer_account
    credit_account = internal_account
    debit_address = customer_address
    credit_address = DEFAULT_ADDRESS

    if reversal:
        debit_account, credit_account = credit_account, debit_account
        debit_address, credit_address = credit_address, debit_address

    postings = posting_utils.create_postings(
        amount=amount,
        debit_account=debit_account,
        credit_account=credit_account,
        denomination=denomination,
        debit_address=debit_address,
        credit_address=credit_address,
    )

    return (
        [
            CustomInstruction(
                postings=postings,
                instruction_details=instruction_details,
                override_all_restrictions=True,
            )
        ]
        if postings
        else []
    )


def create_receivable_accrual_application_postings(
    customer_account: str,
    denomination: str,
    application_amount: Decimal,
    accrual_amount: Decimal,
    accrual_customer_address: str,
    accrual_internal_account: str,
    application_customer_address: str,
    application_internal_account: str,
) -> list[Posting]:
    """Create a list of Postings for applying a receivable accrued charge."""
    if application_amount == 0:
        return []

    # 1. Application postings (Move money from customer to internal income account)
    postings = posting_utils.create_postings(
        amount=application_amount,
        debit_account=customer_account,
        credit_account=application_internal_account,
        denomination=denomination,
        debit_address=application_customer_address,
        credit_address=DEFAULT_ADDRESS,
    )

    # 2. Zero out accrued interest (Reversal of the accrual)
    if accrual_amount != 0:
        postings.extend(
            posting_utils.create_postings(
                amount=accrual_amount,
                debit_account=accrual_internal_account,
                credit_account=customer_account,
                denomination=denomination,
                debit_address=DEFAULT_ADDRESS,
                credit_address=accrual_customer_address,
            )
        )

    return postings


def create_receivable_accrual_application_custom_instruction(
    customer_account: str,
    denomination: str,
    application_amount: Decimal,
    accrual_amount: Decimal,
    instruction_details: dict[str, str],
    accrual_customer_address: str,
    accrual_internal_account: str,
    application_customer_address: str,
    application_internal_account: str,
) -> list[CustomInstruction]:
    """Create a Custom Instruction for applying a receivable accrued charge."""
    postings = create_receivable_accrual_application_postings(
        customer_account=customer_account,
        denomination=denomination,
        application_amount=application_amount,
        accrual_amount=accrual_amount,
        accrual_customer_address=accrual_customer_address,
        accrual_internal_account=accrual_internal_account,
        application_customer_address=application_customer_address,
        application_internal_account=application_internal_account,
    )

    return (
        [
            CustomInstruction(
                postings=postings,
                instruction_details=instruction_details,
                override_all_restrictions=True,
            )
        ]
        if postings
        else []
    )
