# standard libs
import logging
import os
from pathlib import Path

# third party
import git
from git.exc import GitCommandError
from git.repo import Repo

# inception sdk
from inception_sdk.common.python.flag_utils import flags
from inception_sdk.tools.common.tools_utils import get_hash

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

FLAG_GIT_REPO_ROOT = "git_repo_root"
flags.DEFINE_string(
    name=FLAG_GIT_REPO_ROOT,
    default=".",
    required=False,
    help="path to the root of the Git repo. Repos in parent directories are also considered",
)


class BareRepoException(Exception):
    def __init__(self) -> None:
        super().__init__("Repo has no working dir - this is the sign of a bare repo")


class GitException(Exception):
    pass


def load_repo(path: str | os.PathLike | None = None, **kwargs) -> Repo:
    log.info(f"Looking for repo at or above `{path}`")
    try:
        repo = Repo(path, search_parent_directories=True, **kwargs)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
        log.exception(f"Could not find git repository using path `{path}`")
        raise e

    if repo.working_tree_dir is None:
        raise BareRepoException()

    log.info(f"Using repo at `{repo.working_tree_dir}`")
    return repo


def get_relative_filepath_from_repo(filepath: str, repo: Repo) -> str:
    if repo.working_tree_dir is None:
        raise BareRepoException()
    return str(Path(filepath).relative_to(Path(repo.working_tree_dir)))


def get_file_checksum_from_commit_hash(
    filepath: str,
    commit_hash: str,
    repo: Repo,
    hashing_algorithm: str = "md5",
) -> str:
    """
    Given a filepath, return the file checksum after validating that the file exists in the
    specified commit.

    :param filepath: this must be the absolute filepath of the file being evaluated
    :param commit_hash: the git commit hash (short or long)
    :param repo: the git repo to operate in
    :param hashing_algorithm: the hashing algorithm to use to calculate the file checksum. Must
    be supported by `hashlib`
    """

    if repo.working_tree_dir is None:
        raise BareRepoException()

    relative_file_path = get_relative_filepath_from_repo(filepath=filepath, repo=repo)

    try:
        file_contents = repo.git.show(
            f"{commit_hash}:{relative_file_path}",
            # The file content will potentially differ without this option, which then affects the
            # hash. See https://github.com/gitpython-developers/GitPython/issues/1377 for background
            strip_newline_in_stdout=False,
        )
    except git.GitCommandError as e:
        log.error(
            f"Failed to extract file contents for file `{relative_file_path}` "
            f"at git commit `{commit_hash}` "
        )
        raise e

    # We may want to consider using git hash-object instead of hashing ourselves, which would
    # greatly simplify the git-source-finder. This would need doing in a backwards-compatible
    # way to avoid unnecessarily changing everyone's rendered contracts
    return get_hash(hashing_algorithm=hashing_algorithm, data=file_contents)


def get_latest_commit_with_file(filepath: str, repo: Repo) -> str:

    try:
        return repo.git.log("-n", "1", "--pretty=format:%H", filepath)
    except GitCommandError as e:
        log.exception(e)
        raise GitException(
            f"Unable to find file {get_relative_filepath_from_repo(filepath, repo)} "
            f"in the Git repo."
        )


def get_validated_commit_hash_for_file_checksum(
    filepath: str,
    checksum: str,
    repo: Repo,
    hashing_algorithm: str = "md5",
) -> str:
    commit_hash = get_latest_commit_with_file(filepath=filepath, repo=repo)
    committed_file_checksum = get_file_checksum_from_commit_hash(
        filepath=filepath,
        commit_hash=commit_hash,
        repo=repo,
        hashing_algorithm=hashing_algorithm,
    )
    if checksum == committed_file_checksum:
        return commit_hash
    else:
        raise GitException(
            f"The checksum of {get_relative_filepath_from_repo(filepath, repo)} does not match the "
            f"latest checksum in the Git repo. Ensure that all changes are committed."
        )
