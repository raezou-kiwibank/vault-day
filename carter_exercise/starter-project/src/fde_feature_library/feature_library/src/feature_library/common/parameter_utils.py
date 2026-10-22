__smart_contract_feature__ = True

# standard libs
from calendar import isleap
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import Any

# feature_library
import feature_library.common.utils as utils

# contracts api
from contracts_api import (
    AuthorisationAdjustment,
    CustomInstruction,
    ExpectedParameter,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Release,
    Settlement,
    Transfer,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

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


def distinct_expected_parameters(
    expected_parameters: list[ExpectedParameter],
) -> list[ExpectedParameter]:
    """Filter a list of expected parameters to ensure each parameter ID is unique.

    The first occurrence of a parameter with a given ID is retained, and subsequent
    parameters with the same ID are discarded.

    Args:
        expected_parameters: A list of expected parameters to deduplicate.

    Returns:
        list[ExpectedParameter]: A list of unique expected parameters.
    """
    used_parameter_ids = set()

    def used(parameter_id: str) -> bool:
        """Determine if a parameter_id has been encountered and mark it as used.

        Args:
            parameter_id: The ID of the parameter to check.

        Returns:
            True if the parameter ID has been seen before, False otherwise.
        """
        if parameter_id in used_parameter_ids:
            return True
        used_parameter_ids.add(parameter_id)
        return False

    return [p for p in expected_parameters if not used(p.id)]


## Parameter helpers
def get_parameter_from_observation(
    vault: SmartContractVault,
    name: str,
    # TODO: decide if we want a "default" parameter obs fetcher
    fetcher_id: str,
    is_json: bool = False,
    is_boolean: bool = False,
    is_optional: bool = False,
    default_value: Any | None = None,
) -> Any:
    """Get the parameter value for a given parameter from a vault observation.

    Args:
        vault: Vault object to use for retrieving the parameter observation.
        name: Name of the parameter to retrieve.
        fetcher_id: ID of ParameterObservationFetcher to use.
        is_json: If True, json.loads is called on the retrieved parameter value.
        is_boolean: Boolean parameters are treated as union parameters before calling
            utils.str_to_bool on the retrieved parameter value.
        is_optional: If True, the parameter is treated as optional.
        default_value: Only used in conjunction with the is_optional arg, the value to use if the
            parameter is not set.

    Returns:
        Any: The parameter value. This is type hinted as Any because the parameter could be
            json loaded, therefore its value can be any json serialisable type.
    """
    parameter = vault.get_parameters_observation(fetcher_id=fetcher_id).parameters[name]

    if is_optional:
        parameter = parameter if parameter is not None else default_value

    if is_boolean and parameter is not None:
        parameter = utils.str_to_bool(parameter)  # type: ignore

    if is_json and parameter is not None:
        parameter = loads(parameter)  # type: ignore

    return parameter


def yearly_to_daily_rate(
    effective_date: datetime, yearly_rate: Decimal, days_in_year: str = "actual"
) -> Decimal:
    """Calculate the daily rate from a yearly rate, for a given `days_in_year` convention and date.

    Args:
        effective_date: The date as of which the conversion happens. This may affect the outcome
            based on the `days_in_year` value.
        yearly_rate: The rate to convert.
        days_in_year: The number of days in the year to assume for the calculation. One of `360`,
            `365`, `366` or `actual`. If actual is used, the number of days is based on
            effective_date's year.

    Returns:
        Decimal: The corresponding daily rate.
    """

    days_in_year = days_in_year if days_in_year in VALID_DAYS_IN_YEAR else DEFAULT_DAYS_IN_YEAR
    if days_in_year == "actual":
        num_days_in_year = Decimal("366") if isleap(effective_date.year) else Decimal("365")
    else:
        num_days_in_year = Decimal(days_in_year)

    return utils.round_decimal(yearly_rate / num_days_in_year, decimal_places=RATE_DECIMAL_PLACES)


def yearly_to_monthly_rate(yearly_rate: Decimal) -> Decimal:
    """Converts a yearly rate to a monthly rate.

    Args:
        yearly_rate: The yearly rate to convert.

    Returns:
        Decimal: The corresponding monthly rate.
    """
    return utils.round_decimal(yearly_rate / 12, decimal_places=RATE_DECIMAL_PLACES)
