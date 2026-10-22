# standard libs
import ast
from unittest import TestCase

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.vault.contracts.utils as utils
from inception_sdk.vault.contracts.test.unit import v3_contract_template, v4_contract_template


class IsModuleCLv4Test(TestCase):
    def test_v3_module_is_not_considered_as_v4(self):
        result = utils.is_module_in_contracts_language_v4(v3_contract_template)
        self.assertFalse(result)

    def test_v4_module_is_considered_as_v4(self):
        result = utils.is_module_in_contracts_language_v4(v4_contract_template)
        self.assertTrue(result)

    def test_v4_ast_module_is_considered_as_v4(self):
        ast_module = ast.parse("api='4.0.0'")
        result = utils.is_module_in_contracts_language_v4(ast_module)
        self.assertTrue(result)

    def test_v5_ast_module_is_not_considered_as_v4(self):
        ast_module = ast.parse("api='5.0.0'")
        result = utils.is_module_in_contracts_language_v4(ast_module)
        self.assertFalse(result)

    def test_v3_ast_module_is_not_considered_as_v4(self):
        ast_module = ast.parse("api='3.0.0'")
        result = utils.is_module_in_contracts_language_v4(ast_module)
        self.assertFalse(result)

    def test_ast_module_with_no_api_raises(self):
        ast_module = ast.parse("")
        with self.assertRaisesRegex(utils.MissingApiMetadata, "Could not find an `api` assignment"):
            utils.is_module_in_contracts_language_v4(ast_module)

    def test_ast_module_with_invalid_api_semver_raises(self):
        ast_module = ast.parse("api='bla.bla.bla'")
        with self.assertRaisesRegex(utils.InvalidApiMetadata, "Could not parse `api` value"):
            utils.is_module_in_contracts_language_v4(ast_module)

    def test_ast_module_with_non_ast_constant_api_raises(self):
        ast_module = ast.parse("test='4.0.0'\napi=test")
        with self.assertRaisesRegex(
            utils.InvalidApiMetadata, "`api` value must be an ast.Constant"
        ):
            utils.is_module_in_contracts_language_v4(ast_module)

    def test_get_contract_version(self):
        self.assertEquals(utils.get_contract_version(ast.parse("api='4.0.0'")), Version("4.0.0"))

    def test_validate_missing_contract_version(self):
        with self.assertRaisesRegex(utils.MissingApiMetadata, "Could not find an `api` assignment"):
            utils.is_module_in_contracts_language_v4(ast.parse(""))

    def test_validate_invalid_contract_version(self):
        with self.assertRaisesRegex(utils.InvalidApiMetadata, "Could not parse `api` value"):
            utils.is_module_in_contracts_language_v4(ast.parse("api='bla.bla.bla'"))
