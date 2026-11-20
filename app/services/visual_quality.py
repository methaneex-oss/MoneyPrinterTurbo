"""Lightweight frame-sampling diagnostics for generated videos.

This module inspects decoded pixels with Pillow/MoviePy only. It does not claim
semantic understanding: it detects technical defects and repeated-looking frames
so the pipeline can report actionable warnings without blocking video delivery.
"""
from __future__ import annotations

from typing import Any

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
    pixels = list(tiny.getdata())
    average = sum(pixels) / len(pixels)
    fingerprint = sum(1 << index for index, value in enumerate(pixels) if value >= average)
    return brightness, contrast, edge_activity, fingerprint


def inspect_video_quality(video_path: str, sample_count: int = 12) -> dict:
    """Sample frames and report black/flat frames and near-duplicate samples."""
    sample_count = max(2, min(int(sample_count), 24))
    clip = VideoFileClip(video_path, audio=False)
    try:
        duration = float(clip.duration or 0)
        if duration <= 0:
            raise ValueError("video has no positive duration")

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
        distance = (previous ^ current).bit_count()
        if distance <= 3:
            duplicate_pairs += 1
            duplicate_sample_indices.update((index - 1, index))

    report = {
        "sample_count": len(metrics),
        "duration_seconds": round(duration, 2),
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
    report["flags"] = flags
    return report
