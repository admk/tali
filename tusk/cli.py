import os
from os.path import basename
import re
import sys
import copy
import json
import yaml
import shlex
import argparse
import contextlib
from typing import Literal, Optional, List

from box import Box
from rich.pretty import pretty_repr
from rich.padding import Padding
from rich.console import RenderableType, Group
from rich_argparse import RichHelpFormatter

from . import __name__ as _NAME, __version__, __description__
from .common import (
    format_config, set_level, debug, warn, error, rich_console,
    os_env_swap, flatten)
from .parser import CommandParser
from .book import (
    load, save, undo, redo, history, TaskBook,
    ActionResult, ViewResult, RequiresSave)
from .render.cli import Renderer


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
        ('-db', '--db-dir'): {
            'type': str,
            'default': None,
            'help':
                f"""
                The database folder to use.
                If unspecified,
                it will search in the following order:

                1. The `.tusk/` directory located
                in the nearest ancestral folder
                relative to the current working directory.
                2. The path specified by `config.db_dir`
                    in the configuration file.
                3. `$XDG_DATA_HOME/{_NAME}/book/`.
                4. `~/.config/{_NAME}/book/`.
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
        ('-r', '--redo'): {
            'action': 'store_true',
            'help': 'Redo the last undone run.'
        },
        ('-H', '--history'): {
            'action': 'store_true',
            'help': 'Show the history of the database.'
        },
        ('-R', '--re-index'): {
            'action': 'store_true',
            'help': 'Re-index all items.'
        },
    }

    def __init__(self, args: List[str] = sys.argv) -> None:
        super().__init__()
        args = args[1:]
        parser = self._create_parser()
        options = flatten(list(self.options.keys()))
        self._text_args = " ".join(a for a in args if a in options)
        self.args = parser.parse_args(args)
        if self.args.debug:
            set_level("DEBUG")
        else:
            set_level("INFO")
        self.config = self._init_config()
        # debug(f"Resolved config: {pretty_repr(self.config.to_dict())}")
        command = []
        for a in self.args.command:
            if " " in a:
                a = shlex.quote(a)
            elif a == self.config.token.stdin and not sys.stdin.isatty():
                a = sys.stdin.read()
            command.append(a)
        self.command = " ".join(command).strip()
        debug(f"Command: {self.command!r}")
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

    def _project_root(self, name: Optional[str] = None) -> Optional[str]:
        cwd = os.getcwd()
        while True:
            path = os.path.join(cwd, ".tusk")
            if os.path.exists(path):
                return os.path.join(path, name) if name is not None else path
            cwd = os.path.dirname(cwd)
            if cwd == "/":
                break
        return None

    def _config_paths(self) -> List[str]:
        base_name = "config.yaml"
        default_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), base_name)
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
        xdg_file = os.path.join(xdg_config_home, _NAME, base_name)
        root_file = self._project_root(base_name)
        paths = [default_file, xdg_file, root_file, self.args.rc_file]
        return [p for p in paths if p is not None and os.path.exists(p)]

    def _init_config(self) -> Box:
        config: Optional[Box] = None
        for path in self._config_paths():
            with open(path, "r") as f:
                try:
                    d = yaml.safe_load(f)
                    debug(f"Loaded config from {path!r}.")
                except yaml.YAMLError as e:
                    error(f"Error parsing config file {path!r}: {e}")
            if config is None:
                config = Box(d, box_dots=True)
            else:
                config.merge_update(d)
        if config is None:
            error("No config file found.")
        return format_config(config)

    def _data_dir(self) -> str:
        xdg_data_home = os.environ.get("XDG_DATA_HOME", "~/.local/share")
        xdg_dir = os.path.join(xdg_data_home, _NAME)
        paths = [
            self.args.db_dir, self.config.file.db,
            self._project_root(), xdg_dir]
        paths = [p for p in paths if p is not None and os.path.exists(p)]
        if not paths:
            warn(
                'No database directory found. '
                f'Creating a new one at {xdg_dir!r}.')
        if len(paths) > 1:
            debug(
                'Multiple database directories found '
                f'with precedence: {paths!r}.')
        debug(f"Using database directory: {paths[0]!r}")
        return paths[0]

    def _process_action(self, book: TaskBook, command: str) -> ActionResult:
        if not command.strip():
            command = self.config.view.default or ''
        selection, group, sort, query, action = \
            self.command_parser.parse(command)
        debug(f"Selection: {selection}")
        debug(f"Group: {group}")
        debug(f"Sort: {sort}")
        debug(f"Query: {query}")
        debug(f"Action: {action}")
        group = group or self.config.view.group_by
        sort = sort or self.config.view.sort_by
        if not action:
            result = book.select(selection, group, sort)
            if query:
                result = book.query(result.flatten(), query)
            return result
        if selection is None:
            try:
                title = action.pop("title")
            except KeyError:
                error("Missing title.")
            return book.add(title, **action)  # type: ignore
        before_todos = book.select(selection).grouped_todos[None]
        if action.pop("editor", False):
            warn(f"Editor action is not supported yet.")
        return book.action(before_todos, action)

    def history_action(
        self, db_dir: str, action: Literal["undo", "redo"]
    ) -> ActionResult:
        func = undo if action == "undo" else redo
        return func(db_dir)

    def history(self, db_dir: str) -> ActionResult:
        return history(db_dir)

    def re_index(self, book: TaskBook) -> ActionResult:
        return book.re_index()

    def _print_result(self, result: ActionResult):
        if self.args.json:
            dump = json.dumps(result.to_dict(), indent=self.config.file.indent)
            rich_console.print(dump)
            return dump
        rendered = self.renderer.render_result(result)
        if isinstance(rendered, str | RenderableType):
            rendered = [rendered]
        if self.config.pager.enable and isinstance(result, ViewResult):
            pager = rich_console.pager(styles=self.config.pager.styles)
        else:
            pager = contextlib.nullcontext()
        if self.config.pager.command:
            os_env = os_env_swap(PAGER=self.config.pager.command)
        else:
            os_env = contextlib.nullcontext()
        with os_env, pager:
            rendered = Padding(Group(*rendered), (0, 0, 0, 2))
            rich_console.print(rendered, new_line_start=True)

    def main(self) -> int:
        db_dir = self._data_dir()
        if self.args.undo or self.args.redo:
            if self.args.undo and self.args.redo:
                error("Cannot use both --undo and --redo at the same time.")
            action = "undo" if self.args.undo else "redo"
            self._print_result(self.history_action(db_dir, action))
            return 0
        if self.args.history:
            self._print_result(self.history(db_dir))
            return 0
        todos = load(db_dir)
        book = TaskBook(self.config, todos)
        if self.args.re_index:
            action_result = self.re_index(book)
        else:
            action_result = self._process_action(book, self.command)
        self._print_result(action_result)
        if not isinstance(action_result, RequiresSave):
            return 0
        save(
            self.command, book.todos, action_result, db_dir,
            self.config.file.backup, self.config.file.indent)
        return 0


def main() -> None:
    sys.exit(CLI().main())


if __name__ == "__main__":
    main()
