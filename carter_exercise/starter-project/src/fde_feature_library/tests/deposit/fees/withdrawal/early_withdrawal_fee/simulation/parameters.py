# standard libs
from decimal import Decimal

from inception_sdk.test_framework.common.utils import strip_clu_notation

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalConstraint,
    DecimalConstraintValue,
    DecimalParameterValue,
    ParameterResource,
    ParameterValue,
    StringConstraint,
    StringConstraintValue,
    StringParameterValue,
)

import tests.deposit.fees.withdrawal.early_withdrawal_fee.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

# library

# Accounts V2 endpoint requires parameters to be uploaded using the ParameterValue syntax,
# including instance parameters
default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(5)
    ),
    smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id: (
        DecimalParameterValue(decimal_value=Decimal("0.1"))
    ),
    smart_contract.early_withdrawal_fees.MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
        decimal_value=Decimal(1)
    ),
    smart_contract.early_withdrawal_fees.FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
        decimal_value=Decimal(0)
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
            id=smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id,
            constraint=DecimalConstraint(decimal_constraint=DecimalConstraintValue()),
        ),
        ParameterResource(
            id=smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id,
            constraint=DecimalConstraint(
                decimal_constraint=DecimalConstraintValue(
                    min_value=Decimal(0), max_value=Decimal(1)
                )
            ),
        ),
        ParameterResource(
            id=smart_contract.early_withdrawal_fees.MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id,
            constraint=DecimalConstraint(
                decimal_constraint=DecimalConstraintValue(
                    min_value=Decimal(0), max_value=Decimal(1)
                )
            ),
        ),
        ParameterResource(
            id=smart_contract.early_withdrawal_fees.FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id,
            constraint=DecimalConstraint(
                decimal_constraint=DecimalConstraintValue(
                    min_value=Decimal(0), max_value=Decimal(1)
                )
            ),
        ),
    ]
]
