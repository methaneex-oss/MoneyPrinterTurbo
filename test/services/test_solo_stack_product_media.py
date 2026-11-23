from pathlib import Path

from PIL import Image

from app.services.solo_stack_product_media import (
    PRODUCTS,
    _make_editorial_card,
    identify_products,
    interleave_product_visuals,
)


def test_identifies_named_products_in_episode_mention_order():
    products = identify_products(
        "Canva vs ChatGPT for a freelancer",
        "We will test ChatGPT first, then compare it with Canva.",
        ["Canva AI", "ChatGPT writing"],
        limit=3,
    )
    assert products == ["Canva", "ChatGPT"]


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
