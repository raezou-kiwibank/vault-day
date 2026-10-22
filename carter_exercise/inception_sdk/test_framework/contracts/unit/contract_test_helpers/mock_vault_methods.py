# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from collections import defaultdict
from unittest.mock import Mock

# contracts api
from contracts_api import (
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    BalancesObservation,
    BalanceTimeseries,
    ClientTransaction,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.contract_test_helpers.constants import (
    PostingInstructionTypeList,
)


def apply_mock_methods(
    mock_vault: Mock,
    balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
    balances_interval_fetchers_mapping: (
        dict[str, defaultdict[BalanceCoordinate, BalanceTimeseries]] | None
    ) = None,
    balances_discrete_interval_fetchers_mapping: (
        dict[str, defaultdict[BalanceCoordinate, BalanceDiscreteTimeseries]] | None
    ) = None,
    client_transactions_mapping: dict[str, dict[str, ClientTransaction]] | None = None,
    postings_interval_mapping: dict[str, PostingInstructionTypeList] | None = None,
) -> None:
    """
    Apply common balance and posting mock getters to a mock Vault or Sub-Account Vault object.

    :param mock_vault: The mock Vault or Sub-Account Vault object to apply the mocked methods to.
    :param balances_observation_fetchers_mapping: Mapping of fetcher_id to BalancesObservation.
        Mocks `get_balances_observation(fetcher_id=...)`
    :param balances_interval_fetchers_mapping: Mapping of fetcher_id to balance timeseries.
        Mocks `get_balances_timeseries(fetcher_id=...)`
    :param balances_discrete_interval_fetchers_mapping: Mapping of fetcher_id to balance discrete
        timeseries. Mocks `get_balances_discrete_timeseries(fetcher_id=...)`
    :param client_transactions_mapping: Mapping of fetcher_id to client transactions.
        Mocks `get_client_transactions(fetcher_id=...)`
    :param postings_interval_mapping: Mapping of fetcher_id to list of posting instructions.
        Mocks `get_posting_instructions(fetcher_id=...)`

    :raises KeyError: If the mocked balance methods (e.g., `get_balances_observation`)
        are called with a fetcher_id that was not provided in the initial mappings.
    :raises ValueError: If mocked client transaction or posting instruction methods are called
        without a fetcher_id, or with a fetcher_id that was not provided in the initial mappings.
    """
    balances_observation_fetchers_mapping = balances_observation_fetchers_mapping or {}
    balances_interval_fetchers_mapping = balances_interval_fetchers_mapping or {}
    balances_discrete_interval_fetchers_mapping = balances_discrete_interval_fetchers_mapping or {}
    client_transactions_mapping = client_transactions_mapping or {}
    postings_interval_mapping = postings_interval_mapping or {}

    def mock_get_balances_discrete_timeseries(
        fetcher_id: str,
    ) -> defaultdict[BalanceCoordinate, BalanceDiscreteTimeseries]:
        if fetcher_id in balances_discrete_interval_fetchers_mapping:
            return balances_discrete_interval_fetchers_mapping[fetcher_id]
        raise KeyError(f"Missing balance discrete interval in test setup for {fetcher_id=}")

    def mock_get_balances_observation(fetcher_id: str) -> BalancesObservation:
        if fetcher_id in balances_observation_fetchers_mapping:
            return balances_observation_fetchers_mapping[fetcher_id]
        raise KeyError(f"Missing balance observation in test setup for {fetcher_id=}")

    def mock_get_balance_timeseries(
        fetcher_id: str | None = None,
    ) -> defaultdict[BalanceCoordinate, BalanceTimeseries]:
        if fetcher_id:
            if fetcher_id in balances_interval_fetchers_mapping:
                return balances_interval_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing balance interval in test setup for {fetcher_id=}")
        else:
            raise ValueError("You must provide a fetcher ID")

    def mock_get_client_transaction(fetcher_id: str | None = None):
        if fetcher_id:
            if fetcher_id in client_transactions_mapping:
                return client_transactions_mapping[fetcher_id]

            raise ValueError(f"Missing client transactions in test setup for {fetcher_id=}")
        else:
            raise ValueError("You must provide a fetcher ID")

    def mock_get_posting_instructions(
        fetcher_id: str | None = None,
    ) -> PostingInstructionTypeList:
        if fetcher_id:
            if fetcher_id in postings_interval_mapping:
                return postings_interval_mapping[fetcher_id]

            raise ValueError(f"Missing posting interval in test setup for {fetcher_id=}")
        else:
            raise ValueError("You must provide a fetcher ID")

    mock_vault.get_balances_discrete_timeseries.side_effect = mock_get_balances_discrete_timeseries
    mock_vault.get_balances_observation.side_effect = mock_get_balances_observation
    mock_vault.get_balances_timeseries.side_effect = mock_get_balance_timeseries
    mock_vault.get_client_transactions.side_effect = mock_get_client_transaction
    mock_vault.get_posting_instructions.side_effect = mock_get_posting_instructions
