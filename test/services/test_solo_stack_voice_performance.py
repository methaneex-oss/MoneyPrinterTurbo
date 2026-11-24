from __future__ import annotations

import numpy as np
from PIL import ImageChops

from app.services.solo_stack_voice import build_kokoro_performance_ssml
from app.services.solo_stack_lipsync import build_audio_activity_envelope
from app.services.solo_stack_presenter import build_presenter_frame


def test_kokoro_performance_ssml_escapes_text_and_keeps_sentence_pacing_subtle():
    result = build_kokoro_performance_ssml(
        "Here is the process. But the hidden pricing is expensive."
    )

    assert result.startswith("<speak>")
    assert result.endswith("</speak>")
    assert "&lt;" not in result  # no accidental markup is introduced for ordinary text
    assert '<prosody rate="100%">' in result
    assert '<prosody rate="95%">' in result
    assert "<break time=\"180ms\"/>" in result
    assert "[voice:" not in result  # the selected narrator identity never changes


def test_kokoro_performance_ssml_escapes_untrusted_script_markup():
    result = build_kokoro_performance_ssml("Compare <script> & pricing.")

    assert "&lt;script&gt;" in result
    assert "&amp;" in result
    assert "<script>" not in result


def test_audio_activity_envelope_normalizes_speech_and_quiet_segments(monkeypatch):
    class FakeAudio:
        def __init__(self):
            quiet = np.zeros(8000, dtype="<i2")
            tone = (np.sin(np.arange(8000) * 2 * np.pi * 220 / 8000) * 12000).astype("<i2")
            self.raw_data = quiet.tobytes() + tone.tobytes()

        def set_channels(self, _value):
            return self

        def set_frame_rate(self, _value):
            return self

        def set_sample_width(self, _value):
            return self

    monkeypatch.setattr(
        "app.services.solo_stack_lipsync.AudioSegment.from_file",
        lambda _path: FakeAudio(),
    )
    envelope = build_audio_activity_envelope("unused.mp3", frame_rate=25)

    assert len(envelope) == 50
    assert max(envelope[:25]) == 0.0
    assert max(envelope[25:]) > 0.8


def test_presenter_mouth_shape_changes_with_audio_activity():
    closed = build_presenter_frame(expression="talk", mouth_open=0.0)
    open_mouth = build_presenter_frame(expression="talk", mouth_open=1.0)

    difference = ImageChops.difference(closed, open_mouth)
    assert difference.getbbox() is not None



def test_kokoro_tts_sends_ssml_but_keeps_plain_subtitle_text(monkeypatch, tmp_path):
    from app.services import voice

    original_text = "Explain the workflow. But check the hidden limits."
    captured = {}
    sentinel = object()

    monkeypatch.setitem(
        voice.config.kokoro, "base_url", "http://127.0.0.1:8880/v1"
    )
    monkeypatch.setitem(
        voice.config.kokoro, "solo_stack_performance_enabled", True
    )

    def fake_transport(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(voice, "_openai_compatible_tts", fake_transport)
    result = voice.kokoro_tts(
        text=original_text,
        voice="am_michael",
        voice_file=str(tmp_path / "voice.mp3"),
        performance_direction={"emotion": "explaining"},
    )

    assert result is sentinel
    assert captured["args"][5].startswith("<speak>")
    assert captured["kwargs"]["extra_payload"] == {
        "ssml": True, "allow_voice_tags": True
    }
    assert captured["kwargs"]["subtitle_text"] == original_text
