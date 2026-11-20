from app.services.visual_quality import _frame_metrics


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
