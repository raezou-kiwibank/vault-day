import string
from unittest import TestCase

from ..types import (
    
    SubAccountAddressDetails,
    SubAccountType,
)
from .....utils.exceptions import (
    InvalidSmartContractError,
    StrongTypingError,
)
from .....utils.feature_flags import (
    ACCOUNT_OPENING_WITH_SUB_ACCOUNTS,
    
    skip_if_not_enabled,
)
from .....utils.types_utils import (
    ContractsLanguageDunderMixin,
)

default_address_details = SubAccountAddressDetails(
    address="DEFAULT",
    description="Some desc",
)


class TestSubAccountType(TestCase):
    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance(self):
        sub_account_type = SubAccountType(
            name="SAVE",
            address_details=[default_address_details],
        )

        self.assertEqual("SAVE", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_name_with_hyphens(self):
        sub_account_type = SubAccountType(
            name="sub-account-type",
            address_details=[default_address_details],
        )

        self.assertEqual("sub-account-type", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_name_with_underscores(self):
        sub_account_type = SubAccountType(
            name="sub_account_type",
            address_details=[default_address_details],
        )

        self.assertEqual("sub_account_type", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_name_with_leading_and_trailing_underscore(self):
        sub_account_type = SubAccountType(
            name="_subaccounttype_",
            address_details=[default_address_details],
        )

        self.assertEqual("_subaccounttype_", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_name_with_leading_and_trailing_hyphen(self):
        sub_account_type = SubAccountType(
            name="-subaccounttype-",
            address_details=[default_address_details],
        )

        self.assertEqual("-subaccounttype-", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_numerical_name(self):
        sub_account_type = SubAccountType(
            name="1234",
            address_details=[default_address_details],
        )

        self.assertEqual("1234", sub_account_type.name)
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_create_instance_name_mix_of_allowed_characters(self):
        sub_account_type = SubAccountType(
            name="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
            address_details=[default_address_details],
        )

        self.assertEqual(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
            sub_account_type.name,
        )
        self.assertEqual(1, len(sub_account_type.address_details))
        self.assertEqual(default_address_details, sub_account_type.address_details[0])

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_repr(self):
        sub_account_type = SubAccountType(
            name="SAVE",
            address_details=[default_address_details],
        )
        self.assertTrue(issubclass(SubAccountType, ContractsLanguageDunderMixin))
        self.assertIn("SubAccountType", repr(sub_account_type))

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_equality(self):
        sub_account_1 = SubAccountType(
            name="SAVE",
            address_details=[default_address_details],
        )
        sub_account_2 = SubAccountType(
            name="SAVE",
            address_details=[default_address_details],
        )
        self.assertEqual(sub_account_1, sub_account_2)

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_unequal_name(self):
        sub_account_1 = SubAccountType(
            name="SAVE",
            address_details=[default_address_details],
        )
        sub_account_2 = SubAccountType(
            name="SPEND",
            address_details=[default_address_details],
        )
        self.assertNotEqual(sub_account_1, sub_account_2)

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_unequal_address_details(self):
        sub_account_1 = SubAccountType(
            name="SAVE",
            address_details=[
                SubAccountAddressDetails(
                    address="DEFAULT",
                    description="Some desc",
                )
            ],
        )
        sub_account_2 = SubAccountType(
            name="SPEND",
            address_details=[
                SubAccountAddressDetails(
                    address="DEFAULT",
                    description="Some other desc",
                )
            ],
        )
        self.assertNotEqual(sub_account_1, sub_account_2)

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_with_name_none_raises_error(self):
        with self.assertRaises(StrongTypingError) as ex:
            SubAccountType(name=None, address_details=[default_address_details])
        self.assertEqual("'SubAccountType.name' expected str, got None", str(ex.exception))

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_with_empty_name_raises_error(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="", address_details=[default_address_details])
        self.assertEqual("'SubAccountType.name' must be a non-empty string", str(ex.exception))

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_with_invalid_argument_type_in_name_raises_error(self):
        with self.assertRaises(StrongTypingError) as ex:
            SubAccountType(name=1, address_details=[default_address_details])
        self.assertEqual(
            "'SubAccountType.name' expected str, got '1' of type int",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_with_name_with_invalid_characters_raises_error(self):
        # Check disallowed punctuation except "_" and "-".
        invalid_characters = string.punctuation.replace("_", "").replace("-", "")
        for char in invalid_characters:
            with self.assertRaises(InvalidSmartContractError) as ex:
                SubAccountType(name=char, address_details=[default_address_details])
            self.assertEqual(
                f"'SubAccountType.name' may only contain alphanumeric characters, hyphens and "
                f"underscores. Instead got: '{char}', which contains the invalid characters: {set(char)}",
                str(ex.exception),
            )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_name_with_only_underscore_raises_error(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="_", address_details=[default_address_details])
        self.assertEqual(
            "'SubAccountType.name' must contain at least one alphanumeric character. Instead "
            "got: '_'.",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_name_with_only_hyphen_raises_error(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="-", address_details=[default_address_details])
        self.assertEqual(
            "'SubAccountType.name' must contain at least one alphanumeric character. Instead "
            "got: '-'.",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_name_without_alphanumeric_characters_raises_error(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="-__-", address_details=[default_address_details])
        self.assertEqual(
            "'SubAccountType.name' must contain at least one alphanumeric character. Instead "
            "got: '-__-'.",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_raises_with_no_address_details(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="SAVE", address_details=None)
        self.assertEqual(
            "'SubAccountType.address_details' must be a non empty list, got None", str(ex.exception)
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_raises_with_invalid_argument_type_in_address_details(self):
        with self.assertRaises(StrongTypingError) as ex:
            SubAccountType(name="SAVE", address_details=1)
        self.assertEqual(
            "Expected list of SubAccountAddressDetails objects for 'SubAccountType.address_details'"
            ", got '1'",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_raises_with_list_of_invalid_objects_in_address_details(self):
        with self.assertRaises(StrongTypingError) as ex:
            SubAccountType(name="SAVE", address_details=["some_invalid_objects"])
        self.assertEqual(
            "'SubAccountType.address_details[0]' expected SubAccountAddressDetails, got "
            "'some_invalid_objects' of type str",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_raises_with_empty_address_details(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(name="SAVE", address_details=[])
        self.assertEqual(
            "'SubAccountType.address_details' must be a non empty list, got []",
            str(ex.exception),
        )

    @skip_if_not_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS)
    def test_sub_account_type_raises_with_duplicate_address_in_address_detail_objects(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            SubAccountType(
                name="SAVE",
                address_details=[
                    SubAccountAddressDetails(
                        address="DEFAULT",
                        description="Some desc",
                    ),
                    SubAccountAddressDetails(
                        address="DEFAULT",
                        description="Some desc_2",
                    ),
                ],
            )
        self.assertEqual(
            "SubAccountAddressDetail objects in the sub_account_types.address_details List "
            "in the Smart Contract Metadata must have unique addresses, "
            "duplicate address found: DEFAULT",
            str(ex.exception),
        )



