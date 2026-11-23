"""Client for the loopback-only Colab AnimateDiff generation service."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Callable

import requests
from loguru import logger

from app.config import config
from app.services import task_artifacts
from app.utils import utils

DEFAULT_BASE_URL = "http://127.0.0.1:7862"
MAX_SCENE_GENERATIONS = 8
REQUEST_TIMEOUT = (10, 900)
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


class LocalAnimateDiffError(RuntimeError):
    """A local AnimateDiff generation or download failed."""


def base_url(settings=None) -> str:
    settings = settings or config.app
    value = str(settings.get("animatediff_base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL)
    return value.rstrip("/")


def health_check(settings=None, timeout: float = 1.0) -> dict | None:
    try:
        response = requests.get(f"{base_url(settings)}/health", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if payload.get("status") == "ready" else None
    except (requests.RequestException, ValueError, TypeError):
        return None


def is_enabled(settings=None) -> bool:
    return health_check(settings) is not None


def _aspect_name(video_aspect) -> str:
    try:
        width, height = video_aspect.to_resolution()
    except AttributeError:
        value = str(getattr(video_aspect, "value", video_aspect)).lower()
        if "landscape" in value or "16:9" in value:
            return "landscape"
        if "square" in value or "1:1" in value:
            return "square"
        return "portrait"
    if width == height:
        return "square"
    return "landscape" if width > height else "portrait"


def _persist_sources(task_id: str, records: list[dict]) -> None:
    try:
        saved = task_artifacts.patch_script_data(task_id, material_sources=records)
        if not saved:
            logger.warning(f"AnimateDiff source manifest was not saved: task_id={task_id}")
    except Exception as exc:
        logger.warning(
            "could not save AnimateDiff material manifest: "
            f"task_id={task_id}, error={type(exc).__name__}: {exc}"
        )


def generate_videos(
    *,
    task_id: str,
    search_terms: list[str],
    video_aspect,
    audio_duration: float,
    max_clip_duration: int = 5,
    progress_callback: Callable[[float], None] | None = None,
    settings=None,
) -> list[str]:
    """Generate one short AI-video clip per scene term, then return local MP4 paths.

    MoneyPrinterTurbo's compositor handles trimming, ordering, reuse, subtitles,
    graphics, narration and final encoding. The local model is only responsible
    for generating scene footage. The service is never replaced by a paid API.
    """
    terms = [str(term).strip() for term in (search_terms or []) if str(term).strip()]
    if not terms:
        raise LocalAnimateDiffError("No scene prompts were supplied for AnimateDiff")
    if len(terms) > MAX_SCENE_GENERATIONS:
        terms = terms[:MAX_SCENE_GENERATIONS]
    try:
        required_duration = float(audio_duration)
    except (TypeError, ValueError):
        required_duration = 0.0
    if required_duration <= 0:
        raise LocalAnimateDiffError("Narration duration must be positive before video generation")

    status = health_check(settings)
    if status is None:
        raise LocalAnimateDiffError(
            "The local AnimateDiff GPU service is unavailable. Restart the Colab runtime "
            "setup; no paid video provider will be called."
        )

    task_directory = Path(utils.task_dir(task_id))
    task_directory.mkdir(parents=True, exist_ok=True)
    aspect = _aspect_name(video_aspect)
    video_paths: list[str] = []
    records: list[dict] = []
    total = len(terms)

    for index, term in enumerate(terms, start=1):
        prompt = (
            f"Cinematic documentary footage showing {term}. "
            "Photorealistic, coherent natural physical motion, realistic lighting, "
            "professional documentary cinematography, detailed environment, "
            "stable composition, no text or graphics."
        )
        digest = hashlib.sha256(f"{task_id}:{index}:{term}".encode("utf-8")).hexdigest()[:10]
        target = task_directory / f"animatediff-scene-{index:02d}-{digest}.mp4"
        temporary = target.with_suffix(".mp4.part")
        response = None
        try:
            response = requests.post(
                f"{base_url(settings)}/generate",
                json={"prompt": prompt, "aspect": aspect, "seed": int(digest, 16) % (2**32), "steps": 12},
                timeout=REQUEST_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
            if not temporary.is_file() or temporary.stat().st_size < 16_384:
                raise LocalAnimateDiffError(f"AnimateDiff returned an invalid clip for scene {index}")
            with temporary.open("rb") as generated:
                header = generated.read(32)
            if b"ftyp" not in header:
                raise LocalAnimateDiffError(f"AnimateDiff response for scene {index} is not an MP4")
            os.replace(temporary, target)
        except (requests.RequestException, OSError, LocalAnimateDiffError) as exc:
            temporary.unlink(missing_ok=True)
            raise LocalAnimateDiffError(
                f"AnimateDiff scene {index}/{total} failed for '{term[:80]}': {exc}"
            ) from exc
        finally:
            if response is not None:
                response.close()
        video_paths.append(str(target))
        records.append(
            {
                "provider": "animatediff",
                "local_file": target.name,
                "search_term": term,
                "source_url": None,
            }
        )
        if progress_callback is not None:
            progress_callback(index / total)

    _persist_sources(task_id, records)
    logger.success(
        f"AnimateDiff generated {len(video_paths)} local scene clips "
        f"for {required_duration:.1f}s narration"
    )
    return video_paths
