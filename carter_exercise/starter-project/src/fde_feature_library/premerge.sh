#!/bin/bash
set -eou pipefail

any_element_starts_with() {
    # Searches array the_array for any element that starts with search_value.
    # Parameter search_value is passed by value.  Parameter the_array is passed by name.
    local search_value="$1"
    local -n the_array="$2"
    shift
    for element in "${the_array[@]}"; do
        [[ "$element" == "$search_value"* ]] && return 0
    done
    return 1
}

base_dir=$(pwd)
# Save the list of changed files in the branch to an array
mapfile -t changed_py_files < <(git --no-pager diff --name-only --diff-filter AMR origin/master..HEAD | grep \.py$)


# Find all Python projects in the repo.  For each Python project which contains files that were 
# modified in the branch, run all the tests in the project.
while IFS= read -r -d '' project_name; do
  proj_dir=$(echo `dirname $project_name`|sed s:^\./::);
  if any_element_starts_with "$proj_dir" changed_py_files; then
    echo "Project" $proj_dir "contains changed files in the branch.  Running tests."
    cd "$proj_dir"
    let p=$(nproc)*2; uv run --env-file .env pytest -n $p
    cd "$base_dir"
  fi
done < <(find . -mindepth 2 -type f -name pyproject.toml -print0)

