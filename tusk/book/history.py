import os
import json
from typing import List, Dict
from datetime import datetime

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


def undo(path: str) -> Dict[str, str | datetime]:
    """Restore the most recent version from git history."""
    try:
        repo = _repo(path)
        c = repo.head.commit
        info = {
            "message": str(c.message),
            "hexsha": c.hexsha,
            "timestamp": c.committed_datetime,
        }
        repo.git.checkout('HEAD~1')
    except GitCommandError as e:
        error(f"Failed to undo changes: {e}")
    return info


def history(path: str) -> List[Dict[str, str | datetime]]:
    return [
        {
            'hash': c.hexsha,
            'message': str(c.message),
            'timestamp': c.committed_datetime,
        } for c in _repo(path).iter_commits()
    ]


def save(
    commit_message: str, todos: List[TodoItem], path: str,
    backup: bool = True, indent: int = 4,
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
        json.dump(data, f, indent=indent)
    if backup:
        try:
            with _repo(path) as repo:
                repo.index.add(_MAIN_FILE)
                if repo.is_dirty():
                    repo.index.commit(commit_message)
        except GitCommandError as e:
            error(f"Failed to commit changes: {e}")
