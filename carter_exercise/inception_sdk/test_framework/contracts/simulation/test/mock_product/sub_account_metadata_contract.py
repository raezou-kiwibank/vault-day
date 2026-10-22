# contracts api
from contracts_api import DEFAULT_ADDRESS, SubAccountAddressDetails, SubAccountType

api = "4.0.0"
version = "0.0.1"

sub_account_types = [
    SubAccountType(
        name="SAVE",
        address_details=[
            SubAccountAddressDetails(
                address=DEFAULT_ADDRESS,
                description="The default address for the funds.",
            ),
        ],
    ),
    SubAccountType(
        name="PERMITTED_ADDRESS_SUB_ACCOUNT",
        address_details=[
            SubAccountAddressDetails(
                address=DEFAULT_ADDRESS,
                description="The default address for the funds.",
            ),
            SubAccountAddressDetails(
                address="PERMITTED_ADDRESS",
                description="Permitted address",
            ),
        ],
    ),
]
