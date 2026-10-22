# flake8: noqa

# contracts api
from contracts_api import ExpectedParameter, StringConstraint

denomination = "denomination"
constraint = StringConstraint(min_length=1)
triggers_pre_parameter_change_hook = True
optional = False
denomination_parameter = ExpectedParameter(
    id=denomination,
    constraint=constraint,
    triggers_pre_parameter_change_hook=triggers_pre_parameter_change_hook,
    optional=optional,
)
