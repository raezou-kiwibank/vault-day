# standard libs
from unittest import TestCase
from unittest.mock import MagicMock, patch

# third party
from semantic_version import Version

# inception sdk
from inception_sdk.common.exceptions import TestSetupException
from inception_sdk.test_framework.endtoend import AcceleratedEnd2EndTest, End2Endtest
from inception_sdk.test_framework.endtoend.balances import ACCOUNT_BALANCE_V2_EVENTS_TOPIC


class End2EndtestTest(TestCase):

    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup")
    def test_End2Endtest_adds_balances_v2_topic_if_supported(
        self, _, mock_kafka_setup, mock_testhandle
    ):
        # supported version
        mock_testhandle.vault_version = Version("5.7.0")

        End2Endtest.setUpClass()

        mock_kafka_setup.assert_called_once()
        self.assertIn(ACCOUNT_BALANCE_V2_EVENTS_TOPIC, mock_kafka_setup.call_args.args[0])

    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup")
    def test_End2Endtest_does_not_add_balances_v2_topic_if_unsupported(
        self, _, mock_kafka_setup, mock_testhandle
    ):
        # unsupported version
        mock_testhandle.vault_version = Version("5.6.0")

        End2Endtest.setUpClass()

        mock_kafka_setup.assert_called_once()
        self.assertNotIn(ACCOUNT_BALANCE_V2_EVENTS_TOPIC, mock_kafka_setup.call_args.args[0])

    @patch("inception_sdk.test_framework.endtoend.helper")
    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup")
    def test_AcceleratedEnd2EndTest_adds_balances_v2_topic_if_supported(
        self, mock_standard_setup, mock_kafka_setup, mock_testhandle, _
    ):
        # supported version
        mock_testhandle.vault_version = Version("5.7.0")

        AcceleratedEnd2EndTest.setUpClass()

        mock_kafka_setup.assert_called_once()
        self.assertIn(ACCOUNT_BALANCE_V2_EVENTS_TOPIC, mock_kafka_setup.call_args.args[0])

    @patch("inception_sdk.test_framework.endtoend.helper")
    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup")
    def test_AcceleratedEnd2EndTest_does_not_add_balances_v2_topic_if_unsupported(
        self, mock_standard_setup, mock_kafka_setup, mock_testhandle, _
    ):
        # unsupported version
        mock_testhandle.vault_version = Version("5.6.0")

        AcceleratedEnd2EndTest.setUpClass()

        mock_kafka_setup.assert_called_once()
        self.assertNotIn(ACCOUNT_BALANCE_V2_EVENTS_TOPIC, mock_kafka_setup.call_args.args[0])

    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup_with_multiple_product_versions")
    def test_End2Endtest_calls_multiple_product_version_setup_if_products_defined(
        self,
        mock_standard_setup_with_multiple_product_versions,
        _,
        mock_testhandle,
    ):
        # GIVEN: CONTRACTS is empty
        # GIVEN: PRODUCTS has content to trigger the setup standard with multiple
        # product versions path
        mock_testhandle.CONTRACTS = {}
        mock_testhandle.PRODUCTS = [MagicMock()]
        mock_testhandle.use_kafka = False

        # supported version
        mock_testhandle.vault_version = Version("5.9.0")

        # WHEN setup suite is called
        End2Endtest.setUpClass()

        # THEN: standard_setup_with_multiple_product_versions is called instead of legacy
        mock_standard_setup_with_multiple_product_versions.assert_called_once()

    @patch("inception_sdk.test_framework.endtoend.testhandle")
    @patch("inception_sdk.test_framework.endtoend.kafka_setup")
    @patch("inception_sdk.test_framework.endtoend.standard_setup_with_multiple_product_versions")
    def test_End2Endtest_both_products_contracts_defined_raises(
        self,
        mock_standard_setup_with_multiple_product_versions,
        _,
        mock_testhandle,
    ):
        # GIVEN: CONTRACTS non empty
        # GIVEN: PRODUCTS non empty
        mock_testhandle.CONTRACTS = {"product_id": MagicMock()}
        mock_testhandle.PRODUCTS = [MagicMock()]
        mock_testhandle.use_kafka = False

        # WHEN: setup suite is called
        # THEN: TestSetupException raised as defining CONTRACTS and PRODUCTS violates constraint
        with self.assertRaises(TestSetupException) as ctx:
            End2Endtest.setUpClass()

            self.assertEqual(
                str(ctx.exception),
                "Only one of testhandle.PRODUCTS and testhandle.CONTRACTS can be defined",
            )
