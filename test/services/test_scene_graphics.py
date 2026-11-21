import numpy as np
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
    later_frame = clip.get_frame(1.6)
    assert first_frame.shape == (720, 1280, 3)
    assert middle_frame.shape == (720, 1280, 3)
    assert not np.array_equal(middle_frame, later_frame)
    assert clip.duration == 2.0

def test_scene_label_alpha_fades_at_clip_boundaries():
    from moviepy import ColorClip

    from app.services.scene_animation import add_scene_label

    base_color = (24, 32, 48)
    clip = add_scene_label(
        ColorClip(size=(640, 360), color=base_color, duration=2.0),
        "A quiet ocean at sunset",
        scene_index=1,
    )

    first_frame = clip.get_frame(0.0)
    middle_frame = clip.get_frame(0.8)
    final_frame = clip.get_frame(1.999)
    expected = np.asarray(base_color, dtype=np.uint8)

    assert np.all(first_frame == expected)
    assert np.any(middle_frame != expected)
    assert np.max(np.abs(final_frame.astype(np.int16) - expected)) <= 2
    clip.close()

def test_scene_specific_indicator_paths_move_inside_the_panel():
    from app.services.scene_graphics import _scene_indicator_position

    for scene_type in ("comparison", "timeline", "data", "explainer", "narrative"):
        start = _scene_indicator_position(scene_type, 0.0)
        middle = _scene_indicator_position(scene_type, 1.2)
        assert start != middle
        assert 20 <= start[0] <= 170
        assert 40 <= start[1] <= 135
        assert 20 <= middle[0] <= 170
        assert 40 <= middle[1] <= 135


def test_scene_graphic_overlay_renders_and_animates_without_failing_open():
    from moviepy import ColorClip

    from app.services.scene_graphics import add_scene_graphic

    base_color = (24, 32, 48)
    clip = add_scene_graphic(
        ColorClip(size=(1280, 720), color=base_color, duration=2.5),
        "How the process works",
    )

    first = clip.get_frame(0.7)
    later = clip.get_frame(1.9)
    expected = np.asarray(base_color, dtype=np.uint8)

    assert first.shape == (720, 1280, 3)
    assert np.any(first != expected)
    assert not np.array_equal(first, later)
    clip.close()
