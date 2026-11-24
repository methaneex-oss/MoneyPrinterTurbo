"""Lightweight audio-energy envelope for approximate presenter mouth animation.

This is audio-reactive mouth movement, not phoneme/viseme alignment.
"""
from __future__ import annotations

import numpy as np
from pydub import AudioSegment

from app.utils import utils


def build_audio_activity_envelope(audio_path: str, frame_rate: int = 25) -> list[float]:
    """Decode narration to a compact, normalized RMS activity envelope."""
    if not audio_path or frame_rate < 1:
        return []
    ffmpeg_binary = utils.get_ffmpeg_binary()
    if ffmpeg_binary:
        AudioSegment.converter = ffmpeg_binary
    audio = AudioSegment.from_file(audio_path).set_channels(1).set_frame_rate(8000).set_sample_width(2)
    samples = np.frombuffer(audio.raw_data, dtype="<i2").astype(np.float32) / 32768.0
    if samples.size == 0:
        return []
    window = max(1, round(8000 / frame_rate))
    values = []
    for start in range(0, samples.size, window):
        chunk = samples[start:start + window]
        values.append(float(np.sqrt(np.mean(np.square(chunk), dtype=np.float64))))
    envelope = np.asarray(values, dtype=np.float32)
    reference = float(np.percentile(envelope, 90)) if envelope.size else 0.0
    if not np.isfinite(reference) or reference <= 1e-5:
        return [0.0] * len(values)
    floor = max(0.008, reference * 0.07)
    normalized = np.clip((envelope - floor) / max(reference * 0.72, 1e-5), 0.0, 1.0)
    if normalized.size >= 3:
        normalized[1:-1] = (
            normalized[:-2] * 0.25 + normalized[1:-1] * 0.5 + normalized[2:] * 0.25
        )
    return [round(float(value), 3) for value in normalized]
