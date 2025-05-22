import re
import sys
import logging
from typing import Any, NoReturn, Callable, Dict

from box import Box
from rich.logging import RichHandler
from rich.traceback import install

install()


def strip_rich(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\[/.*?\]", "", text)
    return text


_handler = RichHandler(show_time=False, show_path=False, rich_tracebacks=True)
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[_handler])
log = logging.getLogger("rich")


def set_level(level: int | str) -> None:
    log.setLevel(level)


def debug(msg: Any, *args, **kwargs) -> None:
    log.debug(msg, *args, **kwargs)


def info(msg: Any, *args, **kwargs) -> None:
    log.info(msg, *args, **kwargs)


def warn(msg: Any, *args, **kwargs) -> None:
    log.warning(msg, *args, **kwargs)


def error(msg: Any, *args, **kwargs) -> NoReturn:
    log.error(msg, *args, **kwargs)
    sys.exit(1)


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
            error(f"Config key '{key}' not found.")
        return str(config[key])
    return re.sub(r"{\.([^}]+)}", replace, value)


def format_config(config: Dict[str, Any]) -> Box:
    box_config: Box = Box(config, box_dots=True)
    while True:
        format_value = lambda x: format_config_value(x, box_config)
        formatted = box_recursive_apply(
            box_config, format_value, box_dots=True)
        if formatted == box_config:
            return formatted
        box_config = formatted
