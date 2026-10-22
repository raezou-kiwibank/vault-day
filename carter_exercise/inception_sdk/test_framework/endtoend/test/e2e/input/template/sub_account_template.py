# contracts api
from contracts_api import DEFAULT_ADDRESS, SubAccountAddressDetails, SubAccountType, Tside

# metadata
api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY

sub_account_types = [
    SubAccountType(
        name="SPEND",
        address_details=[
            SubAccountAddressDetails(
                address=DEFAULT_ADDRESS,
                description="Customer accessible funds",
            ),
            SubAccountAddressDetails(
                address="FEES",
                description="Tracks fees charged against this pot (eg, ATM fees)",
            ),
            SubAccountAddressDetails(
                address="SHOPPING",
                description="Tracks funds for shopping expenses",
            ),
            SubAccountAddressDetails(
                address="DINING",
                description="Tracks funds for dining expenses",
            ),
        ],
    ),
    SubAccountType(
        name="SAVE",
        address_details=[
            SubAccountAddressDetails(
                address=DEFAULT_ADDRESS,
                description="Customer accessible funds",
            ),
            SubAccountAddressDetails(
                address="ACCRUED",
                description="Interest accrued during the current period",
            ),
            SubAccountAddressDetails(
                address="APPLIED",
                description="Tracks aggregate interest that has been applied",
            ),
        ],
    ),
]
