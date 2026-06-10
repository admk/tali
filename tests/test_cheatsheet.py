import os
import unittest

import yaml
from box import Box

from tali import __toolname__ as _NAME
from tali.cli import CLI
from tali.common import format_config
from tali.render.cheatsheet import AgentCheatSheet


def load_config():
    root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(root, "..", _NAME, "config.yaml")
    with open(config_path, "r") as f:
        config = Box(yaml.safe_load(f), box_dots=True)
    return format_config(config)


class TestAgentCheatSheet(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_render_includes_agent_workflow(self):
        text = AgentCheatSheet(self.config).render()[0]

        self.assertIn("# Tali Agent Cheatsheet", text)
        self.assertIn("## Agent Workflow", text)
        self.assertIn("## Placeholders", text)
        self.assertIn("| Name | Meaning |", text)
        self.assertIn("`tali -i`", text)
        self.assertIn("| `<selection>` | Expression before the separator", text)
        self.assertIn("| `<action>` | Expression after the separator", text)
        self.assertIn("| `<field>` | Query target after `?`", text)
        self.assertIn("| `tali <selection> . <action>` |", text)
        self.assertIn("`tali 1 . @tag`: Toggle tag", text)
        self.assertIn("| `??` | `title` |", text)
        self.assertIn("| `?_` | `parent` |", text)
        self.assertIn("## Item Nesting", text)
        self.assertIn("| `_` | parent | Parent item for nesting | `_3` |", text)
        self.assertIn("`tali . Write tests _1`", text)
        self.assertIn("`tali 2 . _0`", text)
        self.assertIn("`tali 2 ?_`", text)
        self.assertIn("In editor mode, an indented line", text)
        self.assertIn("Plain indented lines still share prefixes", text)
        self.assertIn("## Date Expressions", text)
        self.assertIn("Date-only forms resolve to end-of-day.", text)
        self.assertIn(
            "| `,` | status | Status. Values: pending (p), done (d/c), "
            "note (n), delete (x), archive (a); bare token toggles "
            "pending/done | `,pending` |",
            text,
        )
        self.assertIn(
            "| `!` | priority | Priority. Values: high (h), normal (n), "
            "low (l); action shorthands: !, !+, !- | `!high` |",
            text,
        )
        self.assertIn(
            "| `^` | deadline | Deadline date expression: named, absolute, "
            "time-only, end, or relative; oo clears in actions | `^today` |",
            text,
        )
        self.assertIn(
            "| `+` | or | OR between selection clauses | `/work + /home` |",
            text,
        )
        self.assertIn(
            "| `~` | not | Negate the next selection filter | `~@waiting` |",
            text,
        )
        self.assertIn(
            "| `(` | group open | Opens a selection expression | "
            "`(/work + /home` |",
            text,
        )
        self.assertIn(
            "| `)` | group close | Closes a selection expression | "
            "`/home) @urgent` |",
            text,
        )
        self.assertIn(
            "`tali (/work + /home) @urgent`: Filter @urgent tasks in "
            "/work or /home",
            text,
        )
        self.assertIn("## Settable Token Values", text)
        self.assertIn(
            "| `,` status | `pending`, `done`, `note`, `archive`, `delete` |",
            text,
        )
        self.assertIn(
            "Default aliases: `p`, `d`/`c`, `n`, `a`, `x`.",
            text,
        )
        self.assertIn(
            "| `!` priority | `high`, `normal`, `low` |",
            text,
        )
        self.assertIn("Default aliases: `h`, `n`, `l`.", text)
        self.assertIn(
            "| `^` deadline | Date Expressions values such as `today`, "
            "`tomorrow`, `feb 21`, `10am`, `mon`, `+3d`, `-1w`, "
            "`+M1d` |",
            text,
        )
        self.assertIn(
            "| Relative | Action offset from item deadline, or now if absent",
            text,
        )
        self.assertIn("`+3d`, `-1w`, `+M1d`", text)
        self.assertIn("`tali . Meeting /work ^'tue 4pm' ,n`", text)

    def test_render_uses_configured_boolean_tokens(self):
        self.config.token["or"] = "OR"
        self.config.token["not"] = "NO"
        self.config.token.open_paren = "["
        self.config.token.close_paren = "]"

        text = AgentCheatSheet(self.config).render()[0]

        self.assertIn(
            "| `OR` | or | OR between selection clauses | `/work OR /home` |",
            text,
        )
        self.assertIn(
            "| `NO` | not | Negate the next selection filter | `NO@waiting` |",
            text,
        )
        self.assertIn(
            "`tali [/work OR /home] @urgent`: Filter @urgent tasks in "
            "/work or /home",
            text,
        )
        self.assertIn(
            "`tali /work NO@waiting`: Filter /work tasks without @waiting",
            text,
        )

    def test_cli_flag_prints_agent_cheatsheet(self):
        cli = CLI(["tali", "--agent-cheatsheet"])
        printed = []

        cli._data_dir = lambda: "."
        cli._print_rendered = lambda rendered: printed.extend(rendered)

        self.assertEqual(cli.main(), 0)
        self.assertEqual(len(printed), 1)
        self.assertIn("# Tali Agent Cheatsheet", printed[0])
