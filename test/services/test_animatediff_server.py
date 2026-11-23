from pathlib import Path


SERVER = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "local-video-models"
    / "server.py"
)


def test_animatediff_server_keeps_safety_checker_and_local_only_binding():
    source = SERVER.read_text(encoding="utf-8")

    assert 'host="127.0.0.1"' in source
    assert 'port=int(os.environ.get("ANIMATEDIFF_PORT", "7862"))' in source
    assert "MINIMUM_VRAM_GIB" in source
    assert "pipeline.enable_model_cpu_offload()" in source
    assert "pipeline.vae.enable_slicing()" in source
    assert "safety_checker=None" not in source
    assert "requires_safety_checker=False" not in source
    assert "BackgroundTask(shutil.rmtree" in source


def test_animatediff_server_rejects_parallel_generation_and_bounds_requests():
    source = SERVER.read_text(encoding="utf-8")

    assert "GENERATION_LOCK.acquire(blocking=False)" in source
    assert "status_code=429" in source
    assert "max_length=1200" in source
    assert "ge=8, le=20" in source
    assert "num_frames=16" in source
    assert '"portrait": (384, 672)' in source
    assert '"landscape": (672, 384)' in source
    assert "imageio_ffmpeg.get_ffmpeg_exe()" in source
