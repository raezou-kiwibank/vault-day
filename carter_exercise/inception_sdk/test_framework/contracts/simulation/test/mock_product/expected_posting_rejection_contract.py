# contracts api
from contracts_api import PrePostingHookArguments, PrePostingHookResult, Rejection, RejectionReason

# Contract Metadata
api = "4.0.0"
version = "0.0.1"
supported_denominations = ["GBP"]


def pre_posting_hook(vault, hook_arguments: PrePostingHookArguments) -> PrePostingHookResult | None:
    if any(
        posting.denomination not in supported_denominations
        for posting in hook_arguments.posting_instructions  # type: ignore [attr-defined]
    ):
        return PrePostingHookResult(
            rejection=Rejection(
                message="Transactions must be in GBP only.",
                reason_code=RejectionReason.WRONG_DENOMINATION,
            )
        )
    return None
