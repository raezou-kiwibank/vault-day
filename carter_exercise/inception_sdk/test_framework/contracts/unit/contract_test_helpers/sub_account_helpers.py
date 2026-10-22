# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from collections import defaultdict
from datetime import datetime
from unittest.mock import Mock

# contracts api
# It is very important to use contracts_api here and not any of the extension types. This is
# because the types here will be passed into the contract and must therefore be exactly as per the
# API (see documentation/testing/unit.md for more details)
from contracts_api import (
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    BalancesObservation,
    BalanceTimeseries,
    ClientTransaction,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.contract_test_helpers.constants import (
    DEFAULT_DATETIME,
    PostingInstructionTypeList,
)
from inception_sdk.test_framework.contracts.unit.contract_test_helpers.mock_vault_methods import (
    apply_mock_methods,
)
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SubAccountVault,
)


class SubAccountsDict(dict):
    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        return None

    def __setitem__(self, key, value):
        raise TypeError(
            "Direct assignment to sub_accounts dictionary is not allowed. "
            "Use create_sub_account_mock() instead."
        )

    def _add_mock(self, key, value):
        # Internal bypass for create_sub_account_mock
        super().__setitem__(key, value)


def create_sub_account_mock(
    self,
    *,
    mock_parent_account: Mock,
    sub_account_id: str,
    sub_account_type: str,
    activation_datetime: datetime = DEFAULT_DATETIME,
    balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
    balances_interval_fetchers_mapping: (
        dict[str, defaultdict[BalanceCoordinate, BalanceTimeseries]] | None
    ) = None,
    balances_discrete_interval_fetchers_mapping: (
        dict[str, defaultdict[BalanceCoordinate, BalanceDiscreteTimeseries]] | None
    ) = None,
    client_transactions_mapping: dict[str, dict[str, ClientTransaction]] | None = None,
    postings_interval_mapping: dict[str, PostingInstructionTypeList] | None = None,
    invoked: bool | None = None,
    existing_mock: Mock | None = None,
) -> Mock | SubAccountVault:
    """
    Create mock Sub-Account Vault object for the test.
    Adds Sub-Account to Account's vault.sub_account and vault.get_sub_account().

    mock_parent_account, sub_account_id, and sub_account_type must be provided.
    activation_datetime will be given default value if not provided.
    All other parameters are optional.

    :param mock_parent_account: Mocked instance of parent Account of Sub-Account mock.
    :param sub_account_id: Sub-Account ID
    :param sub_account_type: Sub-Account Type
    :param activation_datetime: Sub-Account activation datetime. Used to mock
    `savo.get_sub_account_activation_datetime()`
    :param balances_observation_fetchers_mapping: mapping of fetcher_id to balance observation.
    Used to mock `savo.get_balances_observation()`
    :param balances_interval_fetchers_mapping: mapping of fetcher_id to balance timeseries.
    Used to mock `savo.get_balances_timeseries()`
    :param balances_discrete_interval_fetchers_mapping: mapping of fetcher_id to balance
    discrete timeseries. Used to mock `savo.get_balances_discrete_timeseries()`
    :param client_transactions_mapping: mapping of postings fetcher id to Client transactions
    including proposed. Used to mock `savo.get_client_transactions`.
    :param postings_interval_mapping: mapping of postings fetcher_id to posting instructions
    Used to mock `savo.get_posting_instructions()`
    :param invoked: Sets whether the Sub-Account is considered invoked or not
    Used to mock `parent_account.get_sub_accounts()` with invoked
    :param existing_mock: A mock Sub-Account Vault object to re-use instead of
    creating a new mock

    :raises KeyError: when the mocked balance methods (e.g. `get_balances_observation`)
    are used to access data for fetcher_id values that weren't provided on initialisation.
    :raises ValueError: when the mocked client transaction or posting instruction methods
    are used to access data for fetcher_id values that weren't provided on initialisation.

    :return: a mock Sub-Account Vault object
    """
    # Identify mocks more easily
    mock_savo = existing_mock or Mock(name=sub_account_id)

    # mock attributes of a Sub-Account Vault object
    mock_savo.sub_account_id = sub_account_id
    mock_savo.sub_account_type = sub_account_type

    # Sub-Account Vault object specific methods
    mock_savo.get_sub_account_activation_datetime.return_value = activation_datetime

    # Common Account and Sub-Account methods
    apply_mock_methods(
        mock_vault=mock_savo,
        balances_observation_fetchers_mapping=balances_observation_fetchers_mapping,
        balances_interval_fetchers_mapping=balances_interval_fetchers_mapping,
        balances_discrete_interval_fetchers_mapping=balances_discrete_interval_fetchers_mapping,
        client_transactions_mapping=client_transactions_mapping,
        postings_interval_mapping=postings_interval_mapping,
    )

    # Attach mapping dictionaries to support get_sub_accounts with fetcher_id
    mock_savo.balances_observation_fetchers_mapping = balances_observation_fetchers_mapping or {}
    mock_savo.balances_interval_fetchers_mapping = balances_interval_fetchers_mapping or {}
    mock_savo.balances_discrete_interval_fetchers_mapping = (
        balances_discrete_interval_fetchers_mapping or {}
    )
    mock_savo.client_transactions_mapping = client_transactions_mapping or {}
    mock_savo.postings_interval_mapping = postings_interval_mapping or {}

    # Set value of invoked to support get_sub_accounts with invoked
    mock_savo.invoked = invoked

    mock_parent_account.sub_accounts._add_mock(mock_savo.sub_account_id, mock_savo)
    return mock_savo


def apply_get_sub_accounts(
    mock_parent_account: Mock,
) -> None:

    def mock_get_sub_accounts(
        sub_account_types: list[str] | None = None,
        fetcher_ids: list[str] | None = None,
        invoked: bool | None = None,
    ) -> list[Mock]:
        """
        mock method for vault.get_sub_accounts()
        mimics the functionality of the method, given the parent Account and Sub-Accounts are mock
        objects

        :param sub_account_types: optional, list of valid Sub-Account types to be returned
        :param fetcher_ids: optional, list of fetcher ids every returned Sub-Account must support
        :param invoked: optional, filters Sub-Accounts based on their invoked value
        Note: Inception SDK does not support a concept of `invoked`,
        so this param is for completeness

        :raises KeyError: when sub_account_types contains a type not present on any of the
        Sub-Account Vault objects
        :raises KeyError: when fetcher_ids contains a fetcher_id not present on any of the
        Sub-Account Vault objects

        :return: list of mock Sub-Account Vault objects
        """
        all_savos = list(mock_parent_account.sub_accounts.values())

        # types and fetcher_ids which are defined on the Sub-Accounts
        configured_sub_account_types: set[str] = set()
        configured_fetchers: set[str] = set()

        filtered_savos = []

        for savo in all_savos:
            savo_type = savo.sub_account_type
            configured_sub_account_types.add(savo_type)

            savo_fetchers: set[str] = set()
            for mapping_attr in [
                "balances_observation_fetchers_mapping",
                "balances_interval_fetchers_mapping",
                "balances_discrete_interval_fetchers_mapping",
                "client_transactions_mapping",
                "postings_interval_mapping",
            ]:
                mapping = getattr(savo, mapping_attr, {})
                if not isinstance(mapping, Mock):
                    savo_fetchers.update(mapping.keys())

            configured_fetchers.update(savo_fetchers)

            # Apply active filters
            if sub_account_types is not None and savo_type not in sub_account_types:
                continue

            if fetcher_ids is not None and not all(fid in savo_fetchers for fid in fetcher_ids):
                continue

            if invoked is not None and savo.invoked != invoked:
                continue

            filtered_savos.append(savo)

        if sub_account_types is not None:
            for savo_type in sub_account_types:
                if savo_type not in configured_sub_account_types:
                    raise KeyError(
                        f"sub_account_type '{savo_type}' is not present on any mock Sub-Account"
                    )

        if fetcher_ids is not None:
            for fid in fetcher_ids:
                if fid not in configured_fetchers:
                    raise KeyError(f"fetcher_id '{fid}' is not present on any mock Sub-Account")

        return sorted(filtered_savos, key=lambda sub_account: sub_account.sub_account_id)

    mock_parent_account.get_sub_accounts.side_effect = mock_get_sub_accounts
