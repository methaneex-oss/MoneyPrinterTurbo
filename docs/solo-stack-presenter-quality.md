# Solo Stack presenter quality — first-release gate

## Objective

Make Stack read as a polished, recognizable recurring host at actual YouTube Shorts
render sizes. The presenter is a character with a stable identity, not a disposable
overlay asset. This work improves the existing local Pillow renderer without adding
a paid service, external image dependency, or a new runtime model.

## Implemented in this slice

- Render the existing original character at 2x resolution and downsample with
  Lanczos, improving curves, facial details and small brand marks at compact
  9:16 overlay sizes.
- Add a soft offset contact shadow so the host remains legible over changing
  application footage while preserving transparent compositing.
- Pass the RGBA alpha channel to MoviePy as a real clip mask, preventing RGB
  conversion from discarding transparency and producing an opaque dark rectangle.
- Fade each appearance in and out over a short eased interval to avoid hard pops
  at scene boundaries.
- Sample three frames from each eligible scene and scan the full upper/middle
  subtitle-safe region for a low-complexity presenter position. Placement adapts
  to the actual footage instead of alternating fixed corners; uniform scenes use
  a deterministic upper-right fallback. This visual heuristic is not semantic
  object detection, so native-render review remains mandatory.
- Add restrained jacket seam, fastener and hair-highlight details without
  changing the established character silhouette, palette, wardrobe choices,
  acting controls or public renderer signature.
- Keep all rendering local and deterministic. No generated/copyrighted character
  assets or paid APIs are introduced.
- Give curious, skeptical and thoughtful beats distinct eye openness and brow
  cues. Their resting mouth shapes also differ; narration-driven mouth movement
  correctly takes precedence while Stack is speaking.
- Ease eyelid closure/opening across the episode timeline instead of switching
  both eyes closed in a single abrupt frame.
- Distinguish open-palm evidence presentation, a single raised index finger for
  questions/warnings, and a two-handed shrug for trade-off scenes.
- Add understated palm creases while keeping the hand silhouette compact.
- Select alternating labelled non-evidence scenes for host appearances; skip
  product screenshots and recordings so the presenter cannot cover app controls.
- Add regression tests for transparency, antialiased edges, deterministic output,
  expression/action/wardrobe variation, compact overlays, partial blink states,
  distinct facial poses during speech, separate hand gesture families, adaptive
  placement around visually busy regions, subtitle-safe bounds, deterministic
  fallback, and real video compositing over a non-black background.

## Quality boundary

Supersampling, eased eyelids and small hand details improve the existing
procedural 2D design; they do not turn it into a fully rigged 2D/3D actor. The current mouth movement
remains audio-energy-reactive rather than phoneme/viseme synchronized. The current
Kokoro adapter controls pacing, not arbitrary emotional acting or pitch.

A production acceptance pass still needs to inspect rendered frames at native
1080x1920 output, verify that the character does not obscure product evidence or
subtitles, listen to the actual voice sample, and watch a complete episode. The
renderer unit tests alone cannot establish those perceptual outcomes.

## First-video acceptance criteria

1. Stack is recognizable across every appearance and outfit variation.
2. Face, hands, jacket details and silhouette remain clean at native Shorts size.
3. Gestures match the scene's point rather than repeating a generic wave.
4. The host never covers essential app controls, pricing, subtitles or evidence.
5. Host appearances have editorial purpose; evidence footage remains dominant
   when the viewer needs to inspect a product.
6. Voice is clear, natural and intelligible on a phone speaker; mouth movement
   does not visibly contradict speech.
7. The complete render has no clipped character, alpha halo, flicker, timing jump
   or abrupt exit.

A video is not accepted solely because the code path completes successfully.
