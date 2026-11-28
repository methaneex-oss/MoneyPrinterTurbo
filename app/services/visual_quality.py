"""Lightweight frame-sampling diagnostics for generated videos.

This module inspects decoded pixels with Pillow/MoviePy only. It does not claim
semantic understanding: it detects technical defects and repeated-looking frames
so the pipeline can report actionable warnings without blocking video delivery.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image, ImageFilter, ImageStat
from moviepy.video.io.VideoFileClip import VideoFileClip


def _frame_metrics(frame: Any) -> tuple[float, float, float, int]:
    image = Image.fromarray(frame).convert("L")
    image.thumbnail((320, 320))
    stats = ImageStat.Stat(image)
    brightness = float(stats.mean[0])
    contrast = float(stats.stddev[0])

    edges = image.filter(ImageFilter.FIND_EDGES)
    edge_activity = float(ImageStat.Stat(edges).mean[0])

    tiny = image.resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(tiny.get_flattened_data())
    average = sum(pixels) / len(pixels)
    fingerprint = sum(1 << index for index, value in enumerate(pixels) if value >= average)
    return brightness, contrast, edge_activity, fingerprint


def _frames_are_near_duplicates(first: tuple, second: tuple) -> bool:
    """Compare perceptual structure and luminance to avoid black/white collisions."""
    brightness_delta = abs(first[0] - second[0])
    hash_distance = (first[3] ^ second[3]).bit_count()
    return brightness_delta <= 16 and hash_distance <= 3


def _parse_aspect_ratio(value: Any) -> float | None:
    if isinstance(value, (tuple, list)) and len(value) == 2:
        try:
            width, height = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
        return width / height if width > 0 and height > 0 else None
    if isinstance(value, str) and ":" in value:
        try:
            width, height = (float(part.strip()) for part in value.split(":", 1))
        except (TypeError, ValueError):
            return None
        return width / height if width > 0 and height > 0 else None
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return None
    return ratio if ratio > 0 else None


def _sample_audio_peak(audio_clip: Any, sample_count: int = 12) -> float | None:
    if audio_clip is None:
        return None
    duration = float(getattr(audio_clip, "duration", 0) or 0)
    if duration <= 0:
        return 0.0
    sample_count = max(2, min(int(sample_count), 24))
    margin = min(0.05, duration / 20)
    timestamps = [
        margin + (duration - 2 * margin) * index / (sample_count - 1)
        for index in range(sample_count)
    ]
    peak = 0.0
    for timestamp in timestamps:
        # Inspect a short window rather than one point: a valid tone can cross
        # zero at a regular sampling instant and otherwise look falsely silent.
        window = np.clip(
            timestamp + np.linspace(-0.02, 0.02, 33), 0.0, duration
        )
        try:
            sample = np.asarray(audio_clip.get_frame(window), dtype=np.float32)
        except (TypeError, ValueError):
            sample = np.asarray(
                [audio_clip.get_frame(float(point)) for point in window],
                dtype=np.float32,
            )
        if sample.size:
            peak = max(peak, float(np.max(np.abs(sample))))
    return peak


def inspect_video_quality(
    video_path: str,
    sample_count: int = 12,
    *,
    expected_aspect_ratio: Any = None,
    require_audio: bool = False,
) -> dict:
    """Sample frames and report visual defects, aspect mismatch and audio absence."""
    sample_count = max(2, min(int(sample_count), 24))
    clip = VideoFileClip(video_path)
    try:
        duration = float(clip.duration or 0)
        if duration <= 0:
            raise ValueError("video has no positive duration")
        width, height = int(clip.w), int(clip.h)
        actual_aspect_ratio = width / height if height > 0 else 0.0
        audio_clip = clip.audio
        audio_duration = (
            float(audio_clip.duration or 0) if audio_clip is not None else 0.0
        )
        audio_peak = _sample_audio_peak(audio_clip, sample_count)

        # Avoid exact endpoints: some codecs cannot decode the final timestamp.
        margin = min(0.05, duration / 20)
        timestamps = [
            margin + (duration - 2 * margin) * index / (sample_count - 1)
            for index in range(sample_count)
        ]
        metrics = [_frame_metrics(clip.get_frame(timestamp)) for timestamp in timestamps]
    finally:
        clip.close()

    black_frames = sum(brightness < 12 for brightness, _, _, _ in metrics)
    flat_frames = sum(contrast < 5 and edge_activity < 2 for _, contrast, edge_activity, _ in metrics)

    duplicate_pairs = 0
    duplicate_sample_indices = set()
    for index in range(1, len(metrics)):
        previous = metrics[index - 1][3]
        current = metrics[index][3]
        if _frames_are_near_duplicates(metrics[index - 1], metrics[index]):
            duplicate_pairs += 1
            duplicate_sample_indices.update((index - 1, index))

    report = {
        "sample_count": len(metrics),
        "duration_seconds": round(duration, 2),
        "width": width,
        "height": height,
        "aspect_ratio": round(actual_aspect_ratio, 4),
        "has_audio": audio_clip is not None,
        "audio_duration_seconds": round(audio_duration, 2),
        "sampled_audio_peak": round(audio_peak, 5) if audio_peak is not None else None,
        "black_frame_samples": black_frames,
        "low_detail_samples": flat_frames,
        "near_duplicate_adjacent_pairs": duplicate_pairs,
        "visual_variety_ratio": round(
            (len(metrics) - len(duplicate_sample_indices)) / len(metrics), 3
        ),
    }
    flags = []
    if black_frames:
        flags.append("possible_black_frames")
    if flat_frames:
        flags.append("low_detail_frames")
    if duplicate_pairs >= max(2, len(metrics) // 4):
        flags.append("repeated_visuals")
    expected_ratio = _parse_aspect_ratio(expected_aspect_ratio)
    if expected_ratio is not None and abs(actual_aspect_ratio - expected_ratio) > 0.02:
        flags.append("unexpected_aspect_ratio")
    if require_audio and audio_clip is None:
        flags.append("missing_audio")
    elif require_audio and (audio_duration <= 0 or (audio_peak or 0.0) < 0.001):
        flags.append("silent_or_invalid_audio")
    elif audio_clip is not None and abs(audio_duration - duration) > 1.0:
        flags.append("audio_video_duration_mismatch")
    report["flags"] = flags
    return report
