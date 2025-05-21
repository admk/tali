import os
import sys
import yaml
import shlex
import argparse
import textwrap
import contextlib
from typing import Literal

from box import Box
from rich.console import Console
from rich_argparse import RichHelpFormatter

from . import __name__ as _NAME, __version__
from .common import format_config, set_level, debug
from .parser import CommandParser
from .book import load, save, undo, TaskBook
from .render.cli import Renderer
from .render.utils import ActionResult, ViewResult, AddResult, EditResult


class CLI:
    options = {
        ('-v', '--verbose'): {
            'action': 'store_true',
            'help': 'Enable debug output. '
        },
        ('-rc', '--rc-file'): {
            'type': str,
            'default': None,
            'help':
                'The configuration file to use. '
                'If not provided, it reads from '
                f'"$XDG_CONFIG_HOME/{_NAME}/config.toml" or '
                f'"~/.config/{_NAME}/config.toml".',
        },
        ('-u', '--undo'): {
            'action': 'store_true',
            'help': 'Undo the last run.'
        },
        ('-db', '--db-file'): {
            'type': str,
            'default': None,
            'help':
                'The database file to use. '
                'If not provided, it reads from '
                f'`config.db_file` in the configuration file or '
                f'"$XDG_DATA_HOME/{_NAME}/book.json" or '
                f'"~/.config/{_NAME}/book.json".',
        },
    }

    def __init__(self) -> None:
        super().__init__()
        parser = self._create_parser()
        self.rich_console = Console()
        self.args, rargs = parser.parse_known_args()
        if self.args.verbose:
            set_level("DEBUG")
        else:
            set_level("INFO")
        self.config = self._init_config()
        rargs = [shlex.quote(a) if " " in a else a for a in rargs]
        self.command = " ".join(rargs).strip()
        self.command_parser = CommandParser(self.config)
        self.renderer = Renderer(self.config)

    def _xdg_path(
        self, key: Literal["data", "config"]
    ) -> str:
        if key == "data":
            folder = os.environ.get("XDG_DATA_HOME", "~/.local/share")
        elif key == "config":
            folder = os.environ.get("XDG_CONFIG_HOME", "~/.config")
        else:
            raise ValueError(f"Invalid key: {key}")
        return os.path.join(folder, _NAME)

    def _db_file(self) -> str:
        db_file = self.args.db_file
        if db_file:
            return db_file
        db_file = self.config.file.db
        if db_file is not None:
            return db_file
        return os.path.join(self._xdg_path("data"), "book.json")

    def _init_config(self) -> Box:
        if self.args.rc_file:
            rc_file = self.args.rc_file
        else:
            rc_file = os.path.join(self._xdg_path("config"), "config.yaml")
        default_rc_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.yaml")
        with open(default_rc_file, "r") as f:
            config = yaml.safe_load(f)
        rc_file = rc_file if os.path.exists(rc_file) else None
        if rc_file:
            with open(rc_file, "r") as f:
                config |= yaml.safe_load(f)
        return format_config(Box(config, box_dots=True))

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="A keyboard wielder's TODO app.",
            formatter_class=RichHelpFormatter)
        for option, kwargs in self.options.items():
            parser.add_argument(*option, **kwargs)
        return parser

    def _process_action(self, book: TaskBook, command: str) -> ActionResult:
        selection, group, sort, action = self.command_parser.parse(command)
        debug(f"Selection: {selection}")
        debug(f"Group: {group}")
        debug(f"Sort: {sort}")
        debug(f"Action: {action}")
        group = group or self.config.group.by
        sort = sort or self.config.sort.by
        if not action:
            grouped_todos = book.select(selection, group, sort)  # type: ignore
            return ViewResult(
                grouped_todos, group, bool(not selection))  # type: ignore
        if selection is None:
            item = book.add(**action)  # type: ignore
            return AddResult(item)
        before_todos = book.select(selection)[None]
        after_todos = book.action(before_todos, action)
        ids = [todo.id for todo in after_todos]
        before_todos = [todo for todo in before_todos if todo.id in ids]
        return EditResult(before_todos, after_todos)

    def main(self) -> int:
        db_file = self._db_file()
        if self.args.undo:
            undo(db_file)
            return 0
        todos = load(db_file)
        book = TaskBook(self.config, todos)
        result = self._process_action(book, self.command)
        text = self.renderer.render_result(result)
        text = "\n" + textwrap.indent(text, "  ").rstrip()
        if self.config.pager.enable and isinstance(result, ViewResult):
            pager = self.rich_console.pager(styles=self.config.pager.styles)
        else:
            pager = contextlib.nullcontext()
        with pager:
            self.rich_console.print(text)
        if not isinstance(result, (AddResult, EditResult)):
            return 0
        save(self.command, book.todos, db_file, self.config.file.backup)
        return 0


def main() -> None:
    sys.exit(CLI().main())


if __name__ == '__main__':
    main()
