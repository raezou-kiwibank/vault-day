from functools import lru_cache
import string
from typing import List

from .balances import SubAccountAddressDetails


from ...common.docs import _common_docs_path, _smart_contracts_docs_path
from .....utils import exceptions, symbols, types_utils

ALPHANUMERIC_CHARSET = set(string.ascii_letters + string.digits)
# For the name of a SubAccountType, strings are restricted to only contain alphanumeric characters,
# underscores and hyphens.
SUB_ACCOUNT_TYPE_NAME_ALLOWED_CHARSET = ALPHANUMERIC_CHARSET | {"_", "-"}


def validate_sub_account_type_name(error_prefix: str, name: str):
    name_set = set(name)
    if not name_set.issubset(SUB_ACCOUNT_TYPE_NAME_ALLOWED_CHARSET):
        raise exceptions.InvalidSmartContractError(
            f"'{error_prefix}' may only contain alphanumeric characters, hyphens and "
            f"underscores. Instead got: '{name}', which contains the invalid characters: "
            f"{name_set.difference(SUB_ACCOUNT_TYPE_NAME_ALLOWED_CHARSET)}",
        )
    if not bool(name_set & ALPHANUMERIC_CHARSET):
        raise exceptions.InvalidSmartContractError(
            f"'{error_prefix}' must contain at least one alphanumeric character. Instead "
            f"got: '{name}'."
        )


class SubAccountType(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        name: str,
        address_details: List[SubAccountAddressDetails],
    ):
        self.name = name
        self.address_details = address_details
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            item=self.name,
            expected=str,
            check_empty=True,
            hint="str",
            prefix=f"{self.__class__.__name__}.name",
        )
        validate_sub_account_type_name("SubAccountType.name", self.name)

        iterator = types_utils.get_iterator(
            items=self.address_details,
            hint="SubAccountAddressDetails",
            name="SubAccountType.address_details",
            check_empty=True,
        )

        seen = set()
        for i, ad in enumerate(iterator):
            types_utils.validate_type(
                item=ad,
                expected=SubAccountAddressDetails,
                hint="SubAccountAddressDetails",
                prefix=f"{self.__class__.__name__}.address_details[{i}]",
            )

            if ad.address in seen:
                message = (
                    "SubAccountAddressDetail objects in the sub_account_types.address_details List "
                    "in the Smart Contract Metadata must have unique addresses, "
                    f"duplicate address found: {str(ad.address)}"
                )
                raise exceptions.InvalidSmartContractError(message)

            seen.add(ad.address)

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=cls.__name__,
            docstring=f"""
                Describes a Sub-Account type and its attributes. Sub-Account types are defined in
                the [sub_account_types]({_smart_contracts_docs_path}metadata#sub_account_types)
                field in the Contract's metadata.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring=f"Constructs a new {cls.__name__} object.",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="name",
                type="str",
                docstring="""
                    The name of the Sub-Account Type. Must be an alphanumeric string that can also
                    contain hyphens and underscores. Must be unique across all Sub-Account Types
                    declared in a Smart Contract.
                """,
            ),
            types_utils.ValueSpec(
                name="address_details",
                type="List[SubAccountAddressDetails]",
                docstring=f"""
                    A list of
                    [SubAccountAddressDetails]({_common_docs_path}classes/#SubAccountAddressDetails)
                    that specifies all the valid balance addresses for Sub-Accounts of this type.
                    It must not be empty, and `SubAccountAddressDetails.address` must be
                    unique across all `SubAccountAddressDetails` in the list.
                """,
            ),
        ]



