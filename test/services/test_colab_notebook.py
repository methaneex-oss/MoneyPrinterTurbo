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

    assert 'REPO_BRANCH = "feat/solo-stack-presenter-quality-20261124"' in checkout_cell
    assert '"pull", "--ff-only", "origin", REPO_BRANCH' in checkout_cell
    assert "/content/drive/MyDrive/MoneyPrinterTurbo/task-state" in config_cell

    assert "app['enable_redis'] = False" in config_cell
    assert "app['solo_stack_mode'] = True" in config_cell
    assert "app['solo_stack_free_only'] = True" in config_cell
    assert "app['solo_stack_dynamic_visuals_enabled'] = True" in config_cell

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
    nested_script = image_cell.split('script = f"""', 1)[1].split('"""', 1)[0]
    for name, value in {
        "source": "openai_image",
        "base_url": "http://127.0.0.1:7861/v1",
        "model": "realvisxl-v5-lightning",
        "size": "832x1216",
    }.items():
        nested_script = nested_script.replace(
            "{" + name + "!r}", repr(value)
        )
    nested_script = nested_script.replace(
        '{source == "animatediff"!r}', repr(False)
    )
    nested_script = nested_script.replace(
        '{source == "openai_image"!r}', repr(True)
    )
    nested_script = nested_script.replace("{{", "{").replace("}}", "}")
    ast.parse(nested_script)
    assert "gpu_memory_gib < 8" in image_cell
    assert 'SD_TURBO_COMMERCIAL_REGISTERED = False' in image_cell
    assert 'elif gpu_memory_gib >= 14:' in image_cell
    assert 'elif SD_TURBO_COMMERCIAL_REGISTERED:' in image_cell
    assert 'SD-Turbo is not enabled until Stability AI commercial registration is confirmed' in image_cell
    assert 'image_server_env["IMAGE_BACKEND"] = image_backend' in image_cell
    assert 'image_server_env["IMAGE_MODEL"] = image_model' in image_cell
    assert 'warmup_result.get("backend") != image_backend' in image_cell
    assert "/warmup" in image_cell
    assert "timeout=900" in image_cell
    assert 'MODEL_CACHE = Path(os.environ["MPT_HOME"]) / "model-cache" / "huggingface"' in image_cell
    assert 'image_server_env["HF_HOME"] = str(MODEL_CACHE)' in image_cell
    assert 'image_server_env["HUGGINGFACE_HUB_CACHE"] = str(MODEL_CACHE / "hub")' in image_cell
    assert 'app["openai_image_api_keys"] = []' in image_cell
    assert 'set_video_source("pixabay")' in image_cell
    assert 'root = Path(os.environ.get("MPT_HOME", str(Path.cwd())))' in image_cell
    assert 'path = root / "config.toml"' in image_cell
    assert "os.replace(temporary_path, path)" in image_cell
    assert 'app["allow_unverified_animatediff"] = {source == "animatediff"!r}' in image_cell
    assert 'app["solo_stack_local_image_ready"] = {source == "openai_image"!r}' in image_cell
    preflight_cell = next(
        cell for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "Solo Stack preflight tests" in "".join(cell.get("source", []))
    )
    preflight_source = "".join(preflight_cell.get("source", []))
    ast.parse(preflight_source)
    assert "pytest" in preflight_source
    assert "test/services/test_task.py" in preflight_source
    assert "test/services/test_material.py" in preflight_source
    assert "test/services/test_solo_stack_visual_retrieval.py" in preflight_source
    assert "tests/test_visual_quality.py" in preflight_source
    assert 'path = Path("config.toml")' not in image_cell
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
    assert "vram_gib < 12" in video_cell
    assert "free_disk_gib < 16" in video_cell
    assert "server.py" in video_cell
    assert "MODEL_CACHE = DRIVE_ROOT" in video_cell
    assert "model-cache" in video_cell\n    assert "huggingface" in video_cell
    assert "set_video_source('animatediff')" in video_cell
    assert "restore_local_image_source" in video_cell
    assert "No paid fallback" in video_cell
    assert "ALLOW_ANIMATEDIFF_EXPERIMENTAL = False" in video_cell
    assert video_cell.index("if not ALLOW_ANIMATEDIFF_EXPERIMENTAL:") < video_cell.index("torch.cuda.is_available()")

def test_colab_kokoro_setup_is_syntax_valid_and_persists_config_to_drive():
    notebook_path = Path(__file__).resolve().parents[2] / "docs" / "MoneyPrinterTurbo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    kokoro_cell = next(cell for cell in code_cells if "KOKORO_DIR" in cell)

    ast.parse(kokoro_cell)
    assert 'MPT_HOME = Path(os.environ.get("MPT_HOME", str(REPO_DIR)))' in kokoro_cell
    assert 'config_path = MPT_HOME / "config.toml"' in kokoro_cell
    assert 'config_path = REPO_DIR / "config.toml"' not in kokoro_cell
    assert 'audition_path = MPT_HOME / "solo_stack_voice_audition.mp3"' in kokoro_cell
    assert '"solo_stack_performance_enabled": True' in kokoro_cell
    assert 'KOKORO_COMMIT = "5364fc31c770bd60069edc60521eb7bca4e5f5a9"' in kokoro_cell
    assert "LOCAL_MODEL_DIR.symlink_to(MODEL_STORE" in kokoro_cell
    assert '"ssml": True' in kokoro_cell
    assert '"allow_voice_tags": True' in kokoro_cell
    assert "solo_stack_voice_ssml_audition.mp3" in kokoro_cell
    assert "os.killpg(old_proc.pid, signal.SIGTERM)" in kokoro_cell
    assert "EXPECTED_MODEL_HASHES" in kokoro_cell
    assert "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4" in kokoro_cell
    assert "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f" in kokoro_cell
    assert "quarantine-" in kokoro_cell
    assert "for chunk in iter(lambda: handle.read(1024 * 1024), b\"\")" in kokoro_cell
