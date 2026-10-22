# standard libs
from datetime import datetime
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Phase,
    Release,
    Settlement,
    Transfer,
)

PostingInstruction = (
    AuthorisationAdjustment
    | CustomInstruction
    | InboundAuthorisation
    | InboundHardSettlement
    | OutboundAuthorisation
    | OutboundHardSettlement
    | Release
    | Settlement
    | Transfer
)

PostingInstructionTypeList = list[PostingInstruction]


ACCOUNT_ID = "default_account"
CLIENT_TRANSACTION_ID = "MOCK_POSTING"
DEFAULT_DATETIME = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))
DEFAULT_DENOMINATION = "GBP"
DEFAULT_HOOK_EXECUTION_ID = "MOCK_HOOK"
DEFAULT_INTERNAL_ACCOUNT = "1"
DEFAULT_PHASE = Phase.COMMITTED
POSTING_CLIENT_ID = "client_id"
