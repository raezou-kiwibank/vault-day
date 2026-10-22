# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    AccountConstraint,
    AccountNotificationDirective,
    DateTimeConstraint,
    DateTimePrecision,
    DecimalConstraint,
    DefinedDateTime,
    EnumerationConstraint,
    ExpectedParameter,
    ParametersObservationFetcher,
    PostPostingHookArguments,
    PostPostingHookResult,
    StringConstraint,
    Tside,
    fetch_account_data,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY

UTC = ZoneInfo("UTC")

POST_POSTING_NOTIFICATION = "post_posting_notification"
notification_types = [POST_POSTING_NOTIFICATION]

STRING_EXPECTED_PARAM = ExpectedParameter(
    id="&{SOME_STRING_PARAMETER_RESOURCE}",
    constraint=StringConstraint(min_length=1, max_length=100),
)
DECIMAL_EXPECTED_PARAM = ExpectedParameter(
    id="&{SOME_DECIMAL_PARAMETER_RESOURCE}",
    constraint=DecimalConstraint(min_value=Decimal(0), max_value=Decimal(100)),
)
ENUMERATION_EXPECTED_PARAM = ExpectedParameter(
    id="&{SOME_ENUMERATION_PARAMETER_RESOURCE}",
    constraint=EnumerationConstraint(
        permitted_values=[
            "green",
            "gold",
            "red",
        ]
    ),
)
DATETIME_EXPECTED_PARAM = ExpectedParameter(
    id="&{SOME_DATETIME_PARAMETER_RESOURCE}",
    constraint=DateTimeConstraint(
        precision=DateTimePrecision.MINUTE,
        earliest=datetime(2020, 1, 1, tzinfo=UTC),
        latest=datetime(2040, 1, 1, tzinfo=UTC),
    ),
)
ACCOUNT_ID_EXPECTED_PARAM = ExpectedParameter(
    id="&{SOME_ACCOUNT_PARAMETER_RESOURCE}",
    constraint=AccountConstraint(),
)
expected_parameters = [
    STRING_EXPECTED_PARAM,
    DECIMAL_EXPECTED_PARAM,
    ENUMERATION_EXPECTED_PARAM,
    DATETIME_EXPECTED_PARAM,
    ACCOUNT_ID_EXPECTED_PARAM,
]


effective_date_params_obs_fetcher = ParametersObservationFetcher(
    fetcher_id="EFFECTIVE_DATE_PARAMS_FETCHER",
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)
data_fetchers = [
    effective_date_params_obs_fetcher,
]


@fetch_account_data(parameters=["EFFECTIVE_DATE_PARAMS_FETCHER"])
def post_posting_hook(
    vault: SmartContractVault,
    hook_arguments: PostPostingHookArguments,
) -> Optional[PostPostingHookResult]:
    params = vault.get_parameters_observation(
        fetcher_id=effective_date_params_obs_fetcher.fetcher_id
    ).parameters
    string_param: str = params[STRING_EXPECTED_PARAM.id]  # type: ignore
    decimal_param: Decimal = params[DECIMAL_EXPECTED_PARAM.id]  # type: ignore
    enumeration_param: str = params[ENUMERATION_EXPECTED_PARAM.id]  # type: ignore
    datetime_param: datetime = params[DATETIME_EXPECTED_PARAM.id]  # type: ignore
    account_id_param: str = params[ACCOUNT_ID_EXPECTED_PARAM.id]  # type: ignore
    return PostPostingHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type=POST_POSTING_NOTIFICATION,
                notification_details={
                    STRING_EXPECTED_PARAM.id: string_param,
                    DECIMAL_EXPECTED_PARAM.id: str(decimal_param),
                    ENUMERATION_EXPECTED_PARAM.id: enumeration_param,
                    DATETIME_EXPECTED_PARAM.id: datetime_param.isoformat(),
                    ACCOUNT_ID_EXPECTED_PARAM.id: account_id_param,
                },
            )
        ]
    )
