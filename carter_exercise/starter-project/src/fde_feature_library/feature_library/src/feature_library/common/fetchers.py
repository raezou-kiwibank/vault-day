__smart_contract_feature__ = True

# standard libs
from decimal import Decimal

# feature library
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    BalancesDiscreteIntervalFetcher,
    BalancesFilter,
    BalancesIntervalFetcher,
    BalancesObservationFetcher,
    CalendarsIntervalFetcher,
    CalendarsObservationFetcher,
    DefinedDateTime,
    FlagsIntervalFetcher,
    FlagsObservationFetcher,
    LastScheduledEventDateTimesObservationFetcher,
    ParametersIntervalFetcher,
    ParametersObservationFetcher,
    Period,
    PostingsIntervalFetcher,
    RelativeDateTime,
    Shift,
)

FetcherAlias = (
    BalancesDiscreteIntervalFetcher
    | BalancesObservationFetcher
    | BalancesIntervalFetcher
    | CalendarsIntervalFetcher
    | CalendarsObservationFetcher
    | FlagsObservationFetcher
    | FlagsIntervalFetcher
    | LastScheduledEventDateTimesObservationFetcher
    | ParametersIntervalFetcher
    | ParametersObservationFetcher
    | PostingsIntervalFetcher
)
FetcherListAlias = list[FetcherAlias]


def distinct_fetchers(fetchers: FetcherListAlias) -> FetcherListAlias:
    """Filter a list of fetchers to ensure each fetcher ID is unique.

    The first occurrence of a fetcher with a given ID is retained, and subsequent
    fetchers with the same ID are discarded.

    Args:
        fetchers: A list of data fetchers to deduplicate.

    Returns:
        A list of unique data fetchers.
    """
    used_fetcher_ids = set()

    def used(fetcher_id: str) -> bool:
        """Determine if a fetcher ID has been encountered and mark it as used.

        Args:
            fetcher_id: The ID of the fetcher to check.

        Returns:
            True if the fetcher ID has been seen before, False otherwise.
        """
        if fetcher_id in used_fetcher_ids:
            return True
        used_fetcher_ids.add(fetcher_id)
        return False

    return [f for f in fetchers if not used(f.fetcher_id)]


# Balance Observation Fetchers
EFFECTIVE_DATE_BOF_ID = "EFFECTIVE_FETCHER"
EFFECTIVE_DATE_BOF = BalancesObservationFetcher(
    fetcher_id=EFFECTIVE_DATE_BOF_ID, at=DefinedDateTime.EFFECTIVE_DATETIME
)

ALL_BALANCES_LIVE_BOF_ID = "live_balances_bof"
ALL_BALANCES_LIVE_BOF = BalancesObservationFetcher(
    fetcher_id=ALL_BALANCES_LIVE_BOF_ID,
    at=DefinedDateTime.LIVE,
)

DEFAULT_BALANCE_ET_BOF_ID = "default_balance_et_bof"
DEFAULT_BALANCE_ET_BOF = BalancesObservationFetcher(
    fetcher_id=DEFAULT_BALANCE_ET_BOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=BalancesFilter(addresses=[DEFAULT_ADDRESS]),
)

ALL_BALANCES_ET_BOF_ID = "all_balances_et_bof"
ALL_BALANCES_ET_BOF = BalancesObservationFetcher(
    fetcher_id=ALL_BALANCES_ET_BOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

# Retrieves all the postings that happened from the previous day to the effective date.  Since
# these optimised data fetchers are strictly UTC only, timezone-aware Smart Contracts should fetch
# a wider range of data than required and then filter the returned data for the postings within
# the desired time span.
# Note: This fetcher has been defined with the specific end delimiter of EFFECTIVE_DATETIME to
# ensure that when used in the post posting hook the only postings instructions retrieved are the
# ones committed before the proposed posting instructions are processed. This will prevent other
# concurrent operations from being incorrectly retrieved, since the END delimiter defaults to LIVE
EFFECTIVE_DATE_POSTIF_ID = "EFFECTIVE_DATE_POSTINGS_FETCHER"
EFFECTIVE_DATE_POSTIF = PostingsIntervalFetcher(
    fetcher_id=EFFECTIVE_DATE_POSTIF_ID,
    start=RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, shift=Shift(days=-1)),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
)

ONE_MONTH_EFFECTIVE_DATE_BDIF_ID = "one_month_effective_date_fetcher"
ONE_MONTH_EFFECTIVE_DATE_BDIF = BalancesDiscreteIntervalFetcher(
    fetcher_id=ONE_MONTH_EFFECTIVE_DATE_BDIF_ID,
    start=RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, shift=Shift(days=-31)),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
    sampling_period=Period(days=1),
)

data_fetchers = [
    DEFAULT_BALANCE_ET_BOF,
    ALL_BALANCES_ET_BOF,
]


def get_default_balance(
    state: state_utils.SmartContractState,
    denomination: str,
) -> Decimal:
    return state_utils.get_balance_from_state(
        state=state,
        account_address=DEFAULT_ADDRESS,
        fetcher_id=DEFAULT_BALANCE_ET_BOF_ID,
        denomination=denomination,
    )
