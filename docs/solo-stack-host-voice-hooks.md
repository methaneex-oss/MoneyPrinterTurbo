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
Use a self-hosted Kokoro-82M server as the first no-paid-API candidate, with a
fixed selected voice and a small voice audition before production. The model is
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
