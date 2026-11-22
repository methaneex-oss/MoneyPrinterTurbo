import tempfile
import unittest
from pathlib import Path

from app.models import const
from app.services.state import FileState


class TestFileState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state = FileState(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_state_survives_a_new_backend_instance(self):
        self.state.update_task(
            "task-1",
            state=const.TASK_STATE_PROCESSING,
            progress=45,
            video_subject="A durable task",
            videos=["finished-part.mp4"],
        )

        reopened = FileState(self.temp_dir.name)
        task = reopened.get_task("task-1")

        self.assertEqual(task["progress"], 45)
        self.assertEqual(task["video_subject"], "A durable task")
        self.assertEqual(task["videos"], ["finished-part.mp4"])

    def test_updates_preserve_fields_and_patch_does_not_create_tasks(self):
        self.state.update_task("task-1", progress=20, videos=["one.mp4"])
        self.assertTrue(self.state.patch_task("task-1", warnings=["audio skipped"]))
        self.assertFalse(self.state.patch_task("missing", progress=1))

        task = self.state.get_task("task-1")
        self.assertEqual(task["videos"], ["one.mp4"])
        self.assertEqual(task["warnings"], ["audio skipped"])

    def test_pagination_is_stable_and_returns_isolated_snapshots(self):
        for task_id in ("task-c", "task-a", "task-b"):
            self.state.update_task(task_id, progress=10, videos=[])

        first_page, total = self.state.get_all_tasks(page=1, page_size=2)
        self.assertEqual(total, 3)
        self.assertEqual([task["task_id"] for task in first_page], ["task-a", "task-b"])
        first_page[0]["videos"].append("mutated.mp4")
        self.assertEqual(self.state.get_task("task-a")["videos"], [])

    def test_startup_recovery_marks_only_interrupted_processing_tasks(self):
        self.state.update_task("running", state=const.TASK_STATE_PROCESSING, progress=55)
        self.state.update_task("complete", state=const.TASK_STATE_COMPLETE, progress=100)

        reopened = FileState(self.temp_dir.name)
        recovered = reopened.recover_interrupted_tasks()

        self.assertEqual(recovered, 1)
        interrupted = reopened.get_task("running")
        self.assertEqual(interrupted["state"], const.TASK_STATE_FAILED)
        self.assertEqual(interrupted["failed_stage"], "interrupted")
        self.assertIn("generation was interrupted", interrupted["error"])
        self.assertEqual(reopened.get_task("complete")["state"], const.TASK_STATE_COMPLETE)

    def test_task_ids_are_not_used_as_file_paths(self):
        self.state.update_task("../../outside", progress=1)
        self.assertEqual(self.state.get_task("../../outside")["task_id"], "../../outside")
        self.assertEqual(len(list(Path(self.temp_dir.name).glob("*.json")) ), 1)


    def test_corrupt_record_does_not_break_other_task_discovery(self):
        self.state.update_task("healthy", progress=10)
        self.state._path("corrupt-id").write_text(
            "{not valid json", encoding="utf-8"
        )

        self.assertIsNone(self.state.get_task("corrupt-id"))
        self.assertEqual(self.state.list_task_ids(), ["healthy"])


if __name__ == "__main__":
    unittest.main()
