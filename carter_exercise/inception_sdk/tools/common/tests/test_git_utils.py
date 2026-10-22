# standard libs
import unittest
from unittest import TestCase
from unittest.mock import MagicMock, Mock, PropertyMock, patch

# third party
from git import GitCommandError

# inception sdk
import inception_sdk.tools.common.git_utils as git_utils


class TestGitUtils(TestCase):
    def test_get_relative_filepath(self):
        mock_repo = MagicMock(spec_set=git_utils.Repo)
        type(mock_repo).working_tree_dir = "/my/home/directory/repo_root"
        rf = git_utils.get_relative_filepath_from_repo(
            "/my/home/directory/repo_root/library/new_file.py", repo=mock_repo
        )
        self.assertEqual(rf, "library/new_file.py")

    def test_get_relative_filepath_in_bare_repo(self):
        mock_repo = MagicMock(spec_set=git_utils.Repo)
        type(mock_repo).working_tree_dir = None

        with self.assertRaises(git_utils.BareRepoException):
            git_utils.get_relative_filepath_from_repo(
                "/my/home/directory/repo_root/library/new_file.py", repo=mock_repo
            )

    def test_get_file_checksum_in_bare_repo(self):
        mock_repo = MagicMock(spec_set=git_utils.Repo)
        type(mock_repo).working_tree_dir = None

        with self.assertRaises(git_utils.BareRepoException):
            filepath = "working/dir/path/file.py"
            git_utils.get_file_checksum_from_commit_hash(
                filepath=filepath, commit_hash="commit_hash", repo=mock_repo
            )

    @patch.object(git_utils, "get_hash")
    def test_get_file_checksum_from_commit_hash(self, mock_get_hash: MagicMock):
        mock_get_hash.return_value = "checksum"
        mock_repo = MagicMock(spec_set=git_utils.Repo)
        mock_repo.git.show = MagicMock(return_value="file_contents")
        type(mock_repo).working_tree_dir = PropertyMock(return_value="working/dir")

        filepath = "working/dir/path/file.py"
        checksum = git_utils.get_file_checksum_from_commit_hash(
            filepath=filepath, commit_hash="commit_hash", repo=mock_repo
        )
        self.assertEqual(checksum, "checksum")
        mock_get_hash.assert_called_once_with(hashing_algorithm="md5", data="file_contents")

    def test_get_file_checksum_from_commit_hash_git_exception(self):
        mock_repo = MagicMock(spec_set=git_utils.Repo)
        mock_repo.git.show = MagicMock(side_effect=GitCommandError("uh-oh"))
        type(mock_repo).working_tree_dir = PropertyMock(return_value="working/dir")

        with self.assertRaises(GitCommandError) as test:
            filepath = "working/dir/path/file.py"
            git_utils.get_file_checksum_from_commit_hash(
                filepath=filepath, commit_hash="commit_hash", repo=mock_repo
            )
        self.assertEqual(test.exception.args[0], "uh-oh")

    @patch.object(git_utils, "get_latest_commit_with_file")
    @patch.object(git_utils, "get_file_checksum_from_commit_hash")
    def test_get_validated_commit_hash_for_file_checksum(
        self, mock_get_file_checksum_from_commit_hash: Mock, mock_get_current_commit_hash: Mock
    ):
        mock_get_current_commit_hash.return_value = "commit_hash"
        mock_get_file_checksum_from_commit_hash.return_value = "checksum"
        commit_hash = git_utils.get_validated_commit_hash_for_file_checksum(
            filepath="path/file.py", checksum="checksum", repo=Mock()
        )
        self.assertEqual(commit_hash, "commit_hash")

    @patch.object(git_utils, "get_latest_commit_with_file")
    @patch.object(git_utils, "get_file_checksum_from_commit_hash")
    @patch.object(git_utils, "get_relative_filepath_from_repo")
    def test_get_validated_commit_hash_for_file_checksum_invalid(
        self,
        mock_get_relative_filepath: Mock,
        mock_get_file_checksum_from_commit_hash: Mock,
        mock_get_current_commit_hash: Mock,
    ):
        mock_get_current_commit_hash.return_value = "commit_hash"
        mock_get_file_checksum_from_commit_hash.return_value = "muskcehc"
        mock_get_relative_filepath.return_value = "file.py"
        with self.assertRaises(git_utils.GitException) as test:
            git_utils.get_validated_commit_hash_for_file_checksum(
                filepath="path/file.py", checksum="checksum", repo=Mock()
            )
        self.assertEqual(
            test.exception.args[0],
            "The checksum of file.py does not match the latest checksum in the Git repo. Ensure "
            "that all changes are committed.",
        )


if __name__ == "__main__":
    unittest.main()
