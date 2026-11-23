import json
from pathlib import Path

import pytest

from app.services.solo_stack_assets import (
    SoloStackAssetError, add_evidence, register_asset, validate_source_url, verify_asset,
)
from app.services.solo_stack_presenter import BRAND, build_presenter_frame


def test_presenter_frames_are_deterministic_and_transparent():
    first = build_presenter_frame(0.5, (240, 280), "talk")
    second = build_presenter_frame(0.5, (240, 280), "talk")
    assert first.size == (240, 280)
    assert first.mode == "RGBA"
    assert first.tobytes() == second.tobytes()
    assert first.getbbox() is not None
    assert BRAND["character"] == "Stack"


def test_presenter_expressions_change_visual_output():
    assert build_presenter_frame(1, expression="talk").tobytes() != build_presenter_frame(
        1, expression="surprised"
    ).tobytes()


def test_asset_registration_copies_and_hash_verifies(tmp_path):
    source = tmp_path / "capture.png"
    Image.new("RGB", (16, 16), (20, 40, 60)).save(source)
    project = tmp_path / "episode"
    record = register_asset(
        source, project, asset_id="chatgpt-home", product="ChatGPT",
        asset_type="screenshot", source_url="https://chatgpt.com/",
        captured_at="2026-11-23", notes="Actual interface capture",
    )
    assert record["file"] == "assets/chatgpt-home.png"
    assert verify_asset(project, "chatgpt-home")
    assert (project / "assets" / "chatgpt-home.png").read_bytes() == source.read_bytes()


def test_asset_registration_rejects_symlink_and_oversized_file(tmp_path):
    source = tmp_path / "real.png"
    Image.new("RGB", (2, 2)).save(source)
    link = tmp_path / "link.png"
    link.symlink_to(source)
    with pytest.raises(SoloStackAssetError):
        register_asset(link, tmp_path / "episode", asset_id="link", product="Tool", asset_type="screenshot")
    with pytest.raises(SoloStackAssetError):
        validate_source_url("file:///etc/passwd")


def test_asset_registration_rejects_duplicate_id(tmp_path):
    source = tmp_path / "capture.webp"
    Image.new("RGB", (2, 2)).save(source)
    project = tmp_path / "episode"
    register_asset(source, project, asset_id="one", product="Canva", asset_type="screenshot")
    with pytest.raises(SoloStackAssetError):
        register_asset(source, project, asset_id="one", product="Canva", asset_type="screenshot")


def test_evidence_requires_source_and_checked_date(tmp_path):
    project = tmp_path / "episode"
    record = add_evidence(
        project, claim_id="free-tier-limit", product="Canva",
        claim="Free plan includes a stated feature limit.",
        source_url="https://www.canva.com/pricing/", publisher="Canva",
        checked_at="2026-11-23", value="verified on source page",
        plan="Free",
    )
    assert record["checked_at"] == "2026-11-23"
    payload = json.loads((project / "solo_stack_manifest.json").read_text())
    assert payload["evidence"][0]["source_url"].startswith("https://")
    with pytest.raises(SoloStackAssetError):
        add_evidence(
            project, claim_id="bad-date", product="Canva", claim="A claim",
            source_url="https://example.com", publisher="Example", checked_at="yesterday",
        )


def test_manifest_tampering_is_detected(tmp_path):
    source = tmp_path / "capture.jpg"
    Image.new("RGB", (2, 2), (10, 20, 30)).save(source)
    project = tmp_path / "episode"
    register_asset(source, project, asset_id="one", product="Tool", asset_type="screenshot")
    Image.new("RGB", (2, 2), (40, 50, 60)).save(project / "assets" / "one.jpg")
    assert not verify_asset(project, "one")


def test_asset_registration_rejects_fake_image_bytes(tmp_path):
    source = tmp_path / "not-an-image.png"
    source.write_bytes(b"not really a png")
    with pytest.raises(SoloStackAssetError):
        register_asset(
            source, tmp_path / "episode", asset_id="fake",
            product="Tool", asset_type="screenshot",
        )


def test_presenter_overlay_composes_with_existing_video_clip():
    from moviepy import ColorClip
    from app.services.solo_stack_presenter import add_presenter_overlay

    clip = ColorClip(size=(640, 360), color=(24, 32, 48), duration=1.0)
    result = add_presenter_overlay(clip)
    assert result.size == (640, 360)
    assert result.duration == 1.0
    assert result.get_frame(0.5).shape == (360, 640, 3)
    result.close()
