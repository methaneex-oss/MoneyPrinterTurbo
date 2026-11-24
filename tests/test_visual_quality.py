from app.services.visual_quality import (
    _frame_metrics,
    _parse_aspect_ratio,
    _sample_audio_peak,
    inspect_video_quality,
)


def test_frame_metrics_returns_bounded_fingerprint_and_pixel_statistics():
    import numpy as np

    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[16:48, 16:48] = 255
    brightness, contrast, edge_activity, fingerprint = _frame_metrics(frame)

    assert 0 <= brightness <= 255
    assert contrast > 0
    assert edge_activity > 0
    assert 0 <= fingerprint < (1 << 64)


def test_uniform_black_frame_is_low_detail():
    import numpy as np

    brightness, contrast, edge_activity, _ = _frame_metrics(
        np.zeros((32, 32, 3), dtype=np.uint8)
    )
    assert brightness == 0
    assert contrast == 0
    assert edge_activity == 0


def test_perceptual_hash_does_not_treat_black_and_white_as_duplicates():
    from app.services.visual_quality import _frames_are_near_duplicates
    import numpy as np

    black = _frame_metrics(np.zeros((32, 32, 3), dtype=np.uint8))
    white = _frame_metrics(np.full((32, 32, 3), 255, dtype=np.uint8))
    assert not _frames_are_near_duplicates(black, white)
    assert _frames_are_near_duplicates(black, black)



def test_aspect_ratio_parser_accepts_video_aspect_enum_values():
    assert _parse_aspect_ratio("9:16") == 9 / 16
    assert _parse_aspect_ratio((1, 1)) == 1.0
    assert _parse_aspect_ratio("invalid") is None


def test_audio_peak_sampler_detects_real_signal_and_missing_audio():
    import numpy as np

    class FakeAudio:
        duration = 2.0

        def get_frame(self, timestamp):
            return np.array([0.25, -0.5], dtype=np.float32)

    assert _sample_audio_peak(FakeAudio(), sample_count=4) == 0.5
    assert _sample_audio_peak(None) is None



def test_final_video_inspection_reports_vertical_frame_and_audio(tmp_path):
    import numpy as np
    from moviepy import AudioClip, ColorClip

    path = tmp_path / "vertical-with-audio.mp4"
    video = ColorClip(size=(90, 160), color=(30, 80, 120), duration=1.0)
    audio = AudioClip(
        lambda timestamp: 0.1 * np.sin(2 * np.pi * 440 * timestamp),
        duration=1.0,
        fps=16000,
    )
    combined = video.with_audio(audio)
    try:
        combined.write_videofile(
            str(path), fps=10, codec="libx264", audio_codec="aac", logger=None,
        )
    finally:
        combined.close()
        video.close()
        audio.close()

    report = inspect_video_quality(
        str(path), sample_count=3,
        expected_aspect_ratio="9:16", require_audio=True,
    )
    assert report["width"] == 90
    assert report["height"] == 160
    assert report["has_audio"] is True
    assert report["sampled_audio_peak"] > 0.001
    assert "unexpected_aspect_ratio" not in report["flags"]
    assert "missing_audio" not in report["flags"]
    assert "silent_or_invalid_audio" not in report["flags"]
