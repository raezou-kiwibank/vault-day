__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal

import feature_library.common.posting_utils as posting_utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Posting,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameter
FEES_APPLICATION_TIME_PARAM_ID = "&{fees_application_time}"
FEES_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=FEES_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    FEES_APPLICATION_TIME_PARAM,
]

FEES_APPLICATION_TIME_POF_ID = "fees_application_time_pof"

FEES_APPLICATION_TIME_POF = ParametersObservationFetcher(
    fetcher_id=FEES_APPLICATION_TIME_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = FEES_APPLICATION_TIME_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the fees application time feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `FEES_APPLICATION_TIME_POF_ID`.

    Returns:
        Parameters for the fees application time feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def fee_custom_instruction(
    customer_account_id: str,
    denomination: str,
    amount: Decimal,
    internal_account: str,
    customer_account_address: str = DEFAULT_ADDRESS,
    instruction_details: dict[str, str] | None = None,
    reversal: bool = False,
) -> list[CustomInstruction]:
    """Create a Custom Instruction containing customer and internal account postings for a fee.

    :param customer_account_id: the customer account id to use
    :param denomination: the denomination of the fee
    :param amount: the fee amount. If this is amount is <= 0 an empty list is returned
    :param internal_account: the internal account id to use. The DEFAULT address is always
    used on this account
    :param customer_account_address: the address on the customer account to debit, defaults to the
    DEFAULT address
    :param instruction_details: instruction details to add to the postings
    Useful if more than one fee affects a given balance (e.g. un-netted tiered interest)
    :return: Custom instructions to apply fee, if required
    """
    postings = fee_postings(
        customer_account_id=customer_account_id,
        customer_account_address=customer_account_address,
        denomination=denomination,
        amount=amount,
        internal_account=internal_account,
        reversal=reversal,
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


def fee_postings(
    customer_account_id: str,
    customer_account_address: str,
    denomination: str,
    amount: Decimal,
    internal_account: str,
    reversal: bool = False,
) -> list[Posting]:
    """Create customer and internal account postings for applying a fee.

    :param customer_account_id: the customer account id to use
    :param customer_account_address: the address on the customer account to debit
    :param denomination: the denomination of the fee
    :param amount: the fee amount. If this is amount is <= 0 an empty list is returned.
    :param internal_account: the internal account id to use. The default address is always
    used on this account
    :return: the fee postings
    """

    if amount <= 0:
        return []

    return posting_utils.create_postings(
        amount=amount if not reversal else -amount,
        debit_account=customer_account_id,
        credit_account=internal_account,
        denomination=denomination,
        debit_address=customer_account_address,
        credit_address=DEFAULT_ADDRESS,
    )
