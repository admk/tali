import os
import unittest

import yaml
from box import Box

from tali import __toolname__ as _NAME
from tali.book import ActionValueError, TaskBook, TodoItem
from tali.common import format_config
from tali.render.cli import Renderer
from tali.render.common import strip_rich


def load_config():
    root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(root, "..", _NAME, "config.yaml")
    with open(config_path, "r") as f:
        config = Box(yaml.safe_load(f), box_dots=True)
    return format_config(config)


class TestSubItems(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def _book(self, items):
        return TaskBook(self.config, items)

    def test_add_child_inherits_parent_project(self):
        parent = TodoItem(1, "Parent", project="work")
        book = self._book([parent])

        result = book.add("Child", parent=1)

        child = result.items[0]
        self.assertEqual(child.parent, 1)
        self.assertEqual(child.project, "work")
        self.assertEqual(book.todos[2].parent, 1)

    def test_add_child_rejects_conflicting_project(self):
        parent = TodoItem(1, "Parent", project="work")
        book = self._book([parent])

        with self.assertRaisesRegex(ActionValueError, "project"):
            book.add("Child", parent=1, project="home")

    def test_reparent_clear_and_cycle_validation(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        book = self._book([parent, child])

        book.action([child], {"parent": 0})
        self.assertIsNone(book.todos[2].parent)
        self.assertEqual(book.todos[2].project, "work")

        with self.assertRaisesRegex(ActionValueError, "non-existing"):
            book.action([child], {"parent": 99})
        with self.assertRaisesRegex(ActionValueError, "own parent"):
            book.action([parent], {"parent": 1})

        book.todos[2].parent = 1
        with self.assertRaisesRegex(ActionValueError, "cycle"):
            book.action([parent], {"parent": 2})

    def test_project_edit_only_root_and_cascades(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])

        book.action([parent], {"project": "home"})

        self.assertEqual(book.todos[1].project, "home")
        self.assertEqual(book.todos[2].project, "home")
        self.assertEqual(book.todos[3].project, "home")

        with self.assertRaisesRegex(ActionValueError, "child item"):
            book.action([book.todos[2]], {"project": "other"})

    def test_non_delete_status_does_not_mutate_descendants(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])

        book.action([parent], {"status": "done"})

        self.assertEqual(book.todos[1].status, "done")
        self.assertEqual(book.todos[2].status, "pending")
        self.assertEqual(book.todos[3].status, "pending")

    def test_status_selection_uses_effective_descendant_status(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])

        book.action([parent], {"status": "done"})

        pending = book.select({"status": "pending"}).flatten()
        done = book.select({"status": "done"}).flatten()

        self.assertEqual([todo.id for todo in pending], [])
        self.assertEqual([todo.id for todo in done], [1, 2, 3])

    def test_group_by_status_uses_effective_descendant_status(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])

        book.action([parent], {"status": "done"})

        groups = book.select(None, group_by="status").grouped_todos

        self.assertNotIn("pending", groups)
        self.assertEqual([todo.id for todo in groups["done"]], [1, 2, 3])

    def test_delete_status_cascades_to_subtree(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        sibling = TodoItem(4, "Sibling", project="work")
        book = self._book([parent, child, grandchild, sibling])

        result = book.action([parent], {"status": "delete"})

        self.assertEqual([todo.id for todo in result.after], [1, 2, 3])
        self.assertEqual(book.todos[1].status, "delete")
        self.assertEqual(book.todos[2].status, "delete")
        self.assertEqual(book.todos[3].status, "delete")
        self.assertEqual(book.todos[4].status, "pending")

    def test_selection_expands_matched_parent_descendants(self):
        parent = TodoItem(1, "Match", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        other = TodoItem(4, "Other", project="work")
        book = self._book([parent, child, grandchild, other])

        result = book.select({"title": "Match"}).flatten()
        strict = book.select(
            {"title": "Match"},
            include_descendants=False,
        ).flatten()
        top_level = book.select({"parent": 0}).flatten()
        direct_children = book.select({"parent": 1}).flatten()

        self.assertEqual([todo.id for todo in result], [1, 2, 3])
        self.assertEqual([todo.id for todo in strict], [1])
        self.assertEqual([todo.id for todo in top_level], [1, 4])
        self.assertEqual([todo.id for todo in direct_children], [2])

    def test_tag_selection_matches_parent_tags_on_subitems(self):
        parent = TodoItem(79, "Parent", project="work", tags=["feat"])
        child = TodoItem(80, "Child", project="work", parent=79)
        grandchild = TodoItem(81, "Grandchild", project="work", parent=80)
        other = TodoItem(82, "Other", project="work")
        book = self._book([parent, child, grandchild, other])

        tagged_tree = book.select({"tags": ["feat"]}).flatten()
        child_by_tag_and_id = book.select(
            {"tags": ["feat"], "id": [80]}
        ).flatten()
        strict_child_by_tag_and_id = book.select(
            {"tags": ["feat"], "id": [80]},
            include_descendants=False,
        ).flatten()
        untagged = book.select({"tags": []}).flatten()

        self.assertEqual([todo.id for todo in tagged_tree], [79, 80, 81])
        self.assertEqual([todo.id for todo in child_by_tag_and_id], [80, 81])
        self.assertEqual(
            [todo.id for todo in strict_child_by_tag_and_id],
            [80],
        )
        self.assertEqual([todo.id for todo in untagged], [82])
        self.assertEqual(child.tags, [])

    def test_group_by_tag_uses_parent_tags_for_subitems(self):
        parent = TodoItem(79, "Parent", project="work", tags=["feat"])
        child = TodoItem(80, "Child", project="work", parent=79)
        other = TodoItem(81, "Other", project="work")
        book = self._book([parent, child, other])

        groups = book.select(None, group_by="tag").grouped_todos

        self.assertEqual([todo.id for todo in groups["feat"]], [79, 80])
        self.assertEqual([todo.id for todo in groups["_untagged"]], [81])

    def test_render_tree_uses_effective_status_only_for_human_output(self):
        parent = TodoItem(1, "Parent", project="work", status="done")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        renderer = Renderer(self.config)

        human = strip_rich(
            renderer.render({None: [parent, child, grandchild]}, "id")
        )
        idempotent = strip_rich(
            renderer.render(
                {None: [parent, child, grandchild]},
                "id",
                idempotent=True,
            )
        )

        human_lines = human.splitlines()
        idempotent_lines = idempotent.splitlines()
        self.assertIn("✔", human_lines[0])
        self.assertTrue(human_lines[1].startswith("  "))
        self.assertIn("✔", human_lines[1])
        self.assertTrue(human_lines[2].startswith("    "))
        self.assertIn("✔", human_lines[2])
        self.assertEqual(child.status, "pending")
        self.assertFalse(idempotent_lines[1].startswith("  "))
        self.assertIn(",pending", idempotent_lines[1])
        self.assertFalse(idempotent_lines[2].startswith("  "))
        self.assertIn(",pending", idempotent_lines[2])

    def test_render_uses_effective_status_when_parent_is_hidden(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])
        renderer = Renderer(self.config)

        book.action([parent], {"status": "done"})
        result = book.select({"id": [3]})
        text = strip_rich(renderer.render_result(result))

        self.assertIn("✔", text)
        self.assertIn("Grandchild", text)

    def test_stats_use_effective_status(self):
        parent = TodoItem(1, "Parent", project="work")
        child = TodoItem(2, "Child", project="work", parent=1)
        grandchild = TodoItem(3, "Grandchild", project="work", parent=2)
        book = self._book([parent, child, grandchild])
        renderer = Renderer(self.config)

        book.action([parent], {"status": "done"})
        book.select(None)
        text = strip_rich(
            renderer.render_stats(
                list(book.todos.values()),
                list(book.todos.values()),
            )
        )

        self.assertIn("0 pending", text)
        self.assertIn("3 done", text)

    def test_render_orphaned_filtered_child_as_top_level(self):
        child = TodoItem(2, "Child", project="work", parent=1)
        renderer = Renderer(self.config)

        text = strip_rich(renderer.render({None: [child]}, "id"))

        self.assertTrue(text.startswith("   2."))
        self.assertIn("_1", text)
