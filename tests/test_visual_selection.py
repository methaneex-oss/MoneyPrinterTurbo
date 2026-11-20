from types import SimpleNamespace

from app.services.visual_selection import rank_visual_candidates


def _candidate(asset_id, tags=""):
    return SimpleNamespace(
        source_info={"asset_id": asset_id, "tags": tags}
    )


def test_ranks_candidates_by_scene_tag_coverage():
    broad = _candidate("broad", "city buildings traffic")
    exact = _candidate("exact", "astronaut space station earth")
    partial = _candidate("partial", "astronaut training")

    ranked = rank_visual_candidates("astronaut space station", [broad, partial, exact])

    assert [item.source_info["asset_id"] for item in ranked] == [
        "exact", "partial", "broad"
    ]


def test_preserves_provider_order_when_tags_are_missing():
    first = _candidate("first")
    second = _candidate("second")

    assert rank_visual_candidates("ocean waves", [first, second]) == [first, second]


def test_ranking_is_stable_for_equal_scores():
    first = _candidate("first", "forest trees")
    second = _candidate("second", "forest birds")

    assert rank_visual_candidates("forest", [first, second]) == [first, second]


def test_ignores_common_words_and_empty_queries():
    first = _candidate("first", "forest trees")
    second = _candidate("second", "ocean waves")

    assert rank_visual_candidates("the and of", [first, second]) == [first, second]
