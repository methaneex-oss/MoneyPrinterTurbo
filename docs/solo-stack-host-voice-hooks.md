# Solo Stack — host, voice, and episode storytelling bible

Status: creative and engineering specification for the next production implementation.
This document defines the target behavior; it does not claim the renderer or TTS
runtime already implements every item below.

## 1. Creative target

Solo Stack is an honest AI-tools review channel for freelancers and small
business owners. The recurring host is the audience's guide through real work,
not a mascot pasted over stock footage. The visual benchmark is the *effect* of
a successful animated sitcom character: a stable silhouette, instantly readable
expressions, a memorable personality, and recurring mannerisms. Do not copy
Family Guy's character designs, layouts, line work, voices, jokes, or any other
existing character or show.

## 2. Recurring host: Stack

Keep the existing host name **Stack** so the identity already introduced in the
repository is not discarded. Redesign the current primitive figure into a
polished, original 2D character with these durable identifiers:

- Warm, expressive face; large readable eyes; strong but friendly eyebrows.
- Distinctive swept-up dark hair silhouette with one recognizable curl.
- Teal jacket, coral shirt, dark trousers, light trainers.
- Three-bar cyan/coral Stack emblem, used consistently on clothing and graphics.
- Rounded, slightly exaggerated proportions; clean dark outlines; restrained
  cel shading; high contrast at phone-screen size.
- Consistent model sheet: front, three-quarter, profile, full body, and the same
  expression set. Never redraw the character independently per scene.

The character should be recognisable in monochrome from silhouette alone. The
logo/emblem is a secondary identifier, not a substitute for a distinctive face.

### Personality

Stack is curious, sharp, practical, lightly mischievous, and fair. He is
skeptical of marketing claims but never hostile to the viewer. His humour comes
from relatable freelancer problems, visual reactions, dry observations, and
well-timed pauses—not insults, forced catchphrases, or constant jokes.

Recurring behaviors: eyebrow raise when a claim sounds suspicious; thoughtful
chin-rest before a verdict; direct-to-camera question at the opening; a small
celebratory gesture when a tool genuinely saves time; a clear warning gesture
when a limitation matters. These are optional acting choices, not mandatory
beats in every video.

## 3. Voice identity

The voice must be consistent across episodes and feel like one character:
adult, warm mid-range masculine-presenting voice, clear diction, conversational
pace, confident but not announcer-like, with natural emphasis and controlled
energy. Avoid exaggerated radio voice, synthetic sing-song cadence, or
unrelenting high energy.

Delivery rules:
- Openings: direct, curious, and energetic; leave a short beat after the hook.
- Explanations: calm and clear; slow down for prices, limits, and caveats.
- Humour: dry and brief; do not overact.
- Verdicts: decisive, evidence-led, and slightly slower.
- Use sentence-level pauses and pronunciation dictionaries for product names,
  acronyms, currencies, and technical terms.
- Keep one voice identity and voice ID fixed for the channel. Do not rotate
  voices between episodes to chase novelty.

### Free-first TTS direction

The repository already has a Kokoro-compatible TTS adapter and config section.
Use a self-hosted Kokoro-82M server as the first no-paid-API candidate. The
Colab setup auditions `am_michael` and pins that voice ID only after the service
and speech endpoint respond successfully. The model is
listed under Apache-2.0 and is lightweight relative to large speech models;
actual speed and quality must still be measured in the target Colab runtime.
Keep the current working TTS providers as explicit fallbacks. Do not silently
switch to a paid endpoint, and do not make a cloud API key a prerequisite.

Reference: https://github.com/hexgrad/kokoro
Reference server: https://github.com/remsky/Kokoro-FastAPI
License/maintenance comparison checked 2026-11-24:
https://www.assemblyai.com/blog/free-open-source-text-to-speech

## 4. Hook and opening system

Every episode should open with a topic-specific question or tension, because the
viewer should immediately understand why the test matters. This must be
generated from the episode brief, target audience, tested task, and verified
evidence—not selected from a fixed list of canned questions.

The script planner should produce several candidate hooks internally, score
them for specificity, curiosity, credibility, and relevance to the viewer, then
select one. Reject hooks that:
- promise results the episode does not demonstrate;
- imply a tool is free when a relevant limit or paid tier applies;
- use vague bait such as "you won't believe";
- exaggerate a result or invent a personal experience;
- could be reused unchanged for almost any product.

A strong hook creates a concrete decision:
- "Can this free AI actually write a client proposal you'd send?"
- "Is this tool worth paying for if you only have five clients?"
- "Can it turn a messy meeting into actions without missing anything?"

Those examples are illustrations, not hard-coded templates. The generated
opening should then state the task being tested and show the real product
interface or a clearly labelled test setup. The host should react to what is
actually on screen.

## 5. Episode rhythm and visual grammar

Use a balanced composition: host-led explanation alternates with full-screen
real app evidence. Never keep the character over the important part of a UI.
The default sequence is flexible and evidence-driven:

1. Question hook and host reaction.
2. State the real task and evaluation criteria.
3. Show the real application performing the task.
4. Highlight the useful result and the failure/limitation.
5. Compare price, free-tier limits, and realistic alternatives.
6. Give a clear verdict: worth paying for, useful free, or skip.

The planner chooses pacing and scene order based on content. Do not force every
beat into every Short. Use animation to explain a concept, comparison, workflow,
or result—not as decorative motion for its own sake. Preserve readable UI,
large typography, safe areas, and 9:16 mobile framing.

## 6. Production acceptance criteria

A release is not accepted merely because the video renders. Review at least one
complete 9:16 episode and verify:

- Stack is visually consistent across every appearance and recognisable at
  thumbnail size.
- Expressions and gestures correspond to the narration and scene intent.
- Voice is natural, intelligible, correctly pronounced, and consistent.
- The first 2–3 seconds contain a specific, truthful question or tension.
- No generic stock montage substitutes for the actual tested product.
- Real app captures are legible and shown long enough to inspect.
- Prices, limits, and claims match dated evidence.
- The host never obscures essential product UI or subtitles.
- The verdict follows from the demonstration, not the hook.

The current vector-primitive presenter is a prototype and does not yet satisfy
this visual acceptance bar. The Kokoro adapter is present in the repository,
but a working self-hosted Colab endpoint, selected voice audition, and measured
render have not been verified by this specification.


## 7. Performance variation — identity is fixed, acting is not

The character model and voice identity are the continuity anchors. The
performance must be authored per episode and per scene. "Consistent character"
does not mean repeating the same animation, camera angle, emotional register,
scene order, or outfit in every upload.

### Invariants
- Preserve Stack's recognisable face, silhouette, proportions, core palette,
  emblem, and personality.
- Preserve the selected voice, speaker identity, and broad vocal timbre.
- Preserve the channel's evidence-first, candid editorial point of view.

### Episode-driven variables
The episode planner and scene director choose performance from the script's
meaning, emotional intent, and visual evidence. They may vary:
- gaze, head turns, eye direction, blinking, brows, mouth shapes, posture;
- hand gestures, pointing, shrugging, walking, leaning, reacting, and timing;
- shot scale, angle, screen position, entrance/exit, staging, and transitions;
- emotional state (curious, amused, focused, surprised, doubtful, concerned,
  satisfied) and intensity;
- clothing, accessories, and hand props when contextually justified.

Clothing changes are occasional and motivated (for example, a relevant prop or
episode setting), not random costume changes. Keep a stable base wardrobe and
recognition cues; avoid changing several identity features at once.

### Voice performance versus voice identity
The speaker/voice ID remains fixed, but delivery is expressive. The script and
voice renderer may vary rate, emphasis, pitch contour within natural limits,
pauses, sentence grouping, and energy to fit intent. Do not use pitch-shifting
or exaggerated effects that make Stack sound like a different speaker. Avoid
relying on SSML tags unless the selected provider actually supports them; use
provider-specific capability checks and a safe plain-text fallback.

### Acting direction data
Each scene should carry structured direction derived from the script, such as
intent, emotion, intensity, gaze target, gesture family, body movement, shot
framing, wardrobe/prop overrides, and narration delivery. These are semantic
scene directions, not a finite list of canned sequences. The director maps
them to supported animation controls, selecting or composing varied motion.
It must be possible for the same emotion to produce different natural actions
in different scenes.

Do not randomize blindly. Variation must be reproducible from the episode
plan, relevant to meaning, and reviewable. Use deterministic seeds only for
incidental micro-variation (such as blink timing), never to replace editorial
direction.

### Explicit anti-patterns
- Replaying one idle bob/talking loop throughout the episode.
- Making every video open with the same pose or gesture.
- Reusing a fixed six-beat scene sequence regardless of subject.
- Changing Stack's face or voice between videos.
- Making every line sound equally excited.
- Changing outfits so often that the character loses instant recognition.
- Letting character animation cover the real product interface or important
  evidence.

The renderer should support an expanding action/pose library and composable
motion primitives rather than a single baked animation. If the scene calls for
an action not yet supported, use the closest honest staging or add a new
reusable action; do not silently map every intent to the same gesture.


## 8. Implemented production wiring (2026-11-24)

The episode-aware acting director is now implemented in
`app/services/solo_stack_director.py`. It evaluates the actual opening
narration and subject, chooses a semantic emotional intent, gesture family,
gaze, intensity, and occasional context-motivated wardrobe, and returns a
reproducible scene-direction object. It does not replay a fixed gesture sequence
or change Stack's identity.

The Pillow character renderer now supports separate action, expression, gaze,
wardrobe, and intensity controls. The task pipeline supplies the director's
result to the opening-scene compositor. The renderer remains local and does not
require a paid image API. The opening host remains limited to the opening shot
so real product footage stays legible and central.

When Solo Stack mode is enabled, script generation adds channel-specific
requirements: the first spoken sentence must be a truthful, subject-specific
question; the narration must address real freelancer/small-business decisions;
and it must avoid invented results, prices, limits, sources, or personal
experience. The script planner still generates the actual hook from each
episode's subject rather than selecting from a canned hook list.

The Colab notebook now includes an isolated CPU Kokoro-FastAPI setup, a voice
catalog check, and a short speech audition. It pins the Kokoro provider and
voice only if the configured server returns the requested voice and the speech
endpoint successfully produces audio. If startup or synthesis fails, existing
voice settings are preserved. This path is free/open-source software and uses
no paid speech API. The first Colab run still needs to complete the download,
startup, and audio audition in the user's actual runtime before the voice is
considered runtime-verified.

### Remaining acceptance boundary

The renderer is a procedural 2D rig, not a full professional hand-drawn
character animation package. It offers varied pose/expression/wardrobe
directions but does not yet provide skeletal limb interpolation, lip-sync
visemes, frame-by-frame acting authored by an animator, or AI-generated motion.
A complete episode must still be rendered and visually/audio reviewed in Colab
before accepting character appeal, voice quality, or production readiness.
