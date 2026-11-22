import ast
import json
from pathlib import Path


def test_colab_notebook_tracks_active_branch_and_persists_task_state():
    notebook_path = Path(__file__).resolve().parents[2] / "docs" / "MoneyPrinterTurbo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]

    checkout_cell = next(cell for cell in code_cells if "REPO_BRANCH" in cell)
    config_cell = next(cell for cell in code_cells if "task_state_dir" in cell)

    assert 'REPO_BRANCH = "feat/free-ai-video-colab-setup-20261122"' in checkout_cell
    assert '"pull", "--ff-only", "origin", REPO_BRANCH' in checkout_cell
    assert "/content/drive/MyDrive/MoneyPrinterTurbo/task-state" in config_cell

    assert "app['enable_redis'] = False" in config_cell


def test_colab_task_migration_merges_and_verifies_before_removing_local_data():
    notebook_path = Path(__file__).resolve().parents[2] / "docs" / "MoneyPrinterTurbo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    migration_cell = next(cell for cell in code_cells if "merge_runtime_item" in cell)

    assert "filecmp.cmp(source, destination, shallow=False)" in migration_cell
    assert ".drive-backup" in migration_cell
    assert migration_cell.index("filecmp.cmp(") < migration_cell.index("shutil.rmtree(TASKS_DIR)")
    assert "dirs_exist_ok=True" not in migration_cell


def test_colab_local_ai_image_setup_is_syntax_valid_and_has_safe_fallback():
    notebook_path = Path(__file__).resolve().parents[2] / "docs" / "MoneyPrinterTurbo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    image_cell = next(cell for cell in code_cells if "IMAGE_SERVER_DIR" in cell)

    ast.parse(image_cell)
    assert "gpu_memory_gib < 8" in image_cell
    assert 'image_backend = "sdxl" if gpu_memory_gib >= 14 else "sd-turbo"' in image_cell
    assert 'image_server_env["IMAGE_BACKEND"] = image_backend' in image_cell
    assert 'image_server_env["IMAGE_MODEL"] = image_model' in image_cell
    assert 'warmup_result.get("backend") != image_backend' in image_cell
    assert "/warmup" in image_cell
    assert "timeout=900" in image_cell
    assert 'app["openai_image_api_keys"] = []' in image_cell
    assert 'set_video_source("pixabay")' in image_cell
    assert image_cell.index("warmup_request") < image_cell.rindex('set_video_source(\n            "openai_image"')


def test_colab_animatediff_setup_is_syntax_valid_and_isolated():
    notebook_path = Path(__file__).resolve().parents[2] / "docs" / "MoneyPrinterTurbo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    video_cell = next(cell for cell in code_cells if "VIDEO_ENV" in cell)

    ast.parse(video_cell)
    assert "--system-site-packages" in video_cell
    assert "docs/local-video-models/requirements.txt" in video_cell
    assert "torch.cuda.is_available()" in video_cell
    assert "vram_gib < 8" in video_cell
    assert "free_disk_gib < 12" in video_cell
    assert "paid fallback" in video_cell
    assert "model-cache/huggingface" in video_cell
    assert "animatediff-benchmark.mp4" in video_cell
