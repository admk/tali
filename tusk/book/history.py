import os
import json
from typing import List, Optional, Generator

from contextlib import contextmanager
import tempfile
from git import GitCommandError, InvalidGitRepositoryError
from git.repo import Repo

from ..common import error, info, debug
from .item import TodoItem


@contextmanager
def _get_repo(path: str) -> Generator[Repo, None, None]:
    path = os.path.splitext(path)[0] + ".git"
    bare_path = os.path.join(path, ".git")
    if os.path.exists(bare_path):
        bare_repo = Repo(bare_path)
    else:
        bare_repo = Repo.init(bare_path, bare=True)
    yield bare_repo


def load(path: Optional[str]) -> List[TodoItem]:
    if path is None:
        return []
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [TodoItem.from_dict(todo) for todo in json.load(f)]


def undo(path: str) -> str:
    """Restore the most recent version from git history."""
    try:
        with _get_repo(path) as repo:
            message = repo.head.commit.message
            repo.index.checkout('HEAD~1')
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
            with _get_repo(path) as repo:
                repo.index.add(os.path.basename(path))
                repo.index.commit(commit_message)
        except GitCommandError as e:
            error(f"Failed to commit changes: {e}")
