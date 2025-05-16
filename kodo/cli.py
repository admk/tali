import sys
import shlex
import argparse

from . import __version__
from .parser import CommandParser
from .book import TaskBook
from .book.select import GroupBy, SortBy
from .render.cli import Renderer


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
        self.args, self.rargs = parser.parse_known_args()
        # rc_file = args.rc_file or "~/.config/kodo/config.toml"
        self.command_parser = CommandParser()
        self.renderer = Renderer()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="A keyboard wielder's TODO app.")
        for option, kwargs in self.options.items():
            parser.add_argument(*option, **kwargs)
        return parser

    def main(self):
        book = TaskBook(path=self.args.db_file or "book.json")
        rargs = [shlex.quote(a) if " " in a else a for a in self.rargs]
        rargs = " ".join(rargs).strip()
        if rargs:
            selection, group_by, sort_by, action = \
                self.command_parser.parse(rargs)
            # print(selection, group_by, sort_by, action)
        else:
            selection = group_by = sort_by = action = None
        if not action:
            group: GroupBy = \
                group_by or self.default_config["group"]  # type: ignore
            sort: SortBy = \
                sort_by or self.default_config["sort"]  # type: ignore
            grouped_todos = book.select(selection, group, sort)
            text = self.renderer.render(
                grouped_todos, group, bool(not selection))
            print(text)
            return
        if selection is None:
            item = book.add(**action)  # type: ignore
            print("\n" + self.renderer.render_item(item))
            return
        before_todos = book.select(selection)[None]
        after_todos = book.action(before_todos, action)
        print(
            f"\n  Updated {len(before_todos)} item"
            f"{'s' if len(before_todos) > 1 else ''}.\n")
        for btodo, atodo in zip(before_todos, after_todos):
            diff = self.renderer.render_item_diff(btodo, atodo)
            print("  " + diff)


def main():
    sys.exit(CLI().main())


if __name__ == '__main__':
    main()
