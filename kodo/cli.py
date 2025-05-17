import sys
import shlex
import argparse
from typing import Optional, Tuple, Any, Dict, Union, List
from dataclasses import dataclass

from . import __version__
from .parser import CommandParser
from .book import TaskBook
from .book.select import GroupBy, SortBy, FilterBy, FilterValue
from .render.cli import Renderer


@dataclass
class ViewResult:
    grouped_todos: Any
    group: GroupBy
    show_all: bool


@dataclass
class AddResult:
    item: Any


@dataclass
class UpdateResult:
    before_todos: List[Any]
    after_todos: List[Any]


ActionResult = Union[ViewResult, AddResult, UpdateResult]


class CLI:
    options = {
        ('-rc', '--rc-file'): {
            'type': str,
            'default': None,
            'help':
                'The configuration file to use. '
                'If not provided, it reads from "~/.config/kodo/config.toml".',
        },
        ('-db', '--db-file'): {
            'type': str,
            'default': None,
            'help':
                'The database file to use. '
                'If not provided, it reads from "~/.config/kodo/db.json".',
        },
    }
    default_config = {
        "group": "all",
        "sort": "id",
    }

    def __init__(self) -> None:
        super().__init__()
        parser = self._create_parser()
        self.args, rargs = parser.parse_known_args()
        rargs = [shlex.quote(a) if " " in a else a for a in rargs]
        self.command = " ".join(rargs).strip()
        self.command_parser = CommandParser()
        self.renderer = Renderer()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="A keyboard wielder's TODO app.")
        for option, kwargs in self.options.items():
            parser.add_argument(*option, **kwargs)
        return parser

    def _process_action(self, book: TaskBook, command: str) -> ActionResult:
        config = self.default_config
        selection, group, sort, action = self.command_parser.parse(command)
        group = group or config["group"]
        sort = sort or config["sort"]

        if not action:
            grouped_todos = book.select(selection, group, sort)  # type: ignore
            return ViewResult(
                grouped_todos, group, bool(not selection))  # type: ignore
        if selection is None:
            item = book.add(**action)  # type: ignore
            return AddResult(item)
        before_todos = book.select(selection)[None]
        after_todos = book.action(before_todos, action)
        return UpdateResult(before_todos, after_todos)

    def _render_result(self, result: ActionResult) -> str:
        if isinstance(result, ViewResult):
            return self.renderer.render(
                result.grouped_todos, result.group, result.show_all)
        elif isinstance(result, AddResult):
            return "\n" + self.renderer.render_item(result.item)
        elif isinstance(result, UpdateResult):
            text = f"\n  Updated {len(result.before_todos)} item"
            text += f"{'s' if len(result.before_todos) > 1 else ''}.\n"
            for btodo, atodo in zip(result.before_todos, result.after_todos):
                diff = self.renderer.render_item_diff(btodo, atodo)
                text += "\n  " + diff
        else:
            raise ValueError(f"Unknown result type: {type(result)}")
        return text

    def main(self) -> int:
        book = TaskBook(path=self.args.db_file or "book.json")
        result = self._process_action(book, self.command)
        print(self._render_result(result))
        # book.save()
        return 0


def main() -> None:
    sys.exit(CLI().main())


if __name__ == '__main__':
    main()
