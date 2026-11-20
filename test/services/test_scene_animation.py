from PIL import Image

from app.services.scene_animation import (
    build_scene_label_card,
    first_scene_label_indices,
    infer_scene_type,
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



def test_scene_type_inference_selects_distinct_visual_treatments():
    assert infer_scene_type("The difference between two systems") == "comparison"
    assert infer_scene_type("What happened before the industrial revolution") == "timeline"
    assert infer_scene_type("Growth reached 42 percent") == "data"
    assert infer_scene_type("How the process works") == "explainer"
    assert infer_scene_type("A quiet ocean at sunset") == "narrative"


def test_scene_card_uses_type_specific_accent_and_tag():
    comparison = build_scene_label_card("The difference between two systems", 1, 1080)
    narrative = build_scene_label_card("A quiet ocean at sunset", 2, 1080)
    assert comparison.getpixel((5, 60)) != narrative.getpixel((5, 60))
