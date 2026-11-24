from app.services.content_intelligence import audit_script, audit_solo_stack_script


def test_audit_estimates_narration_and_flags_unverified_numeric_claims():
    report = audit_script(
        "Your brain uses about 20 percent of the body's energy. "
        "It contains billions of connections."
    )

    assert report["word_count"] > 0
    assert report["sentence_count"] == 2
    assert report["estimated_narration_seconds_at_150_wpm"] > 0
    assert report["numeric_claims_to_verify"]
    assert report["fact_check_status"] == "not_independently_verified"
    assert "verify_numeric_claims_against_sources" in report["warnings"]


def test_audit_flags_generic_opening_and_absolute_claims():
    report = audit_script(
        "Welcome to this video. This is the first and only method that always works."
    )

    assert "generic_opening" in report["warnings"]
    assert "review_absolute_or_superlative_claims" in report["warnings"]
    assert {"first", "only", "always"}.issubset(
        set(report["absolute_claim_terms_to_review"])
    )


def test_audit_handles_empty_and_non_string_input():
    report = audit_script(None)

    assert report["word_count"] == 0
    assert report["fact_check_status"] == "not_independently_verified"
    assert "empty_script" in report["warnings"]


def test_audit_preserves_percent_currency_and_quantity_units():
    report = audit_script(
        "The rate reached 20%. A project cost $3.5 million over 12 months."
    )

    assert "20%" in report["numeric_claims_to_verify"]
    assert "$3.5 million" in report["numeric_claims_to_verify"]
    assert "12 months" in report["numeric_claims_to_verify"]


def test_audit_keeps_decimal_numbers_intact():
    report = audit_script("The value is 2.5, not 25.")

    assert report["numeric_claims_to_verify"] == ["2.5", "25"]
    assert report["sentence_count"] == 1

def test_audit_flags_long_sentences_and_repetitive_openings():
    long_sentence = (
        "The brain can adapt throughout life because repeated experiences "
        "change the strength of connections between neurons in ways that "
        "support learning, memory, and the development of new skills over time."
    )
    report = audit_script(
        long_sentence
        + " The brain can also change with practice. "
        + "The brain can continue responding to experience."
    )

    assert report["long_sentence_numbers"] == [1]
    assert report["average_sentence_words"] > 0
    assert report["sentence_word_counts"][0] > 28
    assert "long_sentences_check_spoken_cadence" in report["warnings"]
    assert report["repeated_sentence_openings"] == ["the brain can"]
    assert "repeated_sentence_openings" in report["warnings"]


def test_audit_flags_an_overlong_opening_sentence():
    report = audit_script(
        "A detailed explanation of a complicated subject can lose viewers "
        "when the opening sentence takes too long to establish its central idea "
        "before the viewer understands why the topic matters."
    )

    assert "opening_sentence_too_long_for_short_form" in report["warnings"]


def test_solo_stack_audit_accepts_a_topic_specific_question_hook():
    report = audit_solo_stack_script(
        "Can ChatGPT turn a messy meeting into clear client action items? "
        "We will test it with a realistic transcript, then inspect the summary, "
        "action owners, deadlines and missing details. The goal is to see whether "
        "a freelancer can rely on the result without spending more time correcting "
        "it than writing notes manually. We will separate useful features from "
        "unsupported marketing promises.",
        "ChatGPT meeting notes for freelancers",
    )

    assert report["opening_hook"]["is_question"] is True
    assert report["opening_hook"]["topic_specificity_confirmed"] is True
    assert report["editorial_status"] == "structural_checks_passed"
    assert report["fact_check_status"] == "not_independently_verified"


def test_solo_stack_audit_flags_generic_or_non_question_openings():
    report = audit_solo_stack_script(
        "Welcome to this video. Today we are looking at a useful AI tool.",
        "Canva for brand logos",
    )

    assert report["opening_hook"]["is_question"] is False
    assert "opening_hook_must_be_a_question" in report["warnings"]
    assert "opening_hook_is_generic" in report["warnings"]
    assert "opening_hook_topic_specificity_unconfirmed" in report["warnings"]
    assert report["editorial_status"] == "editorial_review_required"


def test_solo_stack_audit_handles_question_mark_followed_by_quote():
    report = audit_solo_stack_script(
        'Can Canva create a brand logo that looks professional?" '
        "We will inspect the result.",
        "Canva brand logo design",
    )

    assert report["opening_hook"]["is_question"] is True
