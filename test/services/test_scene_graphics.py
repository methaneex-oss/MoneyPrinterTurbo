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



def test_animated_scene_overlays_compose_inside_frame():
    from moviepy import ColorClip

    from app.services.scene_animation import add_scene_label
    from app.services.scene_graphics import add_scene_graphic

    clip = ColorClip(size=(1280, 720), color=(24, 32, 48), duration=2.0)
    clip = add_scene_label(
        clip, "Growth reached 42 percent", scene_index=1
    )
    clip = add_scene_graphic(clip, "Growth reached 42 percent")

    first_frame = clip.get_frame(0.0)
    middle_frame = clip.get_frame(0.8)
    assert first_frame.shape == (720, 1280, 3)
    assert middle_frame.shape == (720, 1280, 3)
    assert clip.duration == 2.0
