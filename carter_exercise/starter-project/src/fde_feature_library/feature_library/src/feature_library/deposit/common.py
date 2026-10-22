# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Common parameters for withdrawal limits features."""

__smart_contract_feature__ = True

from contracts_api import ExpectedParameter

ACCOUNT_TIER_PARAM_ID = "&{account_tier}"
ACCOUNT_TIER_PARAM = ExpectedParameter(
    id=ACCOUNT_TIER_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
