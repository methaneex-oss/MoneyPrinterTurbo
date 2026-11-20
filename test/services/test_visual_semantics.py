import pytest

from app.services.visual_semantics import cosine_similarity


def test_cosine_similarity_of_aligned_vectors_is_one():
    assert cosine_similarity([1.0, 2.0], [2.0, 4.0]) == pytest.approx(1.0)


def test_cosine_similarity_of_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 3.0]) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "first, second",
    [
        ([], []),
        ([1.0], [1.0, 2.0]),
        ([0.0, 0.0], [1.0, 2.0]),
        ([float("nan")], [1.0]),
    ],
)
def test_cosine_similarity_rejects_invalid_vectors(first, second):
    with pytest.raises(ValueError):
        cosine_similarity(first, second)

def test_disabled_semantic_inspection_does_not_load_optional_model(monkeypatch):
    from app.services import visual_semantics

    monkeypatch.setattr(visual_semantics, "is_enabled", lambda: False)
    monkeypatch.setattr(
        visual_semantics,
        "_load_model",
        lambda *_args: pytest.fail("optional model must not load while disabled"),
    )

    assert visual_semantics.score_video_text("missing.mp4", "a person walking") is None
