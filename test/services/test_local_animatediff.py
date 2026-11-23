from pathlib import Path

import pytest

from app.services import local_animatediff


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.payload[:chunk_size]
        yield self.payload[chunk_size:]

    def close(self):
        return None


def valid_mp4_bytes():
    return b"\x00\x00\x00\x18ftypmp42" + (b"x" * 20_000)


def test_generate_videos_writes_verified_clips_and_manifest(tmp_path, monkeypatch):
    manifest = []
    requests_seen = []

    monkeypatch.setattr(local_animatediff, "health_check", lambda settings=None: {"status": "ready"})
    monkeypatch.setattr(local_animatediff.utils, "task_dir", lambda task_id: str(tmp_path))
    monkeypatch.setattr(
        local_animatediff.requests,
        "post",
        lambda url, **kwargs: (
            requests_seen.append((url, kwargs)) or FakeResponse(valid_mp4_bytes())
        ),
    )
    monkeypatch.setattr(
        local_animatediff.task_artifacts,
        "patch_script_data",
        lambda task_id, **updates: manifest.append(updates) or True,
    )

    paths = local_animatediff.generate_videos(
        task_id="synthetic-task",
        search_terms=["ocean waves", "mountain glacier"],
        video_aspect="portrait",
        audio_duration=18.5,
    )

    assert len(paths) == 2
    assert all(Path(path).is_file() for path in paths)
    assert len(requests_seen) == 2
    for _, kwargs in requests_seen:
        assert kwargs["json"]["aspect"] == "portrait"
        assert 0 <= kwargs["json"]["seed"] <= (2**32 - 1)
        assert kwargs["timeout"] == local_animatediff.REQUEST_TIMEOUT
    assert manifest[0]["material_sources"][0]["provider"] == "animatediff"
    assert manifest[0]["material_sources"][1]["search_term"] == "mountain glacier"


def test_generate_videos_fails_closed_when_local_service_is_unavailable(monkeypatch):
    monkeypatch.setattr(local_animatediff, "health_check", lambda settings=None: None)
    with pytest.raises(local_animatediff.LocalAnimateDiffError, match="no paid video provider"):
        local_animatediff.generate_videos(
            task_id="synthetic-task",
            search_terms=["ocean waves"],
            video_aspect="portrait",
            audio_duration=5,
        )


def test_generate_videos_rejects_non_mp4_response(tmp_path, monkeypatch):
    monkeypatch.setattr(local_animatediff, "health_check", lambda settings=None: {"status": "ready"})
    monkeypatch.setattr(local_animatediff.utils, "task_dir", lambda task_id: str(tmp_path))
    monkeypatch.setattr(
        local_animatediff.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(b"not an mp4" + (b"x" * 20_000)),
    )
    with pytest.raises(local_animatediff.LocalAnimateDiffError, match="not an MP4"):
        local_animatediff.generate_videos(
            task_id="synthetic-task",
            search_terms=["ocean waves"],
            video_aspect="portrait",
            audio_duration=5,
        )
    assert not list(tmp_path.glob("*.part"))

def test_task_routes_animatediff_source_to_local_backend(monkeypatch):
    from app.models.schema import VideoParams
    from app.services import task

    calls = {}
    expected = ["clip-one.mp4"]

    def fake_generate_videos(**kwargs):
        calls.update(kwargs)
        return expected

    monkeypatch.setattr(task.local_animatediff, "generate_videos", fake_generate_videos)
    monkeypatch.setattr(task, "_stage_progress_reporter", lambda *args: None)
    params = VideoParams(video_subject="documentary subject", video_source="animatediff")

    result = task.get_video_materials(
        task_id="synthetic-task",
        params=params,
        video_terms=["scene one"],
        audio_duration=12.0,
    )

    assert result == expected
    assert calls["task_id"] == "synthetic-task"
    assert calls["search_terms"] == ["scene one"]
    assert calls["audio_duration"] == 12.0


def test_generate_videos_treats_a_string_as_one_scene(tmp_path, monkeypatch):
    monkeypatch.setattr(local_animatediff, "health_check", lambda settings=None: {"status": "ready"})
    monkeypatch.setattr(local_animatediff.utils, "task_dir", lambda task_id: str(tmp_path))
    monkeypatch.setattr(
        local_animatediff.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(valid_mp4_bytes()),
    )
    monkeypatch.setattr(local_animatediff.task_artifacts, "patch_script_data", lambda *args, **kwargs: True)

    paths = local_animatediff.generate_videos(
        task_id="single-scene",
        search_terms="one complete documentary scene",
        video_aspect="portrait",
        audio_duration=12,
    )

    assert len(paths) == 1
    assert Path(paths[0]).is_file()


def test_generate_videos_rejects_more_than_the_scene_limit_before_network(monkeypatch):
    monkeypatch.setattr(
        local_animatediff,
        "health_check",
        lambda settings=None: pytest.fail("health check must not run for invalid scene counts"),
    )
    with pytest.raises(local_animatediff.LocalAnimateDiffError, match="limited to"):
        local_animatediff.generate_videos(
            task_id="too-many",
            search_terms=[f"scene {index}" for index in range(9)],
            video_aspect="portrait",
            audio_duration=20,
        )


@pytest.mark.parametrize("duration", [0, -1, "invalid", None])
def test_generate_videos_rejects_invalid_audio_duration(duration):
    with pytest.raises(local_animatediff.LocalAnimateDiffError, match="duration must be positive"):
        local_animatediff.generate_videos(
            task_id="invalid-duration",
            search_terms=["a documentary scene"],
            video_aspect="portrait",
            audio_duration=duration,
        )
