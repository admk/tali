import os
import json
from typing import List, Optional

from git import GitCommandError, InvalidGitRepositoryError
from git.repo import Repo

from ..common import error, info, debug
from .item import TodoItem


def _get_repo(path: str) -> Repo:
    dir_path = os.path.dirname(path) or "."
    try:
        return Repo(dir_path)
    except InvalidGitRepositoryError:
        return Repo.init(dir_path)


def load(path: Optional[str]) -> List[TodoItem]:
    if path is None:
        return []
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [TodoItem.from_dict(todo) for todo in json.load(f)]


def undo(path: str):
    """Restore the most recent version from git history."""
    try:
        repo = _get_repo(path)
        info(f"Undid commit {repo.head.commit.message}.")
        repo.git.checkout('HEAD~1')
        debug(
            f"Restored previous version of {path!r} "
            f"with commit {repo.head.commit.message!r}")
    except GitCommandError as e:
        error(f"Failed to undo changes: {e}")


def save(
    commit_message: str, todos: List[TodoItem], path: str, backup: bool = True,
):
    """
    Save the list of todos to a file using git for version control.
    Commits changes if backup is enabled.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        data = [
            todo.to_dict() for todo in todos
            if not todo.status == "delete"]
        json.dump(data, f, indent=4)
    if backup:
        try:
            repo = _get_repo(path)
            repo.index.add(os.path.basename(path))
            repo.index.commit(commit_message)
        except GitCommandError as e:
            error(f"Failed to commit changes: {e}")
