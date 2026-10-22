# Copyright @ 2020 - 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import json
import logging
import os
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Protocol, TypeVar, overload

# third party
from requests import HTTPError
from semantic_version import Version
from typing_extensions import deprecated

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.common.date_helper import isoformat
from inception_sdk.test_framework.endtoend.helper import retry_decorator
from inception_sdk.vault.core_api import (
    AccountStatus,
    AccountV2Status,
    AccountV2Type,
    BatchCreateParameterValueV1RequestBody,
    BatchGetParameterResourceV1ResponseBody,
    CalendarEventStatus,
    CreateAccountV2RequestBody,
    CreateAccountV2Response,
    CreateOptions,
    CreateParameterResourceV1RequestBody,
    CreateParameterValueHierarchyNode,
    CreateParameterValueHierarchyNodeRequestBody,
    CustomerAccountRequestBody,
    GetVaultVersionResponse,
    InternalAccountRequestBody,
    UpdateAccountV2Account,
    UpdateAccountV2RequestBody,
    UpdateMask,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def create_customer(
    id: str = "",
    title: str = "CUSTOMER_TITLE_MR",
    first_name: str = "e2eTest",
    middle_name: str = "",
    last_name: str = "Smith",
    dob: str = "1980-12-25",
    gender: str = "CUSTOMER_GENDER_MALE",
    nationality: str = "GB",
    email_address: str = "e2etesting@tm.com",
    mobile_phone_number: str = "+442079460536",
    home_phone_number: str = "+442079460536",
    business_phone_number: str = "+442079460536",
    contact_method: str = "CUSTOMER_CONTACT_METHOD_NONE",
    country_of_residence: str = "GB",
    country_of_taxation: str = "GB",
    accessibility: str = "CUSTOMER_ACCESSIBILITY_AUDIO",
    additional_details: dict[str, str] | None = None,
) -> str:
    """Creates a customer via the Core API. All fields as per the Core API endpoint.

    :return: The created customer id
    """

    default_customer = {
        "request_id": uuid.uuid4().hex,
        "customer": {
            "id": id,
            "status": "CUSTOMER_STATUS_ACTIVE",
            "customer_details": {
                "title": title,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "dob": dob,
                "gender": gender,
                "nationality": nationality,
                "email_address": email_address,
                "mobile_phone_number": mobile_phone_number,
                "home_phone_number": home_phone_number,
                "business_phone_number": business_phone_number,
                "contact_method": contact_method,
                "country_of_residence": country_of_residence,
                "country_of_taxation": country_of_taxation,
                "accessibility": accessibility,
            },
            "additional_details": additional_details,
        },
    }

    customer = endtoend.helper.send_request(
        "post", "/v1/customers", data=json.dumps(default_customer)
    )

    log.info("Customer %s created", customer["id"])
    endtoend.testhandle.customers.append(customer["id"])
    return customer["id"]


def get_customer(customer_id):
    resp = endtoend.helper.send_request("get", "/v1/customers/" + customer_id)
    return resp


def get_existing_test_customer():
    if endtoend.testhandle.customers:
        return endtoend.testhandle.customers[0]
    else:
        return create_customer()


def set_customer_status(customer_id, status):
    post_body = {
        "request_id": uuid.uuid4().hex,
        "customer": {"status": status},
        "update_mask": {"paths": ["status"]},
    }

    resp = endtoend.helper.send_request(
        "put", "/v1/customers/" + customer_id, data=json.dumps(post_body)
    )
    log.info("Customer %s set to %s", customer_id, status)
    return resp


@deprecated("Use get_customer_accounts_v2 on Vault 5 and above.")
def get_customer_accounts(customer_id: str):
    resp = endtoend.helper.send_request(
        "get",
        "/v1/accounts",
        params={"stakeholder_id": customer_id, "page_size": "100"},
    )

    return resp["accounts"]


def get_customer_accounts_v2(customer_id: str):
    resp = endtoend.helper.send_request(
        "get",
        "/v2/accounts",
        params={
            "stakeholder_id": urllib.parse.quote(customer_id),
            "page_size": "100",
            "type": AccountV2Type.ACCOUNT_TYPE_CUSTOMER.value,
        },
    )

    return resp["accounts"]


def get_customer_addresses(customer_id: str):
    body = {"customer_id": customer_id, "page_size": "1000", "include_previous": "True"}

    resp = endtoend.helper.send_request("get", "/v1/customer-addresses", params=body)

    # A list of customer addresses, ordered by descending creation time.
    return resp["customer_addresses"]


def create_payment_device(routing_info, status="PAYMENT_DEVICE_STATUS_ACTIVE"):
    post_body = {
        "payment_device": {"routing_info": routing_info, "status": status},
        "request_id": uuid.uuid4().hex,
    }

    resp = endtoend.helper.send_request("post", "/v1/payment-devices", data=json.dumps(post_body))

    return resp


def create_parameter_resource(post_body: CreateParameterResourceV1RequestBody) -> dict[str, Any]:
    return endtoend.helper.send_request("post", "/v1/parameters", data=post_body.model_dump_json())


def batch_get_parameter_resources(ids: Iterable[str]) -> BatchGetParameterResourceV1ResponseBody:
    return BatchGetParameterResourceV1ResponseBody.model_validate(
        endtoend.helper.send_request("get", "/v1/parameters:batchGet", params={"ids": ids})
    )


def batch_create_parameter_values(
    post_body: BatchCreateParameterValueV1RequestBody,
) -> dict[str, Any]:
    return endtoend.helper.send_request(
        "post", "/v1/parameter-values:batchCreate", data=post_body.model_dump_json()
    )


def update_parameter_value(
    parameter_value_id: str,
    effective_to_timestamp: core_api.OptionalDatetime | None = None,
    is_cancelled: bool | None = None,
    skip_pre_parameter_change_hook: bool | None = None,
) -> core_api.ParameterValueResource:
    """
    Updates a Parameter Value
    :param parameter_value_id: Unique UUID identifier for the Parameter Value.
    :param effective_to_timestamp: The time until which the Parameter Value is effective
    (excluding this time), in UTC. Optional.
    :param is_cancelled: Indicates whether this Parameter Value has been cancelled before
    it became effective. Optional.
    :param skip_pre_parameter_change_hook: Indicates whether not to run the Smart Contract's pre
    parameter change hook for this Parameter Value update. only take effect if the request cancels
    the Parameter Value. Optional.
    :return: the updated parameter value resource
    """
    if endtoend.testhandle.vault_version < Version("5.1.0") and (
        is_cancelled or skip_pre_parameter_change_hook
    ):
        raise ValueError(
            "The /v1/parameter-values endpoint only supports is_cancelled and "
            "skip_pre_parameter_change_hook on Vault 5.1 and above."
        )

    update_mask_paths: list[str] = list()
    if effective_to_timestamp and is_cancelled:
        raise ValueError(
            "The /v1/parameter-values update can only cancel or set the effective-to time"
        )

    if is_cancelled:
        update_mask_paths.append("is_cancelled")
        parameter_value = core_api.UpdateParameterValueV1ParameterValue(is_cancelled=is_cancelled)
    elif effective_to_timestamp:
        update_mask_paths.append("effective_to_timestamp")
        parameter_value = core_api.UpdateParameterValueV1ParameterValue(
            effective_to_timestamp=effective_to_timestamp.isoformat()
        )
    else:
        raise NameError("No update mask specifying field to update")

    is_cancelled_update_options = core_api.IsCancelledUpdateOptions(
        skip_pre_parameter_change_hook=skip_pre_parameter_change_hook or False
    )

    post_body = core_api.UpdateParameterValueV1RequestBody(
        request_id=str(uuid.uuid4()),
        parameter_value=parameter_value,
        update_mask=UpdateMask(paths=update_mask_paths),
        is_cancelled_update_options=is_cancelled_update_options,
    )

    resp = endtoend.helper.send_request(
        "put", "/v1/parameter-values/" + parameter_value_id, data=post_body.model_dump_json()
    )

    log.info(f"Update Parameter Value ID {parameter_value_id}")

    return core_api.ParameterValueResource.model_validate(resp)


def get_parameter_values(
    parameter_ids: list[str],
    account_ids: list[str] | None = None,
    effective_timestamp_range_from: core_api.OptionalDatetime | None = None,
    effective_timestamp_range_to: core_api.OptionalDatetime | None = None,
) -> list[core_api.ParameterValueResource]:
    """
    Get a list of Parameter Values for the given Parameter IDs.

    :param parameter_ids: Parameter IDs to filter values on.
    :param account_ids: Account IDs to filter values on. Optional.
    :param effective_timestamp_range_from: Values in this range must be less than the value of to.
    Optional.
    :param effective_timestamp_range_to: Values in this range must be greater than or equal to the
    value of from. Optional.
    :return: A list of ParameterValueResource with the specified parameter_ids else return empty
        list.
    """
    body = {
        "parameter_ids": parameter_ids or [],
        "account_ids": account_ids or [],
        "effective_timestamp_range.from": isoformat(effective_timestamp_range_from),
        "effective_timestamp_range.to": isoformat(effective_timestamp_range_to),
    }
    parameter_value_resources = endtoend.helper.list_resources("parameter-values", params=body)
    return [
        core_api.ParameterValueResource.model_validate(parameter_value_resource)
        for parameter_value_resource in parameter_value_resources
    ]


def create_parameter_value_hierarchy_node(
    request_id: str, parameter_value_hierarchy_node: CreateParameterValueHierarchyNode
) -> core_api.ParameterValueHierarchyNode:
    """
    Creates a Parameter Value Hierarchy Node
    :param request_id: str, unique string ID that is used to ensure the request is idempotent
    :param parameter_value_hierarchy_node: CreateParameterValueHierarchyNode definition from
    core_api data model
    :return: the created parameter value hierarchy node resource
    """
    data = CreateParameterValueHierarchyNodeRequestBody(
        request_id=request_id, parameter_value_hierarchy_node=parameter_value_hierarchy_node
    )

    request_response = endtoend.helper.send_request(
        "post", "/v1/parameter-value-hierarchy-nodes", data=data.model_dump_json()
    )

    log.info(f"Created Parameter Value Hierarchy Node: {parameter_value_hierarchy_node}")

    return core_api.ParameterValueHierarchyNode.model_validate(request_response)


@deprecated("Use create_internal_account_v2 on Vault 5 and above.")
def create_internal_account(
    request_id: str,
    internal_account_id: str,
    product_id: str,
    accounting_tside: str,
    permitted_denominations: list | None = None,
    details: dict[str, str] | None = None,
) -> dict[str, Any]:
    post_body = {
        "request_id": request_id,
        "internal_account": {
            "id": internal_account_id,
            "product_id": product_id,
            "permitted_denominations": permitted_denominations,
            "details": details,
            "accounting": {"tside": accounting_tside},
        },
    }

    resp = endtoend.helper.send_request("post", "/v1/internal-accounts", data=json.dumps(post_body))
    return resp


def create_customer_account_v2(
    request_id: str,
    account: CustomerAccountRequestBody,
    create_options: CreateOptions | None = None,
) -> CreateAccountV2Response:
    data = CreateAccountV2RequestBody(
        request_id=request_id,
        account=account,
        create_options=create_options,
    )
    return create_account_v2(data)


def create_internal_account_v2(
    request_id: str,
    account: InternalAccountRequestBody,
) -> CreateAccountV2Response:
    data = CreateAccountV2RequestBody(
        request_id=request_id,
        account=account,
        create_options=None,
    )
    return create_account_v2(data)


def create_account_v2(data: CreateAccountV2RequestBody) -> CreateAccountV2Response:
    response: dict[str, Any] = endtoend.helper.send_request(
        "post", "/v2/accounts", data=data.model_dump_json()
    )
    parsed_response = CreateAccountV2Response.model_validate(response)
    return parsed_response


def create_payment_device_link(
    payment_device_id,
    account_id,
    token=None,
    status="PAYMENT_DEVICE_LINK_STATUS_ACTIVE",
):
    post_body = {
        "payment_device_link": {
            "token": token,
            "payment_device_id": payment_device_id,
            "account_id": account_id,
            "status": status,
        },
        "request_id": uuid.uuid4().hex,
    }

    resp = endtoend.helper.send_request(
        "post", "/v1/payment-device-links", data=json.dumps(post_body)
    )

    return resp


def get_payment_device_links(
    tokens=None,
    payment_device_ids=None,
    account_ids=None,
    effective_timestamp=None,
    include_inactive=None,
):
    # Returns a list of payment device links, or an empty list if none found.

    resp = endtoend.helper.send_request(
        "get",
        "/v1/payment-device-links",
        params={
            "tokens": tokens,
            "payment_device_ids": payment_device_ids,
            "account_ids": account_ids,
            "effective_timestamp": effective_timestamp,
            "include_inactive": include_inactive,
        },
    )

    return resp["payment_device_links"]


def get_payment_device(payment_device_ids):
    # If this ID doesn't exist, Vault will throw an error

    resp = endtoend.helper.send_request(
        "get", "/v1/payment-devices:batchGet", params={"ids": payment_device_ids}
    )

    return resp["payment_devices"][payment_device_ids]


def get_uk_acc_num_and_sort_code(account_id):
    pd_link = get_payment_device_links(account_ids=account_id)

    if len(pd_link) == 0:
        raise NameError("No payment device link found for " "account {}".format(account_id))

    # todo: Search through all pd_links
    pd = get_payment_device(pd_link[0]["payment_device_id"])

    if all(word in pd["routing_info"] for word in ["account_number", "bank_id"]):
        return pd["routing_info"]["account_number"], pd["routing_info"]["bank_id"]
    else:
        raise NameError(
            "No account number or sort code found for account "
            "{}. Has it been set up with UK routing info?".format(account_id)
        )


def create_flag_definition(
    flag_definition_id: str,
    name: str = "",
    description: str = "",
    required_flag_level: str = "FLAG_LEVEL_ACCOUNT",
    flag_visibility: str = "FLAG_VISIBILITY_CONTRACT",
) -> dict[str, str]:
    name = name or flag_definition_id
    description = description or flag_definition_id

    post_body = {
        "request_id": uuid.uuid4().hex,
        "flag_definition": {
            "id": flag_definition_id,
            "name": name,
            "description": description,
            "required_flag_level": required_flag_level,
            "flag_visibility": flag_visibility,
        },
    }

    resp = endtoend.helper.send_request("post", "/v1/flag-definitions", data=json.dumps(post_body))
    log.info(f"Flag definition created: {flag_definition_id}")
    return resp


def list_flag_definitions(
    flag_visibility: str = "FLAG_VISIBILITY_CONTRACT",
    flag_levels: list[str] | None = None,
    include_inactive: str = "true",
) -> list[dict[str, Any]]:
    body = {
        "flag_visibility_level": flag_visibility,
        "flag_levels": flag_levels or ["FLAG_LEVEL_ACCOUNT", "FLAG_LEVEL_CUSTOMER"],
        "include_inactive": include_inactive,
    }
    resp = endtoend.helper.list_resources("flag-definitions", params=body)
    return resp


def batch_get_flag_definitions(ids: list[str]) -> dict[str, dict[str, str]]:
    return endtoend.helper.send_request(
        "get", "/v1/flag-definitions:batchGet", params={"ids": ids}
    )["flag_definitions"]


@overload
def create_flag(
    *,
    flag_name: str,
    account_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: core_api.FlagV1FlagValue = core_api.FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1AccountFlag: ...


@overload
def create_flag(
    *,
    flag_name: str,
    customer_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: core_api.FlagV1FlagValue = core_api.FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1CustomerFlag: ...


@overload
def create_flag(
    *,
    flag_name: str,
    payment_device_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: core_api.FlagV1FlagValue = core_api.FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1PaymentDeviceFlag: ...


def create_flag(
    flag_name: str,
    account_id: str | None = None,
    customer_id: str | None = None,
    payment_device_id: str | None = None,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: core_api.FlagV1FlagValue = core_api.FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1Flag:
    """
    :param flag_name: This corresponds to the flag_definition_id in the API.
    :param account_id: One of account_id, customer_id, or payment_device_id must be supplied.
    :param customer_id: One of account_id, customer_id, or payment_device_id must be supplied.
    :param payment_device_id: One of account_id, customer_id, or payment_device_id must be
    supplied.
    :param description: Metadata for the flag.
    :param effective_timestamp: When the flag should start being applied.
    :param expiry_timestamp: When the flag should stop being applied.
    :param is_backdated: This is new in Vault 5.2.  Supply it if effective_timestamp is earlier
    than the flag's creation date.  If unspecified it will not be included in the output in order
    to maintain compatibility with versions of Vault earlier than 5.2.
    :param value: The flag will behave as True in the smart contract when set to
    FlagValue.FLAG_VALUE_ON; False when set to FlagValue.FLAG_VALUE_OFF.
    """
    if is_backdated and endtoend.testhandle.vault_version < Version("5.2.0"):
        raise ValueError(
            "The /v1/flags endpoint only supports is_backdated on Vault 5.2 and above."
        )

    description = description or flag_name
    flag: core_api.CreateFlagV1Flag | None = None
    entity_type = ""
    if account_id:
        entity_type = "account"
        flag = core_api.CreateFlagV1CreateAccountFlag(
            account_id=account_id,
            flag_definition_id=flag_name,
            description=description,
            effective_timestamp=effective_timestamp,
            expiry_timestamp=expiry_timestamp,
            is_backdated=is_backdated,
            value=value,
        )
    elif customer_id:
        entity_type = "flag"
        flag = core_api.CreateFlagV1CreateCustomerFlag(
            customer_id=customer_id,
            flag_definition_id=flag_name,
            description=description,
            effective_timestamp=effective_timestamp,
            expiry_timestamp=expiry_timestamp,
            is_backdated=is_backdated,
            value=value,
        )
    elif payment_device_id:
        entity_type = "payment_device"
        flag = core_api.CreateFlagV1CreatePaymentDeviceId(
            payment_device_id=payment_device_id,
            flag_definition_id=flag_name,
            description=description,
            effective_timestamp=effective_timestamp,
            expiry_timestamp=expiry_timestamp,
            is_backdated=is_backdated,
            value=value,
        )
    else:
        raise NameError("No target has been specified so flag can not be applied!")

    post_body = core_api.CreateFlagV1RequestBody(
        request_id=str(uuid.uuid4()),
        flag=flag,
    )

    resp = endtoend.helper.send_request("post", "/v1/flags", data=post_body.model_dump_json())
    log.info(
        f"Flag applied to {entity_type} {account_id or customer_id or payment_device_id}: "
        f"{description}"
    )
    return core_api.FlagV1Flag.model_validate(resp)


def remove_flag(flag_id: str) -> dict[str, str]:
    put_body = {
        "request_id": uuid.uuid4().hex,
        "flag": {
            "is_active": False,
        },
        "update_mask": {"paths": ["is_active"]},
    }
    resp = endtoend.helper.send_request("put", f"/v1/flags/{flag_id}", data=json.dumps(put_body))
    log.info(f'Flag {flag_id} {resp["description"]} removed')
    return resp


def get_flag(
    flag_name: str,
    account_ids: list[str] | None = None,
    effective_timestamp_range_from: datetime | None = None,
    effective_timestamp_range_to: datetime | None = None,
) -> list[dict[str, Any]]:
    body = {
        "flag_definition_id": flag_name,
        "account_ids": account_ids or [],
        "effective_timestamp_range.from": isoformat(effective_timestamp_range_from),
        "effective_timestamp_range.to": isoformat(effective_timestamp_range_to),
    }
    resp = endtoend.helper.list_resources("flags", params=body)
    return resp


def create_restriction_set_definition_version(
    restriction_set_definition_id: str,
    restriction_type: str,
    restriction_levels: list[str],
    description: str | None = None,
    request_id: str | None = None,
):
    description = description or restriction_set_definition_id

    post_body = {
        "request_id": request_id or uuid.uuid4().hex,
        "restriction_set_definition_version": {
            "restriction_set_definition_id": restriction_set_definition_id,
            "description": description,
            "restriction_definitions": [
                {
                    "restriction_type": restriction_type,
                    "required_restriction_levels": restriction_levels,
                }
            ],
        },
    }

    resp = endtoend.helper.send_request(
        "post",
        f"/v1/restriction-set-definition/{restriction_set_definition_id}/versions",
        data=json.dumps(post_body),
    )
    log.info(f"Restriction Set Definition created: {description}")
    return resp


def create_restriction_set(
    account_id: str, restriction_set_definition_id: str, name: str = "", description: str = ""
) -> dict:
    name = name or restriction_set_definition_id
    description = description or restriction_set_definition_id

    post_body = {
        "request_id": uuid.uuid4().hex,
        "restriction_set": {
            "restriction_set_definition_id": restriction_set_definition_id,
            "name": name,
            "description": description,
            "restriction_set_parameters": {},
            "account_id": account_id,
        },
    }

    resp = endtoend.helper.send_request("post", "/v1/restriction-sets", data=json.dumps(post_body))
    log.info(
        f"Restriction definition {restriction_set_definition_id} applied to account %s", account_id
    )
    return resp


def remove_restriction_set(account_id: str, restriction_set_id: str):
    resp = update_restriction_set(restriction_set_id, "is_active", False)
    log.info(f"Restriction set {restriction_set_id} removed from account {account_id}")
    return resp


def update_restriction_set(restriction_set_id: str, update_field: str, update_value: str | bool):
    post_body = {
        "request_id": uuid.uuid4().hex,
        "restriction_set": {"id": restriction_set_id, update_field: update_value},
        "update_mask": {"paths": [update_field]},
    }

    resp = endtoend.helper.send_request(
        "put", "/v1/restriction-sets/" + restriction_set_id, data=json.dumps(post_body)
    )
    log.info(f"Restriction set {restriction_set_id} updated: {update_field} set to {update_value}")
    return resp


def get_account_schedule_assocs(account_id: str) -> list[dict[str, str]]:
    body = {
        "account_id": account_id,
    }
    resp = endtoend.helper.list_resources("account-schedule-assocs", params=body)

    # A list of account to schedule associations
    return resp


def batch_get_schedules(schedule_ids) -> dict[str, dict[str, str]]:
    body = {"ids": schedule_ids}

    resp = endtoend.helper.send_request("get", "/v1/schedules:batchGet", params=body)

    # A dict of schedule_id to schedule objects
    return resp["schedules"]


def get_jobs(schedule_id: str) -> list[dict[str, Any]]:
    """
    Gets all the jobs with the specified schedule_id
    :param schedule_id: id for filtering which jobs to retrieved.
    :return: list of schedules with the specified schedule_id else
    return empty list
    """
    body = {"schedule_id": schedule_id}
    return endtoend.helper.list_resources("jobs", params=body)


def get_plan_schedules(plan_id: str) -> list[dict[str, str]]:
    """
    Fetches all the schedules for a plan. The underlying endpoint only returns active schedules
    and there is no way to modify this behaviour
    """

    body = {"plan_id": plan_id}
    return endtoend.helper.list_resources("plan-schedules", page_size=20, params=body)


def get_account_derived_parameters(account_id: str, effective_timestamp: str = ""):
    body: dict[str, str | list[str]] = {
        "fields_to_include": ["INCLUDE_FIELD_DERIVED_INSTANCE_PARAM_VALS"]
    }
    if effective_timestamp:
        body.update({"instance_param_vals_effective_timestamp": effective_timestamp})

    resp = endtoend.helper.send_request("get", f"/v1/accounts/{account_id}", params=body)

    return resp["derived_instance_param_vals"]


def get_live_balances(
    account_id: str,
) -> list[dict[str, str]]:
    params = {
        "account_ids": account_id,
    }

    return endtoend.helper.list_resources("balances/live", params)


def get_timerange_balances(
    account_id: str,
    from_value_time: datetime | None = None,
    to_value_time: datetime | None = None,
) -> list[dict[str, str]]:
    params = {
        "account_ids": account_id,
    }

    if from_value_time:
        params.update({"from_time": from_value_time.astimezone(timezone.utc).isoformat()})
    if to_value_time:
        params.update({"to_time": to_value_time.astimezone(timezone.utc).isoformat()})

    return endtoend.helper.list_resources("balances/timerange", params)


class HasNextPageToken(Protocol):
    next_page_token: str


class HasPageToken(Protocol):
    page_token: str | None = None


# TypeVars to preserve the actual concrete types
RequestT = TypeVar("RequestT", bound=HasPageToken)
ResponseT = TypeVar("ResponseT", bound=HasNextPageToken)
Resource = TypeVar("Resource")


def list_all(
    list_api_call: Callable[[RequestT], ResponseT],
    request: RequestT,
    element_retriever: Callable[[ResponseT], list[Resource]],
) -> list[Resource]:
    """
    A helper method to paginate through all the pages returned by a list request.

    :param list_api_call: The function that will make the call to the API. The input is the provided
        'request' parameter which has a page_token field. The output is the response from the call
        with a next_page_token field.
    :param request: The request to send to the API.
    :param element_retriever: A function to retrieve the resources from the response. The input is
        the result from the call to the API and the output should be a list of resources you want
        returned.
    :return: All the results returned by the 'element_retriever' callable in a single
        list.
    """
    result = []
    while True:
        response = list_api_call(request)
        result.extend(element_retriever(response))
        if not response.next_page_token:
            break
        request.page_token = response.next_page_token
    return result


def list_balances_live(
    request: core_api.ListBalancesLiveRequest,
) -> core_api.ListBalancesLiveResponse:
    """
    Lists and filters balances using the v2 balance live endpoint.

    :param request: A request containing the filters used to list balances.
    :returns: A list of balances that match the applied filters.
    """
    return core_api.ListBalancesLiveResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v2/balances/live",
            params=request.model_dump(),
        )
    )


def list_balances_end(
    request: core_api.ListBalancesEndRequest,
) -> core_api.ListBalancesEndResponse:
    """
    Lists and filters the end balances of an account, including future-dated postings, using the v2
    balance end endpoint.

    :param request: A request containing the filters used to list balances.
    :returns: A list of balances that match the applied filters.
    """
    return core_api.ListBalancesEndResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v2/balances/end",
            params=request.model_dump(),
        )
    )


def list_balances_series(
    request: core_api.ListBalancesSeriesRequest,
) -> core_api.ListBalancesSeriesResponse:
    """
    Lists and filters a time series of balances for an account using the v2 balance series endpoint.

    :param request: A request containing the filters used to list balances.
    :returns: A list of balances that match the applied filters.
    """
    return core_api.ListBalancesSeriesResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v2/balances/series",
            params=request.model_dump(),
        )
    )


def get_account_update(account_update_id: str) -> dict[str, Any]:
    """
    Retrieve a specific account update by its ID.

    :param account_update_id: ID of the account update to retrieve.
    :return: The account update resource.
    """

    resp = endtoend.helper.send_request("get", f"/v1/account-updates/{account_update_id}")

    return resp


def get_account_updates(account_id: str, statuses: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Get a list of account updates for a given account
    :param account_id: account id for the account to get updates for
    :param statuses: statuses of account updates to filter on. Optional.
    :return: list of account updates matching the criteria
    """

    params = {"account_id": account_id, "statuses": statuses}
    return endtoend.helper.list_resources("account-updates", params)


def get_account_updates_by_type(
    account_id: str, update_types: list[str], statuses: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    Gets a list of account updates and filters by type
    :param account_id: the account id to get account updates for
    :param update_types: the list of account update types we want to filter for (not handled in API)
    :param statuses: the list of account update statuses we want to filter for (handled in API)
    :return: list of account updates
    """

    account_updates = get_account_updates(account_id, statuses)
    account_updates_by_type = [
        account_update
        for account_update in account_updates
        for update_type in update_types
        if update_type in account_update
    ]
    return account_updates_by_type


def get_product_version(product_version_id: str, include_code: bool = False) -> dict:
    """
    Fetches product version from instance.

    :param product_version_id: Instance version id of the product, not the id found in the sc file
    :param include_code: Specifies whether raw code needs to be included in response
    """
    view = ["PRODUCT_VERSION_VIEW_INCLUDE_CODE"] if include_code else []
    params = {"ids": product_version_id, "view": view}
    resp = endtoend.helper.send_request("get", "/v1/product-versions:batchGet", params=params)
    return resp["product_versions"][product_version_id]


def batch_get_product_versions(
    request: core_api.BatchGetProductVersionsRequest,
) -> core_api.BatchGetProductVersionsResponse:
    """
    Retrieves a set of Product Versions by their IDs.

    :param request: contains the list of Product Version IDs to retrieve and an optional view.
    :returns: the retrieved product versions.
    """
    return core_api.BatchGetProductVersionsResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/product-versions:batchGet",
            params=request.model_dump(),
        )
    )


def get_vault_instance_information() -> GetVaultVersionResponse:
    return core_api.GetVaultVersionResponse.model_validate(
        endtoend.helper.send_request("get", "/v1/vault-version")
    )


def create_account_update(
    account_id: str,
    account_update: dict[str, dict[str, Any]],
    account_update_id: str = "",
) -> dict[str, Any]:
    """

    :param account_id: account id of the account to update
    :param account_update: dict where the key is the desired account update (i.e.
    instance_param_vals_update, product_version_update, activation_update, closure_update) and the
    value is the dict with the required parameters for the account update type. For example:
    {
        'instance_param_vals_update': {
            'instance_param_vals': {
                'KEY': 'value1'
            }
        }
    }
    :param account_update_id: optional account update id to use. Randomly generated by service if
    omitted
    :return: The resulting account update resource
    """

    body = {
        "request_id": uuid.uuid4().hex,
        "account_update": {
            "id": account_update_id,
            "account_id": account_id,
            **account_update,
        },
    }
    jsonbody = json.dumps(body)
    resp = endtoend.helper.send_request("post", "/v1/account-updates", data=jsonbody)
    log.info(f"Account update {account_update} created")
    return resp


def create_closure_update(account_id: str) -> dict[str, Any]:
    """
    Creates an account update to re-run the close_code hook once the account status is already
    'ACCOUNT_STATUS_PENDING_CLOSURE'
    :param account_id: the account id of the account to update
    :return: The resulting account update resource
    """
    account_update: dict[str, dict] = {"closure_update": {}}
    return create_account_update(account_id, account_update)


def update_account_instance_parameters(
    account_id: str, instance_param_vals: dict[str, Any]
) -> dict[str, Any]:
    """
    Creates an account update to update specified instance parameters to the specified values
    :param account_id: the account id of the account to update
    :param instance_param_vals: dictionary of instance parameter names to updated values
    :return: The resulting account update resource
    """
    account_update = {"instance_param_vals_update": {"instance_param_vals": instance_param_vals}}
    return create_account_update(account_id, account_update)


@deprecated("Use update_account_v2 on Vault 5 and above.")
def update_account(account_id: str, status: AccountStatus) -> dict[str, Any]:
    """
    Update an account
    :param account_id: account id of the account to update
    :param status: new account status
    :return: the updated account
    """
    body = {
        "request_id": str(uuid.uuid4()),
        "account": {"status": status.value},
        "update_mask": {"paths": ["status"]},
    }
    return endtoend.helper.send_request("put", "/v1/accounts/" + account_id, data=json.dumps(body))


def update_account_v2(
    account_id: str,
    status: AccountV2Status | None = None,
    smart_contract_version_id: str | None = None,
    stakeholder_ids: list[str] | None = None,
    parameter_value_hierarchy_node_id: str | None = None,
    alias: str | None = None,
    processing_label: str | None = None,
    details: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Update an account
    :param account_id: account id of the account to update

    Only one of the below updateable fields is allowed.
    :param smart_contract_version_id: new target account smart contract version
    :param stakeholder_ids: new list of stakeholder ids on the account
    :param status: new account status
    :param parameter_value_hierarchy_node_id: new parameter value hierarchy node
    for the account to be associated with
    :param alias: new user-provided alias to be associated with the account
    :param processing_label: new processing label, used to target a particular
    internal account for the customer account's processing group
    :param details: user-provided key/value account details. this is purely for use
    by downstream systems
        - entries can be removed by specifying a key with an empty value
        - keys with values will create new entries or replace existing ones
        - any existing entries with keys not in the request will not be modified
    :return: the updated account
    """
    account = UpdateAccountV2Account(
        smart_contract_version_id=smart_contract_version_id,
        stakeholder_ids=stakeholder_ids,
        status=status,
        parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_id,
        alias=alias,
        processing_label=processing_label,
        details=details,
    )
    update_mask = [key for key, value in account.model_dump().items() if value is not None]
    body = UpdateAccountV2RequestBody(
        request_id=str(uuid.uuid4()),
        account=account,
        update_mask=UpdateMask(paths=update_mask),
    )
    return endtoend.helper.send_request(
        "put", "/v2/accounts/" + urllib.parse.quote(account_id), data=body.model_dump_json()
    )


@retry_decorator(exceptions=(HTTPError), on_http_error_codes=[500, 503])
def create_product_version(
    request_id: str,
    code: str,
    product_id: str,
    supported_denominations: list[str],
    tags: list[str] | None = None,
    params: list[Any] | None = None,
    is_internal: bool = False,
    migration_strategy: str = "PRODUCT_VERSION_MIGRATION_STRATEGY_UNKNOWN",
    contract_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Creates a product version by using the core api endpoint
    :param request_id: str, unique string ID that is used to ensure the request is idempotent
    :param code: str, the smart contract code
    :param product_id: str, the ID of the product we want to create
    :param supported_denominations: list[str], the denominations supported by this product version
    :param tags: list[str], tags for the product version
    :param params: list[object], the parameter values for the product version
    :param is_internal: bool, denotes if the product being uploaded is an internal product or not
    :param migration_strategy: str, the migration strategy for applying the new version
    :param contract_properties: dict[str, object], the contract specific property values
    :return: dict[str, object], return value of core api call
    """
    contract_properties = contract_properties or {}
    display_name = contract_properties.get("display_name", "")
    if is_internal:
        migration_strategy = "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"

    post_body = {
        # ProductVersions are immutable, so we can use that to simply return an already created
        # ProductVersion.
        "request_id": request_id,
        "product_version": {
            "product_id": product_id,
            "code": code,
            "supported_denominations": supported_denominations,
            "params": params,
            "tags": tags or [],
            "display_name": display_name,
            "description": "",
            "summary": "",
        },
        "is_internal": is_internal,
        "migration_strategy": migration_strategy,
    }

    return endtoend.helper.send_request("post", "/v1/product-versions", data=json.dumps(post_body))


def batch_update_product_versions(
    request_id: str,
    product_version_updates: list[core_api.ProductVersionUpdate],
) -> core_api.BatchUpdateProductVersionsResponse:
    """
    Batch update product versions by using the Core API `POST /v1/product-versions:batchUpdate`
    endpoint.

    :param request_id: unique string ID that is used to ensure the request is idempotent
    :param product_version_updates: list of ProductVersionUpdate objects defining what should
    be updated
    :return: BatchUpdateProductVersionsResponse containing the updated product
    versions
    """
    request_body = core_api.BatchUpdateProductVersionsRequestBody(
        request_id=request_id,
        product_version_updates=product_version_updates,
    )

    resp = endtoend.helper.send_request(
        "post",
        "/v1/product-versions:batchUpdate",
        data=request_body.model_dump_json(),
    )
    log.info(f"Batch updated {len(product_version_updates)} product versions")
    return core_api.BatchUpdateProductVersionsResponse.model_validate(resp)


@retry_decorator(exceptions=(HTTPError), on_http_error_codes=[500, 503])
def create_product_version_with_validation(
    request_id: str,
    code: str,
    product_id: str,
    supported_denominations: list[str] | None = None,
    tags: list[str] | None = None,
    params: list[core_api.CreateProductVersionParameter] | None = None,
    is_internal: bool = False,
    migration_strategy: core_api.ProductVersionMigrationStrategy | None = None,
    display_name: str | None = None,
    description: str | None = None,
    summary: str | None = None,
    core_tags: list[core_api.ProductVersionCoreTag] | None = None,
    high_volume_eligibility: core_api.HighVolumeEligibility | None = None,
    adjustments_versioning_policy: core_api.AdjustmentsVersioningPolicy | None = None,
) -> core_api.ProductVersion:
    product_version = core_api.CreateProductVersionRequestProductVersion(
        product_id=product_id,
        display_name=display_name,
        description=description,
        summary=summary,
        tags=tags,
        code=code,
        core_tags=core_tags,
        params=params,
        high_volume_eligibility=high_volume_eligibility,
        supported_denominations=supported_denominations,
        adjustments_versioning_policy=adjustments_versioning_policy,
    )

    request = core_api.CreateProductVersionRequestBody(
        request_id=request_id,
        product_version=product_version,
        migration_strategy=migration_strategy,
        is_internal=is_internal,
    )

    response = endtoend.helper.send_request(
        method="post", path="/v1/product-versions", data=request.model_dump_json()
    )

    return core_api.ProductVersion.model_validate(response)


def create_supervisor_contract(
    request_id: str,
    display_name: str,
):
    """
    Creates a supervisor contract. The core api behaviour means we create a product + product
    version in one API call, whereas supervisors contracts and supervisor contract versions are
    created in separate calls.
    :param request_id: str, unique string ID that is used to ensure the request is idempotent
    :param display_name: str, the human-readable name
    :return: dict[str, object], return value of core api call
    """
    post_body = {
        "request_id": request_id,
        "supervisor_contract": {
            "display_name": display_name,
        },
    }
    return endtoend.helper.send_request(
        "post", "/v1/supervisor-contracts", data=json.dumps(post_body)
    )


def create_supervisor_contract_version(
    request_id: str,
    supervisor_contract_id: str,
    display_name: str,
    description: str,
    code: str,
):
    """
    Creates a supervisor contract version by using the core api endpoint
    :param request_id: str, unique string ID that is used to ensure the request is idempotent
    :param supervisor_contract_id: str, The ID of the SupervisorContract of which this is a version
    :param display_name: str, the human-readable name
    :param description: str, the human-readable description
    :param code: str, the smart contract code
    :return: dict[str, object], return value of core api call
    """
    post_body = {
        "request_id": request_id,
        "supervisor_contract_version": {
            "supervisor_contract_id": supervisor_contract_id,
            "display_name": display_name,
            "description": description,
            "code": code,
        },
    }

    return endtoend.helper.send_request(
        "post", "/v1/supervisor-contract-versions", data=json.dumps(post_body)
    )


def create_account_schedule_tag(
    account_schedule_tag_id: str,
    description: str = "",
    sends_scheduled_operation_reports: bool = True,
    schedule_status_override: str = "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_NO_OVERRIDE",
    schedule_status_override_start_timestamp: str | None = None,
    schedule_status_override_end_timestamp: str | None = None,
    test_pause_at_timestamp: str | None = None,
) -> dict[str, str]:
    post_body = {
        "request_id": str(uuid.uuid4()),
        "account_schedule_tag": {
            "id": account_schedule_tag_id,
            "description": description,
            "sends_scheduled_operation_reports": sends_scheduled_operation_reports,
            "schedule_status_override": schedule_status_override,
            "schedule_status_override_start_timestamp": schedule_status_override_start_timestamp,
            "schedule_status_override_end_timestamp": schedule_status_override_end_timestamp,
            "test_pause_at_timestamp": test_pause_at_timestamp,
        },
    }

    return endtoend.helper.send_request(
        "post", "/v1/account-schedule-tags", data=json.dumps(post_body)
    )


def list_account_schedule_tags(result_limit: int) -> list[dict[str, str]]:
    return endtoend.helper.list_resources("account-schedule-tags", result_limit=result_limit)


def batch_get_account_schedule_tags(
    account_schedule_tag_ids: list[str],
) -> dict[str, dict[str, str]]:
    return endtoend.helper.send_request(
        "get",
        "/v1/account-schedule-tags:batchGet",
        params={"ids": account_schedule_tag_ids},
    )["account_schedule_tags"]


def update_account_schedule_tag(
    account_schedule_tag_id: str,
    schedule_status_override: str | None = None,
    schedule_status_override_start_timestamp: str | None = None,
    schedule_status_override_end_timestamp: str | None = None,
    test_pause_at_timestamp: str | None = None,
) -> dict[str, str]:
    update_mask_paths: list[str] = list()
    account_schedule_tag: dict[str, Any] = dict()

    # status, start timestamp and end timestamp must all be set together
    if schedule_status_override:
        update_mask_paths.extend(
            [
                "schedule_status_override",
                "schedule_status_override_start_timestamp",
                "schedule_status_override_end_timestamp",
            ]
        )
        account_schedule_tag.update(
            {
                "schedule_status_override": schedule_status_override,
                "schedule_status_override_start_timestamp": (
                    schedule_status_override_start_timestamp
                ),
                "schedule_status_override_end_timestamp": schedule_status_override_end_timestamp,
            }
        )

    if test_pause_at_timestamp:
        update_mask_paths.append("test_pause_at_timestamp")
        account_schedule_tag["test_pause_at_timestamp"] = test_pause_at_timestamp

    body = json.dumps(
        {
            "request_id": uuid.uuid4().hex,
            "account_schedule_tag": account_schedule_tag,
            "update_mask": {"paths": update_mask_paths},
        }
    )

    return endtoend.helper.send_request(
        "put", f"/v1/account-schedule-tags/{account_schedule_tag_id}", data=body
    )


def get_calendar_events(
    calendar_ids: list[str] | None = None,
    calendar_event_names: list[str] | None = None,
    calendar_timestamp_from: datetime | None = None,
    calendar_timestamp_to: datetime | None = None,
    active_calendar_event: CalendarEventStatus = CalendarEventStatus.ONLY_TRUE,
) -> list[dict[str, Any]]:
    body = {
        "calendar_ids": calendar_ids or [],
        "calendar_event_names": calendar_event_names or [],
        "calendar_timestamp_range.from": (
            calendar_timestamp_from.isoformat() if calendar_timestamp_from else None
        ),
        "calendar_timestamp_range.to": (
            calendar_timestamp_to.isoformat() if calendar_timestamp_to else None
        ),
        "active_calendar_event": active_calendar_event.value,
    }
    resp = endtoend.helper.list_resources("calendar-event", params=body)

    return resp


def create_calendar_event(
    calendar_id: str,
    start_timestamp: datetime,
    end_timestamp: datetime,
    name: str | None = None,
    event_id: str | None = None,
    is_active: bool = True,
):
    post_body = {
        "request_id": uuid.uuid4().hex,
        "calendar_event": {
            "id": event_id,
            "calendar_id": calendar_id,
            "name": name,
            "is_active": is_active,
            "start_timestamp": start_timestamp.isoformat(),
            "end_timestamp": end_timestamp.isoformat(),
        },
    }

    resp = endtoend.helper.send_request("post", "/v1/calendar-event", data=json.dumps(post_body))

    return resp


def list_calendars(
    order_by: str = "ORDER_BY_CREATE_TIMESTAMP_ASC",
    name_pattern_match_pattern: str | None = None,
    name_pattern_match_match_type: str = "MATCH_TYPE_UNKNOWN",
) -> list[dict[str, Any]]:
    body: dict[str, str | None] = {
        "order_by": order_by,
        "name_pattern_match.pattern": name_pattern_match_pattern,
        "name_pattern_match.match_type": name_pattern_match_match_type,
    }
    resp = endtoend.helper.list_resources("calendars", params=body)

    return resp


def create_calendar(
    calendar_id: str,
    is_active: bool = False,
    display_name: str = "",
    description: str = "",
) -> dict[str, str]:
    display_name = display_name or calendar_id
    description = description or calendar_id

    post_body = {
        "request_id": uuid.uuid4().hex,
        "calendar": {
            "id": calendar_id,
            "is_active": is_active,
            "display_name": display_name,
            "description": description,
        },
    }

    resp = endtoend.helper.send_request("post", "/v1/calendar", data=json.dumps(post_body))

    return resp


def update_calendar(
    calendar_id: str,
    is_active: bool | None = None,
    display_name: str | None = None,
    description: str | None = None,
) -> dict[str, str]:
    updated_fields: dict[str, bool | str] = {}
    if is_active is not None:
        updated_fields["is_active"] = is_active
    if display_name is not None:
        updated_fields["display_name"] = display_name
    if description is not None:
        updated_fields["description"] = description

    post_body = {
        "request_id": uuid.uuid4().hex,
        "calendar": updated_fields,
        "update_mask": {"paths": list(updated_fields.keys())},
    }

    resp = endtoend.helper.send_request(
        "put", f"/v1/calendar/{calendar_id}:updateDetails", data=json.dumps(post_body)
    )

    return resp


def get_contract_modules() -> list[dict[str, Any]]:
    resp = endtoend.helper.list_resources("contract-modules", params=None)

    return resp


def get_contract_module_versions(
    contract_module_id: str = "",
) -> list[dict[str, Any]]:
    body = {
        "contract_module_id": contract_module_id,
    }
    resp = endtoend.helper.list_resources("contract-module-versions", params=body, page_size=10)

    return resp


def get_smart_contract_module_version_links(
    contract_version_id: str,
) -> list[dict[str, Any]]:
    resp = endtoend.helper.list_resources(
        "smart-contract-module-versions-links",
        params={"smart_contract_version_ids": contract_version_id},
    )

    return resp


def get_postings_api_client(
    client_id: str,
) -> dict[str, str]:
    return endtoend.helper.send_request("get", "/v1/postings-api-clients/" + client_id)


def create_postings_api_client(
    request_id: str,
    client_id: str,
    response_topic: str,
) -> dict[str, str]:
    post_body = {
        "request_id": request_id,
        "postings_api_client": {
            "id": client_id,
            "response_topic": response_topic,
        },
    }

    return endtoend.helper.send_request(
        "post", "/v1/postings-api-clients", data=json.dumps(post_body)
    )


@retry_decorator()
def init_postings_api_client(client_id: str, response_topic: str) -> dict[str, str]:
    """
    Postings API client can be missing on the target instance (i.e. bootstrap job as part of DR)
    so ensure it's created if it cannot be found.
    """
    try:
        return get_postings_api_client(client_id)
    except HTTPError as e:
        if "404" not in e.args[0]:
            raise HTTPError(
                "Unexpected error when trying to connect to endpoint /v1/postings-api-clients"
            ) from e

        log.info(
            "Could not find existing Postings API Client with ID: %s."
            "Creating new Postings API Client with above ID.",
            client_id,
        )
        return create_postings_api_client(
            request_id=str(uuid.uuid4()),
            client_id=client_id,
            response_topic=response_topic,
        )


def get_processing_group(processing_group_id: str) -> core_api.ProcessingGroup:
    return core_api.ProcessingGroup.model_validate(
        endtoend.helper.send_request("get", "/v1/processing-groups/" + processing_group_id)
    )


def list_processing_groups() -> list[core_api.ProcessingGroup]:
    processing_groups = endtoend.helper.list_resources("processing-groups")
    return [
        core_api.ProcessingGroup.model_validate(processing_group)
        for processing_group in processing_groups
    ]


# This method uses retries as we've experienced 500 errors when tests run in parallel
# The endpoint should likely handle this better, but it is also not likely to expect
# concurrency given the typical use cases.
# Max retries is set fairly high given the cost of having to rerun tests
@retry_decorator(exceptions=(HTTPError), on_http_error_codes=[500], max_retries=10)
def update_processing_group(
    processing_group_id: str,
    update_request: core_api.UpdateProcessingGroupRequestBody,
) -> core_api.ProcessingGroup:
    return core_api.ProcessingGroup.model_validate(
        endtoend.helper.send_request(
            "put",
            "/v1/processing-groups/" + processing_group_id,
            data=update_request.model_dump_json(),
        )
    )


def create_posting_instruction_batch(
    request: core_api.CreatePostingInstructionBatchRequest,
) -> core_api.CreatePostingInstructionBatchResponse:
    """
    Creates a posting instruction batch using the synchronous posting api endpoint.

    :param request: contains the posting instruction batch to be created.
    :returns: the created posting instruction batch and a list of all live balances for the
        account.
    """

    return core_api.CreatePostingInstructionBatchResponse.model_validate(
        endtoend.helper.send_request(
            "post",
            "/v1/posting-instruction-batches",
            data=request.model_dump_json(),
        )
    )


def list_posting_instruction_batches(
    request: core_api.ListPostingInstructionBatchesRequest,
) -> core_api.ListPostingInstructionBatchesResponse:
    """
    Lists and filters posting instruction batches using the synchronous posting api endpoint.

    :param request: contains the filters used to list posting instruction batches.
    :returns: list of posting instruction batches that match the applied filters.
    """
    return core_api.ListPostingInstructionBatchesResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/posting-instruction-batches",
            params=request.model_dump(),
        )
    )


def batch_get_posting_instruction_batches(
    request: core_api.BatchGetPostingInstructionBatchesRequest,
) -> core_api.BatchGetPostingInstructionBatchesResponse:
    """
    Retrieves a set of Posting Instruction Batches by their IDs using the synchronous posting api
    endpoint.

    :param request: contains the list of Posting Instruction Batch IDs to retrieve.
    :returns: map of requested IDs to CommittedPostingInstructionBatch objects.
    """
    return core_api.BatchGetPostingInstructionBatchesResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/posting-instruction-batches:batchGet",
            params=request.model_dump(),
        )
    )


def list_adjustments(
    request: core_api.ListAdjustmentsRequest,
) -> core_api.ListAdjustmentsResponse:
    """
    Lists and filters Adjustments using the Adjustments endpoint.

    :param request: contains the filters used to list Adjustments.
    :returns: list of Adjustments that match the applied filters.
    """
    return core_api.ListAdjustmentsResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/adjustments",
            params=request.model_dump(),
        )
    )


def batch_get_adjustments(
    request: core_api.BatchGetAdjustmentsRequest,
) -> core_api.BatchGetAdjustmentsResponse:
    """
    Retrieves a set of Adjustments by their IDs.

    :param request: contains the list of Adjustment IDs to retrieve.
    :returns: dict from requested IDs to Adjustments.
    """
    return core_api.BatchGetAdjustmentsResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/adjustments:batchGet",
            params=request.model_dump(),
        )
    )


def bulk_retry_adjustments(
    request: core_api.BulkRetryAdjustmentsRequest,
) -> core_api.BulkRetryAdjustmentsResponse:
    """
    Retries Adjustments with status of ERROR.

    :param request: contains the list of Adjustment IDs to retry.
    :returns: dict from retried IDs to errored Adjustments.
    """
    return core_api.BulkRetryAdjustmentsResponse.model_validate(
        endtoend.helper.send_request(
            "post",
            "/v1/adjustments:bulkRetry",
            data=request.model_dump(),
        )
    )


def list_sub_accounts(
    request: core_api.ListSubAccountsRequest,
) -> core_api.ListSubAccountsResponse:
    """
    Lists and filters Sub-Accounts using the Sub-Accounts endpoint.

    :param request: contains the filters used to list Sub-Accounts.
    :returns: list of Sub-Accounts that match the applied filters.
    """
    return core_api.ListSubAccountsResponse.model_validate(
        endtoend.helper.send_request(
            method="get",
            path="/v1/sub-accounts",
            params=request.model_dump(),
        )
    )


def batch_get_sub_accounts(
    request: core_api.BatchGetSubAccountsRequest,
) -> core_api.BatchGetSubAccountsResponse:
    """
    Retrieves Sub-Accounts by their IDs.

    :param request: contains the filters for /v1/sub-accounts:batchGet
    :returns: dict from requested IDs to Sub-Accounts.
    """
    return core_api.BatchGetSubAccountsResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/sub-accounts:batchGet",
            params=request.model_dump(),
        )
    )


def batch_get_products(
    request: core_api.BatchGetProductsRequest,
) -> core_api.BatchGetProductsResponse:
    """
    Retrieves Products by their ids.

    :param request: contains the filters batch get products
    :returns: the retrieved products
    """
    return core_api.BatchGetProductsResponse.model_validate(
        endtoend.helper.send_request(
            "get",
            "/v1/products:batchGet",
            params=request.model_dump(),
        )
    )


def list_product_versions(
    request: core_api.ListProductVersionsRequestBody,
) -> core_api.ListProductVersionsResponse:
    """
    Returns the list of product versions

    :param request: request params for list product versions
    :return: list of product versions
    """
    return core_api.ListProductVersionsResponse.model_validate(
        endtoend.helper.send_request(
            method="get",
            path="/v1/product-versions",
            params=request.model_dump(),
        )
    )


def update_product_version_params(
    request: core_api.UpdateProductVersionParamsRequestBody,
) -> core_api.ProductVersion:
    """
    Updates the value of one or more parameters for a product version.

    :param request: contains the parameter values to update for a give product version.
    :return: the updated product version
    """
    return core_api.ProductVersion.model_validate(
        endtoend.helper.send_request(
            method="put",
            path=f"/v1/product-versions/{request.product_version_id}:updateParams",
            data=request.model_dump_json(),
        )
    )


def list_product_version_timeseries(
    product_version_id: str,
) -> core_api.ProductVersionParamTimeseriesResponse:
    """
    Fetches resolved param timeseries for a given product version.

    :param product_version_id: unique id of the product version
    :return: the product version param time series
    """
    return core_api.ProductVersionParamTimeseriesResponse.model_validate(
        endtoend.helper.send_request(
            method="get",
            path=f"/v1/product-versions/{product_version_id}:paramTimeseries",
        )
    )


def list_account_attributes(
    request: core_api.ListAccountAttributeValuesRequest,
) -> core_api.ListAccountAttributeValuesResponse:
    """
    Fetches account attribute values for a given list of attribute names, account ids, and
    effective timestamps

    Args:
        account_ids (list[str]): list of account IDs
        attribute (list[str]): list of attribute names
        effective_timestamps (list[datetime]): list of effective timestamps

    Returns:
        list[core_api.AccountAttributeValue]: List of fetched account attribute values
    """

    return core_api.ListAccountAttributeValuesResponse.model_validate(
        endtoend.helper.send_request(
            method="get",
            path="/v1/account-attribute-values",
            params=request.model_dump(exclude_none=True),
        )
    )
