import argparse
import contextlib
import os
import subprocess
import sys
import tempfile
from typing import List, Literal, Optional, Sequence

import yaml
from box import Box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich_argparse import RawDescriptionRichHelpFormatter

from . import __description__, __epilog__
from . import __name__ as _NAME
from . import __version__
from .book import (
    ActionResult,
    ActionValueError,
    AddResult,
    EditResult,
    QueryResult,
    RequiresSave,
    TaskBook,
    TodoItem,
    UndoRedoError,
    ViewResult,
    history,
    load,
    redo,
    save,
    undo,
)
from .common import (
    flatten,
    format_config,
    json_dumps,
    logger,
    os_env_swap,
    rich_console,
)
from .parser import CommandParser, ParserError
from .parser.editor import process_prefix_sharing_lines, strip_comments
from .render.cheatsheet import CheatSheet
from .render.cli import Renderer
from .render.common import strip_rich


class CLI:
    options = {
        ("-h", "--help"): {
            "action": "help",
            "default": argparse.SUPPRESS,
            "help": "Show this help message and exit.",
        },
        ("-v", "--version"): {
            "action": "version",
            "version": f"{_NAME} {__version__}",
            "help": "Show the version number and exit.",
        },
        ("-d", "--debug"): {
            "action": "store_true",
            "help": "Enable debug output.",
        },
        ("--color",): {
            "action": "store_true",
            "help": "Enable colored output.",
        },
        ("-c", "--cheatsheet"): {
            "action": "store_true",
            "help": "Print the cheatsheet and exit. ",
        },
        ("-rc", "--rc-file"): {
            "type": str,
            "default": None,
            "help": f"""
                The configuration file to use.
                If unspecified,
                it will search in the following order:

                1. The `config.toml` file
                   located in the nearest ancestral `.{_NAME}` folder
                   relative to the current working directory;
                2. `$XDG_CONFIG_HOME/{_NAME}/config.toml`;
                3. `~/.config/{_NAME}/config.toml`.
                """,
        },
        ("-erc", "--edit-rc"): {
            "action": "store_true",
            "help": "Launch the editor to edit the configuration file.",
        },
        ("-db", "--db-dir"): {
            "type": str,
            "default": None,
            "help": f"""
                The database folder to use.
                If unspecified,
                it will search in the following order:

                1. The `.{_NAME}/` directory
                   located in the nearest ancestral folder;
                2. The path specified by `config.db_dir`
                    in the configuration file;
                3. `$XDG_DATA_HOME/{_NAME}/book/`;
                4. `~/.config/{_NAME}/book/`.
                """,
        },
        ("-e", "--editor"): {
            "action": "store_true",
            "help": """
                Start the editor with empty content.
                This is useful for adding new items.
                """,
        },
        ("-j", "--json"): {
            "action": "store_true",
            "help": "Output the result in JSON format.",
        },
        ("-s", "--stats"): {
            "action": "store_true",
            "help": "Show statistics for the current view.",
        },
        ("--stats-count",): {
            "type": str,
            "default": None,
            "choices": ["filtered", "all"],
            "help": "Which items to count for statistics.",
        },
        ("-i", "--idempotent"): {
            "action": "store_true",
            "help": "Render output in idempotent format.",
        },
        ("-u", "--undo"): {
            "action": "store_true",
            "help": "Undo the last run.",
        },
        ("-r", "--redo"): {
            "action": "store_true",
            "help": "Redo the last undone run.",
        },
        ("-H", "--history"): {
            "action": "store_true",
            "help": "Show the history of the database.",
        },
        ("-R", "--re-index"): {
            "action": "store_true",
            "help": "Re-index all items.",
        },
    }
    epilog = __epilog__

    def __init__(self, args: List[str] = sys.argv) -> None:
        super().__init__()
        args = args[1:]
        parser = self._create_parser()
        options = flatten(list(self.options.keys()))
        self._text_args = " ".join(a for a in args if a in options)
        self.args = parser.parse_args(args)
        if self.args.debug:
            logger.set_level("debug")
        else:
            logger.set_level("info")
        logger.debug(repr(self.args))
        self.config = self._init_config()
        self.editor_command = self._init_editor_command()
        self.command = self._init_command()
        self.command_parser = CommandParser(self.config)
        self.renderer = Renderer(self.config, self.args.idempotent)

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            add_help=False,
            description=__description__,
            formatter_class=RawDescriptionRichHelpFormatter,
            epilog=self.epilog,
        )
        for option, kwargs in self.options.items():
            parser.add_argument(*option, **kwargs)
        parser.add_argument(
            "command",
            nargs="*",
            default=None,
            help="Command to run. See `--cheatsheet` for details.",
        )
        return parser

    def _project_root(self, name: Optional[str] = None) -> Optional[str]:
        cwd = os.getcwd()
        while True:
            path = os.path.join(cwd, f".{_NAME}")
            if os.path.exists(path):
                return os.path.join(path, name) if name is not None else path
            cwd = os.path.dirname(cwd)
            if cwd == "/":
                break
        return None

    def _config_paths(self) -> List[str]:
        base_name = "config.yaml"
        default_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), base_name
        )
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
                    logger.debug(f"Loaded config from {path!r}.")
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing config file {path!r}: {e}")
            if config is None:
                config = Box(d, box_dots=True)
            else:
                config.merge_update(d)
        if config is None:
            logger.error("No config file found.")
        config = format_config(config)
        logger.debug(f"Resolved config: {repr(config.to_dict())}")
        return config

    def _init_editor_command(self) -> str:
        if self.config.editor is not None:
            return self.config.editor.command
        editor = os.environ.get("EDITOR", "vim")
        return f"{editor} {{}}"

    def _init_command(self) -> str:
        command = []
        for a in self.args.command:
            if a == self.config.token.stdin and not sys.stdin.isatty():
                a = sys.stdin.read()
            command.append(a)
        command = " ".join(command).strip()
        if not command.strip():
            command = self.config.view.default
            logger.debug(f'Command (from ".view.default"): {command!r}')
        else:
            logger.debug(f"Command: {command!r}")
        return command

    def _data_dir(self) -> str:
        xdg_data_home = os.environ.get("XDG_DATA_HOME", "~/.local/share")
        xdg_dir = os.path.join(xdg_data_home, _NAME)
        paths = [
            self.args.db_dir,
            self.config.file.db,
            self._project_root(),
            xdg_dir,
        ]
        paths = [p for p in paths if p is not None and os.path.exists(p)]
        if not paths:
            logger.warn(
                f"No database directory found. Creating a new one at {xdg_dir!r}."
            )
            os.makedirs(xdg_dir, exist_ok=True)
            paths.append(xdg_dir)
        if len(paths) > 1:
            logger.debug(
                f"Multiple database directories found with precedence: {paths!r}."
            )
        logger.debug(f"Using database directory: {paths[0]!r}")
        return paths[0]

    def _process_action(
        self, book: TaskBook, command: str, nested: bool = False
    ) -> List[ActionResult]:
        try:
            parsed = self.command_parser.parse(command)
        except ParserError as e:
            logger.error(e)
        selection, group, sort, query, action = parsed
        logger.debug(f"Selection: {selection}")
        logger.debug(f"Group: {group}")
        logger.debug(f"Sort: {sort}")
        logger.debug(f"Query: {query}")
        logger.debug(f"Action: {action}")
        group = group or self.config.view.group_by
        if self.args.idempotent:
            group = "id"
        sort = sort or self.config.view.sort_by
        if not action:
            result = book.select(selection, group, sort)
            if query:
                result = book.query(result.flatten(), query)
            return [result]
        if selection is None and action != "editor":  # add new item
            try:
                title = action.pop("title")
            except KeyError:
                raise ActionValueError(
                    f"Missing title in command: {command!r}."
                )
            if "project" not in action:
                action["project"] = self.config.item.project.default
            return [book.add(title, **action)]  # type: ignore
        before_todos = book.select(selection).flatten()
        if action != "editor":
            return [book.action(before_todos, action)]
        if nested:
            logger.warn(
                "Cannot nest editor action in another editor action. "
                f"Ignoring command {command!r} "
                "that tries to launch the editor."
            )
            return []
        return self._process_editor_action(before_todos, book)

    def _process_editor_action(
        self,
        before_todos: List[TodoItem],
        book: TaskBook,
        actions: Optional[List[str]] = None,
    ) -> List[ActionResult]:
        editor_actions = self.editor_action(before_todos, actions)
        logger.debug(f"Editor commands:\n{editor_actions!r}")
        edit_result = EditResult([], [])
        add_result = AddResult([])
        error = []
        for action in editor_actions:
            try:
                results = self._process_action(book, action, True)
            except Exception as e:
                if logger.is_enabled_for("debug"):
                    raise e
                logger.warn(f'Failed to process action: "{action}"\n  {e!r}')
                error.append(action)
                continue
            for result in results:
                if isinstance(result, EditResult):
                    edit_result.before.extend(result.before)
                    edit_result.after.extend(result.after)
                if isinstance(result, AddResult):
                    add_result.items.extend(result.items)
        results = []
        if edit_result.before or edit_result.after:
            results.append(edit_result)
        if add_result.items:
            results.append(add_result)
        if error:
            ans = logger.ask(
                "Do you want to continue editing failed actions?", ["Y", "n"]
            )
            if ans == "n":
                return results
            results = self._process_editor_action([], book, error)
        return results

    def _edit_file(self, path: str) -> None:
        if not self.editor_command:
            logger.error(
                "No editor command configured. "
                "Please set `editor.command` in the configuration file."
            )
        try:
            subprocess.run(
                f"{self.editor_command.format(path)}", shell=True, check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to edit file: {e!r}")

    def editor_action(
        self, todos: List[TodoItem], actions: Optional[List[str]] = None
    ) -> List[str]:
        text = self.renderer.render({None: todos}, "id", idempotent=True)
        text = strip_rich(text).rstrip()
        with tempfile.NamedTemporaryFile(
            suffix=f".{_NAME}", mode="w+", delete=False
        ) as temp_file:
            if text:
                temp_file.write(text + "\n")
            if actions:
                temp_file.write("\n".join(actions) + "\n")
            temp_file.flush()
            temp_path = temp_file.name
        self._edit_file(temp_path)
        with open(temp_path, "r") as temp_file:
            edited = temp_file.read().strip().rstrip("\n")
        edited = strip_comments(edited.splitlines())
        edited = process_prefix_sharing_lines(edited)
        os.unlink(temp_path)
        before = [b.strip() for b in text.strip().rstrip("\n").splitlines()]
        edited = [e.strip() for e in edited if e.strip()]
        return [e for e in edited if e not in before]

    def history_action(
        self, db_dir: str, action: Literal["undo", "redo"]
    ) -> ActionResult:
        if not self.config.file.backup:
            logger.error(
                "History is disabled. Please set `file.backup` to `true`."
            )
        func = undo if action == "undo" else redo
        try:
            return func(db_dir)
        except UndoRedoError as e:
            logger.error(e)

    def history(self, db_dir: str) -> ActionResult:
        return history(db_dir)

    def re_index(self, book: TaskBook) -> ActionResult:
        return book.re_index()

    def _render_stats(
        self, book: TaskBook, result: ViewResult
    ) -> Optional[RenderableType]:
        if self.args.json or self.args.idempotent:
            return
        render_stats = False
        enable = self.config.view.stats.enable
        if enable == "always":
            render_stats = True
        if enable == "default" and not self.args.command:
            render_stats = True
        if enable == "all" and result.is_all:
            render_stats = True
        if self.args.stats:
            render_stats = True
        if not render_stats:
            return
        todos = result.flatten()
        if self.args.idempotent or not todos:
            return
        stats = self.renderer.render_stats(todos, list(book.todos.values()))
        return Padding(stats, (1, 0, 0, 2), expand=False)

    def _render_results(
        self, results: List[ActionResult]
    ) -> List[RenderableType]:
        if self.args.json:
            dump = json_dumps(
                [r.to_dict() for r in results], indent=self.config.file.indent
            )
            return [dump]
        rendered: List[RenderableType] = [""]
        for r in results:
            rr = self.renderer.render_result(r)
            rr = [rr] if isinstance(rr, RenderableType) else rr
            if not isinstance(r, QueryResult):
                rr = [Padding(r, (0, 2), expand=False) for r in rr]
            rendered += rr
        return rendered

    def _print_rendered(self, rendered: Sequence[RenderableType]) -> None:
        if self.config.pager.enable:
            pager = rich_console.pager(styles=self.config.pager.styles)
        else:
            pager = contextlib.nullcontext()
        if self.config.pager.command:
            os_env = os_env_swap(PAGER=self.config.pager.command)
        else:
            os_env = contextlib.nullcontext()
        with os_env, pager:
            rich_console.print(Group(*rendered), soft_wrap=True)

    def _print_results(self, results: List[ActionResult]) -> None:
        self._print_rendered(self._render_results(results))

    def main(self) -> int:
        db_dir = self._data_dir()
        if self.args.cheatsheet:
            self._print_rendered(CheatSheet(self.config).render())
            return 0
        if self.args.edit_rc:
            config_path = self._config_paths()[-1]
            self._edit_file(config_path)
        if self.args.undo or self.args.redo:
            if self.args.undo and self.args.redo:
                logger.error(
                    "Cannot use both --undo and --redo at the same time."
                )
            action = "undo" if self.args.undo else "redo"
            self._print_results([self.history_action(db_dir, action)])
            return 0
        if self.args.history:
            self._print_results([self.history(db_dir)])
            return 0
        todos = load(db_dir)
        book = TaskBook(self.config, todos)
        if self.args.re_index:
            action_results = [self.re_index(book)]
        elif self.args.editor:
            action_results = self._process_editor_action([], book)
        else:
            action_results = self._process_action(book, self.command)
        rendered = self._render_results(action_results)
        if not action_results:
            self._print_rendered(["No action taken."])
            return 0
        fr = action_results[-1]
        if isinstance(fr, ViewResult):
            stats = self._render_stats(book, fr)
            if stats:
                rendered.append(stats)
        self._print_rendered(rendered)
        if all(not isinstance(ar, RequiresSave) for ar in action_results):
            return 0
        save(
            self.command,
            list(book.todos.values()),
            action_results,
            db_dir,
            self.config.file.backup,
            self.config.file.indent,
        )
        return 0


def main() -> None:
    sys.exit(CLI().main())


if __name__ == "__main__":
    main()
