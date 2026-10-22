# standard libs
import ast
import inspect
import logging
from types import ModuleType
from typing import Any, overload

# third party
import semantic_version

# inception sdk
from inception_sdk.common.python import ast_utils
from inception_sdk.vault.core_api import ParameterResource

log = logging.getLogger(__name__)


class InvalidApiMetadata(Exception):
    pass


class MissingApiMetadata(Exception):
    pass


def is_module_in_contracts_language_v4(module: ast.Module | ModuleType) -> bool:
    """
    Determines whether a module is a contract written in contracts language v4.
    :return: True if the contract is v4, False otherwise.
    """
    return get_contract_version(module).major == 4


def get_contract_version(module: ast.Module | ModuleType) -> semantic_version.Version:
    """
    The api version must be defined in the metadata as per the Contracts API:
    `api = "major.minor.patch"`
    :param module: the module to check
    :raises InvalidApiException: raised if `api` is found, but not an ast.Constant or
    not valid semver
    :raises MissingApiException: raised if `api` is not found
    :return: semantic_version of the contract.
    """
    if isinstance(module, ModuleType):
        _module = ast.parse(inspect.getsource(module))
    else:
        _module = module

    for stmt in _module.body:
        if isinstance(stmt, ast.Assign) and ast_utils.get_assign_node_target_name(stmt) == "api":
            if not isinstance(stmt.value, ast.Constant):
                raise InvalidApiMetadata(
                    f"Unable to determine contract language version from template.\n"
                    f"`api` value must be an ast.Constant but is {type(stmt)}"
                )
            version_string = str(stmt.value.value)
            if not semantic_version.validate(version_string):
                raise InvalidApiMetadata(
                    f"Unable to determine contract language version from template.\n"
                    f"Could not parse `api` value {version_string} as a semantic version"
                )
            return semantic_version.Version(version_string)

    raise MissingApiMetadata(
        "Unable to determine contract language version from template.\n"
        "Could not find an `api` assignment"
    )


def get_contract_attributes(
    contract_code: str,
) -> dict[str, Any]:
    """
    :param contract code: Smart Contract Python code as a string.
    :return: the attributes from running the contract through Python exec().  If the contract is
    CLv3 then an empty dict will be returned, as valid CLv3 contracts are not valid Python.
    """
    contract_attributes: dict[str, Any] = {}
    # Expected Parameters were introduced in Contracts Language v4.
    if get_contract_version(ast.parse(contract_code)) < semantic_version.Version("4.0.0"):
        return contract_attributes

    exec(contract_code, contract_attributes)
    return contract_attributes


@overload
def get_contract_required_parameter_resources(
    product_id: str,
    contract_code: str,
    e2e_test_case_parameter_resources: list[ParameterResource] | None = None,
) -> list[ParameterResource]: ...


@overload
def get_contract_required_parameter_resources(
    *,
    product_version_id: str,
    contract_code: str,
    e2e_test_case_parameter_resources: list[ParameterResource] | None = None,
) -> list[ParameterResource]: ...


def get_contract_required_parameter_resources(
    product_id: str | None = None,
    contract_code: str = "",
    e2e_test_case_parameter_resources: list[ParameterResource] | None = None,
    *,
    product_version_id: str | None = None,
) -> list[ParameterResource]:
    """
    Pure function that retrieves the expected parameters from the smart contract code, then
    validates that their ids have been supplied in the test_case_parameter_resources for the test.
    Returns only the Parameter Resources from test_case_parameter_resources that correspond to the
    Expected Parameters in the Smart Contract code.
    :param contract code: Smart Contract Python code as a string.  If the contract is CLv3, then
    this function assumes that it has no Expected Parameters, and returns an empty list.
    :param test_case_parameter_resources: the Parameter Resources corresponding to the Smart
    Contract's Expected Parameters.  The list is allowed to have Parameter Resources that the
    Smart Contract doesn't need, but should not be missing any that it does expect.  It can be
    empty if the Smart Contract has no Expected Parameters.
    :return: only the parameter resources that need to be uploaded for the smart contract.
    """
    display_id = product_version_id or product_id
    id_type = "product version id" if product_version_id else "product id"
    if not display_id:
        raise ValueError("Either product_id or product_version_id must be provided.")

    contract_expected_parameter_ids: set[str] = {
        p.id for p in get_contract_attributes(contract_code).get("expected_parameters", [])
    }
    test_case_parameter_resource_ids: set[str] = {
        p.id for p in e2e_test_case_parameter_resources or []
    }
    if undefined_ids := contract_expected_parameter_ids - test_case_parameter_resource_ids:
        raise ValueError(
            f"The expected parameter resources {', '.join(sorted(undefined_ids))} are not supplied"
            f" for the {id_type} {display_id}."
        )

    if unused_ids := test_case_parameter_resource_ids - contract_expected_parameter_ids:
        log.info(
            f"Parameter resources {', '.join(sorted(unused_ids))} were supplied, but not required,"
            f" for the {id_type} {display_id}."
        )

    return [
        p
        for p in e2e_test_case_parameter_resources or []
        if p.id in contract_expected_parameter_ids
    ]
