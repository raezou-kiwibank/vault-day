# Copyright @ 2020 - 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import ast
import collections
import enum
import hashlib
import json
import logging
import os
import random
import re
import string
import time
import urllib.parse
import uuid
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, overload

# third party
from typing_extensions import deprecated

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.kafka import produce_message
from inception_sdk.common.python.file_utils import load_file_contents, load_module_from_filepath
from inception_sdk.test_framework.common.date_helper import isoformat
from inception_sdk.test_framework.common.utils import (
    _get_nested_dict_keys,
    extract_resource,
    replace_clu_dependencies,
    replace_flags_in_parameter,
    replace_schedule_tag_ids_in_contract,
    strip_clu_notation,
)
from inception_sdk.test_framework.endtoend.core_api_helper import AccountStatus
from inception_sdk.test_framework.endtoend.helper import (
    COMMON_ACCOUNT_SCHEDULE_TAG_PATH,
    SetupError,
    TestProduct,
)
from inception_sdk.test_framework.endtoend.kafka_helper import kafka_only_helper, wait_for_messages
from inception_sdk.tools.common.tools_utils import override_logging_level
from inception_sdk.tools.renderer.render_utils import is_file_renderable
from inception_sdk.tools.renderer.renderer import RendererConfig, SmartContractRenderer
from inception_sdk.vault.contracts.utils import get_contract_required_parameter_resources
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    AccountV2Status,
    AccountV2TSide,
    CreateAccountV2Response,
    CreateOptions,
    CreateParameterResourceV1RequestBody,
    CustomerAccountRequestBody,
    FlagV1FlagValue,
    InternalAccountRequestBody,
    ParameterResource,
)

with override_logging_level(logging.WARNING):
    from black import format_str
    from black.mode import Mode

# third party
from requests import HTTPError

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

CONTRACT_NOTIFICATIONS_TOPIC = "vault.core_api.v1.contracts.contract_notification.events"

VALID_ACCOUNT_SCHEDULE_TAG_TIME_DELTA_FIELDS = (
    "test_pause_at_timestamp",
    "schedule_status_override_start_timestamp",
    "schedule_status_override_end_timestamp",
)

DUMMY_CONTRA = "DUMMY_CONTRA"
# These internal accounts should only be used for IDs that should not be changed into
# e2e composite IDs. e.g. internal account "1"
DEFAULT_REQUIRED_INTERNAL_ACCOUNTS_DICT: dict[AccountV2TSide, list[str]] = {
    AccountV2TSide.T_SIDE_LIABILITY: ["1"],
    AccountV2TSide.T_SIDE_ASSET: [],
}


@overload
def get_contract_content_for_e2e(contract_properties: dict[str, Any], *, product_id: str) -> str:
    """Retrieve contract content using a product ID."""
    ...


@overload
def get_contract_content_for_e2e(
    contract_properties: dict[str, Any], *, product_version_id: str
) -> str:
    """Retrieve contract content using a product version ID."""
    ...


def get_contract_content_for_e2e(
    contract_properties: dict[str, Any],
    product_id: str | None = None,
    product_version_id: str | None = None,
) -> str:
    """
    Renders or loads the smart contract content for end-to-end testing.

    Determines the contract content by either rendering a Python module
    via SmartContractRenderer or reading the raw file content.

    :param contract_properties: A dictionary containing contract metadata.
        Must include a 'path' key.
    :param product_id: Identifier for the product (optional if product_version_id provided).
    :param product_version_id: Identifier for the product version
    (optional if product_id provided).
    :return: The fully rendered or raw content of the contract.
    :raise NameError: If 'path' is missing from contract_properties.
    :raise TypeError: If neither product_id nor product_version_id is provided.
    """
    type_id = product_id or product_version_id

    if not contract_properties.get("path"):
        raise NameError(
            f"Contract: {type_id} was not specified with a valid 'path' property. "
            f"Specified with {str(contract_properties)}"
        )

    contract_path = Path(contract_properties.get("path", ""))
    if is_file_renderable(contract_path):
        sc_module = load_module_from_filepath(str(contract_path))
        scr_config = RendererConfig(
            autogen_warning="# Code auto-generated for e2e testing",
            apply_formatting=False,
            use_git=False,
        )
        scr = SmartContractRenderer(sc_module, renderer_config=scr_config)
        scr.render(write_to_file=False)

        # `load_module_from_filepath` executes the module, which will evaluate the metadata
        # expressions like event_types = [feature.get_event_type(..)]
        if hasattr(sc_module, "event_types"):
            # The __repr__ method will include all attribute, even if they weren't set and
            # have a default value.
            scr.rendered_contract = _replace_event_types_with_repr(
                scr.rendered_contract, repr(sc_module.event_types)
            )

        return scr.rendered_contract
    else:
        return load_file_contents(contract_properties["path"])


def upload_contracts(
    contracts: dict[str, dict[str, Any]],
    e2e_test_case_parameter_resources: list[ParameterResource] | None = None,
) -> None:
    """
    Uploads contracts and creates a mapping between original product ids and run-specific ids, so
    that tests do not need to be aware of the modified ids
    :param contracts: dict[str, dict[str, object]], map of product ids and the corresponding
    dictionary of contract properties

    """
    for product_id, contract_properties in contracts.items():
        e2e_contract_data = get_contract_content_for_e2e(
            product_id=product_id, contract_properties=contract_properties
        )

        if endtoend.testhandle.do_version_check:
            check_product_version(product_id, e2e_contract_data)

        # All resource types that can be contract dependencies and for which we use CLU syntax
        # should have their mapping adding to clu_reference_mappings
        e2e_contract_data = replace_clu_dependencies(
            product_id, e2e_contract_data, endtoend.testhandle.clu_reference_mappings
        )

        # Inception contracts do not use CLU syntax for schedule tags (INC-5281)
        e2e_contract_data = replace_schedule_tag_ids_in_contract(
            contract_data=e2e_contract_data,
            # we process internal products for which no schedules ever exist and therefore cannot
            # be set on the testhandle
            id_mapping=endtoend.testhandle.controlled_schedule_tags.get(product_id, {}),
            default_paused_tag_id=endtoend.testhandle.default_paused_tag_id,
        )

        e2e_contract_data = format_str(e2e_contract_data, mode=Mode(line_length=100))
        contract_parameter_resources: list[ParameterResource] = (
            get_contract_required_parameter_resources(
                product_id,
                e2e_contract_data,
                e2e_test_case_parameter_resources,
            )
        )
        # Create Parameter Resources in Vault, for smart contract Expected Parameters.
        endtoend.contracts_helper.create_parameter_definitions(contract_parameter_resources)

        parameters = contract_properties.get("template_params", {})
        supported_denominations = contract_properties.get("supported_denoms", ["GBP"])
        is_internal = contract_properties.get("is_internal", False)
        display_name = contract_properties.get("display_name", "")
        parameters = sanitise_template_parameters(
            parameters,
            endtoend.testhandle.internal_account_id_to_uploaded_id,
            endtoend.testhandle.flag_definition_id_mapping,
        )
        new_params = [
            {"name": param_name, "value": param_value}
            for param_name, param_value in parameters.items()
        ]
        ordered_params = str(collections.OrderedDict(sorted(parameters.items())))

        code_hash = hashlib.md5(
            (
                e2e_contract_data + str(supported_denominations) + display_name + ordered_params
                or ""
            ).encode("utf-8")
        ).hexdigest()
        e2e_unique_product_id = "e2e_" + product_id + "_" + code_hash

        resp = endtoend.core_api_helper.create_product_version(
            request_id=e2e_unique_product_id,
            code=e2e_contract_data,
            product_id=e2e_unique_product_id,
            supported_denominations=supported_denominations,
            tags=[],
            params=new_params,
            is_internal=is_internal,
            migration_strategy="PRODUCT_VERSION_MIGRATION_STRATEGY_UNKNOWN",
            contract_properties=contract_properties,
        )

        # Vault may have already seen this code with a different product id
        log.info("Contract %s uploaded.", resp["product_id"])
        if is_internal:
            endtoend.testhandle.internal_contract_pid_to_uploaded_pid[product_id] = (
                e2e_unique_product_id
            )
        else:
            # We need to store both the product id and the product version id as supervisor syntax
            # depends on the latter
            endtoend.testhandle.contract_pid_to_uploaded_pid[product_id] = e2e_unique_product_id
            endtoend.testhandle.contract_pid_to_uploaded_product_version_id[product_id] = resp["id"]


def upload_contracts_from_products(
    products: list[TestProduct],
    e2e_test_case_parameter_resources: list[ParameterResource] | None = None,
) -> None:
    """
    Upload logically grouped product versions under a given product. To be used when
    attempting to upload multiple product versions for a given product.

    :param products: Products to upload
    :param e2e_test_case_parameter_resource: List of Parameter resources to create in vault
    """

    for product in products:
        for index, product_version in enumerate(product.product_versions):
            migration_strategy = (
                core_api.ProductVersionMigrationStrategy.NEW_PRODUCT
                if index == 0
                else core_api.ProductVersionMigrationStrategy.ADD_VERSION
            )

            e2e_contract_data = get_contract_content_for_e2e(
                product_version_id=product_version.product_version_id,
                contract_properties={"path": product_version.path},
            )

            if endtoend.testhandle.do_version_check:
                check_product_version(product_version.product_version_id, e2e_contract_data)

            # All resource types that can be contract dependencies and for which we use CLU syntax
            # should have their mapping adding to clu_reference_mappings
            e2e_contract_data = replace_clu_dependencies(
                product_version.product_version_id,
                e2e_contract_data,
                endtoend.testhandle.clu_reference_mappings,
            )
            # Inception contracts do not use CLU syntax for schedule tags (INC-5281)
            e2e_contract_data = replace_schedule_tag_ids_in_contract(
                contract_data=e2e_contract_data,
                id_mapping=endtoend.testhandle.controlled_schedule_tags.get(product.product_id, {}),
                default_paused_tag_id=endtoend.testhandle.default_paused_tag_id,
            )

            e2e_contract_data = format_str(e2e_contract_data, mode=Mode(line_length=100))

            # 3. Sanitise params for each version
            contract_parameter_resources: list[ParameterResource] = (
                get_contract_required_parameter_resources(
                    product_version_id=product_version.product_version_id,
                    contract_code=e2e_contract_data,
                    e2e_test_case_parameter_resources=e2e_test_case_parameter_resources,
                )
            )
            # Create Parameter Resources in Vault, for smart contract Expected Parameters.
            endtoend.contracts_helper.create_parameter_definitions(contract_parameter_resources)

            sanitised_params = sanitise_template_parameters(
                product_version.template_params,
                endtoend.testhandle.internal_account_id_to_uploaded_id,
                endtoend.testhandle.flag_definition_id_mapping,
            )

            # Convert to typed objects for the validation helper
            new_params = [
                core_api.CreateProductVersionParameter(name=n, value=v)
                for n, v in sanitised_params.items()
            ]

            ordered_params = str(collections.OrderedDict(sorted(sanitised_params.items())))
            code_hash = hashlib.md5(
                (e2e_contract_data + ordered_params).encode("utf-8")
            ).hexdigest()

            # If this is the *very first* version of a new product, the E2E product_id must
            # be constructed.
            # If this is a subsequent version, the same product_id generated for the first index
            # MUST be used.

            if index == 0:
                e2e_unique_product_id = f"e2e_{product.product_id}_{code_hash}"
                # store this for subsequent iterations
                endtoend.testhandle.contract_pid_to_uploaded_pid[product.product_id] = (
                    e2e_unique_product_id
                )
            else:
                e2e_unique_product_id = endtoend.testhandle.contract_pid_to_uploaded_pid[
                    product.product_id
                ]

            request_id = f"e2e_{product_version.product_version_id}_{uuid.uuid4().hex}"

            resp: core_api.ProductVersion = (
                endtoend.core_api_helper.create_product_version_with_validation(
                    request_id=request_id,
                    code=e2e_contract_data,
                    product_id=e2e_unique_product_id,
                    supported_denominations=product_version.supported_denominations,
                    tags=[],
                    params=new_params,
                    is_internal=product_version.is_internal,
                    display_name=product_version.display_name,
                    migration_strategy=migration_strategy,
                    adjustments_versioning_policy=product_version.adjustments_versioning_policy,
                )
            )

            log.info(f"Product ID {product.product_id} uploaded as {e2e_unique_product_id}")
            log.info(f"Product Version {product_version.product_version_id} uploaded as {resp.id}")

            endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
                product_version.product_version_id
            ] = resp.id


def sanitise_template_parameters(
    parameters: dict[str, Any] | None,
    internal_account_id_to_uploaded_id: dict[str, str] | None = None,
    flag_definition_id_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Sanitises template parameters in preparation for e2e execution, effectively reversing
    the transformation made by `prepare_parameters_for_e2e`.
    :param parameters: the template parameters to sanitise. Refer to the docstring for
    `prepare_parameters_for_e2e` to understand the supported formats
    :param internal_account_id_to_uploaded_id: a mapping of the original internal account id, as
    defined by the test writer, and the e2e internal account id, defined by the framework
    :param flag_definition_id_mapping: a mapping of the original flag definition id, as
    defined by the test writer, and the e2e flag definition id, defined by the framework
    :return: the sanitised parameters - empty if the parameters passed in were empty or None
    """

    if not parameters or (
        not internal_account_id_to_uploaded_id and not flag_definition_id_mapping
    ):
        return parameters or {}

    internal_account_id_to_uploaded_id = internal_account_id_to_uploaded_id or dict()
    flag_definition_id_mapping = flag_definition_id_mapping or dict()

    sanitised_parameters = parameters.copy()
    for param_name, param_value in parameters.items():
        param_is_not_dict: bool = type(param_value) is not dict
        # Once we only support /v1/parameters, we can use similar logic to
        # substitute_e2e_ids_on_create_options to identify parameters relating to internal accounts
        if "_account" in param_name.lower() and param_is_not_dict:
            log.warning(
                f"If {param_name} is an internal account that should be uploaded by the"
                f" framework, ensure that the end-to-end parameter value is a dictionary with"
                f" key internal_account_key, e.g.  'accrued_interest_payable_account'"
                f": {{'internal_account_key': 'accrued_interest_payable_account'}}"
            )

        if param_is_not_dict:
            continue

        if internal_account_key := param_value.get("internal_account_key"):
            sanitised_parameters[param_name] = internal_account_id_to_uploaded_id[
                internal_account_key
            ]

        # check for nested internal accounts
        if nested_internal_accounts := param_value.get("nested_internal_account_keys"):
            sanitised_parameters[param_name] = json.dumps(
                {
                    key: internal_account_id_to_uploaded_id[
                        param_value["nested_internal_account_keys"][key]["internal_account_key"]
                    ]
                    for key in nested_internal_accounts.keys()
                }
            )
        # check for flags in json params
        if any(key == "flag_key" for key in _get_nested_dict_keys(param_value)):
            sanitised_parameters[param_name] = json.dumps(
                replace_flags_in_parameter(param_value, flag_definition_id_mapping)
            )

    return sanitised_parameters


@deprecated("Use create_account_v2 on Vault 5 and above.")
def create_account(
    customer: str | list[str],
    contract: str,
    instance_param_vals: dict[str, str] | None = None,
    permitted_denominations: list[str] | None = None,
    status: str = "ACCOUNT_STATUS_OPEN",
    details: dict[str, str] | None = None,
    force_contract_id: bool = False,
    wait_for_activation: bool = True,
    opening_timestamp: datetime | str | None = None,
    account_id: str | None = None,
) -> dict[str, Any]:
    """
    :param customer: the customer id to create the account for
    :param contract: the product id to instantiate the account with
    :param instance_param_vals:
    :param permitted_denominations: Defaults to GBP
    :param status: the account status to create the account with. One of ACCOUNT_STATUS_PENDING or
     ACCOUNT_STATUS_OPEN
    :param force_contract_id: if True the actual product id is used instead of the e2e product id
    :param details: account details metadata to add to the account
    :param wait_for_activation: if True the account will only be returned once the activation
    account-update is completed
    have been initialised
    :param opening_timestamp: the time when the account was opened. If supplied during account
    creation, the account must be created with status ACCOUNT_STATUS_OPEN and the opening_timestamp
    value must not be a time in the future.
    :param account_id: override the automatically generated account ID
    :return: the account resource
    """
    request_id = str(uuid.uuid4())
    permitted_denominations = permitted_denominations or ["GBP"]
    if contract not in endtoend.testhandle.contract_pid_to_uploaded_pid and not force_contract_id:
        raise NameError(
            f"Contract ID: {contract} not found. Is it specified in endtoend.testhandle.CONTRACTS?"
        )
    # Store, in Vault Core, the API version that was used to create the account so that when
    # tearing down the account, we can know whether to use the v2 accounts API or the v1 API.
    details = details or {}
    details.update(accounts_api_version="v1")

    post_body = {
        "request_id": request_id,
        "account": {
            "product_id": (
                contract
                if force_contract_id
                else (endtoend.testhandle.contract_pid_to_uploaded_pid[contract])
            ),
            "stakeholder_ids": [customer] if type(customer) is not list else customer,
            "instance_param_vals": instance_param_vals,
            "permitted_denominations": permitted_denominations,
            "status": status,
            "details": details,
            "opening_timestamp": isoformat(opening_timestamp),
        },
    }
    if account_id:
        # We know from above that account holds a dict[str, Any]
        post_body["account"].update({"id": account_id})  # type: ignore

    account = endtoend.helper.send_request("post", "/v1/accounts", data=json.dumps(post_body))
    created_account_id = account["id"]
    endtoend.testhandle.accounts.add(created_account_id)
    log.info(
        f"Created account {created_account_id} for customer {customer} with product {contract}"
    )
    if wait_for_activation:
        endtoend.accounts_helper.wait_for_account_update(created_account_id, "activation_update")

    return account


@overload
def create_account_v2(
    product_id: str,
    account: CustomerAccountRequestBody,
    create_options: CreateOptions | None = None,
) -> CreateAccountV2Response:
    """
    :param product_id: Specifies the product used to create account. This should be the unmapped id
    passed used in the `endtoend.testhandle.CONTRACTS` keys.
    :param account: specifics of the customer account to create. The `smart_contract_version_id`
    will be overridden with the e2e equivalent.
    :param create_options: parameter values to pass to the account.
    :return: the account resource
    """
    ...


@overload
def create_account_v2(
    *,
    product_version_id: str,
    account: CustomerAccountRequestBody,
    create_options: CreateOptions | None = None,
) -> CreateAccountV2Response:
    """
    :param product_version_id: Specifies the product version used to create account. This should
    be the unmapped id passed used in the `endtoend.testhandle.PRODUCTS` keys.
    :param account: specifics of the customer account to create. The `smart_contract_version_id`
    will be overridden with the e2e equivalent.
    :param create_options: parameter values to pass to the account.
    :return: the account resource
    """
    ...


def create_account_v2(
    product_id: str | None = None,
    account: CustomerAccountRequestBody | None = None,
    create_options: CreateOptions | None = None,
    *,
    product_version_id: str | None = None,
) -> CreateAccountV2Response:
    """
    Create a V2 account using either a product ID or a product version ID.

    :param product_id: Specifies the product used to create account.
    :param account: specifics of the customer account to create.
    :param create_options: parameter values to pass to the account.
    :param product_version_id: Specifies the product version used to create account.
    :return: the account resource
    """

    def _create_account_v2(
        *,
        uploaded_product_version_id: str,
        account: CustomerAccountRequestBody,
        request_id: str,
        e2e_create_options: CreateOptions | None,
    ) -> CreateAccountV2Response:
        # Store, in Vault Core, the API version that was used to create the account so that when
        # tearing down the account, we can know whether to use the v2 accounts API or the v1 API.
        account.details = account.details or {}
        account.details.update(accounts_api_version="v2")
        account.smart_contract_version_id = uploaded_product_version_id
        account_response: CreateAccountV2Response = (
            endtoend.core_api_helper.create_customer_account_v2(
                request_id=request_id, account=account, create_options=e2e_create_options
            )
        )
        endtoend.testhandle.accounts.add(account_response.id)
        log.info(
            f"Created account {account_response.id} for "
            f"{'customers' if len(account_response.stakeholder_ids) > 1 else 'customer'} "
            f"{','.join(account_response.stakeholder_ids)} with product version "
            f"id {account_response.smart_contract_version_id}."
        )
        return account_response

    if account is None:
        raise ValueError("Argument 'account' must be provided.")

    if product_id and product_version_id:
        raise ValueError("Cannot provide both 'product_id' and 'product_version_id'.")

    uploaded_product_version_id: str | None = None

    if product_id:
        if product_id not in endtoend.testhandle.contract_pid_to_uploaded_pid:
            raise NameError(
                f"Product ID: {product_id} not found. "
                "Is it specified in endtoend.testhandle.CONTRACTS?"
            )
        uploaded_product_version_id = (
            endtoend.testhandle.contract_pid_to_uploaded_product_version_id[product_id]
        )

    elif product_version_id:
        uploaded_product_version_id = (
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id.get(
                product_version_id
            )
        )
        if uploaded_product_version_id is None:
            raise NameError(
                f"Product version ID: {product_version_id} not found. "
                "Is it specified in endtoend.testhandle.PRODUCTS?"
            )
    else:
        raise ValueError("Must provide either 'product_id' or 'product_version_id'.")

    e2e_create_options = substitute_e2e_ids_on_create_options(create_options)
    request_id = str(uuid.uuid4())
    return _create_account_v2(
        uploaded_product_version_id=uploaded_product_version_id,
        account=account,
        request_id=request_id,
        e2e_create_options=e2e_create_options,
    )


def substitute_e2e_ids_on_create_options(
    create_options: CreateOptions | None = None,
) -> CreateOptions | None:
    if not create_options:
        return create_options

    # strip clu notation from IDs
    create_options_parameter_values = {
        strip_clu_notation(id): parameter_value
        for id, parameter_value in (create_options.parameter_values or {}).items()
    }
    parameter_id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id
    internal_account_id_map = endtoend.testhandle.internal_account_id_to_uploaded_id

    return CreateOptions(
        parameter_values={
            parameter_id_map.get(parameter_id, parameter_id): (
                # Internal accounts are used as parameter values, so we need to map these
                # to their e2e ids. We can't assume any other parameter value constraint
                # types relate to SDK resource creation so we leave these alone
                AccountIdParameterValue(
                    account_id_value=internal_account_id_map.get(
                        parameter.account_id_value, parameter.account_id_value
                    )
                )
                if isinstance(parameter, AccountIdParameterValue)
                else parameter
            )
            for parameter_id, parameter in create_options_parameter_values.items()
        },
        sub_accounts=create_options.sub_accounts,
    )


def batch_create_parameter_values(
    parameter_values: core_api.BatchCreateParameterValueV1RequestBody,
) -> dict[str, Any]:
    id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id
    e2e_parameter_values = deepcopy(parameter_values)
    for p in e2e_parameter_values.parameter_values:
        non_clu_id = strip_clu_notation(p.parameter_id)
        p.parameter_id = id_map.get(non_clu_id, non_clu_id)
    return endtoend.core_api_helper.batch_create_parameter_values(e2e_parameter_values)


@deprecated("Use get_account_v2 on Vault 5 and above.")
def get_account(account_id) -> dict[str, Any]:
    resp = endtoend.helper.send_request("get", "/v1/accounts/" + account_id)
    return resp


def get_account_v2(account_id) -> dict[str, Any]:
    return get_accounts_v2_batchGet([account_id])["accounts"][account_id]


def get_accounts_v2_batchGet(account_ids: list[str]) -> dict[str, Any]:
    ids: str = "&ids=".join(urllib.parse.quote(account_id) for account_id in account_ids)
    return endtoend.helper.send_request("get", "/v2/accounts:batchGet?ids=" + ids)


@deprecated("Use _composite_internal_account_v2_id on Vault 5 and above.")
def _composite_internal_account_id(account_id: str, tside: str) -> str:
    short_tside = "A" if tside == "TSIDE_ASSET" else "L"
    return "e2e_" + short_tside + "_" + account_id


def _composite_internal_account_v2_id(account_id: str, t_side: AccountV2TSide) -> str:
    short_tside = "A" if t_side == AccountV2TSide.T_SIDE_ASSET else "L"
    return "e2e_" + short_tside + "_" + account_id


@deprecated("Use create_internal_account_v2 on Vault 5 and above.")
def create_internal_account(
    account_id: str,
    contract: str,
    accounting_tside: str,
    details: dict[str, str] | None = None,
    use_composite_id: bool = True,
) -> dict[str, Any]:
    """
    Creates an internal account and updates the internal_account_id_to_uploaded_id testhandle
    attribute with the original and final account id.

    :param id: the internal account id used to create a specific account
    :param contract: the product id to instantiate the account with. Must be present in testhandle
    internal_contract_pid_to_uploaded_pid attribute.
    :param accounting_tside: specifies the account tside
    :param details: account details metadata to add to the account
    :param use_composite_id: if True the helper will create a deterministic, e2e-specific account
    id that will be re-used across tests. This helps avoid id clashes in environments used by
    multiple teams
    :return: the created internal account resource
    """
    e2e_account_id = (
        _composite_internal_account_id(account_id=account_id, tside=accounting_tside)
        if use_composite_id
        else account_id
    )

    if len(e2e_account_id) > 36:
        raise SetupError(
            f"Internal account id {e2e_account_id} is longer than 36 characters."
            " Please use an internal account id that is up to 30 characters long if using"
            " a composite id or 36 otherwise"
        )

    if contract not in endtoend.testhandle.internal_contract_pid_to_uploaded_pid:
        raise NameError(
            "Contract ID: {} not found. " "Is it specified in the testfile?".format(contract)
        )

    # idempotent requests help handle scenarios where concurrent tests try to create the same
    # accounts, but in 5.0 onwards idempotency is only guaranteed for a 7d window so we still
    # rely on an id check for those scenarios
    request_id = e2e_account_id
    product_id = endtoend.testhandle.internal_contract_pid_to_uploaded_pid[contract]
    internal_account = endtoend.core_api_helper.create_internal_account(
        request_id=request_id,
        internal_account_id=e2e_account_id,
        product_id=product_id,
        accounting_tside=accounting_tside,
        details=details,
    )
    endtoend.testhandle.internal_account_id_to_uploaded_id[account_id] = e2e_account_id

    return internal_account


def create_internal_account_v2(
    account_id: str,
    t_side: AccountV2TSide,
    details: dict[str, str] | None = None,
    use_composite_id: bool = True,
) -> CreateAccountV2Response:
    """
    Creates an internal account and updates the internal_account_id_to_uploaded_id testhandle
    attribute with the original and final account id.

    :param id: the internal account id used to create a specific account
    :param accounting_tside: specifies the account tside
    :param details: account details metadata to add to the account
    :param use_composite_id: if True the helper will create a deterministic, e2e-specific account
    id that will be re-used across tests. This helps avoid id clashes in environments used by
    multiple teams
    :return: the created internal account resource
    """
    e2e_account_id = (
        _composite_internal_account_v2_id(account_id=account_id, t_side=t_side)
        if use_composite_id
        else account_id
    )

    if len(e2e_account_id) > 36:
        raise SetupError(
            f"Internal account id {e2e_account_id} is longer than 36 characters."
            " Please use an internal account id that is up to 30 characters long if using"
            " a composite id or 36 otherwise."
        )

    # idempotent requests help handle scenarios where concurrent tests try to create the same
    # accounts, but in 5.0 onwards idempotency is only guaranteed for a 7d window so we still
    # rely on an id check for those scenarios
    request_id = e2e_account_id
    internal_account: CreateAccountV2Response = endtoend.core_api_helper.create_internal_account_v2(
        request_id=request_id,
        account=InternalAccountRequestBody(
            id=e2e_account_id,
            status=AccountV2Status.ACCOUNT_STATUS_OPEN,
            details=details,
            t_side=t_side,
        ),
    )
    endtoend.testhandle.internal_account_id_to_uploaded_id[account_id] = e2e_account_id
    return internal_account


@deprecated("Use get_internal_account_v2 on Vault 5 and above.")
def get_internal_account(account_id):
    return endtoend.helper.send_request("get", "/v1/internal-accounts/" + account_id)


def get_internal_account_v2(account_id):
    return get_account_v2(account_id)


def get_specific_balance(
    account_id,
    address,
    asset="COMMERCIAL_BANK_MONEY",
    phase="POSTING_PHASE_COMMITTED",
    denomination="GBP",
    sleep=0,
):
    time.sleep(sleep)
    balances = endtoend.core_api_helper.get_live_balances(account_id)

    for balance in balances:
        if (
            balance["account_address"] == address
            and balance["asset"] == asset
            and balance["phase"] == phase
            and balance["denomination"] == denomination
        ):
            return balance["amount"]

    return "0"


def some_non_zero_balances_exist(account_id: str) -> bool:
    """
    Checks if any non-zero balances exist for a given account
    :param account_id: if of the account to check balances for
    :return: True if any non-zero balances exist, False otherwise
    """

    balances = endtoend.core_api_helper.get_live_balances(account_id)

    return any(balance["amount"] != "0" for balance in balances)


@deprecated("Use clear_balances_v2 on Vault 5 and above.")
def clear_balances(account_handle):
    account_id = account_handle["id"]

    balances = endtoend.core_api_helper.get_live_balances(account_id)

    if account_handle["accounting"]["tside"] == "TSIDE_LIABILITY":
        liability_account = True
    else:
        liability_account = False

    for balance in balances:
        if balance["amount"] != "0":
            amount = Decimal(balance["amount"])
            postings = []
            credit = (amount < 0 and liability_account) or (amount > 0 and not liability_account)
            postings.append(
                endtoend.postings_helper.create_posting(
                    account_id=account_id,
                    amount=str(abs(amount)),
                    denomination=balance["denomination"],
                    asset=balance["asset"],
                    account_address=balance["account_address"],
                    phase=balance["phase"],
                    credit=credit,
                )
            )
            postings.append(
                endtoend.postings_helper.create_posting(
                    account_id=endtoend.testhandle.internal_account_id_to_uploaded_id[
                        endtoend.testhandle.internal_account
                    ],
                    amount=str(abs(amount)),
                    denomination=balance["denomination"],
                    asset=balance["asset"],
                    account_address="DEFAULT",
                    phase=balance["phase"],
                    credit=not credit,
                )
            )
            # withdrawal_override & calendar_override needed to force the funds out of TD
            # todo: make this use output from KERN-I-26

            pib_id = endtoend.postings_helper.create_custom_instruction(
                postings,
                batch_details={
                    "calendar_override": "true",
                    "force_override": "true",
                    "withdrawal_override": "true",
                },
                instruction_details={"force_override": "true"},
                client_batch_id="TEARDOWN_" + str(uuid.uuid4()),
            )
            # ensure that the balances have been updated for this pib
            endtoend.balances_helper.wait_for_posting_balance_updates(
                account_id=account_id,
                posting_instruction_batch_id=pib_id,
            )

    # TODO: Add back in after TM-24384 is resolved to fix wallet e2e
    # endtoend.helper.retry_call(
    #     func=some_non_zero_balances_exist,
    #     f_args=[account_handle],
    #     expected_result=False
    # )
    return


def clear_balances_v2(account_handle):
    account_id = account_handle["id"]
    t_side = AccountV2TSide(account_handle["t_side"])
    liability_account = t_side == AccountV2TSide.T_SIDE_LIABILITY

    balances = endtoend.core_api_helper.get_live_balances(account_id)
    for balance in balances:
        if balance["amount"] != "0":
            amount = Decimal(balance["amount"])
            postings = []
            credit = (amount < 0 and liability_account) or (amount > 0 and not liability_account)
            postings.append(
                endtoend.postings_helper.create_posting(
                    account_id=account_id,
                    amount=str(abs(amount)),
                    denomination=balance["denomination"],
                    asset=balance["asset"],
                    account_address=balance["account_address"],
                    phase=balance["phase"],
                    credit=credit,
                    sub_account_id=balance.get("sub_account_id", ""),
                )
            )
            postings.append(
                endtoend.postings_helper.create_posting(
                    account_id=endtoend.testhandle.internal_account_id_to_uploaded_id[
                        endtoend.testhandle.internal_account
                    ],
                    amount=str(abs(amount)),
                    denomination=balance["denomination"],
                    asset=balance["asset"],
                    account_address="DEFAULT",
                    phase=balance["phase"],
                    credit=not credit,
                )
            )
            # withdrawal_override & calendar_override needed to force the funds out of TD
            # todo: make this use output from KERN-I-26

            pib_id = endtoend.postings_helper.create_custom_instruction(
                postings,
                batch_details={
                    "calendar_override": "true",
                    "force_override": "true",
                    "withdrawal_override": "true",
                },
                instruction_details={"force_override": "true"},
                client_batch_id="TEARDOWN_" + str(uuid.uuid4()),
            )
            # ensure that the balances have been updated for this pib
            endtoend.balances_helper.wait_for_posting_balance_updates(
                account_id=account_id,
                posting_instruction_batch_id=pib_id,
            )

    # TODO: Add back in after TM-24384 is resolved to fix wallet e2e
    # endtoend.helper.retry_call(
    #     func=some_non_zero_balances_exist,
    #     f_args=[account_handle],
    #     expected_result=False
    # )
    return


@deprecated("Use clear_account_balances_v2 on Vault 5 and above.")
def clear_account_balances(account):
    account_id = account["id"]

    # TODO: This needs revisiting. The 3 attempts are for 1) initial clean-up, 2) clean-up of any
    # unintended side-effects, 3) final attempt before giving up. It will never work for some
    # contracts. It is also prone to flakes as the balances may not have updated between attempts
    for _ in range(3):
        if some_non_zero_balances_exist(account_id):
            clear_balances(account)

    if some_non_zero_balances_exist(account_id):
        raise Exception(
            f"{datetime.utcnow()} - " f"Balances aren't being cleared for account {account_id}.",
            f"Latest balances:\n{endtoend.core_api_helper.get_live_balances(account_id)}",
        )


def clear_account_balances_v2(account):
    account_id = account["id"]

    # TODO: This needs revisiting. The 3 attempts are for 1) initial clean-up, 2) clean-up of any
    # unintended side-effects, 3) final attempt before giving up. It will never work for some
    # contracts. It is also prone to flakes as the balances may not have updated between attempts
    for _ in range(3):
        if some_non_zero_balances_exist(account_id):
            clear_balances_v2(account)

    if some_non_zero_balances_exist(account_id):
        raise Exception(
            f"{datetime.utcnow()} - " f"Balances aren't being cleared for account {account_id}.",
            f"Latest balances:\n{endtoend.core_api_helper.get_live_balances(account_id)}",
        )


def clear_specific_address_balance(
    account_handle: dict[str, Any], address: str, denomination: str = "GBP"
) -> bool:
    """
    Asserts balance of provided address, sends posting DEFAULT to negate that amount
    :param account_handle: the account resource
    :param address: the address to be cleared.
    :param denomination: denomination of the address to be cleared.
    :return: True if a posting was sent to clear the balance else return false.
    """

    # TODO: Would it be worth expanding to allow custom instructions to zero specific addresses
    #  instead of DEFAULT?
    account_id = account_handle["id"]

    balance = get_specific_balance(account_id, address, denomination=denomination)

    if balance == "0":
        log.info("Balance returned zero, retrying to confirm")
        time.sleep(5)
        balance = get_specific_balance(account_id, address, denomination=denomination)

    if account_handle["accounting"]["tside"] == "TSIDE_LIABILITY":
        liability_account = True
    else:
        liability_account = False

    log.info(f"Clear initiated for {address}")

    if balance != "0":
        amount = Decimal(balance)
        credit = (amount < 0 and liability_account) or (amount > 0 and not liability_account)

        if credit:
            endtoend.postings_helper.inbound_hard_settlement(
                account_id=account_id,
                amount=str(abs(amount)),
                denomination=denomination,
                override=True,
                batch_details={"withdrawal_override": "true"},
            )
        else:
            endtoend.postings_helper.outbound_hard_settlement(
                account_id=account_id,
                amount=str(abs(amount)),
                denomination=denomination,
                override=True,
                batch_details={"withdrawal_override": "true"},
            )
        return True

    return False


@deprecated("Use terminate_account_v2 on Vault 5 and above.")
def terminate_account(account: dict[str, Any]) -> dict[str, Any]:
    """
    Update an account to the appropriate terminal status. For accounts that are still in PENDING
    status this is the CANCELLED status. For accounts that are in OPEN or PENDING_CLOSURE status
    this is the CLOSED status
    :param account: the account to terminate
    :return: the terminated account
    """
    account_id = account["id"]
    endtoend.accounts_helper.wait_for_all_account_updates_to_complete(account_id)

    # Refresh account in case the status has been changed as part of the test
    account = endtoend.contracts_helper.get_account(account_id)
    account_status = AccountStatus(account["status"])

    if account_status in [
        AccountStatus.ACCOUNT_STATUS_CLOSED,
        AccountStatus.ACCOUNT_STATUS_CANCELLED,
    ]:
        return account

    elif account_status is AccountStatus.ACCOUNT_STATUS_PENDING:
        # Unactivated accounts should be cancelled instead of closed
        return endtoend.core_api_helper.update_account(
            account_id, AccountStatus.ACCOUNT_STATUS_CANCELLED
        )

    elif account_status is not AccountStatus.ACCOUNT_STATUS_PENDING_CLOSURE:
        clear_account_balances(account)
        account = endtoend.core_api_helper.update_account(
            account["id"], AccountStatus.ACCOUNT_STATUS_PENDING_CLOSURE
        )
        endtoend.accounts_helper.wait_for_account_update(account_id, "closure_update")

    return endtoend.core_api_helper.update_account(account_id, AccountStatus.ACCOUNT_STATUS_CLOSED)


def terminate_account_v2(account: dict[str, Any]) -> dict[str, Any]:
    """
    Update an account to the appropriate terminal status. For accounts that are still in PENDING
    status this is the CANCELLED status. For accounts that are in OPEN or PENDING_CLOSURE status
    this is the CLOSED status
    :param account: the account to terminate
    :return: the terminated account
    """
    account_id = account["id"]

    # Refresh account in case the status has been changed as part of the test
    account = endtoend.contracts_helper.get_account_v2(account_id)
    account_status = AccountV2Status(account["status"])

    if account_status in [
        AccountV2Status.ACCOUNT_STATUS_CLOSED,
        AccountV2Status.ACCOUNT_STATUS_CANCELLED,
    ]:
        return account

    elif account_status is AccountV2Status.ACCOUNT_STATUS_PENDING:
        # Unactivated accounts should be cancelled instead of closed
        return endtoend.core_api_helper.update_account_v2(
            account_id, status=AccountV2Status.ACCOUNT_STATUS_CANCELLED
        )

    elif account_status is not AccountV2Status.ACCOUNT_STATUS_CLOSING:
        clear_account_balances_v2(account)
        account = endtoend.core_api_helper.update_account_v2(
            account["id"], status=AccountV2Status.ACCOUNT_STATUS_CLOSED
        )

    return account


def teardown_all_accounts():
    fail_count = 0
    for account_id in endtoend.testhandle.accounts:
        try:
            account = get_account_v2(account_id)
            # This is API that was used to create the account as stored on the account
            # details metadata.
            account_api_version = account["details"].get("accounts_api_version", "v1")
            if account_api_version == "v2":
                terminate_account_v2(account)
            else:
                account_v1 = get_account(account_id)
                terminate_account(account_v1)
        # We want to continue tearing down all accounts even if one fails
        except BaseException as e:
            fail_count += 1
            log.exception(f"Failed to teardown account {account_id}: {e.args}")
    endtoend.testhandle.accounts.clear()
    # Raise a single exception if one or more teardowns failed as this warrants investigation
    if fail_count > 0:
        raise Exception(f"{datetime.utcnow()} - Failed to teardown {fail_count} accounts")


def update_product_parameter(product_id: str, params_to_update: dict[str, str]) -> dict[str, str]:
    product_version_id = get_current_product_version_id(product_id)

    items_to_add = [
        {"name": param_name, "value": param_value}
        for param_name, param_value in params_to_update.items()
    ]
    data = {"request_id": str(uuid.uuid4()), "items_to_add": items_to_add}

    resp = endtoend.helper.send_request(
        "put",
        f"/v1/product-versions/{product_version_id}:updateParams",
        data=json.dumps(data),
    )

    return resp


def get_current_product_version_id(product_id: str, e2e: bool = True) -> str:
    """
    Returns version id of the product from the specified instance.
    One can specify whether the version id of the e2e product or the original product
    corresponding to the product_id is returned - done through the e2e parameter.

    :param product_id: str Smart contract id as specified in the file
    :param e2e: bool
    """
    unique_product_id = product_id
    if e2e:
        unique_product_id = endtoend.testhandle.contract_pid_to_uploaded_pid[product_id]

    params = {"ids": unique_product_id}

    resp = endtoend.helper.send_request("get", "/v1/products:batchGet", params=params)

    return resp["products"][unique_product_id]["current_version_id"]


def create_account_schedule_tags(controlled_schedules: dict[str, list[str]]) -> None:
    """
    Creates the account schedule tags required to control all specified schedules during
    E2E tests, plus a default paused tag that can be assigned to any schedules that won't
    be triggered.  Outputs are set on the `endtoend.testhandle.controlled_schedule_tags`
    and `default_paused_tag_id` attributes respectively.

    The function handles two setup modes:
    1. Multiple product version setup (when `testhandle.PRODUCTS` is populated):
       `controlled_schedules` should map product IDs to lists of schedule event types.
       Tags are shared across different versions of the same product.
    2. Legacy setup (when `testhandle.CONTRACTS` is populated):
       `controlled_schedules` should map product IDs to lists of schedule event types.
       Tags are preserved across products defined in `testhandle.CONTRACT_VERSION_UPGRADES`.

    :param controlled_schedules: A dictionary mapping product IDs to a list of
        schedule event type names that should be controlled.
    """
    log.info("Creating required account schedule tags")

    def _create_and_upload_tag(
        tag: dict[str, Any],
        product_id: str,
        schedule_id: str,
    ) -> str:
        # We always want the tag id to be unique, or a single tag could control all e2e accounts
        # which may result in accidental large-scale operations
        e2e_tag_id = tag["id"] + "_" + schedule_id + "_" + str(uuid.uuid4())
        log.debug(f"Creating {e2e_tag_id=} for {schedule_id=} on {product_id=}")
        try:
            uploaded_tag = endtoend.core_api_helper.create_account_schedule_tag(
                account_schedule_tag_id=e2e_tag_id,
                description=tag.get("description", ""),
                sends_scheduled_operation_reports=tag.get(
                    "sends_scheduled_operation_reports", False
                ),
                schedule_status_override=tag.get(
                    "schedule_status_override",
                    "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_NO_OVERRIDE",
                ),
                schedule_status_override_start_timestamp=tag.get(
                    "schedule_status_override_start_timestamp",
                ),
                schedule_status_override_end_timestamp=tag.get(
                    "schedule_status_override_end_timestamp"
                ),
                test_pause_at_timestamp=tag.get("test_pause_at_timestamp"),
            )
        except HTTPError as e:
            # This handles cases where the tag has already been created
            if "409 Client Error: Conflict" in e.args[0]:
                existing_tag = endtoend.endtoend.core_api_helper.batch_get_account_schedule_tags(
                    account_schedule_tag_ids=[e2e_tag_id]
                )[e2e_tag_id]
                if existing_tag != tag:
                    # We could expand this to attempt updates, but it is normally a sign of
                    # incorrect tag_id reuse and should be fixed elsewhere
                    raise ValueError(
                        f"Found existing tag with same id but different attributes."
                        f"\nExisting Tag:\n{existing_tag}\nNew Tag:\n{tag}"
                    )
                uploaded_tag = existing_tag
            else:
                raise e

        return uploaded_tag["id"]

    # the tag id is overridden later to be as unique as required
    default_tag_contents = extract_resource(
        COMMON_ACCOUNT_SCHEDULE_TAG_PATH, "account_schedule_tag"
    )

    endtoend.testhandle.controlled_schedule_tags = {
        product_id: {
            schedule: _create_and_upload_tag(
                default_tag_contents, product_id=product_id, schedule_id=schedule
            )
            for schedule in schedules
        }
        for product_id, schedules in controlled_schedules.items()
    }

    # Preserve tags for the same event types across products if they have been tagged as
    # a contract version upgrade pair. This is only required for legacy CONTRACTS setups
    # where multiple versions of the same product are defined as separate products.
    # In the new PRODUCTS approach, multiple versions share the same product id and
    # consequently share the same tags.
    if endtoend.testhandle.CONTRACTS:
        for from_product, to_product in endtoend.testhandle.CONTRACT_VERSION_UPGRADES.items():
            # The ordering is important here as it means we still honour explicit requests
            # to control schedules differently in the upgraded product
            final_to = {
                **endtoend.testhandle.controlled_schedule_tags.get(from_product, {}),
                **endtoend.testhandle.controlled_schedule_tags.get(to_product, {}),
            }
            if final_to:
                endtoend.testhandle.controlled_schedule_tags[to_product] = final_to

    endtoend.testhandle.default_paused_tag_id = _create_and_upload_tag(
        default_tag_contents, product_id="All", schedule_id="DEFAULT"
    )


def create_flag_definitions(flag_definitions: dict[str, str]) -> None:
    """
    Creates flag definitions, handling scenarios where they may already exist
    :param flag_definitions: list of flag definition ids and corresponding resource file
     paths
    """
    log.info("Creating required flag definitions")

    for flag_definition_id, file_path in flag_definitions.items():
        definition = extract_resource(
            file_path=flag_definitions[flag_definition_id],
            resource_type="flag_definition",
        )

        # re-use e2e flag definition ids if the same flag definition file is re-used across
        # schedules or tests
        if file_path in endtoend.testhandle.flag_file_paths_to_e2e_ids:
            e2e_flag_definition_id = endtoend.testhandle.flag_file_paths_to_e2e_ids[
                flag_definitions[flag_definition_id]
            ]
            endtoend.testhandle.flag_definition_id_mapping[flag_definition_id] = (
                e2e_flag_definition_id
            )
            log.info(f"Reusing flag {e2e_flag_definition_id} for {flag_definition_id}")
            continue

        # this id is chosen to be unique and also relatable to the original flag definition
        e2e_flag_definition_id = f"E2E_{flag_definition_id}_{uuid.uuid4().hex}"
        endtoend.testhandle.flag_definition_id_mapping[flag_definition_id] = e2e_flag_definition_id
        endtoend.testhandle.flag_file_paths_to_e2e_ids[file_path] = e2e_flag_definition_id
        endtoend.core_api_helper.create_flag_definition(
            flag_definition_id=e2e_flag_definition_id,
            name=e2e_flag_definition_id,
            description=str(definition.get("description", "")),
            required_flag_level=str(definition.get("required_flag_level", "")),
            flag_visibility=str(definition.get("flag_visibility", "")),
        )


@overload
def create_flag(
    *,
    flag_definition_id: str,
    account_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: FlagV1FlagValue = FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1AccountFlag: ...


@overload
def create_flag(
    *,
    flag_definition_id: str,
    customer_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: FlagV1FlagValue = FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1CustomerFlag: ...


@overload
def create_flag(
    *,
    flag_definition_id: str,
    payment_device_id: str,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: FlagV1FlagValue = FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1PaymentDeviceFlag: ...


def create_flag(
    *,
    flag_definition_id: str,
    account_id: str | None = None,
    customer_id: str | None = None,
    payment_device_id: str | None = None,
    description: str | None = None,
    effective_timestamp: datetime | None = None,
    expiry_timestamp: datetime | None = None,
    is_backdated: bool | None = None,
    value: FlagV1FlagValue = FlagV1FlagValue.FLAG_VALUE_ON,
) -> core_api.FlagV1AccountFlag | core_api.FlagV1CustomerFlag | core_api.FlagV1PaymentDeviceFlag:
    """
    Create a flag at the relevant level (account, customer or payment device), referring
    to the original unmapped flag definition id.
    :param flag_definition_id: The original unmapped flag definition id, as specified in the
    `endtoend.testhandle.FLAG_DEFINITIONS` keys
    :param account_id: The account to apply the flag to. One of account_id, customer_id, or
    payment_device_id must be supplied.
    :param customer_id: The customer to apply the flag to. One of account_id, customer_id, or
    payment_device_id must be supplied.
    :param payment_device_id: The payment device to apply the flag to. One of account_id,
    customer_id, or payment_device_id must be supplied.
    :param description: Metadata for the flag.
    :param effective_timestamp: When the flag should start being applied.
    :param expiry_timestamp: When the flag should stop being applied.
    :param is_backdated: This is new in Vault 5.2.  Supply it if effective_timestamp is earlier
    than the flag's creation date. If unspecified it will not be included in the output in order
    to maintain compatibility with versions of Vault earlier than 5.2.
    :param value: The flag will behave as True in the smart contract when set to
    FlagValue.FLAG_VALUE_ON; False when set to FlagValue.FLAG_VALUE_OFF.

    :return: the created flag object
    """
    if account_id:
        flag_entity_id = {"account_id": account_id}
    elif customer_id:
        flag_entity_id = {"customer_id": customer_id}
    elif payment_device_id:
        flag_entity_id = {"payment_device_id": payment_device_id}

    return endtoend.core_api_helper.create_flag(
        flag_name=endtoend.testhandle.flag_definition_id_mapping[flag_definition_id],
        description=description,
        effective_timestamp=effective_timestamp,
        expiry_timestamp=expiry_timestamp,
        is_backdated=is_backdated,
        value=value,
        **flag_entity_id,
    )


def get_flag(
    flag_name: str,
    account_ids: list[str] | None = None,
    effective_timestamp_range_from: datetime | None = None,
    effective_timestamp_range_to: datetime | None = None,
) -> list[dict[str, Any]]:
    return endtoend.core_api_helper.get_flag(
        flag_name=endtoend.testhandle.flag_definition_id_mapping[flag_name],
        account_ids=account_ids,
        effective_timestamp_range_from=effective_timestamp_range_from,
        effective_timestamp_range_to=effective_timestamp_range_to,
    )


def create_required_internal_accounts(
    required_internal_accounts: dict[AccountV2TSide, list[str]],
) -> None:
    """
    Creates the required internal accounts, handling scenarios where they may already exist.
    Ensures that the DUMMY_CONTRA internal account is created even when excluded
    from the required_internal_accounts dict
    :param required_internal_accounts: dict of tside to list of required internal account ids
    """
    log.info("Creating required internal products")

    # Guarantee that DUMMY_CONTRA is created
    liability_accounts: list[str] = required_internal_accounts.setdefault(
        AccountV2TSide.T_SIDE_LIABILITY, [DUMMY_CONTRA]
    )
    if DUMMY_CONTRA not in liability_accounts:
        liability_accounts.append(DUMMY_CONTRA)

    log.info("Creating required internal accounts")

    for t_side, internal_account_ids in required_internal_accounts.items():
        for internal_account_id in internal_account_ids:
            e2e_composite_id = _composite_internal_account_v2_id(
                account_id=internal_account_id, t_side=t_side
            )
            if _does_internal_account_exist(e2e_composite_id):
                endtoend.testhandle.internal_account_id_to_uploaded_id[internal_account_id] = (
                    e2e_composite_id
                )
            else:
                created_account = create_internal_account_v2(
                    account_id=internal_account_id,
                    t_side=t_side,
                )
                log.info(f"Internal Account {created_account.id} created")

    # create internal accounts that do not use an e2e composite ID
    for tside, internal_account_ids in DEFAULT_REQUIRED_INTERNAL_ACCOUNTS_DICT.items():
        for internal_account_id in internal_account_ids:
            if not _does_internal_account_exist(internal_account_id):
                created_account = create_internal_account_v2(
                    account_id=internal_account_id,
                    t_side=tside,
                    use_composite_id=False,
                )
                log.info(f"Internal Account {created_account.id} created using non-e2e ID")


def _does_internal_account_exist(internal_account_id: str) -> bool:
    try:
        get_internal_account_v2(internal_account_id)
    except HTTPError as e:
        if "404 Client Error: Not Found for url" in e.args[0]:
            log.debug(f"{internal_account_id} not found in env")
            return False
        else:
            raise e
    return True


def check_product_version(product_id: str, file_product_data: str):
    """
    Check the Product version against the instance
    used for testing.

    An exception is raised if it is present in the instance at the same version
    but different content.

    :param product_id: The identifier of the product
    :param file_product_data: The parsed product data file
    """
    try:
        product_version_id = get_current_product_version_id(product_id, e2e=False)
        resp = endtoend.core_api_helper.get_product_version(product_version_id, True)
        instance_product_data = resp["code"]
        instance_product_ver = _get_version_identifier(resp["display_version_number"])
    except (HTTPError, KeyError, TypeError):
        log.warning(
            f"{product_id} not found on instance."
            f"Skipping product validation for this smart contract."
        )
        return None

    file_product_ver = _get_file_product_version(file_product_data)
    # If this product is loaded on the instance and at the same version,
    # check the content is the same
    if instance_product_ver == file_product_ver and instance_product_data != file_product_data:
        raise ValueError(
            f"{datetime.utcnow()} -"
            f" Instance has different content for {product_id}:"
            f" Version increment may be required"
        )
    else:
        log.info(f"{product_id} {file_product_ver} matches on instance")


def _get_file_product_version(product_data: str) -> str:
    """
    Extracts the version of a product from the file contents
    """
    version_line = re.search(r"version\s=\s'[0-9]+\.[0-9]+\.[0-9]+'", product_data)
    if version_line:
        return version_line.groupdict()["version"]
    raise Exception("Cannot extract version of the smart contract")


def _get_version_identifier(product_version_number: dict[str, int]) -> str:
    """
    Extracts version identifier as str from the dictionary coming back in batchGet API response.

    :param product_version_number: Example structure:
    {   "major": 1,
        "minor": 1,
        "patch": 1,
        "label": "value1"
        }
    """
    version_id_list = [str(product_version_number[part]) for part in ["major", "minor", "patch"]]
    return ".".join(version_id_list)


def convert_account(account_id: str, product_version_id: str) -> dict[str, Any]:
    """
    Perform an account conversion using account updates
    :param account_id: account id of the account to convert
    :param to_product_id: target product ID to convert account to
    :return: The resulting account update resource
    """

    account_update = {"product_version_update": {"product_version_id": product_version_id}}
    return endtoend.core_api_helper.create_account_update(account_id, account_update)


def create_calendars(calendars: dict[str, str]) -> None:
    """
    Creates calendars, handling scenarios where they may already exist
    :param calendars: contract calendar ids and their corresponding resource file paths
    """
    log.info("Creating required calendars")

    required_calendars = {
        calendar_id: extract_resource(
            file_path=calendars[calendar_id],
            resource_type="calendar",
        )
        for calendar_id in calendars
    }

    # In most cases the calendars will already exist, unless we're on a new environment, or
    # introducing a new one. We therefore first check if they exist and only create if
    # missing, vs first trying to create, which will mostly fail due to existing calendars
    for (
        contract_calendar_id,
        calendar,
    ) in required_calendars.items():
        e2e_calendar_id = _generate_unique_calendar_id(contract_calendar_id)
        calendar_display_name = calendar.get("display_name", "")

        log.info(f"creating calendar with id {e2e_calendar_id}")
        endtoend.core_api_helper.create_calendar(
            calendar_id=e2e_calendar_id,
            is_active=calendar.get("is_active", True),
            display_name=calendar_display_name,
            description=calendar.get("description", ""),
        )

        endtoend.testhandle.calendar_ids_to_e2e_ids[contract_calendar_id] = e2e_calendar_id


def _generate_unique_calendar_id(contract_calendar_id: str) -> str:
    """
    Generates a unique calendar id given an original id
    :param contract_calendar_id: the original calendar id
    :return: the unique calendar id
    """
    random_chars = "".join(random.choice(string.ascii_letters) for x in range(10))

    return "e2e_" + contract_calendar_id + "_" + random_chars.upper()


def deactivate_all_calendars():
    for calendar_id in endtoend.testhandle.calendar_ids_to_e2e_ids.values():
        endtoend.core_api_helper.update_calendar(calendar_id, is_active=False)
        log.info(f"Calendar {calendar_id} active status set to false")
    endtoend.testhandle.calendar_ids_to_e2e_ids.clear()


# Replace event types with the string representation
class RemoveEventTypes(ast.NodeTransformer):
    def __init__(self) -> None:
        # ensure the same id is re-used for each occurrence
        self.replacement_id = f"event_types_E2E_replacement_{uuid.uuid4().hex}"

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id == "event_types":
            # replace original `event_types` with an arbitrary variable name so that they don't
            # interfere with out e2e-specific `event_types` with modified tag ids.
            # event_types_groups will still refer to the original event types, which is ok as the
            # event type names are the same
            return ast.Name(id=self.replacement_id, ctx=node.ctx)
        return self.generic_visit(node)


def _replace_event_types_with_repr(rendered_contract: str, event_types_repr: str) -> str:
    tree = ast.parse(rendered_contract)
    ast.fix_missing_locations(RemoveEventTypes().visit(tree))
    rendered_contract = ast.unparse(tree)
    # append compiled event_types repr to end of contract
    rendered_contract += f"\n\nevent_types = {event_types_repr}\n"
    return rendered_contract


class ContractNotificationResourceType(enum.Enum):
    RESOURCE_ACCOUNT = "RESOURCE_ACCOUNT"
    RESOURCE_PLAN = "RESOURCE_PLAN"


@kafka_only_helper
def send_contract_notification(
    notification_type: str,
    notification_details: dict[str, str],
    resource_id: str,
    resource_type: ContractNotificationResourceType,
) -> None:
    """Creates a contract notification and produces it on the relevant platform topic. Useful for
    testing auto-instantiation behaviours.

    :param notification_type: the type to populate on the notification
    :param notification_details: the details to populate on the notification
    :param resource_id: the id of the resource that would be emitting the notification (doesn't
    have to be a real id as this function effectively mocks a contract/plan instantiating the
    notification
    :param resource_type: indicates whether an account or plan emitted the notification
    :return: None
    """

    event_msg = {
        "event_id": uuid.uuid4().hex,
        "notification_type": notification_type,
        "resource_id": resource_id,
        "resource_type": resource_type.value,
        "notification_details": notification_details,
    }

    produce_message(
        endtoend.testhandle.kafka_producer, CONTRACT_NOTIFICATIONS_TOPIC, json.dumps(event_msg)
    )


@kafka_only_helper
def wait_for_contract_notification(
    notification_type: str,
    notification_details: dict[str, str],
    resource_id: str,
    resource_type: ContractNotificationResourceType,
):
    consumer = endtoend.testhandle.kafka_consumers[CONTRACT_NOTIFICATIONS_TOPIC]

    def matcher(event_msg, unique_message_ids):
        event_request_id = event_msg.get("event_id")
        event_resource_id = event_msg.get("resource_id")
        event_notification_type = event_msg.get("notification_type")
        event_resource_type = ContractNotificationResourceType(event_msg.get("resource_type"))
        event_notification_details = event_msg.get("notification_details")

        message_id = f"{event_resource_id}_{event_notification_type}"
        if message_id in unique_message_ids:
            if (
                resource_type != event_resource_type
                or notification_details != event_notification_details
            ):
                log.info(
                    f"Notification found for resource id `{event_resource_id}` and notification "
                    f"type `{event_notification_type}` but resource_type `{event_resource_type}` "
                    f"and/or notification details `{event_notification_details}` do not match "
                    f"expected `{resource_type}` and `{notification_details}`"
                )
                return "", event_request_id, False
            return (
                message_id,
                event_request_id,
                True,
            )

        return "", event_request_id, False

    unmatched_contract_notifications = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids={f"{resource_id}_{notification_type}": None},
        inter_message_timeout=30,
        matched_message_timeout=30,
    )

    if len(unmatched_contract_notifications) > 0:
        raise Exception(
            f"Failed to retrieve {len(unmatched_contract_notifications)} notifications "
            f"with following id and type: {', '.join(unmatched_contract_notifications.keys())}"
        )


def prepare_parameters_for_e2e(
    parameters: dict[str, Any],
    internal_account_param_mapping: Mapping[str, str] | None = None,
    nested_internal_account_param_mapping: Mapping[str, Mapping[str, str]] | None = None,
    flag_param_mapping: Mapping[str, list[str] | Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Prepares parameter values for e2e tests by inserting keys used by the framework to recognise:
    - internal accounts
    - nested internal accounts
    - flags definitions
    Other parameters are passed through.
    Note that any scenarios where the internal account or flag definition id(s) are not at the top
    level of the value will need to be handled manually in the `parameters` argument. For example:
    {
        "my_param": ["flag_id", "flag_id_2"], # This is handled
        "my_param_2": {"flag_id": "other_value", "flag_id_2": "other_value_2"}, # This is handled
        "my_param_4": {
            "other_value": ["flag_id", "flag_id_2"], # This is NOT handled
            "other_value_2": { # This is NOT handled
                "flag_id": "another_value",
                "flag_id_2": "another_value_2"
            },
        }
    }
    There is no support for a parameter requiring both internal account id and flag definition id
    substitution.

    The following substitutions will be made:
    Internal Accounts Mapping:
        "param_name":"internal_account"

        is substituted  with:

        "param_name":{"internal_account_key": "internal_account"}

    Nested Internal Accounts Mapping:
        "param_name": {"key_1":"internal_account_1", "key_2":"internal_account_2"}

         is substituted  with:

        "param_name": {
            "nested_internal_account_keys":{
                "key_1": {"internal_account_key": "internal_account_1"},
                "key_2": {"internal_account_key": "internal_account_2"}
            }
        }

    Flag Mapping:
        "my_param": ["flag_id", "flag_id_2"]

        is substituted  with:

        "my_param": {"flag_key": ["flag_id", "flag_id_2"]}

        OR
        "my_param": {"flag_id": "other_value", "flag_id_2": "other_value_2"}

        is substituted  with:

        "my_param": {
            "flag_key": {"flag_id": "other_value", "flag_id_2": "other_value_2"}
        }


    :param parameters: the original test parameter names and values
    :param internal_account_param_mapping: internal account parameter names to desired account id
    pre e2e substitution
    :param nested_internal_account_param_mapping: internal account parameter names to a mapping of
    key to desired account id pre e2e substitution
    :param flag_param_mapping: flag parameter names to desired values pre e2e substitution.
    :return: the updated parameter map
    """

    e2e_parameters = deepcopy(parameters)

    for internal_account_param, account_id in (internal_account_param_mapping or {}).items():
        e2e_parameters[internal_account_param] = {"internal_account_key": account_id}

    for nested_internal_account_param, nested_internal_account in (
        nested_internal_account_param_mapping or {}
    ).items():
        e2e_parameters[nested_internal_account_param] = {
            "nested_internal_account_keys": {
                key: {"internal_account_key": nested_internal_account[key]}
                for key in nested_internal_account.keys()
            }
        }

    for flag_param, value in (flag_param_mapping or {}).items():
        e2e_parameters[flag_param] = {"flag_key": value}

    return e2e_parameters


def create_parameter_definitions(parameter_resources_defs: list[ParameterResource]) -> None:
    """
    Creates parameter definitions, handling scenarios where they may already exist
    :param resource_directories: list of resource file directories for Parameter(s)
    """
    log.info("Creating required parameter definitions")
    for parameter in parameter_resources_defs:
        post_body = CreateParameterResourceV1RequestBody(
            # Using a deterministic request id will allow Vault's idempotency rules to create the
            # parameter if it is not there, or to give a success response if it already exists,
            # rather than a rejection.
            request_id=parameter.id,
            parameter=parameter,
        )
        endtoend.core_api_helper.create_parameter_resource(post_body)
        log.info(f"Created parameter with id '{parameter.id}'")


def batch_get_parameter_resources(
    ids: Iterable[str],
) -> core_api.BatchGetParameterResourceV1ResponseBody:
    """Batch gets the requested resources, mapping the original parameter id to the e2e id
    in both the request parameters and the keys of the response. The returned parameters themselves
    are not modified

    :param ids: the original, unmapped parameter ids to batch get
    :return: the core_api response with the e2e parameter ids in the underlying
    dict[str, ParameterResource] keys mapped back to original ids
    """
    non_clu_ids = [strip_clu_notation(id) for id in ids]

    id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id
    e2e_ids = [id_map.get(id, id) for id in non_clu_ids]

    result = endtoend.core_api_helper.batch_get_parameter_resources(e2e_ids)
    reverse_id_map = {value: key for key, value in id_map.items()}
    result.parameters = {
        reverse_id_map.get(id, id): parameter for id, parameter in result.parameters.items()
    }

    return result


def get_parameter_values(
    parameter_ids: list[str],
    account_ids: list[str] | None = None,
    effective_timestamp_range_from: core_api.OptionalDatetime | None = None,
    effective_timestamp_range_to: core_api.OptionalDatetime | None = None,
) -> list[core_api.ParameterValueResource]:
    """
    Get a list of Parameter Values, mapping the original parameter id to the e2e id
    in both the request parameters and the keys of the response.
    The returned parameters themselves are not modified.


    :param parameter_ids: Parameter IDs to filter values on.
    :param account_ids: Account IDs to filter values on. Optional.
    :param effective_timestamp_range_from: Values in this range must be less than the value of to.
    Optional.
    :param effective_timestamp_range_to: Values in this range must be greater than or equal to the
    value of from. Optional.
    :return: A list of ParameterValueResource with the specified parameter_ids else return empty
        list.
    """
    non_clu_ids = [strip_clu_notation(id) for id in parameter_ids]

    id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id
    e2e_ids = [id_map.get(id, id) for id in non_clu_ids]

    return endtoend.core_api_helper.get_parameter_values(
        parameter_ids=e2e_ids,
        account_ids=account_ids,
        effective_timestamp_range_from=effective_timestamp_range_from,
        effective_timestamp_range_to=effective_timestamp_range_to,
    )


def batch_get_products(
    request: core_api.BatchGetProductsRequest,
) -> core_api.BatchGetProductsResponse:
    """
    Retrieves Products by their original ids, as specified in endtoend.testhandle.CONTRACTS keys.
    :param request: contains the filters for /v1/products:batchGet. Original product ids will be
    mapped to the end-to-end ids.
    :returns: the retrieved products. The end-to-end product ids will be mapped back to the
    original ids in the request, but the product version ids will be unaffected.
    """

    mapped_ids: list[str] = []
    reverse_mapping = {}
    for product_id in request.ids:
        if product_id not in endtoend.testhandle.contract_pid_to_uploaded_pid:
            raise ValueError(
                f"Product ID: {product_id} not recognised. Is it specified in "
                "endtoend.testhandle.CONTRACTS?"
            )
        mapped_ids += product_id
        reverse_mapping[endtoend.testhandle.contract_pid_to_uploaded_pid[product_id]] = product_id

    mapped_request = core_api.BatchGetProductsRequest(
        ids=[
            endtoend.testhandle.contract_pid_to_uploaded_pid[original_id]
            for original_id in request.ids
        ]
    )

    mapped_response = endtoend.core_api_helper.batch_get_products(mapped_request)
    unmapped_products = {}

    for mapped_product_id, product in mapped_response.products.items():
        # in theory the core api could return a product_id we don't recognise, but that would
        # most likely be a core api bug we can't handle
        if unmapped_id := reverse_mapping.get(mapped_product_id):
            unmapped_products[unmapped_id] = product.model_copy(update={"id": unmapped_id})
        else:
            raise ValueError(
                f"Product ID: {mapped_product_id} returned by Core API but not known to the"
                "Test Framework"
            )

    return core_api.BatchGetProductsResponse.model_validate({"products": unmapped_products})
