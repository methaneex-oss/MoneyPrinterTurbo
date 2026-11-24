# Solo Stack presenter performance

## Runtime behavior

The recurring host is rendered locally by `app/services/solo_stack_presenter.py` with Pillow. The character's visual identity and Solo Stack emblem remain stable; scene direction can vary action, expression, gaze, intensity and wardrobe.

During video composition, `app/services/video.py` places the host on alternating scene indices. Each appearance is limited to the smaller of 3.5 seconds or 46% of that scene. This intentionally leaves intervening scenes fully available for product footage, screen evidence and graphics.

`app/services/solo_stack_director.py` derives the episode-level performance from the narration and subject. When a scene has a grounded label, `plan_scene_performance` derives a scene-specific direction from that label. Neutral labels receive deterministic gesture variation; labels with semantic cues can select a more specific emotional beat. The episode wardrobe and intensity are retained when scene-level direction is applied.

## What this does not claim

- The host is a local 2D rendered character, not a fully rigged actor.
- The current overlay is scene-aware, not phoneme-accurate lip synchronization.
- The current TTS request path does not receive per-line emotional prosody from this presenter director.
- The public product-image capture path does not authenticate into user accounts or demonstrate account-specific workflows.

These limitations are deliberate verification boundaries. A later speech-animation phase should use actual word/phoneme timing from the selected TTS provider, preserve the configured voice identity, and be tested against generated audio before it is described as synchronized.

## Quality constraints

- Do not place the host over every frame; keep real app evidence legible.
- Keep one recognizable character identity and the episode's selected voice identity.
- Change gestures and expression in response to scene meaning rather than a fixed repeating animation playlist.
- Do not claim a real workflow was performed unless the video contains a genuine recording of that workflow.
