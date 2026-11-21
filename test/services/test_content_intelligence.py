from app.services.content_intelligence import audit_script


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
