__smart_contract_feature__ = True

# Balance Observation Fetchers
from contracts_api import BalancesObservationFetcher, DefinedDateTime

PRINCIPAL_ET_BOF_ID = "PRINCIPAL_ET_BOF"
PRINCIPAL_ET_BOF = BalancesObservationFetcher(
    fetcher_id=PRINCIPAL_ET_BOF_ID, at=DefinedDateTime.EFFECTIVE_DATETIME
)


data_fetchers = [
    PRINCIPAL_ET_BOF,
]
