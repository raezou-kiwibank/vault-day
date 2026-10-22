# standard libs
import logging
import os

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.endtoend import (
    skipForVaultVersionGreaterThan,
    skipForVaultVersionLessThan,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

endtoend.testhandle.CONTRACTS = {
    "test_contract": {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
}


class TestVaultVersion(endtoend.End2Endtest):
    skip_assertion_msg = "The decorator on this test case should cause it to be skipped."

    def test_version(self):
        vault_version = endtoend.testhandle.vault_version
        self.assertGreater(vault_version, Version("0.0.0"))

    # Core local returns the year as the major version, hence why the version here is so large.
    @skipForVaultVersionLessThan(Version("10000.0.0"))
    def test_skip_by_vault_version_lt(self):
        self.assertFalse(True, self.skip_assertion_msg)

    @skipForVaultVersionGreaterThan(Version("0.0.0"))
    def test_skip_by_vault_version_gt(self):
        self.assertFalse(True, self.skip_assertion_msg)
