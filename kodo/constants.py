MAX_TITLE_LENGTH = 20
MAX_DESCRIPTION_LENGTH = 30
DATE_FORMAT = "%-d-%b-%y"

FORMAT = {
    "all": " {id}.{status}{title}{project}{tags}{priority}{deadline}{description}",
    "project": " {id}.{status}{title}{tags}{priority}{deadline}{description}",
    "tag": " {id}.{status}{title}{project}{priority}{deadline}{description}",
    "priority": " {id}.{status}{title}{project}{tags}{deadline}{description}",
    "deadline": " {id}.{status}{title}{project}{tags}{priority}{description}",
    "created_at": " {id}.{status}{title}{project}{tags}{priority}{deadline}{description}",
}
PREFIXES = {
    'project': '/',
    'tag': '#',
    'deadline': '^',
    'id': '@',
    'priority': '!',
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
