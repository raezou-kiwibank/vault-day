# standard libs
from unittest import TestCase, mock, skip

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils

MOCK_ENV_VARS = {
    "INC_USE_KAFKA": "os_env_use_kafka",
    "INC_USE_SYNC_POSTINGS": "os_env_use_sync_postings",
}

# os.environ is used at import time, so patching in test setup is too late
with mock.patch.dict("os.environ", MOCK_ENV_VARS) as mock_os_environ:
    # inception sdk
    import inception_sdk.test_framework.endtoend as endtoend


class E2EFlagSetupOSEnvTest(TestCase):
    def setUp(self) -> None:
        endtoend.FLAGS.unparse_flags()
        return super().setUp()

    @skip(
        "TODO (TM-136482): Manual execution succeeds. Temporarily disabled "
        "pending investigation of plz test discrepancies"
    )
    def test_use_kafka_defaults_to_os_env(
        self,
    ):
        flag_utils.parse_flags(argv=[])
        self.assertEqual(endtoend.FLAGS.use_kafka, True)

    @skip(
        "TODO (TM-136482): Manual execution succeeds. Temporarily disabled "
        "pending investigation of plz test discrepancies"
    )
    def test_use_sync_postings_defaults_to_os_env(
        self,
    ):
        flag_utils.parse_flags(argv=[])
        self.assertEqual(endtoend.FLAGS.use_sync_postings, False)


class E2EFlagSetupCLIOverrideTest(TestCase):
    def setUp(self) -> None:
        endtoend.FLAGS.unparse_flags()
        return super().setUp()

    def test_use_kafka_can_be_overridden_via_cli(
        self,
    ):
        flag_utils.parse_flags(argv=["binary", "--use_kafka=False"])
        self.assertEqual(endtoend.FLAGS.use_kafka, False)

    def test_use_sync_postings_can_be_overridden_via_cli(
        self,
    ):
        flag_utils.parse_flags(argv=["binary", "--use_sync_postings=True"])
        self.assertEqual(endtoend.FLAGS.use_sync_postings, True)
