# standard libs
import os
from unittest import TestCase
from unittest.mock import Mock, call, patch

# inception sdk
import inception_sdk.common.python.file_utils as file_utils
import inception_sdk.common.python.resources as resources


class FileUtilsTests(TestCase):
    @patch.object(file_utils.resources, "resource_or_file_string")
    @patch.object(file_utils.os.path, "abspath")
    def test_load_sdk_file_in_plz_as_wheel_retries_with_prefix(
        self,
        mock_abspath: Mock,
        mock_resource_or_file_string: Mock,
    ):
        # When run as a third_party python_wheel via plz, the first attempt to load from original
        # path will fail, and should then # be retried with the third_party/python3 prefix
        mock_abspath.return_value = "some/path/plz-out/inception_sdk/some/file.py"
        mock_resource_or_file_string.side_effect = [FileNotFoundError, "dummy_contents"]

        contents = file_utils.load_file_contents("inception_sdk/some/file.py")
        self.assertEqual(contents, "dummy_contents")

        mock_resource_or_file_string.assert_has_calls(
            calls=[
                call("inception_sdk/some/file.py", utf8=True),
                call("third_party/python3/inception_sdk/some/file.py", utf8=True),
            ]
        )

    @patch.object(file_utils.resources, "resource_or_file_string")
    @patch.object(file_utils.os.path, "abspath")
    def test_load_sdk_file_in_plz_as_non_wheel_does_not_retry_with_prefix(
        self,
        mock_abspath: Mock,
        mock_resource_or_file_string: Mock,
    ):
        # When run as a python_library via plz, the first attempt to load from original
        # path should pass
        mock_abspath.return_value = "some/path/plz-out/inception_sdk/some/file.py"
        mock_resource_or_file_string.side_effect = ["dummy_contents"]

        contents = file_utils.load_file_contents("inception_sdk/some/file.py")
        self.assertEqual(contents, "dummy_contents")
        mock_resource_or_file_string.assert_called_with("inception_sdk/some/file.py", utf8=True)

    @patch.object(file_utils.importlib.resources, "read_text")
    @patch.object(file_utils.os.path, "abspath")
    def test_load_sdk_file_non_plz_uses_importlib(
        self,
        mock_abspath: Mock,
        mock_importlib_read_text: Mock,
    ):
        mock_abspath.return_value = "some/path/inception_sdk/some/file.py"
        mock_importlib_read_text.side_effect = ["dummy_contents"]

        contents = file_utils.load_file_contents("inception_sdk/some/file.py")
        self.assertEqual(contents, "dummy_contents")
        mock_importlib_read_text.assert_called_with("inception_sdk.some", "file.py", "utf-8")

    @patch.object(file_utils.resources, "resource_or_file_string")
    @patch.object(file_utils.os.path, "abspath")
    def test_load_non_sdk_file_in_plz(
        self,
        mock_abspath: Mock,
        mock_resource_or_file_string: Mock,
    ):
        mock_abspath.return_value = "some/path/plz-out/some/file.py"
        mock_resource_or_file_string.side_effect = ["dummy_contents"]

        contents = file_utils.load_file_contents("some/file.py")
        self.assertEqual(contents, "dummy_contents")
        mock_resource_or_file_string.assert_called_with("some/file.py", utf8=True)

    @patch.object(file_utils.resources, "resource_or_file_string")
    @patch.object(file_utils.os.path, "abspath")
    def test_load_non_sdk_file_non_plz(
        self,
        mock_abspath: Mock,
        mock_resource_or_file_string: Mock,
    ):
        mock_abspath.return_value = "some/path/some/file.py"
        mock_resource_or_file_string.side_effect = ["dummy_contents"]

        contents = file_utils.load_file_contents("some/file.py")
        self.assertEqual(contents, "dummy_contents")
        mock_resource_or_file_string.assert_called_with("some/file.py", utf8=True)

    def test_normalise_windows_path(
        self,
    ):
        orig_platform = os.name
        os.name = "nt"
        nt_path = "third_party\\python3\\"
        repo_path = "inception_sdk/test_framework/contracts/empty_asset_contract.py"
        joint_path = os.path.join(nt_path, repo_path)
        print(os.name)

        norm_path = resources._normalise_platform_path(joint_path)
        os.name = orig_platform

        self.assertEqual(
            norm_path,
            r"third_party\python3\inception_sdk\test_framework\contracts\empty_asset_contract.py",
        )

    def test_normalise_posix_path(
        self,
    ):
        orig_platform = os.name
        os.name = "posix"
        posix_path = r"third_party/python3"
        repo_path = "inception_sdk/test_framework/contracts/empty_asset_contract.py"
        joint_path = os.path.join(posix_path, repo_path)
        print(os.name)

        norm_path = resources._normalise_platform_path(joint_path)
        os.name = orig_platform

        self.assertEqual(
            norm_path,
            r"third_party/python3/inception_sdk/test_framework/contracts/empty_asset_contract.py",
        )
