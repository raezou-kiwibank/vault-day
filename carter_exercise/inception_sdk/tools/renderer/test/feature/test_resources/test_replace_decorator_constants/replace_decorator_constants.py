# flake8: noqa
# standard libs
from datetime import datetime
from typing import Optional

# contracts api
from contracts_api import (
    PostPostingHookArguments,
    PostPostingHookResult,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    SubAccountVaultObjectsConfig,
    fetch_account_data,
    fetch_sub_account_data,
    requires,
)

# inception sdk
import inception_sdk.tools.renderer.test.feature.test_resources.test_replace_decorator_constants.feature_1 as feature_1
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"


def custom_decorator(*args, **kwargs):
    def wrapper_func(*args, **kwargs):
        pass

    return wrapper_func


EVENT_2 = "EVENT_2"
BOF_2 = "bof_2"
POF_2 = "pof_2"

PIF_2 = "pif_2"
PIF_3 = "pif_3"
PIF_4 = "pif_4"
ALL_LOCAL_PIF = [PIF_2, PIF_3, PIF_4]

CUSTOM_DATA = "CUSTOM_DATA"

chained_bof = feature_1.BOF_1
twice_chained_bof = chained_bof


# variable references in requires and fetch_account_data should be replaced with string literals
@requires(
    event_type=feature_1.EVENT_1,
    parameters=True,
    balances="latest",
    last_execution_datetime=[feature_1.EVENT_1],
)
# constants in requires and fetch_account_data should be replaced with string literals.
@fetch_account_data(
    balances=[BOF_2],
    postings=[feature_1.CHAINED_PIF_1, *feature_1.CHAINED_PIFS, *ALL_LOCAL_PIF],
    event_type=EVENT_2,
    parameters=[POF_2],
)
# fetch_sub_account_data does not require string literal replacement.
@fetch_sub_account_data(
    sub_account_vault_objects_config=SubAccountVaultObjectsConfig.WITH_FETCHER_REQUIREMENTS,
    balances={
        feature_1.SUB_ACCOUNT_TYPE_SAVE: [
            feature_1.FETCH_SUB_ACCOUNT_DATA_BOF_ACTIVE,
        ],
    },
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> Optional[ScheduledEventHookResult]:
    pass


# CUSTOM_DATA should not be replaced since custom decorators ignored
@custom_decorator(data=CUSTOM_DATA)
# chained_bof AND twice_chained_bof should be replaced with the value of feature_1.BOF_1
# i.e. "bof_1"
@fetch_account_data(balances=[chained_bof])
@fetch_account_data(balances={"v1": [chained_bof], "v2": [twice_chained_bof]})
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> Optional[PostPostingHookResult]:
    pass
