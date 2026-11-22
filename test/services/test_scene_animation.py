from PIL import Image

from app.services.scene_animation import (
    build_scene_label_card,
    build_scene_progress_frame,
    first_scene_label_indices,
    normalize_scene_label,
    scene_label_x,
    scene_progress_width,
)


def test_normalize_scene_label_removes_controls_and_bounds_length():
    assert normalize_scene_label("  ocean\n  waves  ") == "ocean waves"
    assert len(normalize_scene_label("x" * 100)) == 72


def test_scene_label_card_is_transparent_and_matches_requested_width():
    card = build_scene_label_card("Ocean waves at sunset", 3, 1080)
    assert isinstance(card, Image.Image)
    assert card.size == (777, 124)
    assert card.mode == "RGBA"
    assert card.getpixel((0, 0))[3] == 0


def test_scene_label_slides_in_holds_and_slides_out():
    card_width = 600
    target_x = 48
    duration = 2.0
    assert scene_label_x(0, card_width, target_x, duration) == -card_width
    assert scene_label_x(0.5, card_width, target_x, duration) == target_x
    assert scene_label_x(1.99, card_width, target_x, duration) < -card_width + 10


def test_scene_progress_width_is_eased_bounded_and_handles_invalid_duration():
    assert scene_progress_width(0, 2, 100) == 0
    assert scene_progress_width(1, 2, 100) == 50
    assert scene_progress_width(2, 2, 100) == 100
    assert scene_progress_width(3, 2, 100) == 100
    assert scene_progress_width(1, 0, 100) == 0
    assert scene_progress_width(1, 2, 0) == 0


def test_scene_progress_frame_is_transparent_and_grows_over_time():
    start = build_scene_progress_frame(0, 2, (500, 124))
    middle = build_scene_progress_frame(1, 2, (500, 124))
    end = build_scene_progress_frame(2, 2, (500, 124))

    assert start.shape == (124, 500, 4)
    assert start.dtype.name == "uint8"
    assert start[0, 0, 3] == 0
    # The rail remains visible, while its cyan foreground advances over time.
    assert tuple(start[112, 100, :3]) != tuple(middle[112, 100, :3])
    assert tuple(middle[112, 350, :3]) == tuple(start[112, 350, :3])
    assert tuple(end[112, 350, :3]) != tuple(middle[112, 350, :3])


def test_scene_labels_only_appear_at_first_occurrence_of_each_query():
    paths = ["shot-a.mp4", "shot-b.mp4", "shot-c.mp4", "shot-d.mp4"]
    labels = {
        "shot-a.mp4": "ocean waves",
        "shot-b.mp4": "ocean waves",
        "shot-c.mp4": "city skyline",
        "shot-d.mp4": "ocean waves",
    }

    assert first_scene_label_indices(paths, labels) == {
        0: "ocean waves",
        2: "city skyline",
    }


def test_scene_labels_without_manifest_return_no_overlays():
    assert first_scene_label_indices(["shot.mp4"], None) == {}
