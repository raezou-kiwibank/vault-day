# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    AccountIdShape,
    AccountNotificationDirective,
    DateShape,
    NumberShape,
    Parameter,
    ParameterLevel,
    ParameterUpdatePermission,
    PostPostingHookArguments,
    PostPostingHookResult,
    StringShape,
    Tside,
    UnionItem,
    UnionItemValue,
    UnionShape,
    requires,
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

STRING_PARAM = Parameter(
    name="string_param",
    description="Parameter for strings.",
    display_name="Parameter strings.",
    shape=StringShape(),
    level=ParameterLevel.INSTANCE,
    default_value="SOME_PARAM",
    update_permission=ParameterUpdatePermission.USER_EDITABLE,
)
DECIMAL_PARAM = Parameter(
    name="decimal_param",
    description="Parameter for decimals.",
    display_name="Parameter decimals.",
    shape=NumberShape(),
    level=ParameterLevel.INSTANCE,
    default_value=Decimal(1),
    update_permission=ParameterUpdatePermission.USER_EDITABLE,
)
ENUMERATION_PARAM = Parameter(
    name="enumeration_param",
    description="Parameter for enumerations.",
    display_name="Parameter enumerations.",
    shape=UnionShape(
        items=[
            UnionItem(key="green", display_name="Green"),
            UnionItem(key="gold", display_name="Gold"),
            UnionItem(key="red", display_name="Red"),
        ]
    ),
    level=ParameterLevel.INSTANCE,
    default_value=UnionItemValue(key="red"),
    update_permission=ParameterUpdatePermission.USER_EDITABLE,
)
DATETIME_PARAM = Parameter(
    name="datetime_param",
    description="Parameter for datetimes.",
    display_name="Parameter datetimes.",
    shape=DateShape(),
    level=ParameterLevel.INSTANCE,
    default_value=datetime(2020, 1, 1, tzinfo=UTC),
    update_permission=ParameterUpdatePermission.USER_EDITABLE,
)
ACCOUNT_ID_PARAM = Parameter(
    name="account_id_param",
    description="Parameter for account_id.",
    display_name="Parameter account_id.",
    shape=AccountIdShape(),
    level=ParameterLevel.INSTANCE,
    default_value="ACCOUNT_ID_PARAM",
    update_permission=ParameterUpdatePermission.USER_EDITABLE,
)
parameters = [
    STRING_PARAM,
    DECIMAL_PARAM,
    ENUMERATION_PARAM,
    DATETIME_PARAM,
    ACCOUNT_ID_PARAM,
]


@requires(parameters=True)
def post_posting_hook(
    vault: SmartContractVault,
    hook_arguments: PostPostingHookArguments,
) -> Optional[PostPostingHookResult]:
    effective_datetime = hook_arguments.effective_datetime
    string_param: str = str(
        vault.get_parameter_timeseries(name=STRING_PARAM.name).at(at_datetime=effective_datetime)
    )
    decimal_param: Any | None = vault.get_parameter_timeseries(name=DECIMAL_PARAM.name).at(
        at_datetime=effective_datetime
    )
    enumeration_param: UnionItemValue | Any = vault.get_parameter_timeseries(
        name=ENUMERATION_PARAM.name
    ).at(at_datetime=effective_datetime)
    datetime_param: datetime | Any = vault.get_parameter_timeseries(name=DATETIME_PARAM.name).at(
        at_datetime=effective_datetime
    )
    account_id_param: str = str(
        vault.get_parameter_timeseries(name=ACCOUNT_ID_PARAM.name).at(
            at_datetime=effective_datetime
        )
    )
    return PostPostingHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type=POST_POSTING_NOTIFICATION,
                notification_details={
                    STRING_PARAM.name: string_param,
                    DECIMAL_PARAM.name: str(decimal_param),
                    ENUMERATION_PARAM.name: enumeration_param.key,
                    DATETIME_PARAM.name: datetime_param.isoformat(),
                    ACCOUNT_ID_PARAM.name: account_id_param,
                },
            )
        ]
    )
