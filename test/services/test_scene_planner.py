from app.services.scene_planner import (
    build_scene_labels,
    plan_scene,
    split_script_sections,
)


def test_split_script_sections_uses_paragraph_boundaries():
    assert split_script_sections("First section.\\n\\nSecond section.") == [
        "First section.",
        "Second section.",
    ]


def test_split_script_sections_falls_back_to_sentences():
    assert split_script_sections("First sentence. Second sentence!") == [
        "First sentence.",
        "Second sentence!",
    ]


def test_plan_scene_heading_is_grounded_in_narration():
    plan = plan_scene("ocean waves", "The ocean shapes coastlines over thousands of years.")
    assert plan["heading"] == "The ocean shapes coastlines over thousands of years."
    assert plan["query"] == "ocean waves"
    assert plan["intent"] == "narrative"


def test_build_scene_labels_aligns_queries_to_relevant_script_sections():
    script = (
        "Ancient forests store carbon and support biodiversity.\\n\\n"
        "Modern cities use transport networks to move millions of people."
    )
    labels = build_scene_labels(
        script,
        {
            "/clips/forest.mp4": "ancient forest biodiversity",
            "/clips/city.mp4": "modern city transport",
        },
    )
    assert labels["/clips/forest.mp4"].startswith("Ancient forests")
    assert labels["/clips/city.mp4"].startswith("Modern cities")


def test_build_scene_labels_has_chronological_fallback_for_unmatched_queries():
    labels = build_scene_labels(
        "Opening section about a journey.\\n\\nClosing section about arrival.",
        {"/clips/one.mp4": "unrelated alpha", "/clips/two.mp4": "unrelated beta"},
    )
    assert labels["/clips/one.mp4"].startswith("Opening section")
    assert labels["/clips/two.mp4"].startswith("Closing section")


def test_empty_and_malformed_inputs_are_safe():
    assert build_scene_labels("", None) == {}
    assert build_scene_labels("Some narration.", {"/clip.mp4": ""}) == {}
