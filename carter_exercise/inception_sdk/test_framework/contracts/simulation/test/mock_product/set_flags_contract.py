# fmt: off
# Copyright @ 2021 Thought Machine Group Limited. All rights reserved.
"""
An example that shows required flags being declared in a Smart Contract
"""
# standard libs

# contracts api
from contracts_api import (
    DefinedDateTime,
    DerivedParameterHookArguments,
    DerivedParameterHookResult,
    FlagsObservationFetcher,
    Parameter,
    ParameterLevel,
    StringShape,
    fetch_account_data,
)

display_name = "Contract with Flags"
api = "4.0.0"
version = "1.0.0"
summary = "Contract with Flags"


data_fetchers = [
    FlagsObservationFetcher(
        fetcher_id="flags_of",
        at=DefinedDateTime.EFFECTIVE_DATETIME,
    ),
]

parameters = [
    Parameter(
        name="flag_value_on_parameter",
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        derived=True,
        description="Value for `flag_value_on` flag",
        display_name="Value for `flag_value_on` flag",
    ),
    Parameter(
        name="flag_backdated_parameter",
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        derived=True,
        description="Value for `flag_backdated` flag",
        display_name="Value for `flag_backdated` flag",
    ),
    Parameter(
        name="flag_value_off_then_on_parameter",
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        derived=True,
        description="Value for `flag_value_off_then_on` flag",
        display_name="Value for `flag_value_off_then_on` flag",
    ),
]

@fetch_account_data(flags=["flags_of"])
def derived_parameter_hook(
    vault, hook_arguments: DerivedParameterHookArguments
) -> DerivedParameterHookResult:
    flags = vault.get_flags_observation(fetcher_id="flags_of").flags
    return DerivedParameterHookResult(
        parameters_return_value={
            "flag_value_on_parameter": str(flags["flag_value_on"]),
            "flag_backdated_parameter": str(flags["flag_backdated"]),
            "flag_value_off_then_on_parameter": str(flags["flag_value_off_then_on"]),
        }
    )


# fmt: on
