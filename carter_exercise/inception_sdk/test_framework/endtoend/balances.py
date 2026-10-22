# standard libs
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.common.balance_helpers import (
    Balance,
    BalanceDimensions,
    NetBalance,
    NetBalanceMismatches,
    NetBalances,
    compare_balances as compare_balances_inner,
    dict_to_net_balance,
    get_account_ids_from_net_balances,
    get_net_balance_mismatches,
    get_net_balances_for_account,
)
from inception_sdk.test_framework.endtoend.core_api_helper import (
    get_live_balances,
    get_timerange_balances,
    list_all,
    list_balances_end,
    list_balances_live,
    list_balances_series,
)
from inception_sdk.test_framework.endtoend.kafka_helper import kafka_only_helper, wait_for_messages
from inception_sdk.vault.core_api import (
    BalanceTimeView,
    ListBalancesEndRequest,
    ListBalancesLiveRequest,
    ListBalancesSeriesRequest,
    LiveBalanceV2,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

ACCOUNT_BALANCE_EVENTS_TOPIC = "vault.core_api.v1.balances.account_balance.events"

ACCOUNT_BALANCE_V2_EVENTS_TOPIC = "vault.core_api.v2.balances.balance.events"


@kafka_only_helper
def wait_for_balance_updates(
    posting_instruction_batch_ids: list[str],
    matched_message_timeout: int = 30,
    inter_message_timeout: int = 30,
) -> list[dict[str, str]]:
    """
    Kafka-based helper to wait for balance updates.

    :param posting_instruction_batch_ids: List of posting instruction batch ids
        that have triggered the balance updates to wait for
    :param matched_message_timeout: A maximum time to wait between receiving matched messages from
        the consumer (0 for no timeout).
    :param inter_message_timeout: A maximum time to wait between receiving any messages from the
        consumer (0 for no timeout).
    :return: List of balances.
    """

    consumer = endtoend.testhandle.kafka_consumers[ACCOUNT_BALANCE_EVENTS_TOPIC]

    balances = []

    def matcher(event_msg, unique_message_ids):
        pib_id = event_msg["posting_instruction_batch_id"]
        event_request_id = event_msg["event_id"]
        if pib_id in unique_message_ids:
            items = [
                item
                for item in event_msg["balances"]
                if item["posting_instruction_batch_id"] == pib_id
            ]
            balances.extend(items)
            return pib_id, event_request_id, True
        else:
            return "", event_request_id, False

    log.info(f"Waiting for {len(posting_instruction_batch_ids)} balance updates")

    wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids={pib_id: None for pib_id in posting_instruction_batch_ids},
        matched_message_timeout=matched_message_timeout,
        inter_message_timeout=inter_message_timeout,
    )

    log.info("All balances updated")
    return balances


def wait_for_all_account_balances(
    accounts_expected_balances: dict[str, list[tuple[BalanceDimensions, str]]],
    description: str = "",
    back_off: float = 1.5,
) -> None:
    """
    Waits until all accounts match the expected balances outcome

    :param accounts_expected_balances: The expected balances keyed by account ID.
    :param description: Description of the expected outcome.
    :return: None.
    """

    if endtoend.testhandle.use_kafka:
        wait_for_account_balances_by_ids(accounts_expected_balances)
    else:
        for account_id in [*accounts_expected_balances.keys()]:
            endtoend.helper.retry_call(
                func=compare_balances,
                f_args=[
                    account_id,
                    accounts_expected_balances[account_id],
                ],
                expected_result={},
                back_off=back_off,
                failure_message=f'Unexpected balances for {account_id} at stage "{description}"',
            )


@dataclass
class AccountBalances:
    value_balances: list[tuple[BalanceDimensions, str]] = field(default_factory=list)
    booking_balances: list[tuple[BalanceDimensions, str]] = field(default_factory=list)


def wait_for_expected_account_balances_v2(
    accounts_expected_balances: dict[str, AccountBalances],
    description: str = "",
    back_off: float = 1.5,
) -> None:
    """
    Waits until all accounts match the expected balances outcome.

    :param accounts_expected_balances: The expected value and booking balances keyed by account id.
    :param description: The description of the expected outcome.
    :return: None.
    """

    if endtoend.testhandle.use_kafka:
        wait_for_account_balances_v2_by_ids(
            accounts_expected_balances,
        )
    else:
        for account_id in [*accounts_expected_balances.keys()]:
            endtoend.helper.retry_call(
                func=compare_live_balances,
                f_args=[
                    account_id,
                    accounts_expected_balances[account_id],
                ],
                expected_result=({}, {}),
                back_off=back_off,
                failure_message=f'Unexpected balances for {account_id} at stage "{description}"',
            )


def wait_for_account_balances_by_pib(
    account_id: str, posting_instruction_batch_id: str | None = None
) -> list[dict[str, str]]:
    """
    Posting Instruction Batch ID has been removed from the balances endpoint.
    The current implementation is supported from our side and is a simple
    iteration to find which balances match up with a PIB ID
    """
    balances = get_timerange_balances(account_id)

    if posting_instruction_batch_id:
        return [
            balance
            for balance in balances
            if balance["posting_instruction_batch_id"] == posting_instruction_batch_id
        ]

    return balances


@kafka_only_helper
def wait_for_account_balances_by_ids(
    accounts_expected_balances: dict[str, list[tuple[BalanceDimensions, str]]],
    matched_message_timeout: int = 30,
    inter_message_timeout: int = 30,
    return_failed_accounts: bool = False,
) -> None | dict[str, list[tuple[BalanceDimensions, str]]]:
    """
    Listen to the balance update events Kafka topic for the account_ids specified.

    :param accounts_expected_balances: The expected balances keyed by account ID.
    :param matched_message_timeout: A maximum time to wait between receiving matched messages from
        the consumer (0 for no timeout).
    :param inter_message_timeout: A maximum time to wait between receiving any messages from the
        consumer (0 for no timeout).
    :param return_failed_accounts: Boolean to return failed account ids instead of raising an
        exception.
    :return: None by default. If `return_failed_accounts` is True, the `accounts_expected_balances`
        entries that were not received are returned.
    :raises Exception: Raised if some `accounts_expected_balances` are not received and
        `return_failed_accounts` is False.
    """
    consumer = endtoend.testhandle.kafka_consumers[ACCOUNT_BALANCE_EVENTS_TOPIC]

    def matcher(event_msg, unique_message_ids):
        event_account_id = event_msg["account_id"]
        event_request_id = event_msg["event_id"]
        if event_account_id in unique_message_ids:
            balance_wrapper = event_msg.get("balances")
            actual_balances = create_balance_dict(balance_wrapper)
            if (
                compare_balances_inner(
                    accounts_expected_balances[event_account_id], actual_balances
                )
                == {}
            ):
                return (
                    event_account_id,
                    event_request_id,
                    True,
                )
            else:
                return ("", event_request_id, True)
        else:
            return "", event_request_id, False

    failed_account_ids = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids=accounts_expected_balances,
        matched_message_timeout=matched_message_timeout,
        inter_message_timeout=inter_message_timeout,
    )

    if return_failed_accounts:
        return failed_account_ids

    if len(failed_account_ids) > 0:
        transformed_outcome = (
            "Failed to retrieve all expected account balance updates for account ids\n"
        )

        for account_id in failed_account_ids.keys():
            transformed_outcome += f"\n{account_id}: \n" + str(
                accounts_expected_balances[account_id]
            )
        raise Exception(transformed_outcome)
    return None


@kafka_only_helper
def wait_for_account_balances_v2_by_ids(
    accounts_expected_balances: dict[str, AccountBalances],
    matched_message_timeout: int = 30,
    inter_message_timeout: int = 30,
    return_failed_accounts: bool = False,
) -> None | dict[str, list[tuple[BalanceDimensions, str]]]:
    """
    Listens to the balance update events Kafka topic for the specified account IDs.

    :param accounts_expected_value_balances: The expected value balances keyed by account ID.
    :param accounts_expected_booking_balances: The expected booking balances keyed by account ID.
    :param matched_message_timeout: The maximum time to wait between receiving matched messages from
        the consumer (0 for no timeout).
    :param inter_message_timeout: The maximum time to wait between receiving any messages from the
        consumer (0 for no timeout).
    :param return_failed_accounts: Boolean to return failed account ids instead of raising an
        exception.
    :return: None by default. If `return_failed_accounts` is True, the `accounts_expected_balances`
        entries that were not received are returned.
    :raises Exception: Raised if some `accounts_expected_balances` are not received and
        `return_failed_accounts` is False.
    """
    consumer = endtoend.testhandle.kafka_consumers[ACCOUNT_BALANCE_V2_EVENTS_TOPIC]

    def matcher(event_msg, unique_message_ids):
        event_account_id = event_msg["account_id"]
        event_request_id = event_msg["event_id"]
        if event_account_id in unique_message_ids:
            value_balances = event_msg["value_balances"]
            booking_balances = event_msg["booking_balances"]

            actual_value_balances = create_balance_dict(value_balances)
            actual_booking_balances = create_balance_dict(booking_balances)
            if all(
                [
                    compare_balances_inner(
                        accounts_expected_balances[event_account_id].value_balances,
                        actual_value_balances,
                    )
                    == {},
                    compare_balances_inner(
                        accounts_expected_balances[event_account_id].booking_balances,
                        actual_booking_balances,
                    )
                    == {},
                ]
            ):
                return (
                    event_account_id,
                    event_request_id,
                    True,
                )
            return ("", event_request_id, True)
        else:
            return "", event_request_id, False

    failed_account_ids = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids=accounts_expected_balances,
        matched_message_timeout=matched_message_timeout,
        inter_message_timeout=inter_message_timeout,
    )

    if return_failed_accounts:
        return failed_account_ids

    if len(failed_account_ids) > 0:
        transformed_outcome = (
            "Failed to retrieve all expected account balance updates for account ids\n"
        )

        for account_id in failed_account_ids.keys():
            transformed_outcome += f"\n{account_id}: \n" + str(
                accounts_expected_balances[account_id]
            )
        raise Exception(transformed_outcome)
    return None


def wait_for_posting_balance_updates(
    account_id: str, posting_instruction_batch_id: str
) -> list[dict[str, str]]:
    """
    Waits for the balances updates corresponding to a given posting instruction batch.

    :param account_id: Account ID to check balances for.
    :param posting_instruction_batch_id: ID of the posting instruction batch to get balance
        updates for.
    :return: the balances updated by the posting instruction batch. This does not include balances
        that weren't affected.
    """

    if endtoend.testhandle.use_kafka:
        return wait_for_balance_updates(
            posting_instruction_batch_ids=[posting_instruction_batch_id],
        )
    else:
        return endtoend.helper.retry_call(
            func=wait_for_account_balances_by_pib,
            f_kwargs={
                "account_id": account_id,
                "posting_instruction_batch_id": posting_instruction_batch_id,
            },
            expected_result=True,
            result_wrapper=lambda x: len(x) > 0,
            failure_message=(
                f"Balances for pib {posting_instruction_batch_id} and account id "
                f"{account_id} never updated"
            ),
        )


def wait_for_account_balances(
    account_id: str,
    expected_balances: list[tuple[BalanceDimensions, str]],
    description: str = "",
    back_off: float = 1.5,
) -> None:
    """
    Waits until balances match the expected outcome.

    :param account_id: The account ID to check balances for,
    :param expected_balances: The expected balances.
    :param description: Description of the expected outcome.
    :return: None.
    """
    log.info(f"Waiting for account balances for: {account_id=}")

    if endtoend.testhandle.use_kafka:
        wait_for_account_balances_by_ids({account_id: expected_balances})
    else:
        endtoend.helper.retry_call(
            func=compare_balances,
            f_args=[account_id, expected_balances],
            expected_result={},
            back_off=back_off,
            failure_message=f'Unexpected balances for {account_id} at stage "{description}"',
        )

    log.info(f"Account balances found for: {account_id=}")


def get_balance_timestamp(balance: dict[str, str]) -> str:
    """
    Returns the timestamp associated with a balance. This works for both v1 and v2 balances.

    :param balance: The dictionary containing the keys and values associated with a single balance.
    :return: The timestamp for the balance.
    """
    # Balance v2 uses timestamp and balance v1 uses value_time
    timestamp = balance.get("value_time")
    if timestamp is not None:
        return timestamp
    # The timestamp on v2 balances may be None, so we set it to an empty string
    return balance.get("timestamp", "")


def create_balance_dict(balances: list[dict[str, str]]) -> defaultdict[BalanceDimensions, Balance]:
    """
    Converts a balance response into a dictionary from balance dimension to the corresponding
    balance.

    :param balances: List of balances returned by the /v1/balances endpoint, assumed to be
        in ascending order.
    :return: Contract-like balance dictionary mapping dimensions to balances. If multiple balances
        exist for a given BalanceDimension, only the first balance will be returned for it.
    """
    balance_dict: dict[BalanceDimensions, Balance] = {}
    for balance in balances:
        key: BalanceDimensions = BalanceDimensions(
            balance["account_address"],
            balance["asset"],
            balance["denomination"],
            balance["phase"],
        )
        # We assume the balances are in descending order by timestamp, and so ensure we only
        # return the latest balance for a given coordinate. Any balances for a given
        # coordinate will only be added to this dictionary once; successive ones will be ignored.
        if key not in balance_dict:
            balance_dict[key] = Balance(
                balance["total_credit"],
                balance["total_debit"],
                balance["amount"],
                standardise_balance_value_time_format(get_balance_timestamp(balance)),
            )

    balance_default_dict = defaultdict(lambda: Balance(0, 0, 0), balance_dict)

    return balance_default_dict


def compare_balances(
    account_id: str, expected_balances: list[tuple[BalanceDimensions, str]]
) -> dict[BalanceDimensions, dict[str, Decimal]]:
    """
    Compare the actual live balances to specified expected_balances. Any dimensions not included in
    expected_balances are ignored. Only net values are compared, differences in credit and debit
    values are not considered. If there's a mismatch in net values, an entry is added to the
    dictionary in the following format:
    {
        BalanceDimensions: {
            'expected': Decimal(expected net)
            'actual': Decimal(actual net)
        }
    }

    :param account_id: The account id of the account to check balances for.
    :param expected_balances: The expected balances.
    :return: The delta between expected and actual balances.
    """
    balance_dict = create_balance_dict(get_live_balances(account_id))
    return compare_balances_inner(expected_balances, balance_dict)


def compare_live_balances(
    account_id: str,
    expected_balances: AccountBalances,
) -> tuple[
    dict[BalanceDimensions, dict[str, Decimal]], dict[BalanceDimensions, dict[str, Decimal]]
]:
    """
    Compare the actual live balances to specified expected_balances. Any dimensions not included
    in expected_balances are ignored. Only net values are compared, differences in credit and debit
    values are not considered. If there's a mismatch in net values, an entry is added to the
    dictionary in the following format:
    {
       BalanceDimensions: {
           'expected': Decimal(expected net)
           'actual': Decimal(actual net)
        }
    }

    :param account_id: The account id of the account to check balances for.
    :param expected_balances: The expected balances.
    :param view: The balance view to compare against, defaults to BalanceTimeView.VALUE.
    :return: A tuple where the first value is the delta between expected and actual value
        balances and the second value is the delta between the expect and actual booking balances.
    """
    value_balance: list[dict[str, str]] = list_all(
        list_api_call=list_balances_live,
        request=ListBalancesLiveRequest(
            account_id=account_id,
            view=BalanceTimeView.VALUE,
            page_size=10,
        ),
        element_retriever=lambda r: [balance.model_dump() for balance in r.balances],
    )
    value_balance_dict = create_balance_dict(value_balance)

    booking_balance: list[dict[str, str]] = list_all(
        list_api_call=list_balances_live,
        request=ListBalancesLiveRequest(
            account_id=account_id,
            view=BalanceTimeView.BOOKING,
            page_size=10,
        ),
        element_retriever=lambda r: [balance.model_dump() for balance in r.balances],
    )

    booking_balance_dict = create_balance_dict(booking_balance)
    return (
        compare_balances_inner(expected_balances.value_balances, value_balance_dict),
        compare_balances_inner(expected_balances.booking_balances, booking_balance_dict),
    )


def compare_end_balances(
    account_id: str,
    expected_balances: list[tuple[BalanceDimensions, str]],
    view: BalanceTimeView = BalanceTimeView.VALUE,
    snapshot_timestamp: datetime | None = None,
) -> dict[BalanceDimensions, dict[str, Decimal]]:
    """
    Compare the actual end balances to specified expected_balances. Any dimensions not included
    in expected_balances are ignored. Only net values are compared, differences in credit and debit
    values are not considered. If there's a mismatch in net values, an entry is added to the
    dictionary in the following format:
    {
       BalanceDimensions: {
           'expected': Decimal(expected net)
           'actual': Decimal(actual net)
        }
    }

    :param account_id: The account ID of the account to check balances for.
    :param expected_balances: The expected balances.
    :param view: The balance view to compare against, defaults to BalanceTimeView.VALUE.
    :param snapshot_timestamp: Optional time to only include postings with an insertion_timestamp
        earlier than the provided snapshot_timestamp, defaults to None.
    :return: A tuple where the first value is the delta between expected and actual value
        balances and the second value is the delta between the expect and actual booking balances.
    """
    balances: list[dict[str, str]] = list_all(
        list_api_call=list_balances_end,
        request=ListBalancesEndRequest(
            account_id=account_id,
            snapshot_timestamp=snapshot_timestamp,
            view=view,
            page_size=10,
        ),
        element_retriever=lambda r: [balance.model_dump() for balance in r.balances],
    )

    balance_dict = create_balance_dict(balances)
    return compare_balances_inner(expected_balances, balance_dict)


def get_balances_dict(
    account_id: str,
    from_value_time: datetime | None = None,
    to_value_time: datetime | None = None,
    exclude_starting_balance: bool = False,
    live: bool = True,
) -> defaultdict[BalanceDimensions, Balance]:
    """
    Retrieves balances from Core API and transforms into a balance dictionary.

    :param account_id: The account ID to retrieve balances for.
    :param from_value_time: Optional value time to retrieve from. Ignored if live=True.
    :param to_value_time: Optional value time to retrieve up until. Ignored if live=True.
    :param exclude_starting_balance: If True the balances before from_value_time are excluded.
        Ignored if live=True.
    :param live: If true, Live balances will be fetched. If false, balances will be fetched
        between the from_value_time and to_value_time timeranges.
    :return: Contract-like balance dictionary mapping dimensions to balances. When fetching
        balances by timerange, only the latest balance will be returned for a given coordinate.
    """

    return create_balance_dict(
        get_live_balances(account_id)
        if live
        else get_timerange_balances(account_id, from_value_time, to_value_time)
    )


def get_balances_v2_dict(
    account_id: str,
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    snapshot_timestamp: datetime | None = None,
    addresses: list[str] | None = None,
    view: BalanceTimeView = BalanceTimeView.VALUE,
    live: bool = True,
) -> defaultdict[BalanceDimensions, Balance]:
    """
    Retrieves balances from Core API and transforms into a balance dictionary.

    :param account_id: The account to retrieve balances for.
    :param start_timestamp: Optional time to retrieve from. Ignored if live=True and required
        if live=False, defaults to None.
    :param end_timestamp: Optional time to retrieve up until. Ignored if live=True, defaults to
        None.
    :param snapshot_timestamp: Optional time that includes postings with an insertion_timestamp
        earlier than (or equal to) this time, and exclude balance changes from any postings with an
        insertion_timestamp later than this time. Ignored if live=True, defaults to None.
    :param addresses: Optional address to fetch balances for, defaults to None.
    :param view: Optional view to fetch balances for, defaults to BalanceTimeView.VALUE.
    :param live: Set to True if for live balances only, or False to also get historical balances,
        defaults to True.
    :raises Exception: If start_timestamp is not provided when live=False.
    :return: A dictionary mapping balance dimensions to balances.
    """
    if live:
        balances: list[dict[str, str]] = list_all(
            list_api_call=list_balances_live,
            request=ListBalancesLiveRequest(
                account_id=account_id,
                addresses=addresses,
                view=view,
                page_size=10,
            ),
            element_retriever=lambda r: [balance.model_dump() for balance in r.balances],
        )

        return create_balance_dict(balances)

    if start_timestamp is None:
        raise Exception("must provide start_timestamp when live=False")

    balances = list_all(
        list_api_call=list_balances_series,
        request=ListBalancesSeriesRequest(
            account_id=account_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            snapshot_timestamp=snapshot_timestamp,
            addresses=addresses,
            view=view,
            page_size=10,
        ),
        element_retriever=lambda r: [balance.model_dump() for balance in r.balances],
    )
    return create_balance_dict(balances)


def standardise_balance_value_time_format(timestamp: str) -> datetime:
    """
    Removes milliseconds from datetime string to a datetime string of exactly length 20
    and returns this as a datetime object.
    e.g 1990-01-01T00:00:00.12345Z becomes 1990-01-01T00:00:00Z which is then converted
    into a datetime object.

    :param timestamp: Datetime to be converted, defaults to '1970-01-01T00:00:00Z'.
    :return: Timestamp as a datetime object.
    """
    if timestamp:
        return datetime.strptime(timestamp[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ")
    return datetime.strptime("1970-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")


def wait_for_live_net_balances(
    expected_balances: NetBalances,
    description: str = "",
    back_off_factor: float = 1.5,
) -> None:
    """
    Waits until actual live balances match the expected NetBalance objects.
    This helper can be used to assert on expected Account-level and Sub-Account-level live balances.

    :param expected_balances: The NetBalances expected to be matched against.
    :param description: The description of the expected outcome.
    :param back_off_factor: Multiplication factor for the sleep time between retries.
    :return: None.
    """
    if not endtoend.testhandle.use_kafka:
        wait_for_net_balances_by_ids(
            expected_balances,
        )
    else:
        endtoend.helper.retry_call(
            func=compare_net_balances,
            f_args=[expected_balances],
            expected_result={},
            back_off=back_off_factor,
            failure_message=f'Unexpected balances at stage "{description}"',
        )


@kafka_only_helper
def wait_for_net_balances_by_ids(
    expected_balances: NetBalances,
    matched_message_timeout: int = 30,
    inter_message_timeout: int = 30,
) -> None:
    """
    Listens to the balance update events Kafka topic for the expected balances.

    Waits for all Account IDs in the expected balances to appear in the on the balance.event topic.
    For each Account ID validates the expected value_balances and expected booking_balances are
    present, returning an error message if not.

    :param expected_balances: The expected value and booking live balances.
    :param matched_message_timeout: The maximum time to wait between receiving matched messages from
    the consumer
    :param inter_message_timeout: The maximum time to wait between receiving any messages from
    the consumer
    """
    consumer = endtoend.testhandle.kafka_consumers[ACCOUNT_BALANCE_V2_EVENTS_TOPIC]

    merged_net_balances: dict[str, list[NetBalance]] = defaultdict(list)

    for net_balance in (
        expected_balances.value_net_balances + expected_balances.booking_net_balances
    ):
        merged_net_balances[net_balance.account_id].append(net_balance)

    all_mismatches: dict[str, NetBalanceMismatches] = {}

    def matcher(event_msg: dict[str, Any], unique_message_ids_internal: list[str]):
        event_account_id = event_msg["account_id"]
        event_request_id = event_msg["event_id"]

        if event_account_id in unique_message_ids_internal:
            expected_balances_for_account = get_net_balances_for_account(
                expected_balances, event_account_id
            )

            value_balances: list[dict] = event_msg.get("value_balances", [])
            booking_balances: list[dict] = event_msg.get("booking_balances", [])

            actual_value_net_balances = [dict_to_net_balance(b) for b in value_balances]
            actual_booking_net_balances = [dict_to_net_balance(b) for b in booking_balances]

            actual_balances_for_account = NetBalances(
                value_net_balances=actual_value_net_balances,
                booking_net_balances=actual_booking_net_balances,
            )

            mismatches = get_net_balance_mismatches(
                expected_balances_for_account, actual_balances_for_account
            )
            if mismatches:
                all_mismatches[event_account_id] = mismatches[event_account_id]

            if not mismatches:
                return event_account_id, event_request_id, True
            return "", event_request_id, True

        else:
            return "", event_request_id, False

    failed_account_ids = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids=merged_net_balances,
        matched_message_timeout=matched_message_timeout,
        inter_message_timeout=inter_message_timeout,
    )

    if len(failed_account_ids) > 0:
        transformed_outcome = "Failed to retrieve all expected balance updates for account ids\n"
        for account_id in failed_account_ids.keys():
            transformed_outcome += f"\n{account_id}:\n"
            if account_id in all_mismatches:
                mismatch_info = all_mismatches[account_id]
                if mismatch_info.expected_value_balances:
                    transformed_outcome += (
                        f"Value Balances Mismatches:\n"
                        f"Expected: {mismatch_info.expected_value_balances}\n"
                        f"Actual: {mismatch_info.actual_value_balances}\n"
                    )
                if mismatch_info.expected_booking_balances:
                    transformed_outcome += (
                        f"Booking Balances Mismatches:\n"
                        f"Expected: {mismatch_info.expected_booking_balances}\n"
                        f"Actual: {mismatch_info.actual_booking_balances}\n"
                    )
            else:
                transformed_outcome += "No balance events received for this account.\n"
        raise Exception(transformed_outcome)


def get_net_balances(
    account_id: str, view: BalanceTimeView, page_size: int = 10
) -> list[NetBalance]:
    """
    Calls the GET /v2/balances endpoint and returns the NetBalances.

    :param account_id: Account ID for the balances to fetch.
    :param view: The type of balances to fetch, either VALUE or BOOKING.
    :param page_size: The number of balances to return per request.
    :return: The NetBalances of the response.
    """
    response: list[LiveBalanceV2] = list_all(
        list_api_call=list_balances_live,
        request=ListBalancesLiveRequest(account_id=account_id, view=view, page_size=page_size),
        element_retriever=lambda r: r.balances,
    )
    net_balances: list[NetBalance] = []
    for live_balance in response:
        net_balances.append(
            NetBalance(
                amount=live_balance.amount,
                account_id=live_balance.account_id,
                account_address=live_balance.account_address,
                phase=live_balance.phase,
                asset=live_balance.asset,
                denomination=live_balance.denomination,
                sub_account_id=live_balance.sub_account_id,
            ),
        )
    return net_balances


def compare_net_balances(
    expected_balances: NetBalances,
) -> dict[str, NetBalanceMismatches]:
    """
    Given expected balances, calls the synchronous core api endpoint for each Account ID,
    returning a dictionary mapping account IDs to NetBalanceMismatches objects
    for accounts that have mismatches.

    :param expected_balances: The expected balances to be returned from the request.
    :return: dict of account ID to NetBalanceMismatches objects.
    """

    account_ids = get_account_ids_from_net_balances(expected_balances)
    actual_balances = NetBalances(value_net_balances=[], booking_net_balances=[])

    for account_id in account_ids:
        actual_balances.value_net_balances.extend(
            get_net_balances(account_id, BalanceTimeView.VALUE)
        )
        actual_balances.booking_net_balances.extend(
            get_net_balances(account_id, BalanceTimeView.BOOKING)
        )

    return get_net_balance_mismatches(expected_balances, actual_balances)
