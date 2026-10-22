# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

# feature_library
from feature_library.common.state_utils import SmartContractState

# contracts api
from contracts_api import BalanceDefaultDict

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault


def initialise_mock_state(
    vault: SmartContractVault | MagicMock | None = None,
    effective_datetime: datetime | None = None,
    parameters: dict[str, datetime | Decimal | str | None] | None = None,
    balances: BalanceDefaultDict | None = None,
) -> SmartContractState:
    from contracts_api import Balance

    return SmartContractState(
        vault=vault or MagicMock(),
        effective_datetime=effective_datetime or MagicMock(),
        parameters=parameters or {},
        balances=balances or BalanceDefaultDict(lambda: Balance(), {}),
        inflight_postings=[],
    )
