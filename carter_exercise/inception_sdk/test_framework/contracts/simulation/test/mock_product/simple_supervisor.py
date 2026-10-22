# contracts api
from contracts_api import SmartContractDescriptor

api = "4.0.0"
version = "1.0.0"

supervised_smart_contracts = [
    SmartContractDescriptor(
        alias="supervisee", smart_contract_version_id="&{supervisee_version_id}"
    )
]
