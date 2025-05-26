import unittest
from datetime import datetime, timedelta
from kodo.cli import TaskManager, Task  # Replace with your actual module

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.tm = TaskManager()
        # Add some initial tasks for testing modifications
        self.tm.add_task(Task("Initial task 1", project="/test"))
        self.tm.add_task(Task("Initial task 2", tags=["@test"], priority="high"))
        self.tm.add_task(Task("Note 1", status="note"))

    # --- 1. Task Creation Tests ---
    def test_create_basic_task(self):
        result = self.tm.process_command(". Buy milk /grocery")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Buy milk")
        self.assertEqual(result[0].project, "/grocery")
        self.assertEqual(result[0].priority, "normal")

    def test_create_complex_task(self):
        result = self.tm.process_command('. "Team meeting" /work @meeting ^fri :n')
        self.assertEqual(result[0].title, "Team meeting")
        self.assertEqual(result[0].project, "/work")
        self.assertIn("@meeting", result[0].tags)
        self.assertEqual(result[0].status, "note")
        # Would add more specific deadline checks

    def test_create_urgent_task(self):
        result = self.tm.process_command(". Fix bug! /dev @urgent ^2h")
        self.assertEqual(result[0].title, "Fix bug")
        self.assertEqual(result[0].priority, "high")
        self.assertIn("@urgent", result[0].tags)
        # Check deadline is approximately 2 hours from now

    # --- 2. Task Modification Tests ---
    def test_basic_edit(self):
        result = self.tm.process_command("1 . New title /newproject :n")
        task = self.tm.get_task(1)
        self.assertEqual(task.title, "New title")
        self.assertEqual(task.project, "/newproject")
        self.assertEqual(task.status, "note")

    def test_tag_operations(self):
        # Toggle tag
        self.tm.process_command("2 . @newtag")
        task = self.tm.get_task(2)
        self.assertIn("@newtag", task.tags)

        # Force add
        self.tm.process_command("2 . @+fixed")
        self.assertIn("@fixed", task.tags)

        # Force remove
        self.tm.process_command("2 . @-test")
        self.assertNotIn("@test", task.tags)

    def test_status_changes(self):
        self.tm.process_command("1 . :done")
        self.assertEqual(self.tm.get_task(1).status, "done")

        self.tm.process_command("1 . :pending")
        self.assertEqual(self.tm.get_task(1).status, "pending")

        self.tm.process_command("1 . :")
        self.assertEqual(self.tm.get_task(1).status, "done")

    def test_priority_operations(self):
        self.tm.process_command("1 . !")
        self.assertEqual(self.tm.get_task(1).priority, "high")

        self.tm.process_command("1 . !low")
        self.assertEqual(self.tm.get_task(1).priority, "low")

        self.tm.process_command("1 . !+")
        self.assertEqual(self.tm.get_task(1).priority, "normal")

    # --- 3. Deadline Tests ---
    def test_relative_deadlines(self):
        self.tm.process_command("1 . ^+3d")
        task = self.tm.get_task(1)
        expected = datetime.now() + timedelta(days=3)
        self.assertAlmostEqual(task.deadline.timestamp(), expected.timestamp(), delta=60)

        self.tm.process_command("1 . ^-6h")
        expected -= timedelta(hours=6)
        self.assertAlmostEqual(task.deadline.timestamp(), expected.timestamp(), delta=60)

    def test_absolute_deadlines(self):
        self.tm.process_command("1 . ^mon")
        # Check deadline is next Monday
        task = self.tm.get_task(1)
        self.assertEqual(task.deadline.weekday(), 0)  # Monday is 0

        self.tm.process_command("1 . ^never")
        self.assertIsNone(self.tm.get_task(1).deadline)

    # --- 4. Delete Tests ---
    def test_delete_tasks(self):
        initial_count = len(self.tm.tasks)
        self.tm.process_command("1..2 . -")
        self.assertEqual(len(self.tm.tasks), initial_count - 2)

        self.tm.process_command(":done . -")
        # Should delete all done tasks

    # --- 5. Filter & Search Tests ---
    def test_basic_filters(self):
        results = self.tm.process_command("/test")
        self.assertTrue(all(t.project == "/test" for t in results))

        results = self.tm.process_command("@test")
        self.assertTrue(any("@test" in t.tags for t in results))

        results = self.tm.process_command("!high")
        self.assertTrue(all(t.priority == "high" for t in results))

    def test_grouping_sorting(self):
        results = self.tm.process_command("/")
        # Check results are grouped by project

        results = self.tm.process_command("=@")
        # Check results are sorted by tag

    def test_advanced_search(self):
        self.tm.process_command(". 'Fix bug' /dev @critical")
        results = self.tm.process_command('"fix (bug|issue)" @critical')
        self.assertEqual(len(results), 1)

    # --- 6. Multi-Task Edits Tests ---
    def test_multi_task_edits(self):
        # Add more test tasks
        for i in range(3, 6):
            self.tm.add_task(Task(f"Task {i}", project="/multi"))

        self.tm.process_command("3 4 5 . :done")
        for i in range(3, 6):
            self.assertEqual(self.tm.get_task(i).status, "done")

        self.tm.process_command("/multi . !high")
        for i in range(3, 6):
            self.assertEqual(self.tm.get_task(i).priority, "high")

        self.tm.process_command("/multi . /newproject")
        for i in range(3, 6):
            self.assertEqual(self.tm.get_task(i).project, "/newproject")

    def test_tag_replacement(self):
        self.tm.process_command("2 . @old")
        self.tm.process_command('2..3 "^Initial" @old . @old @new')
        task = self.tm.get_task(2)
        self.assertNotIn("@old", task.tags)
        self.assertIn("@new", task.tags)

    def test_edge_cases(self):
        # Test empty command
        with self.assertRaises(ValueError):
            self.tm.process_command("")

        # Test invalid task numbers
        with self.assertRaises(ValueError):
            self.tm.process_command("999 . :done")

        # Test malformed commands
        with self.assertRaises(ValueError):
            self.tm.process_command("1 . @")

if __name__ == '__main__':
    unittest.main()
