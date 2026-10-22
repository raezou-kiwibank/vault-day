# flake8: noqa
# contracts api
from contracts_api import FetchSubAccountData, SubAccountDataScope

EVENT_1 = "EVENT_1"
BOF_1 = "bof_1"

CHAINED_PIF_1 = "chained_pif_1"
CHAINED_PIF_2 = "chained_pif_2"
CHAINED_PIF_3 = "chained_pif_3"
CHAINED_PIFS = [CHAINED_PIF_2, CHAINED_PIF_3]

SUB_ACCOUNT_TYPE_SAVE = "SAVE"
SUB_ACCOUNT_BALANCES_OBSERVATION_FETCHER_ID = "sub_account_bof_id"
FETCH_SUB_ACCOUNT_DATA_BOF_ACTIVE = FetchSubAccountData(
    fetcher_id=SUB_ACCOUNT_BALANCES_OBSERVATION_FETCHER_ID, data_scope=SubAccountDataScope.ACTIVE
)
