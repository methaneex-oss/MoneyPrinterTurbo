from PIL import Image

from app.services.scene_graphics import build_scene_graphic


def test_scene_graphic_builds_transparent_panel_for_each_visual_grammar():
    for label in (
        "The difference between two systems",
        "What happened before the industrial revolution",
        "Growth reached 42 percent",
        "How the process works",
        "A quiet ocean at sunset",
    ):
        panel = build_scene_graphic(label)
        assert isinstance(panel, Image.Image)
        assert panel.mode == "RGBA"
        assert panel.size == (470, 190)
        assert panel.getpixel((0, 0))[3] == 0


def test_data_graphic_does_not_require_or_invent_numeric_values():
    panel = build_scene_graphic("A discussion of information and evidence")
    assert panel.size == (470, 190)
