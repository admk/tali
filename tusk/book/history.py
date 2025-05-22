import os
import json
from typing import List

from git import InvalidGitRepositoryError, GitCommandError
from git.repo import Repo

from ..common import error
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


def undo(path: str) -> str:
    """Restore the most recent version from git history."""
    try:
        repo = _repo(path)
        message = repo.head.commit.message
        repo.git.checkout('HEAD~1')
    except GitCommandError as e:
        error(f"Failed to undo changes: {e}")
    return str(message)


def save(
    commit_message: str, todos: List[TodoItem], path: str, backup: bool = True,
):
    """
    Save the list of todos to a file using git for version control.
    Commits changes if backup is enabled.
    """
    main_file = os.path.join(path, _MAIN_FILE)
    with open(main_file, "w") as f:
        data = [
            todo.to_dict() for todo in todos
            if not todo.status == "delete"]
        json.dump(data, f, indent=4)
    if backup:
        try:
            with _repo(path) as repo:
                repo.index.add(_MAIN_FILE)
                repo.index.commit(commit_message)
        except GitCommandError as e:
            error(f"Failed to commit changes: {e}")
