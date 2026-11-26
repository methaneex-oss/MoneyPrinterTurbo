"""Topic-aware image and video retrieval for Solo Stack episodes.

Uses free Pixabay and Wikimedia Commons search, stores source/licence metadata,
downloads validated image/video bytes, and renders local motion clips. Retrieved
stock/Commons media are supporting visuals only; they never count as authentic
product-interface evidence.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from PIL import Image

logger = logging.getLogger(__name__)

_CACHE_SECONDS = 24 * 60 * 60
_MAX_SCENES = 4
_MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
_MAX_VIDEO_DOWNLOAD_BYTES = 40 * 1024 * 1024
_ALLOWED_IMAGE_HOSTS = {"cdn.pixabay.com", "pixabay.com", "upload.wikimedia.org"}
_ALLOWED_VIDEO_HOSTS = {"cdn.pixabay.com", "pixabay.com", "upload.wikimedia.org"}
_STOP = {
    "about", "after", "also", "and", "are", "because", "before", "but", "can",
    "could", "does", "for", "from", "how", "into", "its", "more", "not", "our",
    "should", "that", "the", "their", "them", "then", "there", "these", "this",
    "those", "through", "using", "what", "when", "where", "which", "while",
    "with", "would", "your",
}


def _tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(
            r"[a-z0-9][a-z0-9.+#_-]*", str(value or "").casefold()
        )
        if len(token) > 1 and token not in _STOP
    ]


def build_scene_queries(
    subject: str, script: str, terms=None, limit: int = _MAX_SCENES
) -> list[str]:
    """Create ordered, script-grounded queries without a fixed product catalogue."""
    sentences = [
        re.sub(r"\s+", " ", part).strip(" -\t")
        for part in re.split(r"(?<=[.!?])\s+|\n+", str(script or ""))
    ]
    sentences = [part for part in sentences if len(_tokens(part)) >= 3]
    if not sentences and subject:
        sentences = [str(subject).strip()]
    try:
        maximum = max(1, min(int(limit), _MAX_SCENES))
    except (TypeError, ValueError):
        maximum = _MAX_SCENES

    queries: list[str] = []
    for sentence in sentences:
        tokens = _tokens(sentence)
        if not tokens:
            continue
        # Keep technical names and multi-word phrases intact; trim narration
        # filler rather than turning each scene into the same broad subject query.
        phrase = " ".join(tokens[:9])
        query = phrase[:100].strip()
        if query and query.casefold() not in {item.casefold() for item in queries}:
            queries.append(query)
        if len(queries) >= maximum:
            break

    if not queries and subject:
        queries = [str(subject).strip()[:100]]
    if terms:
        extras = [terms] if isinstance(terms, str) else list(terms)
        for item in extras:
            candidate = str(item or "").strip()[:100]
            if candidate and candidate.casefold() not in {
                query.casefold() for query in queries
            }:
                queries.append(candidate)
            if len(queries) >= maximum:
                break
    return queries[:maximum]


def _cache_path(cache_dir: Path, query: str, provider: str) -> Path:
    cache_key = (provider + ":" + query.casefold()).encode("utf-8")
    digest = hashlib.sha256(cache_key).hexdigest()
    return cache_dir / f"{provider}-{digest}.json"


def _read_cache(path: Path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(payload.get("cached_at", 0)) < _CACHE_SECONDS:
            return payload.get("items", [])
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def _write_cache(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(
            {"cached_at": time.time(), "items": items},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _pixabay_search(query: str, cache_dir: Path, api_key: str) -> list[dict]:
    cache = _cache_path(cache_dir, query, "pixabay")
    cached = _read_cache(cache)
    if cached is not None:
        return cached
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": api_key, "q": query, "image_type": "photo",
            "orientation": "all", "safesearch": "true",
            "per_page": 12, "min_width": 640, "min_height": 360,
        },
        timeout=(10, 25),
    )
    response.raise_for_status()
    payload = response.json()
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    items = []
    for hit in hits if isinstance(hits, list) else []:
        if not isinstance(hit, dict):
            continue
        items.append({
            "provider": "pixabay",
            "asset_id": str(hit.get("id") or ""),
            "query": query,
            "image_url": hit.get("largeImageURL") or hit.get("webformatURL"),
            "source_url": hit.get("pageURL"),
            "title": hit.get("tags") or query,
            "tags": hit.get("tags") or "",
            "creator": hit.get("user") or "",
            "license": "Pixabay Content License",
            "attribution": f"{hit.get('user') or 'Contributor'} via Pixabay",
            "width": hit.get("imageWidth") or hit.get("webformatWidth") or 0,
            "height": hit.get("imageHeight") or hit.get("webformatHeight") or 0,
        })
    _write_cache(cache, items)
    return items


def _commons_search(query: str, cache_dir: Path) -> list[dict]:
    cache = _cache_path(cache_dir, query, "commons")
    cached = _read_cache(cache)
    if cached is not None:
        return cached
    response = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
            "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata",
            "iiurlwidth": 1280,
        },
        headers={
            "User-Agent": (
                "SoloStackVisualResearch/1.0 "
                "(https://github.com/methaneex-oss/MoneyPrinterTurbo)"
            )
        },
        timeout=(10, 25),
    )
    response.raise_for_status()
    payload = response.json()
    pages = (payload.get("query") or {}).get("pages") or {}
    items = []
    for page in pages.values() if isinstance(pages, dict) else []:
        if not isinstance(page, dict):
            continue
        info_list = page.get("imageinfo") or []
        if not isinstance(info_list, list) or not info_list:
            continue
        if not isinstance(info_list[0], dict):
            continue
        info = info_list[0]
        meta = info.get("extmetadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        def meta_value(key):
            value = meta.get(key) or {}
            return re.sub(r"<[^>]+>", "", str(value.get("value") or "")).strip()
        items.append({
            "provider": "wikimedia_commons",
            "asset_id": str(page.get("pageid") or ""),
            "query": query,
            "image_url": info.get("thumburl") or info.get("url"),
            "source_url": info.get("descriptionurl"),
            "title": page.get("title") or query,
            "tags": page.get("title") or "",
            "creator": meta_value("Artist"),
            "license": meta_value("LicenseShortName") or "License not identified",
            "attribution": meta_value("AttributionRequired") or meta_value("Artist"),
            "width": info.get("thumbwidth") or info.get("width") or 0,
            "height": info.get("thumbheight") or info.get("height") or 0,
        })
    _write_cache(cache, items)
    return items



def _pixabay_video_search(query: str, cache_dir: Path, api_key: str) -> list[dict]:
    """Search Pixabay's video catalogue; videos retain source/licence metadata."""
    cache = _cache_path(cache_dir, query, "pixabay_video")
    cached = _read_cache(cache)
    if cached is not None:
        return cached
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={
            "key": api_key, "q": query, "safesearch": "true",
            "per_page": 12, "min_width": 640, "min_height": 360,
        },
        timeout=(10, 25),
    )
    response.raise_for_status()
    payload = response.json()
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    items = []
    for hit in hits if isinstance(hits, list) else []:
        if not isinstance(hit, dict):
            continue
        variants = hit.get("videos") or {}
        variant = variants.get("medium") or variants.get("large") or variants.get("small") or {}
        if not isinstance(variant, dict):
            continue
        items.append({
            "provider": "pixabay_video",
            "asset_id": str(hit.get("id") or ""),
            "query": query,
            "video_url": variant.get("url"),
            "source_url": hit.get("pageURL"),
            "title": hit.get("tags") or query,
            "tags": hit.get("tags") or "",
            "creator": hit.get("user") or "",
            "license": "Pixabay Content License",
            "attribution": f"{hit.get('user') or 'Contributor'} via Pixabay",
            "width": variant.get("width") or 0,
            "height": variant.get("height") or 0,
            "duration": hit.get("duration") or 0,
        })
    _write_cache(cache, items)
    return items


def _download_video(item: dict, destination: Path) -> Path | None:
    """Download a bounded Pixabay video; reject redirects outside approved hosts."""
    url = item.get("video_url")
    try:
        parsed = urlparse(str(url or ""))
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_VIDEO_HOSTS
            or parsed.username is not None or parsed.password is not None
            or (parsed.port is not None and parsed.port != 443)
        ):
            return None
        response = requests.get(str(url), stream=True, timeout=(10, 30))
        try:
            final_url = urlparse(response.url)
            if (
                final_url.scheme != "https"
                or final_url.hostname not in _ALLOWED_VIDEO_HOSTS
                or final_url.username is not None or final_url.password is not None
            ):
                return None
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if not (content_type.startswith("video/") or content_type == "application/octet-stream"):
                return None
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > _MAX_VIDEO_DOWNLOAD_BYTES:
                    return None
                chunks.append(chunk)
            body = b"".join(chunks)
            if not body:
                return None
        finally:
            response.close()
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = destination.with_suffix(".mp4")
        target.write_bytes(body)
        # ffprobe must confirm a decodable video stream before accepting the file.
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration", "-of", "json", str(target)],
            check=True, capture_output=True, timeout=30,
        )
        stream_data = json.loads(probe.stdout.decode("utf-8", errors="replace"))
        if not (stream_data.get("streams") or []):
            target.unlink(missing_ok=True)
            return None
        return target
    except (OSError, ValueError, requests.RequestException, subprocess.SubprocessError) as exc:
        logger.debug("Skipping invalid dynamic video candidate: %s", type(exc).__name__)
        try:
            destination.with_suffix(".mp4").unlink(missing_ok=True)
        except OSError:
            pass
        return None


def _render_video_clip(
    source_path: Path, output_path: Path, duration: float, aspect: str
) -> None:
    width, height = (1080, 1920) if aspect in {"9:16", "portrait"} else (1920, 1080)
    safe_duration = max(2.0, min(float(duration), 6.0))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1",
         "-i", str(source_path), "-t", str(safe_duration),
         "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
         f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=#101827,"
         "fps=30,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-movflags", "+faststart", str(output_path)],
        check=True, capture_output=True, timeout=120,
    )


def _commons_video_search(query: str, cache_dir: Path) -> list[dict]:
    """Search Wikimedia Commons video files and preserve their licence metadata."""
    cache = _cache_path(cache_dir, query, "commons_video")
    cached = _read_cache(cache)
    if cached is not None:
        return cached
    response = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:video {query}", "gsrnamespace": 6,
            "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata",
        },
        headers={"User-Agent": "SoloStackVisualResearch/1.0 (https://github.com/methaneex-oss/MoneyPrinterTurbo)"},
        timeout=(10, 25),
    )
    response.raise_for_status()
    payload = response.json()
    pages = (payload.get("query") or {}).get("pages") or {}
    items = []
    for page in pages.values() if isinstance(pages, dict) else []:
        info_list = page.get("imageinfo") or []
        if not info_list or not isinstance(info_list[0], dict):
            continue
        info = info_list[0]
        media_url = info.get("url")
        if not media_url:
            continue
        meta = info.get("extmetadata") or {}
        def meta_value(key):
            value = meta.get(key) or {}
            return re.sub(r"<[^>]+>", "", str(value.get("value") or "")).strip()
        items.append({
            "provider": "wikimedia_commons_video",
            "asset_id": str(page.get("pageid") or ""),
            "query": query,
            "video_url": media_url,
            "source_url": info.get("descriptionurl"),
            "title": page.get("title") or query,
            "tags": page.get("title") or "",
            "creator": meta_value("Artist"),
            "license": meta_value("LicenseShortName") or "License not identified",
            "attribution": meta_value("AttributionRequired") or meta_value("Artist"),
            "width": info.get("width") or 0,
            "height": info.get("height") or 0,
        })
    _write_cache(cache, items)
    return items


def _vision_review_candidate(query: str, candidate: dict, media_path: Path) -> dict:
    """Optional independent multimodal reviewer; configure via environment only."""
    import base64
    import os

    base = os.getenv("SOLO_STACK_VISION_API_BASE", "").strip()
    model = os.getenv("SOLO_STACK_VISION_MODEL", "").strip()
    key = os.getenv("SOLO_STACK_VISION_API_KEY", "").strip()
    if not base or not model:
        return {"enabled": False, "score": 0, "reason": "vision reviewer not configured"}
    try:
        from PIL import Image
        frame_path = media_path
        if media_path.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
            frame_path = media_path.with_suffix(".review.jpg")
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i",
                 str(media_path), "-frames:v", "1", "-vf", "scale=768:-1",
                 str(frame_path)],
                check=True, capture_output=True, timeout=30,
            )
        with Image.open(frame_path) as im:
            im.thumbnail((768, 768))
            buffer = io.BytesIO()
            im.convert("RGB").save(buffer, format="JPEG", quality=82)
        data = base64.b64encode(buffer.getvalue()).decode("ascii")
        endpoint = base.rstrip("/")
        if endpoint.endswith("/v1"):
            endpoint += "/chat/completions"
        elif endpoint.endswith("/api"):
            endpoint += "/chat"
        else:
            endpoint += "/v1/chat/completions"
        prompt = (
            "You are an independent visual asset reviewer for an educational video. "
            "Judge the attached image/frame against the scene requirement, not its filename. "
            "Reject generic, unrelated, misleading, wrong-product, or merely keyword-matching "
            "images. If a named product/UI is required, verify that it visibly depicts that "
            "specific product/interface and feature; do not infer authenticity from appearance. "
            "Return JSON only: {score:0-100, relevant:true/false, depicts_requested_subject:true/false, "
            "authentic_product_ui:false, reason:'brief', visible_subject:'brief'}. "
            "Requirement: " + query + " Candidate title/tags: " +
            str(candidate.get("title") or candidate.get("tags") or "")
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}"} if key else {},
            json={"model": model, "temperature": 0,
                  "messages":[{"role":"user","content":[
                      {"type":"text","text":prompt},
                      {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+data}}
                  ]}]},
            timeout=(15, 60),
        )
        response.raise_for_status()
        payload=response.json()
        content=payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        match=re.search(r"\{.*\}", str(content), re.S)
        if not match:
            return {"enabled": True, "score": 0, "reason": "reviewer returned non-JSON"}
        result=json.loads(match.group(0))
        score=max(0,min(100,int(result.get("score",0))))
        return {"enabled":True,"score":score,
                "relevant":bool(result.get("relevant")),
                "depicts_requested_subject":bool(result.get("depicts_requested_subject")),
                "authentic_product_ui":bool(result.get("authentic_product_ui")),
                "reason":str(result.get("reason",""))[:400],
                "visible_subject":str(result.get("visible_subject",""))[:200],
                "model":model}
    except Exception as exc:
        logger.warning("Visual AI review failed: %s", type(exc).__name__)
        return {"enabled":True,"score":0,"reason":"review failed: "+type(exc).__name__}


def _candidate_score(query: str, item: dict) -> int:
    query_terms = set(_tokens(query))
    candidate_text = " ".join(
        str(item.get(key) or "") for key in ("title", "tags", "source_url")
    )
    candidate_terms = set(_tokens(candidate_text))
    return len(query_terms & candidate_terms)


def _license_is_usable(item: dict) -> bool:
    """Only use sources with a known licence suitable for edited video."""
    if item.get("provider") in {"pixabay", "pixabay_video"}:
        return True
    license_name = str(item.get("license") or "").casefold()
    restricted_markers = (
        "noncommercial", "non-commercial", "cc by-nd", "cc-by-nd",
        "cc by-nc", "cc-by-nc",
    )
    if any(marker in license_name for marker in restricted_markers):
        return False
    return (
        "public domain" in license_name
        or "cc0" in license_name
        or "cc by 4.0" in license_name
        or "cc-by-4.0" in license_name
        or "cc by-sa 4.0" in license_name
        or "cc-by-sa-4.0" in license_name
    )


def _download_image(item: dict, destination: Path) -> Path | None:
    url = item.get("image_url")
    try:
        parsed = urlparse(str(url or ""))
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_IMAGE_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or (parsed.port is not None and parsed.port != 443)
        ):
            return None
        response = requests.get(str(url), stream=True, timeout=(10, 30))
        try:
            final_url = urlparse(response.url)
            if (
                final_url.scheme != "https"
                or final_url.hostname not in _ALLOWED_IMAGE_HOSTS
                or final_url.username is not None
                or final_url.password is not None
            ):
                return None
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            content_type = content_type.split(";", 1)[0].lower()
            if not content_type.startswith("image/"):
                return None
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > _MAX_DOWNLOAD_BYTES:
                    return None
                chunks.append(chunk)
            body = b"".join(chunks)
            if not body:
                return None
        finally:
            response.close()
        with Image.open(io.BytesIO(body)) as image:
            if (
                image.width < 320
                or image.height < 180
                or image.width * image.height > 40_000_000
            ):
                return None
            image_format = image.format
            image.verify()
        extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image_format)
        if not extension:
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = destination.with_suffix(extension)
        target.write_bytes(body)
        return target
    except (
        OSError,
        ValueError,
        requests.RequestException,
        Image.DecompressionBombError,
    ) as exc:
        logger.debug(
            "Skipping invalid dynamic visual candidate: %s", type(exc).__name__
        )
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def _render_motion_clip(
    image_path: Path, output_path: Path, duration: float, aspect: str
) -> None:
    width, height = (1080, 1920) if aspect in {"9:16", "portrait"} else (1920, 1080)
    fps = 30
    frames = max(1, int(max(2.0, min(float(duration), 6.0)) * fps))
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps),
            "-i", str(image_path),
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=#101827,"
                f"zoompan=z='min(zoom+0.00025,1.02)':"
                f"d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
            ),
            "-frames:v", str(frames), "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "22", "-movflags", "+faststart",
            str(output_path),
        ],
        check=True, capture_output=True, timeout=90,
    )


def prepare_dynamic_scene_visuals(
    task_id: str,
    subject: str,
    script: str,
    terms=None,
    aspect: str = "9:16",
    duration: float = 3.5,
    max_scenes: int = _MAX_SCENES,
) -> list[str]:
    """Find supporting stills; mark non-evidence, never authenticated product UI."""
    from app.services.material import get_api_key
    from app.utils import utils

    task_dir = Path(utils.task_dir(task_id)).resolve()
    root = task_dir / "solo_stack" / "dynamic_visuals"
    cache_dir = root / "cache"
    media_dir = root / "images"
    clips_dir = root / "clips"
    for directory in (cache_dir, media_dir, clips_dir):
        directory.mkdir(parents=True, exist_ok=True)

    try:
        api_key = get_api_key("pixabay_api_keys") or ""
    except Exception:
        api_key = ""

    manifest = {"schema_version": 1, "visuals": []}
    clips: list[str] = []
    queries = build_scene_queries(subject, script, terms, limit=max_scenes)
    for scene_index, query in enumerate(queries, start=1):
        candidates = []
        for provider_search in (
            lambda: _pixabay_video_search(query, cache_dir, api_key),
            lambda: _commons_video_search(query, cache_dir),
            lambda: _pixabay_search(query, cache_dir, api_key),
            lambda: _commons_search(query, cache_dir),
        ):
            try:
                candidates.extend(provider_search())
            except Exception as exc:
                logger.warning(
                    "Solo Stack dynamic visual search unavailable (%s): %s",
                    type(exc).__name__, query[:80],
                )
        candidates = [
            item for item in candidates
            if _license_is_usable(item) and _candidate_score(query, item) > 0
        ]
        candidates = sorted(
            candidates,
            key=lambda item: (-_candidate_score(query, item), 0 if item.get("video_url") else 1, item.get("provider", "")),
        )
        reviewed_candidates = []
        candidate_reviews = []
        # Acquire several candidates first; do not stop at the first keyword match.
        for candidate in candidates[:6]:
            asset_name = candidate.get("asset_id") or "asset"
            if candidate.get("video_url"):
                source_path = media_dir / f"scene-{scene_index}-{candidate.get('provider')}-{asset_name}.mp4"
                downloaded = _download_video(candidate, source_path)
                media_type = "video"
            else:
                source_path = media_dir / f"scene-{scene_index}-{candidate.get('provider')}-{asset_name}.img"
                downloaded = _download_image(candidate, source_path)
                media_type = "image"
            if not downloaded:
                continue
            review = _vision_review_candidate(query, candidate, downloaded)
            accepted = bool(
                (review.get("enabled") and review.get("relevant")
                 and review.get("depicts_requested_subject") and review.get("score", 0) >= 72)
                or (not review.get("enabled") and _candidate_score(query, candidate) >= 2)
            )
            candidate_reviews.append({"provider": candidate.get("provider"),
                "asset_id": candidate.get("asset_id"), "source_url": candidate.get("source_url"),
                "review": review, "accepted": accepted})
            # A configured reviewer is mandatory for selection: a model failure or
            # low score cannot silently fall back to keyword relevance.
            if review.get("enabled") and (
                not review.get("relevant") or not review.get("depicts_requested_subject")
                or review.get("score", 0) < 72
            ):
                continue
            if not review.get("enabled") and _candidate_score(query, candidate) < 2:
                continue
            reviewed_candidates.append((candidate, downloaded, media_type, review))
        selected = reviewed_candidates[0] if reviewed_candidates else None
        if not selected:
            manifest["visuals"].append({
                "scene_id": scene_index, "query": query, "status": "unresolved",
                "candidate_reviews": candidate_reviews,
            })
            continue

        candidate, source_path, media_type, review = selected
        clip_path = clips_dir / f"scene-{scene_index}.mp4"
        try:
            if media_type == "video":
                _render_video_clip(source_path, clip_path, duration, aspect)
            else:
                _render_motion_clip(source_path, clip_path, duration, aspect)
        except Exception as exc:
            logger.warning(
                "Could not render dynamic visual clip: %s", type(exc).__name__
            )
            manifest["visuals"].append({
                "scene_id": scene_index,
                "query": query,
                "status": "downloaded_not_rendered",
                "source_url": candidate.get("source_url"),
                "license": candidate.get("license"),
            })
            continue

        record = {
            "scene_id": scene_index, "query": query, "status": "available",
            "provider": candidate.get("provider"),
            "asset_id": candidate.get("asset_id"),
            "file": str(clip_path.relative_to(task_dir)),
            "source_file": str(source_path.relative_to(task_dir)),
            "media_type": media_type,
            "source_url": candidate.get("source_url"),
            "license": candidate.get("license"),
            "creator": candidate.get("creator"),
            "attribution": candidate.get("attribution"),
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "width": candidate.get("width"), "height": candidate.get("height"),
            "is_product_evidence": False,
            "visual_review": review,
            "candidate_reviews": candidate_reviews,
        }
        manifest["visuals"].append(record)
        clips.append(str(clip_path))

    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return clips
