# Solo Stack presenter performance

## Host and acting

Stack is rendered locally as a reusable 2D character. Episode-level direction is derived from the narration and subject. Scene labels can add gesture and expression variation while preserving the episode's selected wardrobe and overall character identity. The presenter appears on alternating scenes, with short overlays, leaving intervening scenes unobstructed for real app evidence.

## Voice identity and delivery

The Colab preset selects one Kokoro voice ID (`am_michael`) for the channel. When Solo Stack voice performance is enabled, the Kokoro-FastAPI request uses SSML prosody-rate spans derived from sentence-level semantic cues and short inter-sentence breaks. This is deliberately restrained pacing variation, not a claim that Kokoro's SSML adapter provides arbitrary emotional acting, pitch control, or a different voice per scene. The voice ID is never changed by the director.

The SSML path uses the documented `ssml: true` and `allow_voice_tags: true` request flags. It is enabled only for the Solo Stack Kokoro path; other providers and ordinary MoneyPrinterTurbo jobs retain their existing request behavior. The Colab notebook enables the corresponding Kokoro-FastAPI server flags.

## Mouth animation and synchronization boundary

The presenter compositor decodes the narration into a compact 25 Hz RMS activity envelope. Stack's mouth opening follows that envelope on the scene timeline, so the mouth is more active during spoken audio and closes during quieter regions. This works with any narration provider and does not require another AI model.

This is **audio-reactive mouth animation**, not phoneme-accurate lip synchronization. RMS energy does not identify phonemes, syllables, or visemes, and scene offsets are estimated from the ordered clip durations. Exact lip sync would require word/phoneme timestamps and a phoneme-to-viseme mapping with verified timeline alignment. Do not describe the current behavior as phoneme-accurate.

## Evidence and quality constraints

- Keep real app footage and genuine screen recordings readable; the host must not cover key UI evidence.
- Do not claim that a user workflow was performed unless the video contains a genuine recording of that workflow.
- Public product-page visuals are not authenticated account demonstrations.
- Do not claim voice quality or acting quality is approved until a generated episode has been listened to and reviewed.
