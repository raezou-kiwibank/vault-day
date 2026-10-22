# standard libs
from unittest import TestCase
from unittest.mock import Mock, PropertyMock, patch

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils
from inception_sdk.vault.environment import Environment

MOCK_ENV_VARS = {
    "INC_ENVIRONMENT_NAME": "os_env_environment_name",
    "INC_ENVIRONMENT_CONFIG_PATH": "os_env_environment_config_path",
}

# os.environ is used at import time, so patching in test setup is too late
with patch.dict("os.environ", MOCK_ENV_VARS) as mock_os_environ:
    # inception sdk
    import inception_sdk.common.config as config


@patch("logging.Logger.info")
@patch.object(config, "load_environments")
@patch.object(config, "FLAGS")
class ConfigExtractionTest(TestCase):
    non_default_env: Environment
    default_env: Environment
    available_environments: dict[str, Environment]

    @classmethod
    def setUpClass(cls) -> None:
        cls.maxDiff = None

        return super().setUpClass()

    def setUp(self) -> None:
        # as we sometimes assert on the mocks' calls they must be reset for each test
        self.non_default_env = Environment(
            name="non_default_env", core_api_url="core_api_url", auth=Mock()
        )
        self.default_env = Environment(name="default_env", core_api_url="core_api_url", auth=Mock())
        self.available_environments = {
            "default_env": self.default_env,
            "non_default_env": self.non_default_env,
        }
        return super().setUp()

    def test_env_to_use_is_authenticated(
        self, flags_mock, load_environments_mock, info_logger_mock: Mock
    ):
        # Everything configured to return default_env except for the function parameter
        type(flags_mock).environment_name = PropertyMock(return_value="default_env")
        load_environments_mock.return_value = self.available_environments

        env, _ = config.extract_environments_from_config(default_environment_name="default_env")

        self.assertEqual(env, self.default_env)
        # we've passed in a mock to the `auth` parameter, so the types aren't properly recognised
        self.default_env.auth.jwt.refresh_jwt.assert_called_once()  # type: ignore

    def test_function_parameter_take_top_priority(
        self, flags_mock, load_environments_mock, info_logger_mock: Mock
    ):
        # Everything configured to return default_env except for the function parameter
        type(flags_mock).environment_name = PropertyMock(return_value="default_env")
        load_environments_mock.return_value = self.available_environments

        env, _ = config.extract_environments_from_config(
            environment_name="non_default_env", default_environment_name="default_env"
        )

        self.assertEqual(env, self.non_default_env)
        info_logger_mock.assert_called_once_with(
            "Using environment non_default_env - hardcoded (e.g. in test module)"
        )

    def test_flag_variables_take_second_priority(
        self, flags_mock, load_environments_mock, info_logger_mock: Mock
    ):
        # Everything configured to return default_env except flag and function param
        type(flags_mock).environment_name = PropertyMock(return_value="non_default_env")
        load_environments_mock.return_value = self.available_environments

        env, _ = config.extract_environments_from_config(
            environment_name="", default_environment_name="default_env"
        )

        self.assertEqual(env, self.non_default_env)
        info_logger_mock.assert_called_once_with(
            "Using environment non_default_env - specified in CLI/OS Flags"
        )

    def test_default_environment_name_takes_third_priority(
        self, flags_mock, load_environments_mock, info_logger_mock: Mock
    ):
        # Everything configured to return nothing, except default env param
        type(flags_mock).environment_name = PropertyMock(return_value="")

        load_environments_mock.return_value = self.available_environments

        env, _ = config.extract_environments_from_config(
            environment_name="", default_environment_name="default_env"
        )

        self.assertEqual(env, self.default_env)
        info_logger_mock.assert_called_once_with(
            "Using environment default_env - specified as default (e.g. framework config)"
        )

    def test_no_environment_name_by_any_mechanism_raises_exception(
        self, flags_mock, load_environments_mock, info_logger_mock: Mock
    ):
        type(flags_mock).environment_name = PropertyMock(return_value="")

        load_environments_mock.return_value = self.available_environments
        with self.assertRaisesRegex(ValueError, r"No environment_name found.*"):
            config.extract_environments_from_config(
                environment_name="", default_environment_name=""
            )


class CommonFlagSetupTest(TestCase):
    # These tests all rely on the import-level os.environ patch
    def test_environment_name_defaults_to_os_env(
        self,
    ):
        flag_utils.parse_flags(argv=[])
        self.assertEqual(config.FLAGS.environment_name, "os_env_environment_name")

    def test_environment_path_config_defaults_to_os_env(
        self,
    ):
        flag_utils.parse_flags(argv=[])
        self.assertEqual(config.FLAGS.environment_config_path, "os_env_environment_config_path")
