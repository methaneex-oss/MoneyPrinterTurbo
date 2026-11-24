import numpy as np
from moviepy import ColorClip

from app.services.solo_stack_presenter import (
    add_presenter_overlay,
    build_presenter_frame,
)

def test_presenter_quality_renderer_preserves_requested_dimensions_and_alpha():
    frame = build_presenter_frame(0.75, (240, 280), expression="curious")
    assert frame.size == (240, 280)
    assert frame.mode == "RGBA"
    alpha = frame.getchannel("A")
    values = set(alpha.getdata())
    assert 0 in values
    assert any(0 < value < 255 for value in values)

def test_presenter_quality_renderer_is_deterministic():
    first = build_presenter_frame(
        1.25, (320, 373), expression="skeptical",
        action="lean", wardrobe="smart", mouth_open=0.4,
    )
    second = build_presenter_frame(
        1.25, (320, 373), expression="skeptical",
        action="lean", wardrobe="smart", mouth_open=0.4,
    )
    assert first.tobytes() == second.tobytes()

def test_presenter_quality_renderer_keeps_acting_and_costume_variation():
    base = build_presenter_frame(0.9, (240, 280), action="present")
    reaction = build_presenter_frame(
        0.9, (240, 280), expression="surprised", action="react",
    )
    creative = build_presenter_frame(
        0.9, (240, 280), expression="thoughtful",
        action="think", wardrobe="creative",
    )
    assert len({base.tobytes(), reaction.tobytes(), creative.tobytes()}) == 3

def test_presenter_quality_renderer_handles_short_overlay_dimensions():
    frame = build_presenter_frame(0.2, (104, 122), expression="talk")
    assert frame.size == (104, 122)
    assert frame.getbbox() is not None

def test_presenter_blink_transitions_through_partial_and_closed_states():
    open_frame = build_presenter_frame(0.16, (240, 280))
    partial_frame = build_presenter_frame(0.19, (240, 280))
    closed_frame = build_presenter_frame(0.225, (240, 280))

    # Compare the face region rather than the full frame so the assertion
    # specifically protects eyelid motion from regressing into a hard switch.
    face_box = (75, 65, 175, 125)
    open_face = open_frame.crop(face_box).tobytes()
    partial_face = partial_frame.crop(face_box).tobytes()
    closed_face = closed_frame.crop(face_box).tobytes()
    assert len({open_face, partial_face, closed_face}) == 3

def test_presenter_uses_distinct_curious_skeptical_and_thoughtful_faces():
    curious = build_presenter_frame(1.1, (240, 280), expression="curious")
    skeptical = build_presenter_frame(1.1, (240, 280), expression="skeptical")
    thoughtful = build_presenter_frame(1.1, (240, 280), expression="thoughtful")
    talking = build_presenter_frame(1.1, (240, 280), expression="talk")

    face_box = (70, 55, 175, 135)
    faces = {
        frame.crop(face_box).tobytes()
        for frame in (curious, skeptical, thoughtful, talking)
    }
    assert len(faces) == 4

def test_facial_expression_remains_visible_during_audio_reactive_speech():
    curious = build_presenter_frame(
        1.1, (240, 280), expression="curious", mouth_open=0.65,
    )
    skeptical = build_presenter_frame(
        1.1, (240, 280), expression="skeptical", mouth_open=0.65,
    )
    face_box = (70, 55, 175, 115)
    assert curious.crop(face_box).tobytes() != skeptical.crop(face_box).tobytes()

def test_presenter_overlay_preserves_transparency_over_video():
    background = (24, 80, 120)
    source = ColorClip(size=(360, 640), color=background, duration=2.0)
    composite = add_presenter_overlay(source)

    try:
        frame = composite.get_frame(0.5)
        # The presenter's upper-left overlay pixel is outside the character.
        # It must reveal the source footage, not become an opaque black box.
        assert tuple(frame[28, 162]) == background
    finally:
        composite.close()

def test_presenter_distinguishes_open_palm_question_and_shrug_actions():
    present = build_presenter_frame(1.3, (240, 280), action="present")
    question = build_presenter_frame(1.3, (240, 280), action="question")
    shrug = build_presenter_frame(1.3, (240, 280), action="shrug")
    warn = build_presenter_frame(1.3, (240, 280), action="warn")

    assert len({
        present.tobytes(), question.tobytes(), shrug.tobytes(), warn.tobytes()
    }) == 4

def test_presenter_overlay_fades_in_and_out_without_a_hard_pop():
    background = (24, 80, 120)
    source = ColorClip(size=(360, 640), color=background, duration=2.0)
    composite = add_presenter_overlay(source)

    try:
        start = composite.get_frame(0.0)
        middle = composite.get_frame(0.46)
        end = composite.get_frame(0.91)
        # Sample the face area in the upper-right presenter placement.
        point = (100, 250)

        start_delta = np.abs(start[point] - np.asarray(background)).sum()
        middle_delta = np.abs(middle[point] - np.asarray(background)).sum()
        end_delta = np.abs(end[point] - np.asarray(background)).sum()

        assert start_delta == 0
        assert middle_delta > 20
        assert end_delta < middle_delta
    finally:
        composite.close()


def test_presenter_auto_placement_avoids_a_visually_busy_zone():
    from app.services.solo_stack_presenter import _overlay_position_scores

    frame = np.full((640, 360, 3), 112, dtype=np.uint8)
    # Simulate dense UI/text in the upper-right zone while the left and center
    # remain visually quiet. The presenter should not default to that busy area.
    yy, xx = np.indices((210, 150))
    pattern = ((xx // 3 + yy // 3) % 2) * 220
    frame[0:210, 210:360, :] = pattern[..., None]
    scores = _overlay_position_scores(frame, (110, 180))
    right_top = (360 - 110 - max(12, int(360 * 0.035)), max(8, int(640 * 0.04)))
    selected = min(scores, key=lambda position: (scores[position], position[1], -position[0]))
    assert selected != right_top
    assert selected[1] + 180 <= int(640 * 0.66)


def test_presenter_auto_placement_is_deterministic_for_uniform_scenes():
    from app.services.solo_stack_presenter import _overlay_position_scores

    frame = np.full((640, 360, 3), 112, dtype=np.uint8)
    scores = _overlay_position_scores(frame, (110, 180))
    selected = min(scores, key=lambda position: (scores[position], position[1], -position[0]))
    assert selected == (360 - 110 - max(12, int(360 * 0.035)), max(8, int(640 * 0.04)))
