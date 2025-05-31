import os
import re
import sys
import json
import logging
from typing import Any, NoReturn, Callable, Generator, Sequence, TypeVar, List
from contextlib import contextmanager

from box import Box
from rich.logging import RichHandler
from rich.traceback import install as _rich_traceback_install
from rich.console import Console, RenderableType
from rich.panel import Panel

_rich_traceback_install()
rich_console = Console()


T = TypeVar('T')


def flatten(l: Sequence[Sequence[T]]) -> List[T]:
    return [item for sublist in l for item in sublist]


def json_dumps(obj: Any, indent=2, **kwargs) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, **kwargs)


def json_dump(obj: Any, fp: Any, indent=2, **kwargs) -> None:
    json.dump(obj, fp, ensure_ascii=False, indent=indent, **kwargs)


@contextmanager
def os_env_swap(**kwargs) -> Generator[None, None, None]:
    old_env = os.environ.copy()
    os.environ.update(kwargs)
    yield
    os.environ.update(old_env)


class Logger:
    level_symbols = {
        "debug": "[dim]◦[/dim]",
        "info": "[blue]•[/blue]",
        "warn": "[yellow]![/yellow]",
        "error": "[red]‼[/red]",
    }
    def __init__(self):
        super().__init__()
        handler = RichHandler(
            show_level=False, show_time=False, show_path=False,
            markup=True, rich_tracebacks=True)
        self.logger = logging.getLogger("rich")
        logging.basicConfig(
            level=logging.INFO, format="%(message)s", handlers=[handler])

    def is_enabled_for(self, level: int | str) -> bool:
        if isinstance(level, str):
            int_level = getattr(logging, level.upper())
        else:
            int_level = level
        return self.logger.isEnabledFor(int_level)

    def set_level(self, level: int | str) -> None:
        level = level.upper() if isinstance(level, str) else level
        self.logger.setLevel(level)

    def _format_msg(self, level: str, msg: Any) -> str:
        return f"{self.level_symbols[level]} {msg}"

    def debug(self, msg: Any, *args, **kwargs) -> None:
        msg = self._format_msg("debug", msg)
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs) -> None:
        msg = self._format_msg("info", msg)
        self.logger.info(msg, *args, **kwargs)

    def warn(self, msg: Any, *args, **kwargs) -> None:
        msg = self._format_msg("warn", msg)
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs) -> NoReturn:
        msg = self._format_msg("error", msg)
        self.logger.error(msg, *args, **kwargs)
        sys.exit(1)


logger = Logger()


def box_recursive_apply(
    value: Any, func: Callable[[Any], Any], *args, **kwargs
) -> Box:
    if isinstance(value, Box):
        return Box(
            {k: box_recursive_apply(v, func) for k, v in value.items()},
            *args, **kwargs)
    return func(value)


def format_config_value(value: int | str, config: Box) -> int | str:
    if not isinstance(value, str):
        return value
    def replace(match):
        key = match.group(1).lstrip('.')
        if key not in config:
            logger.error(f"Config key '{key}' not found.")
        return str(config[key])
    return re.sub(r"{\.([^}]+)}", replace, value)


def format_config(config: Box) -> Box:
    while True:
        format_value = lambda x: format_config_value(x, config)
        formatted = box_recursive_apply(
            config, format_value, box_dots=True)
        if formatted == config:
            return formatted
        config = formatted
