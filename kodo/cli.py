import re
import argparse
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Callable

from .book import TaskBook
from .render import Renderer


class TaskBookCLI:
    def __init__(self, taskbook: TaskBook):
        self.taskbook = taskbook
        self.parser = self._create_parser()
        self.command_handlers = {
            'add': self._handle_add,
            'remove': self._handle_single_arg,
            'defer': self._handle_defer,
            'note': self._handle_single_arg,
            'pending': self._handle_single_arg,
            'done': self._handle_single_arg,
            'star': self._handle_single_arg,
            'unstar': self._handle_single_arg,
        }

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description='')
        subparsers = parser.add_subparsers(dest='command', required=True)
        commands = {
            'add': self._add_parser_config(),
            'remove': self._remove_parser_config(),
            'defer': self._defer_parser_config(),
            'note': self._simple_parser_config('note'),
            'pending': self._simple_parser_config('pending'),
            'done': self._simple_parser_config('done'),
            'star': self._simple_parser_config('star'),
        }
        for cmd, config in commands.items():
            self._add_subparser(subparsers, cmd, config)

        return parser

    def _add_subparser(self, subparsers, cmd, config):
        subparser = subparsers.add_parser(
            cmd,
            aliases=config['aliases'],
            help=config['help']
        )
        for arg_spec, kwargs in config['args']:
            self._add_argument(subparser, arg_spec, kwargs)

    def _add_argument(self, subparser, arg_spec, kwargs):
        arg_names = [arg_spec] if isinstance(arg_spec, str) else arg_spec
        dest = arg_names[0].lstrip('-').replace('-', '_')
        subparser.add_argument(*arg_names, **kwargs, dest=dest)

    def _add_parser_config(self) -> Dict[str, Any]:
        return {
            'aliases': ['a'],
            'help': 'Add a task with /project, #tags, ^deadline',
            'args': [
                ('args', {
                    'nargs': '+',
                    'help': 'Task with #tags, /project, ^deadline'
                }),
            ]
        }

    def _remove_parser_config(self) -> Dict[str, Any]:
        return {
            'aliases': ['rm'],
            'help': 'Remove tasks by ID',
            'args': [
                ('ids', {
                    'nargs': '+',
                    'type': int,
                    'help': 'Task IDs to remove'
                }),
            ]
        }

    def _defer_parser_config(self) -> Dict[str, Any]:
        return {
            'aliases': ['d'],
            'help': 'Defer tasks by days',
            'args': [
                ('ids', {
                    'nargs': '+',
                    'type': int,
                    'help': 'Task IDs to defer'
                }),
                (('-d', '--days'), {
                    'type': int,
                    'default': 1,
                    'help': 'Days to defer (default: 1)'
                }),
            ]
        }

    def _simple_parser_config(self, cmd: str) -> Dict[str, Any]:
        aliases_map = {
            'done': ['c'],
            'star': ['s'],
        }
        if cmd == 'star':
            help = f'Toggle star for tasks'
        else:
            help = f'Mark tasks as {cmd}'
        return {
            'aliases': aliases_map.get(cmd, []),
            'help': help,
            'args': [
                ('ids', {
                    'nargs': '+',
                    'type': int,
                    'help': f'Task IDs to mark as {cmd}'
                }),
            ]
        }

    def _parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        if not deadline_str:
            return None
        match = re.match(r'^(\d+)([dwm])$', deadline_str)
        if not match:
            raise ValueError(f"Invalid deadline: {deadline_str}")
        amount = int(match.group(1))
        unit = match.group(2)
        days_map = {'d': 1, 'w': 7, 'm': 30}
        delta = timedelta(days=amount * days_map[unit])
        return datetime.now() + delta

    def _parse_add_args(self, args: List[str]) -> Tuple[str, Dict[str, Any]]:
        title_parts = []
        tags = []
        project = "Inbox"
        deadline = None
        for arg in args:
            if arg.startswith('#'):
                tags.append(arg[1:])
            elif arg.startswith('/'):
                project = arg[1:]
            elif arg.startswith('^'):
                deadline = self._parse_deadline(arg[1:])
            else:
                title_parts.append(arg)
        return ' '.join(title_parts), {
            'project': project,
            'tags': tags,
            'deadline': deadline,
            'status': 'pending',
            'priority': 'normal'
        }

    def _handle_add(self, args: argparse.Namespace) -> List[Any]:
        title, kwargs = self._parse_add_args(args.args)
        todo = self.taskbook.add(title=title, **kwargs)
        return [todo]

    def _handle_defer(self, args: argparse.Namespace) -> List[Any]:
        return [
            self.taskbook.defer(todo_id, days=args.days)
            for todo_id in args.ids]

    def _handle_single_arg(self, args: argparse.Namespace) -> List[Any]:
        method = getattr(self.taskbook, args.command)
        return [method(todo_id) for todo_id in args.ids]

    def run(self, args: Optional[List[str]] = None):
        parsed_args = self.parser.parse_args(args)

        try:
            handler = self._get_handler(parsed_args.command)
            if not handler:
                print(f"Unknown command: {parsed_args.command}")
                return

            results = handler(parsed_args)
            if results:
                self._print_results(parsed_args.command, results)

        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            self.taskbook.save()

    def _get_handler(self, command: str) -> Optional[Callable]:
        if command in self.command_handlers:
            return self.command_handlers[command]

        for cmd, aliases in self._get_command_aliases().items():
            if command in aliases:
                return self.command_handlers[cmd]
        return None

    def _get_command_aliases(self) -> Dict[str, List[str]]:
        return {
            cmd: self.parser._subparsers._group_actions[0]
                .choices[cmd]._aliases
            for cmd in self.command_handlers
            if hasattr(self.parser._subparsers._group_actions[0]
                      .choices[cmd], '_aliases')
        }

    def _print_results(self, command: str, results: List[Any]):
        action = command.capitalize()
        items = ", ".join(str(todo.id) for todo in results)
        print(f"{action} tasks: {items}")
