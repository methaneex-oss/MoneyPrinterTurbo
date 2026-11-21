"""Regression tests for narration-aware scene metadata and semantic query separation."""
import json
import os

from app.services import task


def test_scene_labels_and_semantic_queries_remain_distinct(tmp_path, monkeypatch):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    script_data = {
        "script": (
            "Ancient forests store carbon and support biodiversity.\n\n"
            "Modern cities use transport networks to move millions of people."
        ),
        "material_sources": [
            {"local_file": "forest.mp4", "search_term": "ancient forest biodiversity"},
            {"local_file": "city.mp4", "search_term": "modern city transport"},
        ],
    }
    (task_dir / "script.json").write_text(
        json.dumps(script_data), encoding="utf-8"
    )
    monkeypatch.setattr(task.utils, "task_dir", lambda _task_id: str(task_dir))
    video_paths = [
        os.path.join(str(task_dir), "forest.mp4"),
        os.path.join(str(task_dir), "city.mp4"),
    ]

    search_queries = task._get_material_source_groups("task-1", video_paths)
    scene_labels = task._get_material_scene_labels("task-1", video_paths)

    assert search_queries[video_paths[0]] == "ancient forest biodiversity"
    assert search_queries[video_paths[1]] == "modern city transport"
    assert scene_labels[video_paths[0]].startswith("Ancient forests")
    assert scene_labels[video_paths[1]].startswith("Modern cities")
    assert scene_labels != search_queries
