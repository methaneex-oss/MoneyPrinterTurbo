"""Capture genuine public product visuals from official software websites.

This deliberately captures public product-page imagery only. It never logs into
third-party accounts, fabricates interfaces, or labels marketing illustrations
as authenticated in-app demonstrations.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Official product pages with public product imagery. Keep this catalogue
# explicit: no search-engine image scraping or arbitrary URL fetching.
PRODUCTS = {
    "ChatGPT": {
        "aliases": ("chatgpt", "openai chat"),
        "url": "https://chatgpt.com/overview/",
        "domain": "chatgpt.com",
    },
    "Claude": {
        "aliases": ("claude", "anthropic"),
        "url": "https://claude.com/product/overview",
        "domain": "claude.com",
    },
    "Notion": {
        "aliases": ("notion", "notion ai"),
        "url": "https://www.notion.com/product/features",
        "domain": "notion.com",
    },
    "Canva": {
        "aliases": ("canva", "magic studio"),
        "url": "https://www.canva.com/",
        "domain": "canva.com",
    },
    "Grammarly": {
        "aliases": ("grammarly",),
        "url": "https://www.grammarly.com/features",
        "domain": "grammarly.com",
    },
    "Zapier": {
        "aliases": ("zapier",),
        "url": "https://zapier.com/press",
        "domain": "zapier.com",
    },
    "Perplexity": {
        "aliases": ("perplexity",),
        "url": "https://www.perplexity.ai/",
        "domain": "perplexity.ai",
    },
    "Cursor": {
        "aliases": ("cursor ai", "cursor editor"),
        "url": "https://www.cursor.com/features",
        "domain": "cursor.com",
    },
    "ClickUp": {
        "aliases": ("clickup", "click up"),
        "url": "https://clickup.com/features/ai",
        "domain": "clickup.com",
    },
    "Figma": {
        "aliases": ("figma",),
        "url": "https://www.figma.com/product/",
        "domain": "figma.com",
    },
}
_IMAGE_HINTS = re.compile(
    r"(app|interface|screen|editor|dashboard|chat|design|document|workflow|product|feature)",
    re.I,
)
_MAX_IMAGE_BYTES = 18 * 1024 * 1024
_MAX_IMAGES_PER_PRODUCT = 2


def identify_products(subject: str, script: str, terms=None, limit: int = 3) -> list[str]:
    """Return supported products actually named in the episode, in mention order."""
    if isinstance(terms, str):
        terms = [terms]
    elif terms is None:
        terms = []
    text = " ".join([subject or "", script or "", *terms]).casefold()
    matches = []
    for name, item in PRODUCTS.items():
        positions = [text.find(alias.casefold()) for alias in item["aliases"]]
        positions = [position for position in positions if position >= 0]
        if positions:
            matches.append((min(positions), name))
    return [name for _, name in sorted(matches)[:max(0, min(5, limit))]]


def _safe_image_extension(url: str, content_type: str) -> str | None:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type.split(";", 1)[0].strip().lower())


def _download_page_images(page, destination: Path) -> list[tuple[Path, str]]:
    candidates = page.locator("img").evaluate_all(
        """els => els.map((img, index) => ({
          src: img.currentSrc || img.src || '',
          alt: img.alt || '',
          width: img.naturalWidth || img.width || 0,
          height: img.naturalHeight || img.height || 0,
          index
        }))"""
    )
    # Official product pages frequently expose their hero/product screenshot
    # through Open Graph metadata rather than a visible <img> element.
    metadata_images = page.locator(
        'meta[property="og:image"], meta[name="twitter:image"]'
    ).evaluate_all(
        """els => els.map((meta, index) => ({
          src: meta.content || '',
          alt: 'official product interface image',
          width: 1200,
          height: 675,
          index: 10000 + index
        }))"""
    )
    candidates.extend(metadata_images)
    candidates = [
        item for item in candidates
        if item["src"].startswith("https://")
        and item["width"] >= 320 and item["height"] >= 160
        and _safe_image_extension(item["src"], "image/png") is not None
        and (_IMAGE_HINTS.search(item["alt"]) or _IMAGE_HINTS.search(urlparse(item["src"]).path))
    ]
    candidates.sort(
        key=lambda item: (
            0 if _IMAGE_HINTS.search(item["alt"]) else 1,
            -(item["width"] * item["height"]),
            item["index"],
        )
    )
    saved = []
    seen = set()
    for item in candidates:
        if item["src"] in seen:
            continue
        seen.add(item["src"])
        try:
            response = page.request.get(item["src"], timeout=15000)
            if not response.ok:
                continue
            body = response.body()
            content_type = response.headers.get("content-type", "")
            extension = _safe_image_extension(item["src"], content_type)
            if not extension or not body or len(body) > _MAX_IMAGE_BYTES:
                continue
            filename = f"product-image-{len(saved) + 1}{extension}"
            target = destination / filename
            target.write_bytes(body)
            with Image.open(target) as image:
                image.verify()
            saved.append((target, item["src"]))
            if len(saved) >= _MAX_IMAGES_PER_PRODUCT:
                break
        except Exception as exc:
            logger.debug("Skipping official product image %s: %s", item["src"], exc)
    return saved


def _fit_image(source: Path, target_size: tuple[int, int]) -> Image.Image:
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target_size, "#111B2C")
        canvas.paste(image, ((target_size[0] - image.width) // 2,
                             (target_size[1] - image.height) // 2))
        return canvas


def _make_editorial_card(source: Path, output: Path, product: str, aspect: str,
                         source_host: str) -> None:
    """Place the real product visual in a branded editorial frame."""
    portrait = aspect in {"9:16", "portrait"}
    size = (1080, 1920) if portrait else (1920, 1080)
    canvas = Image.new("RGB", size, "#101827")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42 if portrait else 48)
        small = ImageFont.truetype("DejaVuSans.ttf", 23 if portrait else 25)
    except OSError:
        font, small = ImageFont.load_default(), ImageFont.load_default()
    margin = 56 if portrait else 100
    draw.text((margin, 74 if portrait else 52), product.upper(), fill="#F6F4EE", font=font)
    draw.rounded_rectangle(
        (margin, 145 if portrait else 125, margin + 230, 157 if portrait else 137),
        radius=6, fill="#46D3E7",
    )
    panel_w = size[0] - margin * 2
    panel_h = 640 if portrait else 760
    panel_y = 600 if portrait else 190
    image = _fit_image(source, (panel_w - 28, panel_h - 28))
    canvas.paste(image, (margin + 14, panel_y + 14))
    draw.rounded_rectangle(
        (margin, panel_y, margin + panel_w, panel_y + panel_h),
        radius=22, outline="#46D3E7", width=5,
    )
    footer_y = panel_y + panel_h + (90 if portrait else 60)
    draw.text((margin, footer_y), "OFFICIAL PRODUCT VISUAL", fill="#46D3E7", font=small)
    draw.text((margin, footer_y + 42), source_host, fill="#A8B4C7", font=small)
    canvas.save(output, quality=94)


def _render_still_clip(still: Path, output: Path, duration: float,
                       aspect: str, fps: int = 30) -> None:
    width, height = (1080, 1920) if aspect in {"9:16", "portrait"} else (1920, 1080)
    frames = max(1, int(duration * fps))
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-i", str(still),
        "-vf", (
            f"zoompan=z='min(zoom+0.00035,1.025)':d={frames}:"
            f"s={width}x{height}:fps={fps},format=yuv420p"
        ),
        "-frames:v", str(frames), "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "21", "-movflags", "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, timeout=90)


def prepare_episode_product_visuals(
    task_id: str,
    subject: str,
    script: str,
    terms=None,
    aspect: str = "9:16",
    duration: float = 4.0,
    max_products: int = 2,
) -> list[str]:
    """Capture official public product visuals and render timeline-ready clips.

    Playwright is optional at import time. If the browser is unavailable, the
    caller can continue with its existing stock/local media workflow.
    """
    products = identify_products(subject, script, terms, limit=max_products)
    if not products:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Solo Stack official product visuals require Playwright; "
            "the Colab setup cell must install it first."
        ) from exc

    from app.utils import utils

    task_dir = Path(utils.task_dir(task_id)).resolve()
    media_dir = task_dir / "solo_stack" / "product_visuals"
    media_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = media_dir / "manifest.json"
    manifest = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "assets": [],
    }
    clips = []
    material_records = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=1,
                locale="en-US",
            )
            for product in products:
                try:
                    spec = PRODUCTS[product]
                    product_dir = media_dir / re.sub(r"[^a-z0-9]+", "-", product.casefold()).strip("-")
                    product_dir.mkdir(parents=True, exist_ok=True)
                    page.goto(spec["url"], wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2500)
                    page.evaluate("window.scrollTo(0, Math.min(650, document.body.scrollHeight))")
                    page.wait_for_timeout(900)
                    source_page = page.url
                    parsed = urlparse(source_page)
                    if parsed.scheme != "https" or not (
                        parsed.hostname == spec["domain"]
                        or parsed.hostname.endswith("." + spec["domain"])
                    ):
                        logger.warning("Official page redirected outside its allowlisted domain: %s", source_page)
                        continue
    
                    images = _download_page_images(page, product_dir)
                    if not images:
                        screenshot = product_dir / "official-product-page.png"
                        page.screenshot(path=str(screenshot), full_page=False)
                        images = [(screenshot, source_page)]
    
                    product_slug = re.sub(r"[^a-z0-9]+", "-", product.casefold()).strip("-")
                    for image_index, (source_image, image_url) in enumerate(images, start=1):
                        card = product_dir / f"visual-card-{image_index}.jpg"
                        clip = product_dir / f"{product_slug}-product-visual-{image_index}.mp4"
                        _make_editorial_card(source_image, card, product, aspect, spec["domain"])
                        _render_still_clip(card, clip, duration, aspect)
                        digest = hashlib.sha256(source_image.read_bytes()).hexdigest()
                        manifest["assets"].append({
                            "product": product,
                            "asset_type": "official_product_page_image" if image_url != source_page
                                          else "official_product_page_capture",
                            "file": str(source_image.relative_to(task_dir)),
                            "rendered_clip": str(clip.relative_to(task_dir)),
                            "source_page": source_page,
                            "source_asset_url": image_url,
                            "sha256": digest,
                            "captured_at": manifest["captured_at"],
                            "note": "Public official-site visual; not an authenticated in-app task recording.",
                        })
                        clips.append(str(clip))
                        material_records.append({
                            "local_file": clip.name,
                            "search_term": f"{product} official product interface",
                        })
                except Exception as exc:
                    logger.warning("Could not capture official product visuals for %s: %s", product, exc)
                    continue
        finally:
            browser.close()

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if material_records:
        script_path = task_dir / "script.json"
        try:
            payload = json.loads(script_path.read_text(encoding="utf-8"))
            records = payload.setdefault("material_sources", [])
            existing = {item.get("local_file") for item in records if isinstance(item, dict)}
            records.extend(item for item in material_records if item["local_file"] not in existing)
            script_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not add official product visuals to source manifest: %s", exc)
    return clips
