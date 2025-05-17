import sys
import logging
from typing import Any, NoReturn

from rich.logging import RichHandler
from rich.traceback import install


_handler = RichHandler(show_time=False, show_path=False, rich_tracebacks=True)
logging.basicConfig(
    level="NOTSET", format="%(message)s",
    handlers=[_handler])
log = logging.getLogger("rich")

install()

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
