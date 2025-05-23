import os
import sys
import copy
import json
import yaml
import shlex
import argparse
import textwrap
import contextlib
from typing import Literal, List
from datetime import datetime

from box import Box
from rich.box import SIMPLE_HEAVY
from rich.panel import Panel
from rich.pretty import pretty_repr
from rich.console import Console
from rich_argparse import RichHelpFormatter

from . import __name__ as _NAME, __version__, __description__
from .common import (
    format_config, set_level, debug, warn, error, os_env_swap, flatten)
from .parser import CommandParser
from .book import load, save, undo, history, TaskBook
from .render.cli import Renderer
from .render.utils import (
    timedelta_format, ActionResult, ViewResult, AddResult, EditResult)


class CLI:
    options = {
        ('-v', '--version'): {
            'action': 'version',
            'version': f"{_NAME} {__version__}",
            'help': 'Show the version number and exit.'
        },
        ('-d', '--debug'): {
            'action': 'store_true',
            'help': 'Enable debug output. '
        },
        ('-rc', '--rc-file'): {
            'type': str,
            'default': None,
            'help':
                f"""
                The configuration file to use.
                If not provided, it reads from
                `$XDG_CONFIG_HOME/{_NAME}/config.toml` or
                `~/.config/{_NAME}/config.toml`.
                """
        },
        ('-db', '--db-path'): {
            'type': str,
            'default': None,
            'help':
                f"""
                The database to use.
                If unspecified,
                it will search in the following order:

                1. The `.tusk` directory located
                in the nearest ancestral folder
                relative to the current working directory.
                2. The path specified by `config.db_path`
                    in the configuration file.
                3. `$XDG_DATA_HOME/{_NAME}/book.json`.
                4. `~/.config/{_NAME}/book.json`.
                """,
        },
        ('-j', '--json'): {
            'action': 'store_true',
            'help': 'Output the result in JSON format. '
        },
        ('-u', '--undo'): {
            'action': 'store_true',
            'help': 'Undo the last run.'
        },
        ('-H', '--history'): {
            'action': 'store_true',
            'help': 'Show the history of the database.'
        },
        ('-r', '--re-index'): {
            'action': 'store_true',
            'help': 'Re-index all items.'
        },
    }

    def __init__(self, args: List[str] = sys.argv) -> None:
        super().__init__()
        args = args[1:]
        parser = self._create_parser()
        self.rich_console = Console()
        options = flatten(list(self.options.keys()))
        self._text_args = " ".join(a for a in args if a in options)
        self.args = parser.parse_args(args)
        if self.args.debug:
            set_level("DEBUG")
        else:
            set_level("INFO")
        self.config = self._init_config()
        debug("Config:")
        debug(pretty_repr(self.config.to_dict()))
        command = [shlex.quote(a) if " " in a else a for a in self.args.command]
        self.command = " ".join(command).strip()
        self.command_parser = CommandParser(self.config)
        self.renderer = Renderer(self.config)

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=__description__,
            formatter_class=RichHelpFormatter)
        for option, kwargs in self.options.items():
            parser.add_argument(*option, **kwargs)
        parser.add_argument(
            'command', nargs=argparse.REMAINDER,
            default=None, help='Command to run.')
        return parser

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

    def _db_path(self) -> str:
        db_path = self.args.db_path
        if db_path:
            return db_path
        cwd = os.getcwd()
        while True:
            db_path = os.path.join(cwd, ".tusk")
            if os.path.exists(db_path):
                return db_path
            cwd = os.path.dirname(cwd)
            if cwd == "/":
                break
        if self.config.file.db is not None:
            return db_path
        return os.path.join(self._xdg_path("data"), "book")

    def _init_config(self) -> Box:
        if self.args.rc_file:
            rc_file = self.args.rc_file
        else:
            rc_file = os.path.join(self._xdg_path("config"), "config.yaml")
        default_rc_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.yaml")
        with open(default_rc_file, "r") as f:
            config = Box(yaml.safe_load(f), box_dots=True)
        rc_file = rc_file if os.path.exists(rc_file) else None
        if rc_file:
            with open(rc_file, "r") as f:
                config.merge_update(yaml.safe_load(f))
        return format_config(config)

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
            try:
                title = action.pop("title")
            except KeyError:
                error("Missing title.")
            item = book.add(title, **action)  # type: ignore
            return AddResult(item)
        before_todos = book.select(selection)[None]
        after_todos = book.action(before_todos, action)
        ids = [todo.id for todo in after_todos]
        before_todos = [todo for todo in before_todos if todo.id in ids]
        return EditResult(before_todos, after_todos)

    def undo(self, db_path: str) -> int:
        message = undo(db_path)
        command, _, *updates = message.splitlines()
        text = self.config.message.undo.format(command)
        text = "\n" + textwrap.indent(text, "  ")
        self.rich_console.print(text)
        updates = textwrap.dedent("\n".join(updates))
        self.rich_console.print(Panel.fit(updates))
        return 0

    def history(self, db_path: str) -> int:
        from rich.table import Table
        table = Table(box=SIMPLE_HEAVY)
        table.add_column("Time", justify="right")
        table.add_column("Commit")
        for item in history(db_path):
            dt = item["ts"].replace(tzinfo=None)  # type: ignore
            dt = timedelta_format(datetime.now() - dt, num_components=1)
            message = item["message"].splitlines()[0]  # type: ignore
            table.add_row(dt, message)
        self.rich_console.print(table)
        return 0

    def re_index(self, book: TaskBook) -> EditResult:
        old_todos = copy.deepcopy(book.todos)
        book.re_index()
        return EditResult(old_todos, book.todos)

    def main(self) -> int:
        db_path = self._db_path()
        if self.args.undo:
            return self.undo(db_path)
        if self.args.history:
            return self.history(db_path)
        todos = load(db_path)
        book = TaskBook(self.config, todos)
        if self.args.re_index:
            result = self.re_index(book)
        else:
            result = self._process_action(book, self.command)
        if self.args.json:
            print(json.dumps(result.to_dict()))
            return 0
        text = self.renderer.render_result(result)
        text = "\n" + textwrap.indent(text, "  ").rstrip()
        if self.config.pager.enable and isinstance(result, ViewResult):
            pager = self.rich_console.pager(styles=self.config.pager.styles)
        else:
            pager = contextlib.nullcontext()
        if self.config.pager.command:
            os_env = os_env_swap(PAGER=self.config.pager.command)
        else:
            os_env = contextlib.nullcontext()
        with os_env, pager:
            self.rich_console.print(text)
        if not isinstance(result, (AddResult, EditResult)):
            return 0
        message = [self.command, text]
        if self._text_args:
            args = f"\n  [bright_black]args: {self._text_args}[/bright_black]"
            message.append(args)
        save("\n".join(message), book.todos, db_path, self.config.file.backup)
        return 0


def main() -> None:
    sys.exit(CLI().main())


if __name__ == "__main__":
    main()
