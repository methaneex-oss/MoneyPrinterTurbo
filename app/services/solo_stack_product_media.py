"""Build episode product visuals from verified captures and official public pages.

Operator-supplied screenshots and screen recordings take priority; public
allowlisted vendor imagery fills remaining slots. This service never logs into
third-party accounts, fabricates interfaces, or labels marketing imagery as an
authenticated in-app demonstration.
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
    "Gemini": {
        "aliases": ("gemini", "google gemini"),
        "url": "https://gemini.google.com/",
        "domain": "gemini.google.com",
    },
    "Google Workspace": {
        "aliases": ("google workspace", "workspace by google"),
        "url": "https://workspace.google.com/",
        "domain": "workspace.google.com",
    },
    "Microsoft 365": {
        "aliases": ("microsoft 365", "office 365"),
        "url": "https://www.microsoft.com/microsoft-365",
        "domain": "microsoft.com",
    },
    "Asana": {
        "aliases": ("asana",),
        "url": "https://asana.com/product/ai",
        "domain": "asana.com",
    },
    "Trello": {
        "aliases": ("trello",),
        "url": "https://trello.com/",
        "domain": "trello.com",
    },
    "Airtable": {
        "aliases": ("airtable",),
        "url": "https://www.airtable.com/platform",
        "domain": "airtable.com",
    },
    "Slack": {
        "aliases": ("slack",),
        "url": "https://slack.com/features/ai",
        "domain": "slack.com",
    },
    "Make": {
        "aliases": ("make.com", "make automation"),
        "url": "https://www.make.com/en",
        "domain": "make.com",
    },
    "n8n": {
        "aliases": ("n8n",),
        "url": "https://n8n.io/",
        "domain": "n8n.io",
    },
    "Loom": {
        "aliases": ("loom",),
        "url": "https://www.loom.com/",
        "domain": "loom.com",
    },
    "Descript": {
        "aliases": ("descript",),
        "url": "https://www.descript.com/",
        "domain": "descript.com",
    },
    "Calendly": {
        "aliases": ("calendly",),
        "url": "https://calendly.com/features",
        "domain": "calendly.com",
    },
    "HubSpot": {
        "aliases": ("hubspot",),
        "url": "https://www.hubspot.com/products/ai",
        "domain": "hubspot.com",
    },
    "GitHub Copilot": {
        "aliases": ("github copilot", "copilot for github"),
        "url": "https://github.com/features/copilot",
        "domain": "github.com",
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


def interleave_product_visuals(existing_clips: list[str], product_clips: list[str]) -> list[str]:
    """Distribute product evidence clips through the existing episode timeline."""
    existing = list(existing_clips or [])
    visuals = list(product_clips or [])
    if not visuals:
        return existing
    result = []
    cursor = 0
    for index, clip in enumerate(visuals):
        position = int((index + 1) * (len(existing) + 1) / (len(visuals) + 1))
        result.extend(existing[cursor:position])
        result.append(clip)
        cursor = position
    result.extend(existing[cursor:])
    return result


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


def _make_editorial_card(
    source: Path,
    output: Path,
    product: str,
    aspect: str,
    source_host: str,
    source_label: str = "OFFICIAL PRODUCT VISUAL",
) -> None:
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
    if portrait:
        # A portrait operator capture should use the available vertical canvas,
        # not be shrunk into the same shallow landscape card as a desktop image.
        with Image.open(source) as source_image:
            source_ratio = source_image.width / max(1, source_image.height)
        if source_ratio < 1.15:
            panel_y, panel_h = 250, 1320
        else:
            panel_y, panel_h = 600, 640
    else:
        panel_h, panel_y = 760, 190
    image = _fit_image(source, (panel_w - 28, panel_h - 28))
    canvas.paste(image, (margin + 14, panel_y + 14))
    draw.rounded_rectangle(
        (margin, panel_y, margin + panel_w, panel_y + panel_h),
        radius=22, outline="#46D3E7", width=5,
    )
    footer_y = panel_y + panel_h + (90 if portrait else 60)
    draw.text((margin, footer_y), source_label, fill="#46D3E7", font=small)
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


def _render_video_capture_clip(
    source: Path,
    output: Path,
    duration: float,
    aspect: str,
    fps: int = 30,
) -> None:
    """Normalize a genuine screen recording without stretching its UI."""
    width, height = (1080, 1920) if aspect in {"9:16", "portrait"} else (1920, 1080)
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
        "-t", str(max(1.0, min(float(duration), 8.0))),
        "-map", "0:v:0",
        "-vf", (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=#101827,"
            f"fps={fps},format=yuv420p"
        ),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, timeout=120)


def prepare_episode_product_visuals(
    task_id: str,
    subject: str,
    script: str,
    terms=None,
    aspect: str = "9:16",
    duration: float = 4.0,
    max_products: int = 2,
) -> list[str]:
    """Prepare product visuals, preferring verified operator captures.

    Verified screenshots and screen recordings from the persistent Solo Stack
    asset library are used first. Public official product-page imagery fills
    remaining slots. The function never logs into third-party accounts or
    presents marketing images as authenticated task recordings.
    """
    products = identify_products(subject, script, terms, limit=max_products)
    if not products:
        return []

    from app.services import solo_stack_assets
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
    clips: list[str] = []
    material_records: list[dict] = []
    user_capture_counts: dict[str, int] = {}

    # Operator-provided screenshots and screen recordings take priority. The
    # asset service verifies the original file against its SHA-256 manifest.
    try:
        verified_assets = solo_stack_assets.verified_assets_for_products(
            utils.storage_dir("solo_stack"), products
        )
    except (OSError, solo_stack_assets.SoloStackAssetError) as exc:
        logger.warning("Solo Stack asset library unavailable: %s", exc)
        verified_assets = []

    assets_by_product: dict[str, list[dict]] = {}
    for asset in verified_assets:
        if asset.get("asset_type") == "logo":
            continue
        product_key = str(asset.get("product", "")).casefold()
        assets_by_product.setdefault(product_key, []).append(asset)

    for product in products:
        product_dir = media_dir / re.sub(r"[^a-z0-9]+", "-", product.casefold()).strip("-")
        product_dir.mkdir(parents=True, exist_ok=True)
        product_slug = re.sub(r"[^a-z0-9]+", "-", product.casefold()).strip("-")
        selected_assets = assets_by_product.get(product.casefold(), [])[:_MAX_IMAGES_PER_PRODUCT]
        rendered_count = 0

        for asset_index, asset in enumerate(selected_assets, start=1):
            card = None
            clip = None
            try:
                source = Path(asset["path"])
                source_host = (
                    urlparse(str(asset.get("source_url") or "")).hostname
                    or "USER-SUPPLIED CAPTURE"
                )
                if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    card = product_dir / f"user-capture-card-{asset_index}.jpg"
                    clip = product_dir / f"{product_slug}-real-app-capture-{asset_index}.mp4"
                    _make_editorial_card(
                        source, card, product, aspect, source_host,
                        source_label="USER-CAPTURED APP VISUAL",
                    )
                    _render_still_clip(card, clip, duration, aspect)
                else:
                    clip = product_dir / f"{product_slug}-screen-recording-{asset_index}.mp4"
                    _render_video_capture_clip(source, clip, duration, aspect)
            except Exception as exc:
                if card is not None:
                    card.unlink(missing_ok=True)
                if clip is not None:
                    clip.unlink(missing_ok=True)
                logger.warning(
                    "Could not render operator capture %s for %s; trying other visuals: %s",
                    asset.get("asset_id", "unknown"),
                    product,
                    exc,
                )
                continue

            clips.append(str(clip))
            rendered_count += 1
            manifest["assets"].append({
                "product": product,
                "asset_type": "operator_capture",
                "source_asset_type": asset.get("asset_type"),
                "source_asset_id": asset.get("asset_id"),
                "source_asset_file": asset.get("file"),
                "rendered_clip": str(clip.relative_to(task_dir)),
                "source_page": asset.get("source_url"),
                "sha256": asset.get("sha256"),
                "captured_at": asset.get("captured_at"),
                "note": (
                    "Operator-supplied app capture; original bytes verified "
                    "against the persistent Solo Stack asset-library manifest."
                ),
            })
            material_records.append({
                "local_file": clip.name,
                "search_term": f"{product} real app screen capture",
                "source_kind": "solo_stack_product_evidence",
                "product": product,
            })

        user_capture_counts[product] = rendered_count

    # Public vendor pages are a fallback/complement, not a replacement for
    # authentic operator-supplied recordings. Do not launch Chromium when all
    # named products already have enough verified captures.
    products_needing_public_visuals = [
        product for product in products
        if user_capture_counts.get(product, 0) < _MAX_IMAGES_PER_PRODUCT
    ]
    sync_playwright = None
    if products_needing_public_visuals:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            if not clips:
                raise RuntimeError(
                    "Solo Stack official product visuals require Playwright; "
                    "the Colab setup cell must install it first."
                ) from exc
            logger.warning(
                "Playwright is unavailable; continuing with verified operator captures"
            )

    if sync_playwright is not None:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    page = browser.new_page(
                        viewport={"width": 1080, "height": 1920},
                        device_scale_factor=1,
                        locale="en-US",
                    )
                    for product in products_needing_public_visuals:
                        remaining = _MAX_IMAGES_PER_PRODUCT - user_capture_counts.get(product, 0)
                        if remaining <= 0:
                            continue
                        try:
                            spec = PRODUCTS[product]
                            product_dir = media_dir / re.sub(
                                r"[^a-z0-9]+", "-", product.casefold()
                            ).strip("-")
                            product_dir.mkdir(parents=True, exist_ok=True)
                            page.goto(spec["url"], wait_until="domcontentloaded", timeout=45000)
                            page.wait_for_timeout(2500)
                            page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(900)
                            source_page = page.url
                            parsed = urlparse(source_page)
                            if parsed.scheme != "https" or not (
                                parsed.hostname == spec["domain"]
                                or parsed.hostname.endswith("." + spec["domain"])
                            ):
                                logger.warning(
                                    "Official page redirected outside its allowlisted domain: %s",
                                    source_page,
                                )
                                continue

                            images = _download_page_images(page, product_dir)[:remaining]
                            if not images:
                                screenshot = product_dir / "official-product-page.png"
                                page.screenshot(path=str(screenshot), full_page=False)
                                images = [(screenshot, source_page)]

                            product_slug = re.sub(
                                r"[^a-z0-9]+", "-", product.casefold()
                            ).strip("-")
                            start_index = user_capture_counts.get(product, 0) + 1
                            for image_index, (source_image, image_url) in enumerate(
                                images, start=start_index
                            ):
                                card = product_dir / f"visual-card-{image_index}.jpg"
                                clip = product_dir / (
                                    f"{product_slug}-product-visual-{image_index}.mp4"
                                )
                                _make_editorial_card(
                                    source_image, card, product, aspect, spec["domain"]
                                )
                                _render_still_clip(card, clip, duration, aspect)
                                digest = hashlib.sha256(source_image.read_bytes()).hexdigest()
                                manifest["assets"].append({
                                    "product": product,
                                    "asset_type": (
                                        "official_product_page_image"
                                        if image_url != source_page
                                        else "official_product_page_capture"
                                    ),
                                    "file": str(source_image.relative_to(task_dir)),
                                    "rendered_clip": str(clip.relative_to(task_dir)),
                                    "source_page": source_page,
                                    "source_asset_url": image_url,
                                    "sha256": digest,
                                    "captured_at": manifest["captured_at"],
                                    "note": (
                                        "Public official-site visual; not an authenticated "
                                        "in-app task recording."
                                    ),
                                })
                                clips.append(str(clip))
                                material_records.append({
                                    "local_file": clip.name,
                                    "search_term": f"{product} official product interface",
                                    "source_kind": "solo_stack_product_evidence",
                                    "product": product,
                                })
                        except Exception as exc:
                            logger.warning(
                                "Could not capture official product visuals for %s: %s",
                                product,
                                exc,
                            )
                            continue
                finally:
                    browser.close()
        except Exception as exc:
            logger.warning(
                "Public product-page capture unavailable; preserving verified "
                "operator captures: %s",
                exc,
            )

    product_coverage = []
    for product in products:
        product_assets = [
            asset for asset in manifest["assets"]
            if str(asset.get("product") or "").casefold() == product.casefold()
        ]
        product_coverage.append({
            "product": product,
            "visual_count": len(product_assets),
            "sources": sorted({
                str(asset.get("asset_type") or "unknown")
                for asset in product_assets
            }),
            "status": "available" if product_assets else "missing",
        })
    manifest["product_coverage"] = product_coverage
    manifest["missing_products"] = [
        item["product"] for item in product_coverage
        if item["status"] == "missing"
    ]
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    script_path = task_dir / "script.json"
    try:
        payload = json.loads(script_path.read_text(encoding="utf-8"))
        payload["product_visual_coverage"] = product_coverage
        payload["product_visual_manifest"] = str(manifest_path.relative_to(task_dir))
        records = payload.setdefault("material_sources", [])
        existing = {
            item.get("local_file")
            for item in records if isinstance(item, dict)
        }
        records.extend(
            item for item in material_records
            if item["local_file"] not in existing
        )
        script_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, TypeError) as exc:
        logger.warning(
            "Could not persist Solo Stack product visual coverage: %s",
            exc,
        )
    return clips
