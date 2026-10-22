# standard libs
from decimal import Decimal
from json import dumps

from inception_sdk.test_framework.common.utils import strip_clu_notation

# inception sdk
from inception_sdk.vault.core_api import (
    AccountConstraint,
    AccountConstraintValue,
    AccountIdParameterValue,
    DecimalConstraint,
    DecimalConstraintValue,
    DecimalParameterValue,
    EnumerationConstraint,
    EnumerationConstraintValue,
    EnumerationParameterValue,
    ParameterResource,
    ParameterValue,
    StringConstraint,
    StringConstraintValue,
    StringParameterValue,
)

import tests.deposit.fees.inactivity.simulation.accounts as accounts
import tests.deposit.fees.inactivity.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(10)
    ),
    smart_contract.inactivity_fee.INACTIVITY_FLAGS_PARAM.id: StringParameterValue(
        string_value=dumps(["ACCOUNT_INACTIVE"])
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_DAY_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(1)
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="00:00:01"
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM.id: EnumerationParameterValue(  # noqa: E501
        enumeration_value="False"
    ),
}

expected_param_resources: list[ParameterResource] = [
    ParameterResource(id=strip_clu_notation(p.id), constraint=p.constraint)
    for p in [
        ParameterResource(
            id=smart_contract.denomination_module.DENOMINATION_PARAM.id,
            constraint=StringConstraint(string_constraint=StringConstraintValue()),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FEE_PARAM.id,
            constraint=DecimalConstraint(
                decimal_constraint=DecimalConstraintValue(min_value=Decimal(0))
            ),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FLAGS_PARAM.id,
            constraint=StringConstraint(string_constraint=StringConstraintValue()),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id,
            constraint=AccountConstraint(account_constraint=AccountConstraintValue()),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM.id,
            constraint=EnumerationConstraint(
                enumeration_constraint=EnumerationConstraintValue(
                    permitted_values=["True", "False"]
                )
            ),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_DAY_PARAM.id,
            constraint=DecimalConstraint(decimal_constraint=DecimalConstraintValue()),
        ),
        ParameterResource(
            id=smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_TIME_PARAM.id,
            constraint=StringConstraint(string_constraint=StringConstraintValue()),
        ),
    ]
]
