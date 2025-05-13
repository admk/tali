TOKENS = {
    'separator': '.',
    'range': '..',
    'project': '/',
    'tag': '@',
    'deadline': '^',
    'priority': '!',
    'status': ':',
    'sort': '=',
    'delete': '--',
}

common_format = \
    " {id}.{status}{title}{project}{tags}{priority}{deadline}{description}"
FORMAT = {
    "all": common_format,
    "project": common_format.replace("{project}", ""),
    "tag": common_format.replace("{tags}", ""),
    "priority": common_format.replace("{priority}", ""),
    "deadline": common_format.replace("{deadline}", ""),
    "created_at": common_format,
}
ID_ATTRS = {"color": "grey"}
TITLE_ATTRS = {
    "priority.low": {"color": "grey"},
    "priority.high": {"color": "magenta", "attrs": ["bold"]},
    "status.done": {"color": "grey", "attrs": ["strike"]},
}
PROJECT_ATTRS = {"attrs": ["bold"]}
DESCRIPTION_ATTRS = {"color": "grey", "attrs": ["italic"]}
GROUP_PROGRESS_ATTRS = {"color": "grey"}
GROUP_ATTRS = {"attrs": ["bold"]}
PRIORITY_SYMBOLS = {
    "high": "!",
    "normal": None,
    "low": None,
}
PRIORITY_ATTRS = {
    "high": {"color": "magenta", "attrs": ["bold"]},
    "normal": {"color": None},
    "low": {"color": "grey"},
}
PRIORITY_FORMATTED = {
    "high": f"{PRIORITY_SYMBOLS['high']} high",
    "normal": f"{PRIORITY_SYMBOLS['normal'] or '.'} normal",
    "low": f"{PRIORITY_SYMBOLS['low'] or '_'} low",
}
STATUS_SYMBOLS = {
    "note": "·",
    "pending": "☐",
    "done": "✔",
}
STATUS_ATTRS = {
    "note": {"color": "blue", "attrs": ["bold"]},
    "pending": {"color": "yellow", "attrs": ["bold"]},
    "done": {"color": "green", "attrs": ["bold"]},
}
STATUS_FORMATTED = {k: f"{v} {k}" for k, v in STATUS_SYMBOLS.items()}
TAG_SYMBOLS = {
    "star": "★",
}
TAG_ATTRS = {
    "_default": {"attrs": ["underline"]},
    "star": {"color": "yellow"},
}
DEADLINE_ATTRS = {
    "_inactive": {"color": "grey"},
    "_default": {"color": "blue"},
    2592000: {"color": "green"},
    604800: {"color": "cyan"},
    86400: {"color": "magenta"},
    3600: {"color": "yellow"},
    0: {"color": "red"},
}
PROGRESS_ATTRS = {
    "_default": {"color": "green", "attrs": ["bold"]},
    0.9: {"color": "cyan", "attrs": ["bold"]},
    0.75: {"color": "blue", "attrs": ["bold"]},
    0.5: {"color": "magenta", "attrs": ["bold"]},
    0.25: {"color": "yellow", "attrs": ["bold"]},
    0: {"color": "red", "attrs": ["bold"]},
}

SECONDS = {
    "y": 31536000,
    'M': 2592000,
    'w': 604800,
    'd': 86400,
    'h': 3600,
    'm': 60,
    's': 1,
}
MAX_TITLE_LENGTH = 20
MAX_DESCRIPTION_LENGTH = 30
DATE_FORMAT = "%y-%b-%-d"
