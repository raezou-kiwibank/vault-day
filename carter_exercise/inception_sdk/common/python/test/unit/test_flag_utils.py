# standard libs
import sys
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

# third party
from absl.flags import IllegalFlagValueError, UnrecognizedFlagError

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils


@patch.object(flag_utils, "FLAGS")
class FlagUtilsTests(TestCase):
    def test_apply_flag_modifier(self, mock_FLAGS: MagicMock):
        # get_flag_value is used to get the value
        # This mock is only used to assert that the new value is set correctly
        mock_flag_attribute = PropertyMock()
        type(mock_FLAGS).my_flag = mock_flag_attribute
        mock_FLAGS.get_flag_value.return_value = "some_value"

        flag_utils.apply_flag_modifiers({"my_flag": lambda x: x + "/"})

        mock_flag_attribute.assert_called_once_with("some_value/")


class FlagParsingTests(TestCase):
    def tearDown(self) -> None:
        flag_utils.FLAGS.unparse_flags()
        return super().tearDown()

    def test_parse_flags_with_known_flags(self):
        remaining = flag_utils.parse_flags(argv=["binary", "--log_level=INFO"], allow_unknown=False)
        self.assertListEqual(remaining, [])
        self.assertEqual(flag_utils.FLAGS.log_level, "INFO")

    def test_parse_flags_with_unknown_args_raises(self):
        with self.assertRaises(UnrecognizedFlagError) as ctx:
            flag_utils.parse_flags(argv=["binary", "--b", "--c"], allow_unknown=False)
        self.assertEqual(ctx.exception.args[0], "Unknown command line flag 'b'")

    @patch.object(flag_utils, "logger")
    def test_parse_flags_with_unknown_args_and_allow_unknown(self, mock_logger: MagicMock):
        remaining = flag_utils.parse_flags(argv=["binary", "--b", "--c"], allow_unknown=True)
        self.assertListEqual(remaining, ["--b", "--c"])
        mock_logger.warning.assert_called_once_with("Ignoring unrecognised flags ['--b', '--c']")

    @patch.object(flag_utils, "logger")
    def test_parse_flags_with_no_unknown_args_and_allow_unknown(self, mock_logger: MagicMock):
        remaining = flag_utils.parse_flags(
            argv=["binary"],
            allow_unknown=True,
        )
        self.assertListEqual(remaining, [])
        mock_logger.warning.assert_not_called()

    def test_parse_flags_with_positional_accepts_single_dash(self):
        remaining = flag_utils.parse_flags(
            argv=["binary", "--log_level=INFO", "-"], positional=True, allow_unknown=False
        )
        self.assertListEqual(remaining, ["-"])

    def test_parse_flags_with_positional_accepts_positional_args(self):
        remaining = flag_utils.parse_flags(
            argv=["binary", "--log_level=INFO", "test"], positional=True, allow_unknown=False
        )
        self.assertListEqual(remaining, ["test"])

    @patch.object(flag_utils, "sys", spec=sys)
    def test_parse_flags_with_help_sys_exits(self, mock_sys: MagicMock):
        flag_utils.parse_flags(argv=["binary", "--help"])
        mock_sys.exit.assert_called_once_with(0)

    @patch.object(flag_utils, "FLAGS")
    @patch.object(flag_utils, "sys", spec=sys)
    def test_parse_flags_with_error_and_help_sys_exits(
        self, mock_sys: MagicMock, mock_flags: MagicMock
    ):
        type(mock_flags).help = PropertyMock(return_value=True)
        mock_flags.is_parsed.return_value = True
        mock_flags.side_effect = IllegalFlagValueError("bla")
        with self.assertRaises(IllegalFlagValueError):
            flag_utils.parse_flags(argv=["binary", "--bla"])

        mock_sys.exit.assert_called_once_with(0)

    @patch.object(flag_utils, "logger")
    def test_parse_flags_with_invalid_value_raises(self, mock_log: MagicMock):
        with self.assertRaises(IllegalFlagValueError) as ctx:
            flag_utils.parse_flags(argv=["binary", "--log_level=1234"])
        self.assertEqual(
            ctx.exception.args[0],
            "flag --log_level=1234: value should be one of "
            "<DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL>",
        )
        mock_log.exception.assert_called_once_with(ctx.exception)
