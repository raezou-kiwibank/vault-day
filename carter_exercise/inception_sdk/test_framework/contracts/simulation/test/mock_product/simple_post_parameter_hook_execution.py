from contracts_api import (
	ExpectedParameter,
	PostParameterChangeHookArguments,
	PostParameterChangeHookResult,
	AccountNotificationDirective,
)

from json import dumps

api = "4.0.0"
version = "8.0.0"

expected_parameters = [
	ExpectedParameter(
		id="expected-parameter-id",
		optional=True,
		triggers_pre_parameter_change_hook=False,
		triggers_post_parameter_change_hook=True,
	)
]


def post_parameter_change_hook(
	vault, hook_arguments: PostParameterChangeHookArguments
) -> PostParameterChangeHookResult | None:
	return None