from app.services.solo_stack_director import plan_performance


def test_same_character_identity_gets_different_scene_performance():
    curious = plan_performance(
        "Can this AI actually save a freelancer time? Let's test the workflow.",
        "AI proposal writing",
    )
    skeptical = plan_performance(
        "The marketing claim sounds impressive, but the free plan hides a major limit.",
        "AI proposal writing",
    )
    assert curious["action"] != skeptical["action"]
    assert curious["expression"] != skeptical["expression"]
    assert curious["wardrobe"] == skeptical["wardrobe"] == "smart"


def test_director_is_reproducible_and_uses_topic_context():
    script = "Can this tool turn a messy meeting into clear action items?"
    first = plan_performance(script, "Meeting notes")
    second = plan_performance(script, "Meeting notes")
    assert first == second
    assert first["emotion"] == "curious"
    assert first["action"] == "question"


def test_director_does_not_force_one_fixed_action():
    scripts = [
        ("Can it do the job?", "Freelance workflow"),
        ("The hidden fee changes the decision.", "AI subscription pricing"),
        ("This result is genuinely useful and saves time.", "AI assistant"),
        ("There is a privacy risk in this workflow.", "Client data security"),
    ]
    actions = {plan_performance(script, topic)["action"] for script, topic in scripts}
    assert len(actions) >= 3
