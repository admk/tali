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
        self.assertIn("## Date Expressions", text)
        self.assertIn("Date-only forms resolve to end-of-day.", text)
        self.assertIn(
            "| Relative | Action offset from item deadline, or now if absent",
            text,
        )
        self.assertIn("`+3d`, `-1w`, `+M1d`", text)
        self.assertIn("`tali . Meeting /work ^'tue 4pm' ,n`", text)

    def test_cli_flag_prints_agent_cheatsheet(self):
        cli = CLI(["tali", "--agent-cheatsheet"])
        printed = []

        cli._data_dir = lambda: "."
        cli._print_rendered = lambda rendered: printed.extend(rendered)

        self.assertEqual(cli.main(), 0)
        self.assertEqual(len(printed), 1)
        self.assertIn("# Tali Agent Cheatsheet", printed[0])
