import json
from pathlib import Path

from PIL import Image

from app.services.solo_stack_product_media import (
    PRODUCTS,
    _make_editorial_card,
    _product_visual_coverage,
    _render_video_capture_clip,
    identify_products,
    interleave_product_visuals,
    prepare_episode_product_visuals,
)
from app.services.solo_stack_assets import (
    register_asset,
    verified_assets_for_products,
)


def test_identifies_named_products_in_episode_mention_order():
    products = identify_products(
        "Canva vs ChatGPT for a freelancer",
        "We will test ChatGPT first, then compare it with Canva.",
        ["Canva AI", "ChatGPT writing"],
        limit=3,
    )
    assert products == ["Canva", "ChatGPT"]


def test_logo_only_asset_does_not_satisfy_product_visual_coverage():
    logo_only = _product_visual_coverage(
        ["ChatGPT"],
        [{"product": "ChatGPT", "asset_type": "logo"}],
    )
    assert logo_only[0]["status"] == "missing"
    assert logo_only[0]["visual_count"] == 0

    with_screenshot = _product_visual_coverage(
        ["ChatGPT"],
        [
            {"product": "ChatGPT", "asset_type": "logo"},
            {"product": "ChatGPT", "asset_type": "screenshot"},
        ],
    )
    assert with_screenshot[0]["status"] == "available"
    assert with_screenshot[0]["visual_count"] == 1


def test_does_not_add_unmentioned_products_or_guess_from_generic_ai_terms():
    assert identify_products(
        "Best AI tools for freelancers",
        "We test a proposal workflow and compare the output.",
    ) == []


def test_product_catalog_uses_official_https_domains():
    for name, item in PRODUCTS.items():
        assert item["url"].startswith("https://")
        assert item["domain"] in item["url"]
        assert item["aliases"]


def test_editorial_card_preserves_real_product_image_inside_brand_frame(tmp_path):
    source = tmp_path / "official-ui.png"
    Image.new("RGB", (1280, 720), "#ffffff").save(source)
    output = tmp_path / "card.jpg"
    _make_editorial_card(source, output, "Notion", "9:16", "notion.com")
    with Image.open(output) as result:
        assert result.size == (1080, 1920)
        pixel = result.getpixel((0, 0))
        assert max(abs(actual - expected) for actual, expected in zip(pixel, (16, 24, 39))) <= 3


def test_portrait_operator_capture_uses_a_tall_mobile_evidence_panel(tmp_path):
    source = tmp_path / "portrait-app.png"
    Image.new("RGB", (720, 1280), "#ff0000").save(source)
    output = tmp_path / "portrait-card.jpg"

    _make_editorial_card(source, output, "Notion", "9:16", "USER-SUPPLIED CAPTURE")

    with Image.open(output).convert("RGB") as result:
        assert result.size == (1080, 1920)
        min_x, min_y = result.width, result.height
        max_x = max_y = -1
        for y in range(200, 1600):
            for x in range(80, 1000):
                red, green, blue = result.getpixel((x, y))
                if red > 180 and green < 90 and blue < 90:
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x), max(max_y, y)
    assert max_y - min_y > 1100
    assert max_x - min_x > 600


def test_identifies_products_from_a_single_string_term():
    assert identify_products("", "", "Use Claude to review this proposal") == ["Claude"]


def test_image_extension_rejects_svg_and_non_image_content_types():
    from app.services.solo_stack_product_media import _safe_image_extension

    assert _safe_image_extension("https://cdn.example.com/app.webp", "image/webp") == ".webp"
    assert _safe_image_extension("https://cdn.example.com/app", "image/jpeg; charset=binary") == ".jpg"
    assert _safe_image_extension("https://cdn.example.com/logo.svg", "image/svg+xml") is None



def test_product_visuals_are_distributed_through_existing_timeline():
    assert interleave_product_visuals(
        ["stock-1.mp4", "stock-2.mp4", "stock-3.mp4", "stock-4.mp4"],
        ["canva.mp4", "chatgpt.mp4"],
    ) == [
        "stock-1.mp4",
        "canva.mp4",
        "stock-2.mp4",
        "stock-3.mp4",
        "chatgpt.mp4",
        "stock-4.mp4",
    ]


def test_timeline_is_unchanged_when_no_product_visuals_exist():
    clips = ["stock-1.mp4", "stock-2.mp4"]
    assert interleave_product_visuals(clips, []) == clips



def test_scene_performance_varies_neutral_beats_without_changing_episode_wardrobe():
    from app.services.solo_stack_director import plan_scene_performance

    base = {"emotion": "skeptical", "wardrobe": "smart", "intensity": 0.8}
    first = plan_scene_performance("Canva", 0, base)
    second = plan_scene_performance("Canva", 1, base)
    assert first["action"] != second["action"]
    assert first["wardrobe"] == second["wardrobe"] == "smart"
    assert first["intensity"] == second["intensity"] == 0.8


def test_scene_performance_uses_semantic_cues_when_present():
    from app.services.solo_stack_director import plan_scene_performance

    result = plan_scene_performance("Hidden pricing and expensive plan", 2, {})
    assert result["emotion"] == "skeptical"
    assert result["action"] == "lean"



def test_verified_asset_lookup_filters_products_and_detects_tampering(tmp_path):
    library = tmp_path / "solo_stack"
    source = tmp_path / "chatgpt.png"
    Image.new("RGB", (24, 24), "#46D3E7").save(source)
    register_asset(
        source, library, asset_id="chatgpt-screen", product="ChatGPT",
        asset_type="screenshot",
    )

    matching = verified_assets_for_products(library, ["chatgpt"])
    assert len(matching) == 1
    assert matching[0]["asset_id"] == "chatgpt-screen"
    assert Path(matching[0]["path"]).is_file()

    Path(matching[0]["path"]).write_bytes(b"tampered")
    assert verified_assets_for_products(library, ["ChatGPT"]) == []


def test_episode_uses_verified_operator_captures_without_launching_browser(tmp_path, monkeypatch):
    from app.utils import utils

    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "script.json").write_text(
        '{"script":"We will demonstrate ChatGPT."}', encoding="utf-8"
    )
    library = tmp_path / "solo_stack"
    source_a = tmp_path / "chatgpt-a.png"
    source_b = tmp_path / "chatgpt-b.png"
    Image.new("RGB", (32, 24), "#46D3E7").save(source_a)
    Image.new("RGB", (32, 24), "#FF8963").save(source_b)
    register_asset(
        source_a, library, asset_id="chatgpt-a", product="ChatGPT",
        asset_type="screenshot",
    )
    register_asset(
        source_b, library, asset_id="chatgpt-b", product="ChatGPT",
        asset_type="screenshot",
    )

    monkeypatch.setattr(utils, "task_dir", lambda _task_id: str(task_dir))
    monkeypatch.setattr(utils, "storage_dir", lambda *_parts: str(library))

    def fake_card(_source, output, *_args, **_kwargs):
        output.write_bytes(b"editorial-card")

    def fake_still(_source, output, *_args, **_kwargs):
        output.write_bytes(b"rendered-video")

    monkeypatch.setattr(
        "app.services.solo_stack_product_media._make_editorial_card", fake_card
    )
    monkeypatch.setattr(
        "app.services.solo_stack_product_media._render_still_clip", fake_still
    )

    clips = prepare_episode_product_visuals(
        task_id="task-1",
        subject="ChatGPT review",
        script="We will demonstrate ChatGPT.",
        aspect="9:16",
        duration=4,
        max_products=1,
    )

    assert len(clips) == 2
    assert all(Path(clip).is_file() for clip in clips)
    manifest = json.loads(
        (task_dir / "solo_stack" / "product_visuals" / "manifest.json").read_text()
    )
    assert [item["asset_type"] for item in manifest["assets"]] == [
        "operator_capture", "operator_capture"
    ]
    task_manifest = json.loads((task_dir / "script.json").read_text())
    assert len(task_manifest["material_sources"]) == 2
    assert all(
        "real app screen capture" in item["search_term"]
        for item in task_manifest["material_sources"]
    )
    assert all(
        item["source_kind"] == "solo_stack_product_evidence"
        for item in task_manifest["material_sources"]
    )
    assert all(item["product"] == "ChatGPT" for item in task_manifest["material_sources"])


def test_screen_recording_normalizer_preserves_aspect_and_drops_source_audio(tmp_path, monkeypatch):
    from app.services import solo_stack_product_media

    source = tmp_path / "screen-recording.mp4"
    output = tmp_path / "normalized.mp4"
    source.write_bytes(b"input")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output.write_bytes(b"normalized")

    monkeypatch.setattr(solo_stack_product_media.subprocess, "run", fake_run)
    _render_video_capture_clip(source, output, 4, "9:16")

    command = captured["command"]
    filter_value = command[command.index("-vf") + 1]
    assert "scale=1080:1920:force_original_aspect_ratio=decrease" in filter_value
    assert "pad=1080:1920" in filter_value
    assert "-map" in command and "0:v:0" in command
    assert "-an" in command
    assert output.is_file()


def test_identifies_claude_code_and_llama_cpp_as_distinct_official_sources():
    products = identify_products(
        "Claude Code vs llama.cpp",
        "Compare Claude Code in the terminal with local llama.cpp inference.",
        limit=3,
    )
    assert products == ["Claude Code", "llama.cpp"]
    assert identify_products(
        "Claude Code vs Claude chat",
        "Compare Claude Code with the Claude chat assistant.",
        limit=3,
    ) == ["Claude Code", "Claude"]
    assert PRODUCTS["Claude Code"]["domain"] == "claude.com"
    assert PRODUCTS["llama.cpp"]["url"] == "https://github.com/ggml-org/llama.cpp"
    assert PRODUCTS["llama.cpp"]["source_label"] == "OFFICIAL PROJECT PAGE"
    assert PRODUCTS["llama.cpp"]["asset_type"] == "official_project_page_capture"


def test_identifies_unlisted_business_apps_from_comparison_title():
    assert identify_products(
        "Wave vs Zoho Invoice for freelancers",
        "Would you trust Wave to send your invoices? Zoho Invoice offers "
        "another way to manage client billing.",
        limit=2,
    ) == ["Wave", "Zoho Invoice"]


def test_extracts_products_from_a_category_prefixed_comparison_title():
    assert identify_products(
        "Best CRM tools: HubSpot vs Zoho CRM for small businesses",
        "HubSpot and Zoho CRM are the products in this comparison.",
        limit=2,
    ) == ["HubSpot", "Zoho CRM"]


def test_identifies_unlisted_apps_from_category_episode_script():
    assert identify_products(
        "Best invoicing software for freelancers",
        "Would you trust Wave to send your invoices? Zoho Invoice can help "
        "small businesses manage billing.",
        limit=2,
    ) == ["Wave", "Zoho Invoice"]


def test_discovers_official_site_from_wikidata_without_a_product_catalogue_entry(
    monkeypatch,
):
    from app.services import solo_stack_product_media

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    responses = [
        FakeResponse({
            "search": [{"id": "Q123", "label": "FreshBooks"}]
        }),
        FakeResponse({
            "entities": {
                "Q123": {
                    "claims": {
                        "P856": [{
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://www.freshbooks.com/"
                                }
                            }
                        }]
                    }
                }
            }
        }),
    ]

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(solo_stack_product_media.requests, "get", fake_get)
    source = solo_stack_product_media.discover_official_product_source("FreshBooks")
    assert source["url"] == "https://www.freshbooks.com/"
    assert source["domain"] == "freshbooks.com"
    assert source["discovery_method"] == "wikidata_official_website_property"
