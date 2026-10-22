from datetime import datetime
from unittest import mock, TestCase

from .. import sub_accounts_lib




class PublicV400VaultFunctionsTestCase(TestCase):
    def setUp(self, *args, **kwargs):
        self.vault = mock.create_autospec(sub_accounts_lib.VaultFunctionsABC)

    def test_cannot_use_unknown_vault_method(self):
        def foo(vault):
            vault.some_unknown_method()

        with self.assertRaises(AttributeError):
            foo(self.vault)

    def test_cannot_mock_return_value_on_unknown_method(self):
        with self.assertRaises(AttributeError):
            self.vault.some_unknown_method.return_value = 1

    def test_mock_vault_raises_error_on_unexpected_args(self):
        def foo(vault):
            vault.get_sub_account_activation_datetime(unexpected_arg="foo")

        with self.assertRaises(TypeError) as e:
            foo(self.vault)

        self.assertEqual(
            "got an unexpected keyword argument 'unexpected_arg'",
            e.exception.args[0],
        )

    def test_get_sub_account_activation_datetime(self):
        def foo(vault):
            return vault.get_sub_account_activation_datetime()

        sub_account_activation_datetime = datetime(2025, 7, 11)

        self.vault.get_sub_account_activation_datetime.return_value = (
            sub_account_activation_datetime
        )
        self.assertEqual(sub_account_activation_datetime, foo(self.vault))


class PublicV400VaultFunctionsSpecTestCase(TestCase):
    def test_spec_public_methods_are_sorted_alphabetically(self):
        lib_api_functions = list(
            sub_accounts_lib.VaultFunctionsABC._spec().public_methods.keys()  # noqa: SLF001
        )
        self.assertEqual(lib_api_functions, sorted(lib_api_functions))

    def test_spec_public_methods(self):
        lib_api_functions = list(
            sub_accounts_lib.VaultFunctionsABC._spec().public_methods.keys()  # noqa: SLF001
        )
        self.assertIn("get_sub_account_activation_datetime", lib_api_functions)

    
