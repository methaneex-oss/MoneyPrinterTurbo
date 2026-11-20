from PIL import Image

from app.services.scene_animation import (
    build_scene_label_card,
    normalize_scene_label,
    scene_label_x,
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
