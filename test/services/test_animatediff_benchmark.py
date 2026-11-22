import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "local-video-models"
    / "animatediff_benchmark.py"
)
spec = importlib.util.spec_from_file_location("animatediff_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class FakeCuda:
    def __init__(self, *, available=True, memory_gib=15.0, capability=(7, 5)):
        self.available = available
        self.memory_gib = memory_gib
        self.capability = capability

    def is_available(self):
        return self.available

    def current_device(self):
        return 0

    def get_device_properties(self, device):
        assert device == 0
        return SimpleNamespace(
            name="Fake Colab GPU",
            total_memory=self.memory_gib * (1024**3),
        )

    def get_device_capability(self, device):
        assert device == 0
        return self.capability


def fake_torch(cuda):
    return SimpleNamespace(cuda=cuda)


def test_runtime_preflight_reports_gpu_and_fp16():
    report = benchmark.check_runtime(fake_torch(FakeCuda()))

    assert report["device"] == "Fake Colab GPU"
    assert report["compute_capability"] == "7.5"
    assert report["vram_gib"] == 15.0
    assert report["precision"] == "float16"


def test_runtime_preflight_fails_without_cuda():
    with pytest.raises(RuntimeError, match="requires a CUDA GPU"):
        benchmark.check_runtime(fake_torch(FakeCuda(available=False)))


def test_runtime_preflight_fails_before_model_download_when_vram_is_low():
    with pytest.raises(RuntimeError, match="benchmark gate"):
        benchmark.check_runtime(fake_torch(FakeCuda(memory_gib=7.9)))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"num_frames": 24}, "fixed at 16 frames"),
        ({"width": 640}, "fixed at 16 frames"),
        ({"height": 640}, "fixed at 16 frames"),
        ({"steps": 0}, "steps must be between"),
        ({"steps": 26}, "steps must be between"),
        ({"prompt": "  "}, "prompt cannot be empty"),
    ],
)
def test_generation_rejects_unsupported_benchmark_inputs_before_importing_models(
    kwargs, message
):
    with pytest.raises(ValueError, match=message):
        benchmark.generate_benchmark("unused.mp4", **kwargs)
