import os
import re
import sys
import logging
from typing import Any, NoReturn, Callable, Generator, Sequence, TypeVar, List
from contextlib import contextmanager

from box import Box
from rich.logging import RichHandler
from rich.traceback import install as _rich_traceback_install
from rich.console import Console

_rich_traceback_install()
rich_console = Console()


T = TypeVar('T')


def flatten(l: Sequence[Sequence[T]]) -> List[T]:
    return [item for sublist in l for item in sublist]


@contextmanager
def os_env_swap(**kwargs) -> Generator[None, None, None]:
    old_env = os.environ.copy()
    os.environ.update(kwargs)
    yield
    os.environ.update(old_env)


class Logger:
    def __init__(self):
        super().__init__()
        handler = RichHandler(
            show_level=False, show_time=False, show_path=False, rich_tracebacks=True)
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

    def debug(self, msg: Any, *args, **kwargs) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warn(self, msg: Any, *args, **kwargs) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs) -> NoReturn:
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
