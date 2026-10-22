import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# To use with uv: uv run --with gitpython precommit.py
try:
    from git import Repo
except ImportError:
    print("Please install gitpython: uv pip install gitpython")
    sys.exit(1)


def run_command(args: list[str], cwd: Path | str | None = None) -> bool:
    """Helper to run shell commands and return success status."""
    result = subprocess.run(args, cwd=cwd)
    return result.returncode == 0


def get_staged_files(repo_dir: str) -> list[Path]:
    """Retrieves a list of staged Python files that currently exist on disk."""
    repo = Repo(repo_dir)
    # Use git command directly to get staged files that exist
    # Filter: A (Added), C (Copied), M (Modified), R (Renamed)
    files_str = repo.git.diff("--cached", "--name-only", "--diff-filter=ACMR")
    if not files_str:
        return []

    staged_files = []
    for line in files_str.split("\n"):
        if line.endswith(".py"):
            path = Path(line).resolve()
            if path.exists():
                staged_files.append(path)
    return staged_files


def reformat_staged_files(staged_files: list[Path]) -> None:
    """Runs Ruff formatter and linter on the provided list of staged files."""
    if not staged_files:
        print("No staged Python files found.")
        return

    # --- 1. Global Linting & Formatting ---
    # Ruff is fast enough to run on all staged files at once from the root
    print(f"--- Formatting and Fixing {len(staged_files)} files ---")
    run_command(["uv", "run", "ruff", "format"] + [str(f) for f in staged_files])
    run_command(["uv", "run", "ruff", "check", "--fix"] + [str(f) for f in staged_files])


def find_project_root(file_path: Path | str) -> Path | None:
    """Climb up from a file to find the nearest pyproject.toml."""
    path = Path(file_path).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def collect_staged_files_by_project(staged_files: list[Path]) -> defaultdict[Path, list[Path]]:
    """Groups staged files by their respective project roots."""
    project_map: defaultdict[Path, list[Path]] = defaultdict(list)
    for f in staged_files:
        root: Path | None = find_project_root(f)
        if root:
            project_map[root].append(f)

    return project_map


def run_command_handle_pytest(args: list[str], cwd: Path | str | None = None) -> bool:
    """Special handler for pytest to allow exit code 5 (no tests found)."""
    result = subprocess.run(args, cwd=cwd)
    return result.returncode in (0, 5)


def run_checks_on_each_project(repo_dir: str, projects: list[Path]) -> None:
    """Runs Pytest and Semgrep checks on each project in the workspace."""
    for project_root in projects:
        # Run Pytest unit tests if tests directory exists
        if (project_root / "tests").exists():
            print(f"  Running pytest for {project_root.name}...")
            if not run_command_handle_pytest(
                ["uv", "run", "--env-file", ".env", "pytest", "-m", "unit"], cwd=project_root
            ):
                print(f"❌ Tests failed in {project_root.name}")
                sys.exit(1)

        # Run Semgrep.
        print(f"  Running Semgrep for {project_root.name}...")
        if not run_command(
            ["uv", "run", "semgrep", "scan", "--error", "--config", repo_dir + "/semgrep.yaml"],
            cwd=project_root,
        ):
            print(f"❌ Tests failed in {project_root.name}")
            sys.exit(1)


def type_check_changed_files_in_project(project_map: defaultdict[Path, list[Path]]) -> None:
    """Runs type checking on staged files within their respective projects."""
    for project_root, files in project_map.items():
        print(f"\n🚀 Processing Project: {project_root.name}")

        # Filter out test files
        files_to_check = [f for f in files if "test" not in f.parts and "tests" not in f.parts]

        if not files_to_check:
            print("  No non-test files to type check.")
            continue

        # Convert absolute paths to paths relative to the project root
        relative_files: list[str] = [str(f.relative_to(project_root)) for f in files_to_check]

        # Type check staged files
        print(f"  Checking types for: {', '.join(relative_files)}...")
        if not run_command(["uv", "run", "ty", "check"] + relative_files, cwd=project_root):
            print(f"❌ Type check failed in {project_root.name}")
            sys.exit(1)


def main() -> None:
    """Main entry point for the pre-commit script."""
    repo_dir: str = os.getcwd()
    staged_files: list[Path] = get_staged_files(repo_dir)
    reformat_staged_files(staged_files)
    project_map: defaultdict[Path, list[Path]] = collect_staged_files_by_project(staged_files)
    type_check_changed_files_in_project(project_map)
    run_checks_on_each_project(repo_dir, list(project_map.keys()))

    print("\n✅ All checks passed!")


if __name__ == "__main__":
    main()
