# Copyright @ 2020 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
import pathlib
import random
import time
from datetime import datetime
from functools import partial, wraps
from typing import Any, Callable, Iterable, Mapping, TypeAlias

# third party
import confluent_kafka
import requests
from pydantic import BaseModel, model_validator
from requests.exceptions import HTTPError
from semantic_version import Version

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.common.exceptions import (
    ConfigurationException,
    TestSetupException,
    UninitialisedKafkaConsumerException,
    UninitialisedKafkaProducerException,
)
from inception_sdk.test_framework.common.config import (
    FLAGS,
    EnvironmentPurpose,
    extract_framework_environments_from_config,
)
from inception_sdk.vault.core_api import (
    AccountV2TSide,
    AdjustmentsVersioningPolicy,
    VaultCoreExtension,
)
from inception_sdk.vault.environment import Environment

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

WORKFLOW_ENDPOINTS = ["workflow", "policies", "task", "ticket"]
DATA_LOADER_ENDPOINTS = ["dependency-groups", "resource-batches", "resources"]
PROMETHEUS_ENDPOINTS = ["query", "query_range"]
COMMON_ACCOUNT_SCHEDULE_TAG_PATH = (
    "inception_sdk/test_framework/endtoend/resources/account_schedule_tags/"
    "paused_account_schedule_tag.resource.yaml"
)


class SetupError(Exception):
    """Raise exception if test setup is incorrect"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class TestInstance:
    def __init__(self) -> None:
        # uploaded e2e-specific workflow definition id to uploaded e2e-specific workflow definition
        # version id
        # populated by the test framework
        # used for teardown purposes
        # e.g. {"CLOSE_US_ACCOUNT_e2e_GLAJAILTJT": "1.0.0,CLOSE_US_ACCOUNT_e2e_GLAJAILTJT"}
        self.uploaded_workflows: dict[str, str] = {}
        # The original workflow definition ids to uploaded e2e-specific workflow definition ids
        # populated by the framework
        # e.g. {"CLOSE_US_ACCOUNT": "CLOSE_US_ACCOUNT_e2e_GLAJAILTJT"}
        self.workflow_definition_id_mapping: dict[str, str] = {}
        # customer ids for customers created directly by this TestInstance (e.g. exc via workflows)
        # populated by the test framework
        # used for teardown purposes
        self.customers: list[str] = []
        # plan ids for plans created directly by this TestInstance (e.g. exc via workflows)
        # used for teardown purposes
        self.plans: list[str] = []
        # original product id to uploaded e2e-specific product id
        # populated by the test framework
        # e.g. {"current_account": "e2e_current_account_asd213hjh"}
        self.contract_pid_to_uploaded_pid: dict[str, str] = {}
        # original product id to uploaded e2e-specific product version id
        # populated by the test framework
        # e.g. {"current_account": "13110"}
        self.contract_pid_to_uploaded_product_version_id: dict[str, str] = {}
        # original product version id to uploaded e2e-specific product version id
        # populated by the test framework
        # e.g. {"product_version_id_1": "1234"}
        self.product_version_id_to_uploaded_product_version_id: dict[str, str] = {}
        # original internal product id to uploaded e2e-specific product id
        # populated by the test framework
        # e.g. {"TSIDE_LIABILITY': "e2e_TSIDE_LIABILITY_89787230b4030eeb5b4284d473f31ace"}
        self.internal_contract_pid_to_uploaded_pid: dict[str, str] = {}
        # Supervisor contract display name to supervisor contract version id
        # populated by the test framework
        # e.g. {"us_products_supervisor": "BwrqXkvhfS"}
        self.supervisorcontract_name_to_id: dict[str, str] = {}
        # Contract module alias to version id
        # populated by the test framework
        # e.g. {"interest_module": "BwrqXkvhfS"}
        self.contract_module_version_name_to_id: dict[str, str] = {}
        # account ids for accounts created directly by this TestInstance (e.g. exc via workfows)
        # used for teardown purposes
        self.accounts: set[str] = set()
        # original internal account id to uploaded e2e-specific account id. The standalone A/L
        # after the e2e_ prefix indicates whether it is an asset or liability account
        # populated by the test framework
        # e.g. {"ACCRUED_INT_RECEIVABLE": "e2e_A_ACCRUED_INT_RECEIVABLE"}
        self.internal_account_id_to_uploaded_id: dict[str, str] = {}
        # kafka topics to corresponding kafka consumers
        # populated by the test framework
        self._kafka_consumers: dict[str, confluent_kafka.Consumer] | None = None
        # kafka producer for general use
        # populated by the test framework
        self._kafka_producer: confluent_kafka.Producer | None = None
        # determines whether kafka helpers will be used, where available
        self.use_kafka: bool = True
        # determines whether synchronous postings API will be used instead of kafka/async
        self.use_sync_postings: bool = False
        # Product id to attributes. Used by test framework to determine which contracts to create
        # as part of setup
        # Populated by the test writer in each test class
        # Attribute dictionary must include k-v pairs:
        # - key: "path", value: file path to the contract file
        # - key: "template_params", value: dictionary of template param names and values
        # e.g. {
        #    "easy_access_saver": {
        #        "path": "library/easy_access_saver/contracts/easy_access_saver.py",
        #        "template_params": {
        #            "param_name": "value"
        #        },
        #    }
        # }
        self.CONTRACTS: dict[str, dict[str, str | dict[str, str]]] = {}
        # List of TestProduct which contains a logical grouping of ProductVersions to associate
        # with as part of setup, populated by the test writer in each test class.
        # Choose this attribute if your tests require multiple product
        # versions upon setup and/or e2e test requires adjustment versioning policy.
        # The product versions are created in order:
        # - the first index i.e. TestProduct.product_versions[0] will be created with
        # migration strategy `NEW_PRODUCT`
        # - subsequent product_versions defined in the list will be with be created with
        # migration strategy `ADD_VERSION`.
        # e.g. endtoend.testhandle.PRODUCTS: list[TestProduct] = [
        #     TestProduct(
        #         product_id="product_id_1",
        #         product_versions=[
        #             TestProductVersion(
        #                 product_version_id="product_version_id_1",
        #                 path="path/to/contract_1.py",
        #                 template_params={},
        #                 adjustments_versioning_policy=AdjustmentsVersioningPolicy.LATEST,
        #                 supported_denominations: list[str] = ["GBP"],
        #                 is_internal = False,
        #                 display_name = "product_version_id_1",
        #             ),
        #             TestProductVersion(
        #                 product_version_id="product_version_id_2",
        #                 path="path/to/contract_2.py",
        #                 template_params={},
        #                 adjustments_versioning_policy=AdjustmentsVersioningPolicy.HISTORIC,
        #                 supported_denominations: list[str] = ["GBP"],
        #                 is_internal = False,
        #                 display_name = "product_version_id_2",
        #             ),
        #         ]
        #     )
        # ]
        # During setup we obfuscate the product_version_id returned by vault after upload. But to
        # access it use the mapping e.g.
        # `product_version_id_to_uploaded_product_version_id["product_version_id_1"]`.
        self.PRODUCTS: list[TestProduct] = []
        # Contract module id to attributes. Used by test framework to determine which contract
        # modules to create as part of setup
        # Populated by the test writer in each test class
        # Attribute dictionary must include k-v pairs:
        # - key: "path", value: file path to the contract module file
        # Optional attributes:
        # - key: "display_name", value: contract module display name
        # e.g. {
        #   "math_module": {"path": "library/common/contract_modules/math_module.py",
        #                   "display_name": "math_module"}
        # }
        self.CONTRACT_MODULES: dict[str, dict[str, str]] = {}
        # Supervisor contract id to attributes. Used by test framework to determine which supervisor
        # contracts to create as part of setup
        # Populated by the test writer in each test class
        # Attribute dictionary must include k-v pairs:
        # - key: "path", value: file path to the supervisor contract file
        # e.g. {
        #    "offset_supervisor_contract": {
        #       "path": "library/mortgage/contracts/offset_supervisor_contract.py"
        #    }
        # }
        self.SUPERVISORCONTRACTS: dict[str, dict[str, str]] = {}
        # Workflow definition id to workflow definition file path. Used by test framework to
        # determine which workflow definitions to create as part of setup
        # Populated by the test writer in each test class
        # e.g. {
        #    "APPLY_FOR_TIME_DEPOSIT": (
        #        "library/time_deposit/workflows/apply_for_time_deposit.yaml"
        #    ),
        # }
        self.WORKFLOWS: dict[str, str] = {}
        # The schedule event type names per product that will be controlled by a test
        # Populated by the test writer for each Accelerated E2E test
        # e.g. {"current_account": ["SCHEDULE_1", "SCHEDULE_2"]}
        self.CONTROLLED_SCHEDULES: dict[str, list[str]] = {}
        # Product ids to be considered as from/to for a contract version upgrade
        # applies to contract and supervisor contracts.
        # Tag ids will be preserved across the from/to versions.
        # Populated by the test writer for each Accelerated E2E test
        # e.g. [
        #    {"my_product_one": "my_product_two"}
        # ]
        self.CONTRACT_VERSION_UPGRADES: dict[str, str] = {}
        # flag definition id to flag definition file path
        # Populated by the test writer in each test class
        # e.g. {
        #   "CURRENT_ACCOUNT_TIER_UPPER": (
        #       "library/current_account/flag_definitions/current_account_tier_upper.resource.yaml"
        #   ),
        # }
        self.FLAG_DEFINITIONS: dict[str, str] = {}
        # Maps TSIDE to a list of internal account ids. Used by test framework to determine which
        # internal products and accounts to create as part of setup.
        # Populated by the test writer in each test class
        # e.g.  AccountV2TSide.T_SIDE_ASSET: [
        #   "ACCRUED_INTEREST_RECEIVABLE_ACCOUNT", "INTEREST_PAID_ACCOUNT"
        # ],
        self.TSIDE_TO_INTERNAL_ACCOUNT_ID: dict[AccountV2TSide, list[str]] = {}
        # Product to schedule event type to tag id
        # Populated by the framework
        # e.g. {"CURRENT_ACCOUNT_TIER_UPPER": "E2E_CURRENT_ACCOUNT_TIER_UPPER"}
        # e.g. {
        #  "current_account": {
        #    "SCHEDULE_1": "e2e_current_account_abcd",
        #    "SCHEDULE_2": "e2e_current_account_efgh"
        #  }
        # }
        self.controlled_schedule_tags: dict[str, dict[str, str]] = {}
        # The paused tag id to use by default for schedules that aren't explicitly included in
        # controlled schedule tags
        # Populated by the framework
        self.default_paused_tag_id: str = ""
        # Original flag id to uploaded e2e-specific id
        # Populated by the framework
        # e.g. {"CURRENT_ACCOUNT_TIER_UPPER": "E2E_CURRENT_ACCOUNT_TIER_UPPER"}
        self.flag_definition_id_mapping: dict[str, str] = {}
        # Flag file path to uploaded e2e-specific id
        # Populated by the framework
        # e.g. {
        #  "library/current_account/flag_definitions/current_account_tier_upper.resource.yaml":
        #  "E2E_CURRENT_ACCOUNT_TIER_UPPER"
        # }
        self.flag_file_paths_to_e2e_ids: dict[str, str] = {}
        # Calendar ids to calendar definition file path
        # Populated by the test writer
        # e.g. {
        #     "TIME_DEPOSIT_BANK_HOLIDAY": (
        #         "library/time_deposit/calendars/time_deposit_bank_holiday.resource.yaml"
        #     )
        # }
        self.CALENDARS: dict[str, str] = {}
        # Calendar id to uploaded e2e-specific id
        # Populated by the framework
        # e.g. {
        #     "TIME_DEPOSIT_BANK_HOLIDAY": "e2e_TIME_DEPOSIT_BANK_HOLIDAY_BwrqXkvhfS"
        # }
        self.calendar_ids_to_e2e_ids: dict[str, str] = {}
        # The default internal account id, used by the framework for certain features like zeroing
        # customer account balances before closure as part of teardown
        self.internal_account: str = "DUMMY_CONTRA"
        # A session to minimise the number of new connections opened by a given instance
        self.session: requests.Session = requests.Session()
        # A workflows-specific session to allow for different authentication headers.
        self.workflows_session: requests.Session = requests.Session()
        # environment names to environment properties. See the config.json for an example
        self.available_environments: dict[str, Environment]
        # environment_name used by this instance, must be a key in `self.available_environments`
        self.environment_name: str = ""
        # Environment config for the environment specified by environment_name
        self.environment: Environment

        # Whether to check version numbers in the deployment file and test instance and
        # fail if there's a mismatch
        self.do_version_check: bool = False
        # Number of seconds delay between one schedule tag pause update and the next
        # This is needed to ensure the results can be distinguished
        # 120 secs should be min because the averaging window on graphs is typically 2min
        self.paused_schedule_tag_delay: int = 600
        # Mappings for CLU references, to be used when uploading e2e resources that depend on these
        # references (e.g. uploading a contract that depends on a flag definition).
        # This is simply a merged version of the other id mapping dictionaries to avoid having to
        # repeat the merge in different helpers
        self.clu_reference_mappings: dict = {}
        # Vault version
        # TODO: In the future can initialise it to a dummy vault_version that will error if you
        # call it and return a helpful message like (you need to load env config before using the
        # vault_version), and then load config method then calls a 'setup' method on the version
        self.vault_version: Version
        # Enabled Vault Core Addons on the test instance
        self.enabled_extensions: list[VaultCoreExtension]
        # A list of directories to gather Parameter resources from. Used by test framework to
        # determine which Parameters(s) to create as part of setup.
        # Populated by the test writer in each test class.
        # e.g. [
        #     "path/to/resource/dir"
        #     "path/to/another/dir"
        # ]
        self.PARAMETER_RESOURCE_DIRS: list[str] = []
        # Parameter Resource (Expected Parameter) id to uploaded e2e-specific id
        # Populated by the framework
        # e.g. {
        #     "SOME_EXPECTED_STRING_PARAM": "e2e_SOME_EXPECTED_STRING_PARAM_8aacdb17187e6acf23"
        # }
        self.parameter_resource_id_to_uploaded_id: dict[str, str] = {}

    def post_init(self) -> None:
        """
        After the TestInstance is instantiated, set the environment variables and Vault
        instance information for the duration of the test execution. This allows class-level skip
        decorators to check the environment's Vault version and extensions.
        """
        # we allow unknown because there may be unittest flags in argv
        flag_utils.parse_flags(allow_unknown=True)
        self.use_kafka = FLAGS.use_kafka
        self.use_sync_postings = FLAGS.use_sync_postings
        log.info(
            f"use_kafka is set to {self.use_kafka} and use_sync_postings is set to {self.use_sync_postings}"  # noqa: E501
        )

        setup_environments(environment_purpose=EnvironmentPurpose.E2E)
        set_vault_instance_information()

    @property
    def kafka_consumers(self):
        if self._kafka_consumers is not None:
            return self._kafka_consumers
        else:
            raise UninitialisedKafkaConsumerException(
                "Kafka consumers have not been initialised but are requested. Is the test being "
                "run with --nouse_kafka / --use_kafka=False but requires Kafka?"
            )

    @kafka_consumers.setter
    def kafka_consumers(self, consumers: dict[str, confluent_kafka.Consumer]):
        self._kafka_consumers = consumers

    @property
    def kafka_producer(self):
        if self._kafka_producer is not None:
            return self._kafka_producer
        else:
            raise UninitialisedKafkaProducerException(
                "Kafka producer has not been initialised but is requested. Is the test being run "
                "with --nouse_kafka / --use_kafka=False but requires Kafka?"
            )

    @kafka_producer.setter
    def kafka_producer(self, producer: confluent_kafka.Producer):
        self._kafka_producer = producer


def setup_environments(environment_purpose: EnvironmentPurpose, environment_name: str = "") -> None:
    environment, available_environments = extract_framework_environments_from_config(
        environment_purpose=environment_purpose, environment_name=environment_name
    )
    endtoend.testhandle.environment = environment
    endtoend.testhandle.available_environments = available_environments
    set_session_headers()


def set_session_headers() -> None:
    headers = {
        "Content-Type": "application/json",
    }
    endtoend.testhandle.session.headers.update(
        headers | endtoend.testhandle.environment.auth_headers()
    )
    # We only set workflow session headers if config includes workflow api url to avoid raising
    # exceptions about missing service acount auth unnecessarily. It's a bit too complicated to
    # dynamically determine if we'll hit workflow endpoints ahead of time.
    if endtoend.testhandle.environment.workflow_api_url:
        endtoend.testhandle.workflows_session.headers.update(
            headers | endtoend.testhandle.environment.workflow_auth_headers()
        )


def set_vault_instance_information() -> None:
    """
    set_vault_instance_information sets the vault version and enabled extensions for the environment
    """
    vault_instance_information = endtoend.core_api_helper.get_vault_instance_information()
    endtoend.testhandle.vault_version = Version(
        version_string=vault_instance_information.version.version_string
    )
    endtoend.testhandle.enabled_extensions = [
        VaultCoreExtension(e) for e in vault_instance_information.extensions
    ]
    log.info(f"Environment Vault version: {endtoend.testhandle.vault_version}")
    log.info(
        "Environment enabled Vault Core extensions: "
        f"{[e.name for e in endtoend.testhandle.enabled_extensions]}"
    )


def get_url(path: str) -> str:
    environment = endtoend.testhandle.environment

    if any(endpoint in path for endpoint in WORKFLOW_ENDPOINTS):
        if not environment.workflow_api_url:
            raise ConfigurationException(
                f"Attempting to use Workflows API {path=} but `workflow_api_url` "
                "missing from environment config"
            )
        url = environment.workflow_api_url + path
    elif any(endpoint in path for endpoint in DATA_LOADER_ENDPOINTS):
        if not environment.data_loader_api_url:
            raise ConfigurationException(
                f"Attempting to use Dataloader API {path=} but `data_loader_api_url` "
                "missing from environment config"
            )
        url = environment.data_loader_api_url + path
    else:
        url = environment.core_api_url + path
    return url


# these are _very_ simplified views of requests annotations for our purposes
RequestsData: TypeAlias = str | Mapping[str, Any] | Iterable[tuple[str, str | None]]
RequestsParams: TypeAlias = str | Mapping[str, str | Iterable[str] | None]


def send_request(
    method: str,
    path: str,
    data: RequestsData | None = None,
    params: RequestsParams | None = None,
    retry_on_expired_jwt=True,
):
    url = get_url(path)
    # Only use workflows session if required since it has to use service account auth
    if (
        endtoend.testhandle.environment.workflow_api_url
        and endtoend.testhandle.environment.workflow_api_url in url
    ):
        session = endtoend.testhandle.workflows_session
    else:
        session = endtoend.testhandle.session

    r: requests.Response = session.request(method, url, params=params, data=data)
    if not r.ok:
        # a JWT may expire during longer end-to-end tests
        if (
            r.status_code == 401
            and session is endtoend.testhandle.session
            and endtoend.testhandle.environment.auth.jwt is not None
            and retry_on_expired_jwt
        ):
            log.debug("Reauthenticating due to expired JWT")
            endtoend.testhandle.environment.auth.jwt.refresh_jwt()
            return send_request(
                method=method,
                path=path,
                data=data,
                params=params,
                # only retry once to avoid an endless loop if something goes wrong with jwt auth
                retry_on_expired_jwt=False,
            )

        # We want to log 400 errors more verbosely to help understand what went wrong
        # Use debug for other cases, as there are genuine cases where expect error responses from
        # Core API and wouldn't want them to be misinterpreted as actual issues
        log_level = log.error if r.status_code == 400 else log.debug
        log_level(f"Method: {method}, url {url}, params {params}, data {data}")
        log_level(r.content)

    r.raise_for_status()

    return r.json()


def list_resources(
    endpoint: str,
    params: Mapping[str, str | Iterable[str] | None] | None = None,
    page_size: int = 50,
    result_limit: int = 0,
    api_version: str = "v1",
) -> list[dict[str, Any]]:
    """
    Reusable method to get all or a subset of results from a paginated endpoint
    :param endpoint: the api endpoint (e.g. balances, account-schedule-updates). Combined with the
    api version to construct the API path to be added to the base url
    :param params: dictionary of parameters to add to the request url
    :param page_size: page size per request. Adjusted for the final request if a result limit
    is specified and page size > (result limit - results retrieved)
    :param result_limit: maximum number of resources to retrieve. 0 or less treated as no limit
    :param api_version: the Vault api version. Not to be confused with Vault version. Combined with
    endpoint to construct the API path the API path to be added to the base url
    :return: list of resources from the relevant endpoint
    """

    results: list[dict[str, Any]] = []
    request_params: dict[str, str | Iterable[str] | None] = dict(params) if params else {}
    page_token = ""

    path = f"/{api_version}/{endpoint}"

    while True:
        if result_limit > 0:
            page_size = min(page_size, result_limit - len(results))
        request_params.update({"page_size": str(page_size), "page_token": page_token})
        resp = send_request("get", path, params=request_params)
        results.extend(list(resp.values())[0])
        page_token = resp["next_page_token"]
        if page_token == "" or (0 < result_limit <= len(results)):
            break

    return results


def teardown_test_resources() -> None:
    """
    Teardown any resources that are specific to a test
    """

    # Resources in the testhandle are not explicitly segregated by test, but as tests within
    # a class (and therefore using the same testhandle) are executed sequentially, so the
    # testhandle will only ever contain the resources for the last test
    for customer in endtoend.testhandle.customers:
        accounts_list = endtoend.core_api_helper.get_customer_accounts_v2(customer)
        for account in accounts_list:
            endtoend.testhandle.accounts.add(account["id"])
        endtoend.core_api_helper.set_customer_status(customer, "CUSTOMER_STATUS_DECEASED")
    endtoend.testhandle.customers.clear()

    endtoend.contracts_helper.teardown_all_accounts()
    endtoend.supervisors_helper.close_all_plans()


def teardown_shared_resources() -> None:
    """
    Teardown any resources that are shared by test in a test class
    """
    endtoend.workflows_helper.delete_all_workflows()
    endtoend.contracts_helper.deactivate_all_calendars()
    if endtoend.testhandle.use_kafka:
        # Setup can fail mid-kafka initialisation, handle this gracefully
        try:
            for consumer in endtoend.testhandle.kafka_consumers.values():
                if consumer:
                    consumer.close()
            endtoend.testhandle.kafka_consumers = {}
            endtoend.testhandle.kafka_producer.flush()
        except (UninitialisedKafkaConsumerException, UninitialisedKafkaProducerException):
            # This can happen if teardown is triggered before the kafka consumers/producer are
            # initialised, which can be ignored since there's no teardown required in this case
            pass
        except confluent_kafka.KafkaException as e:
            log.warning(f"Encountered Kafka Exception during teardown: {e}")


def _retry_inner(
    func: Callable,
    expected_result: Any = None,
    result_wrapper: Callable | None = None,
    max_retries: int = 5,
    timeout: float = 0,
    sleep_time: float = 1,
    back_off: float = 1.5,
    exceptions=Exception,
    on_http_error_codes: list[int] | None = None,
    return_wrapped_result: bool = False,
    failure_message: str = "Error",
) -> Any:
    """
    Retry the function if exceptions of the specified types are raised until either:
    - the optional expected result is returned
    - max_retries count is reached
    - timeout is reached
    Retries are separated by a sleep whose duration is calculated as
    random_number_between(0, sleep_time * (back_off ** attempt_number))
    :param func: Callable that returns the result
    :param expected_result: expected result to poll for. Optional
    :param result_wrapper: Callable to transform func's return.
    :param max_retries: number of times func will be checked
    :param timeout: total seconds to elapse before timing out. 0 means no timeout
    :param sleep_time: base number of seconds to wait between calls to func
    :param back_off: determines how much the sleep time changes after each unsuccessful retry. If
     == 1, the sleep time does not increase. If > 1 the sleep time increases. If < 1 the sleep time
     decreases.
    :param exceptions: an exception of tuple of exceptions that will be caught and retried.
    :param on_http_error_codes: list of http error codes to retry for. If empty all HTTP error codes
    will be retried
    :param return_wrapped_result: if true and a result_wrapper is passed in, the transformed result
    is returned. Otherwise the raw function result is returned
    :param return_wrapped_result: if true and a result_wrapper is passed in, the transformed result
    is returned. Otherwise the raw function result is returned
    :return: the function return, potentially transformed by the result_wrapper (see
    return_wrapped_result)
    """
    start_time = time.time()
    num_tries = 0
    _sleep_time = sleep_time
    on_http_error_codes = on_http_error_codes or []

    while True:
        try:
            original_result = func()
            wrapped_result = result_wrapper(original_result) if result_wrapper else original_result
            # We may want expected results like {} and [] to be checked against
            if expected_result is not None and expected_result != wrapped_result:
                if result_wrapper:
                    raise ValueError(
                        f"{datetime.utcnow()} - "
                        f"Wrapped result {wrapped_result} does not match"
                        f" {expected_result}. wrapper: {result_wrapper}. Original"
                        f" result: {original_result}"
                    )
                else:
                    raise ValueError(
                        f"{datetime.utcnow()} - "
                        f"Result {wrapped_result} does not match {expected_result}"
                    )
            return wrapped_result if return_wrapped_result else original_result
        except exceptions as e:
            # If on_http_error_codes was provided, HTTPErrors are only retried if their status code
            # is found in the list
            if not isinstance(e, HTTPError) or (
                isinstance(e, HTTPError)
                and (not on_http_error_codes or e.response.status_code in on_http_error_codes)
            ):
                log.debug(e)

                if num_tries >= max_retries:
                    log.exception(f"{failure_message} - Retry count exceeded")
                    raise e
                if timeout and time.time() - start_time > timeout:
                    log.exception(f"{failure_message} - Timeout reached after {timeout}s")
                    raise e
                # this is effectively the 'Full Jitter' algorithm described at
                # https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
                _sleep_time = random.uniform(0, sleep_time * (back_off**num_tries))
                time.sleep(_sleep_time)
                num_tries += 1
                log.debug(f"Retrying {func}. Total tries: {num_tries}")
            else:
                raise e


def retry_decorator(
    expected_result: Any = None,
    result_wrapper: Callable | None = None,
    max_retries: int = 5,
    timeout: float = 0,
    sleep_time: float = 1,
    back_off: float = 1.5,
    exceptions=Exception,
    on_http_error_codes: list[int] | None = None,
    return_wrapped_result: bool = False,
) -> Callable:
    """
    Creates a decorator that wraps the function with _retry_inner. See this method's doc string for
    more detail
    :param expected_result: expected result to poll for
    :param result_wrapper: callable to transform the decorated function's return. Optional
    :param max_retries: int, number of times func will be checked
    :param timeout: float, total seconds to elapse before timing out. 0 means no timeout
    :param sleep_time: float, number of seconds to wait between calls to func
    :param back_off: float, multiplication factor for the sleep time between retries. If set to 1,
    sleep time is unchanged between each retry.
    :param exceptions: an exception of tuple of exceptions that will be caught and retried.
    :param on_http_error_codes: list of http error codes to retry for. If empty all HTTP error codes
    will be retried
    :param return_wrapped_result: if true and a result_wrapper is passed in, the transformed result
    is returned. Otherwise the raw function result is returned
    :return: decorator
    """

    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            return _retry_inner(
                func=partial(func, *args, **kwargs),
                expected_result=expected_result,
                result_wrapper=result_wrapper,
                max_retries=max_retries,
                timeout=timeout,
                sleep_time=sleep_time,
                back_off=back_off,
                exceptions=exceptions,
                on_http_error_codes=on_http_error_codes,
                return_wrapped_result=return_wrapped_result,
            )

        return decorator

    return wrapper


def retry_call(
    func: Callable,
    f_args=None,
    f_kwargs=None,
    expected_result: Any = None,
    result_wrapper: Callable | None = None,
    max_retries: int = 5,
    timeout: float = 0,
    sleep_time: float = 1,
    back_off: float = 1.5,
    exceptions=Exception,
    return_wrapped_result: bool = False,
    failure_message: str = "Error",
) -> Any:
    """
    Wraps a function with _retry_inner. See this method's doc string for more detail
    :param func: function to retry
    :param f_args: the function's positional arguments
    :param f_kwargs: the function's kw args
    :param expected_result: expected result to poll for
    :param result_wrapper: callable to transform the decorated function's return. Optional
    :param max_retries: int, number of times func will be checked
    :param timeout: float, total seconds to elapse before timing out. 0 means no timeout
    :param sleep_time: float, number of seconds to wait between calls to func
    :param back_off: float, multiplication factor for the sleep time between retries. If set to 1,
    sleep time is unchanged between each retry.
    :param exceptions: an exception of tuple of exceptions that will be caught and retried.
    :param return_wrapped_result: if true and a result_wrapper is passed in, the transformed result
    is returned. Otherwise the raw function result is returned
    :param failure_message: if specified, this message will be included in any exception raised by
    the wrapper (e.g. timeout reached, max retries attempted)
    :return: the function return, potentially transformed by the result_wrapper (see
    return_wrapped_result)
    """
    f_args = f_args or []
    f_kwargs = f_kwargs or {}
    return _retry_inner(
        func=partial(func, *f_args, **f_kwargs),
        expected_result=expected_result,
        result_wrapper=result_wrapper,
        max_retries=max_retries,
        timeout=timeout,
        sleep_time=sleep_time,
        back_off=back_off,
        exceptions=exceptions,
        return_wrapped_result=return_wrapped_result,
        failure_message=failure_message,
    )


class TestProductVersion(BaseModel):
    """
    A TestProductVersion contains the fields required to create a product version in Vault.
    """

    product_version_id: str
    path: str | pathlib.Path
    supported_denominations: list[str]
    template_params: dict[str, str] | None = None
    # This defaults to AdjustmentsVersioningPolicy.LATEST in the API
    adjustments_versioning_policy: AdjustmentsVersioningPolicy | None = None
    is_internal: bool = False
    display_name: str = ""


class TestProduct(BaseModel):
    """
    A TestProduct upload logically groups a list of product versions to facilitate the upload of
    these multiple product versions during e2e setups.

    Creation of new product versions are created in the order they are declared in
    `product_version`. This will assume that the first index TestProduct.product_versions[0]
    will be the initial product version created with migration strategy `NEW_PRODUCT`. Subsequent
    product versions (say index 1, 2...) will be created with migration strategy `ADD_VERSION`.
    """

    product_id: str
    product_versions: list[TestProductVersion]

    @model_validator(mode="after")
    def check_product_version_ids_uniqueness(self):
        if self.product_versions:
            seen = set()
            duplicate_ids = []
            for pv in self.product_versions:
                if pv.product_version_id in seen:
                    duplicate_ids.append(pv.product_version_id)
                seen.add(pv.product_version_id)

            if duplicate_ids:
                # return duplicate ids to client in error message
                raise TestSetupException(
                    "Each product's product version provided for upload "
                    f"must have unique product_version_id. Duplicates found {sorted(duplicate_ids)}"
                )
        return self


if __name__ == "__main__":
    pass
