import os
import json
import shutil
from typing import List, Optional

from ..common import error
from .item import TodoItem


def load(path: Optional[str]) -> List[TodoItem]:
    if path is None:
        return []
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [TodoItem.from_dict(todo) for todo in json.load(f)]

def undo(path: str):
    backup_path = path.replace(".json", ".undo.json")
    if not os.path.exists(backup_path):
        error(f"Cannot undo, backup file {backup_path!r} does not exist.")
    shutil.copyfile(backup_path, path)
    os.remove(backup_path)

def save(todos: List[TodoItem], path: str, backup: bool = True):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    if backup and os.path.exists(path):
        backup_path = path.replace(".json", ".undo.json")
        shutil.copyfile(path, backup_path)
    with open(path, "w") as f:
        data = [
            todo.to_dict() for todo in todos
            if not todo.status == "delete"]
        json.dump(data, f, indent=4)
