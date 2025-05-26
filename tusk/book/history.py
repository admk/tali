import re
import os
import json
from typing import List, Dict
from datetime import datetime

from git import InvalidGitRepositoryError, GitCommandError
from git.repo import Repo

from ..common import debug, error
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


def checkout(path: str, commit_hash: str) -> Dict[str, str | datetime]:
    repo = _repo(path)
    c = repo.head.commit
    info = {
        "message": str(c.message),
        "hexsha": c.hexsha,
        "timestamp": c.committed_datetime,
    }
    repo.git.checkout(commit_hash)
    debug(f"Checked out commit {commit_hash} in {path}")
    return info


def undo(path: str) -> Dict[str, str | datetime]:
    """Restore the previous version from git history."""
    repo = _repo(path)
    commits = list(repo.iter_commits('main'))
    try:
        index = commits.index(repo.head.commit)
    except ValueError:
        raise ValueError("Current HEAD commit not found in main branch.")
    if index + 1 >= len(commits):
        error("No history to undo.")
    return checkout(path, commits[index + 1].hexsha)


def redo(path: str) -> Dict[str, str | datetime]:
    """Redo the last undone commit."""
    repo = _repo(path)
    commits = list(repo.iter_commits('main'))
    try:
        index = commits.index(repo.head.commit)
    except ValueError:
        raise ValueError("Current HEAD commit not found in main branch.")
    if index == 0:
        error("No history to redo.")
    return checkout(path, commits[index - 1].hexsha)


def history(path: str) -> List[Dict[str, str | datetime]]:
    return [
        {
            "hash": c.hexsha,
            "message": str(c.message),
            "timestamp": c.committed_datetime,
        } for c in _repo(path).iter_commits()
    ]


def save(
    commit_message: str, todos: List[TodoItem], path: str,
    backup: bool = True, indent: int = 4,
):
    """
    Save the list of todos to a file using git for version control.
    Commits changes if backup is enabled and we're at HEAD.
    """
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
        if repo.is_dirty():
            repo.index.commit(commit_message)
    except GitCommandError as e:
        error(f"Failed to commit changes: {e}")
