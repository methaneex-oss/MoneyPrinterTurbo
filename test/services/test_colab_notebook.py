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

    assert 'REPO_BRANCH = "feat/scene-composition-engine"' in checkout_cell
    assert '"pull", "--ff-only", "origin", REPO_BRANCH' in checkout_cell
    assert "/content/drive/MyDrive/MoneyPrinterTurbo/task-state" in config_cell

    assert "app['enable_redis'] = False" in config_cell
