import re
import os
import json
from typing import List, Literal
from datetime import datetime

from git import InvalidGitRepositoryError, GitCommandError, Commit as GitCommit
from git.repo import Repo

from ..common import debug, error
from .result import Commit, ActionResult, HistoryResult, SwitchResult
from .item import TodoItem


_MAIN_FILE = "main"


def _repo(path: str) -> Repo:
    os.makedirs(path, exist_ok=True)
    try:
        return Repo(path)
    except InvalidGitRepositoryError:
        return Repo.init(path)


def load(path: str) -> List[TodoItem]:
    main_file = os.path.join(path, _MAIN_FILE)
    if not os.path.exists(main_file):
        return []
    with open(main_file, "r") as f:
        return [TodoItem.from_dict(todo) for todo in json.load(f)]


def to_commit(
    commit: GitCommit
) -> Commit:
    message, _, *data = str(commit.message).split("\n")
    data = json.loads("\n".join(data))
    action_results = [ActionResult.from_dict(d) for d in data]
    return Commit(
        message, commit.hexsha, commit.committed_datetime,
        commit.hexsha == commit.repo.head.commit.hexsha, action_results)


def checkout(path: str, commit_hash: str) -> Commit:
    repo = _repo(path)
    c = repo.head.commit
    repo.git.checkout(commit_hash)
    debug(f"Checked out commit {commit_hash} in {path}")
    return to_commit(c)


def _undo_redo(
    path: str, action: Literal["undo", "redo"]
) -> SwitchResult:
    """Restore the previous version from git history."""
    repo = _repo(path)
    commits = list(repo.iter_commits("main"))
    before = repo.head.commit
    try:
        index = commits.index(before)
    except ValueError:
        raise ValueError("Current HEAD commit not found in main branch.")
    if action == "undo":
        if index + 1 >= len(commits):
            error("No history to undo.")
        index += 1
        action_results = to_commit(before).action_results
        message = str(before.message)
    elif action == "redo":
        if index == 0:
            error("No history to redo.")
        index -= 1
        action_results = to_commit(commits[index]).action_results
        message = str(commits[index].message)
    else:
        raise ValueError(f"Unknown action: {action}")
    checkout(path, commits[index].hexsha)
    message = message.split("\n", 1)[0]
    result = SwitchResult(action, message, action_results)
    debug(f"{action.capitalize()} result: {result}")
    return result


def undo(path: str) -> SwitchResult:
    return _undo_redo(path, "undo")


def redo(path: str) -> SwitchResult:
    return _undo_redo(path, "redo")


def history(path: str) -> HistoryResult:
    return HistoryResult(
        [to_commit(c) for c in _repo(path).iter_commits("main")])


def save(
    commit_message: str, todos: List[TodoItem],
    action_results: List[ActionResult],
    path: str, backup: bool = True, indent: int = 4,
):
    """
    Save the list of todos to a file using git for version control.
    Commits changes if backup is enabled and we're at HEAD.
    """
    debug(f"Saving todos to {path} with commit message: {commit_message}")
    repo = _repo(path)
    main_file = os.path.join(path, _MAIN_FILE)
    with open(main_file, "w") as f:
        data = [
            todo.to_dict() for todo in todos if not todo.status == "delete"]
        json.dump(data, f, indent=indent)
    if not backup:
        return
    if repo.head.is_detached:
        backup_branch = f"backup-{datetime.now():%Y-%m-%d-%H-%M-%S}"
        repo.git.branch("-m", "main", backup_branch)
        repo.git.checkout("-b", "main")
    try:
        repo.index.add(_MAIN_FILE)
        if not repo.is_dirty():
            return
        result = json.dumps(
            [ar.to_dict() for ar in action_results], indent=indent)
        repo.index.commit(commit_message + "\n\n" + result)
    except GitCommandError as e:
        error(f"Failed to commit changes: {e}")
