# Solo Stack production foundation (Phases 1–2)

This branch adds the channel-specific identity and evidence-first asset foundation
without replacing MoneyPrinterTurbo's existing task, narration, subtitle, or
composition pipeline.

## Phase 1 — identity and presenter
- Brand palette: ink `#101827`, panel `#17243A`, cyan `#46D3E7`, coral
  `#FF8963`, cream `#F6F4EE`.
- Original presenter: **Stack**, an independent cartoon technology analyst.
  The character is drawn deterministically from local vector primitives, not
  generated independently for each shot. Expressions and idle gesture timing
  are stable inputs to the renderer.
- Wordmark: `assets/solo_stack/wordmark.svg`.
- The presenter renderer is opt-in through `config.app.solo_stack_presenter_enabled`
  and can be enabled per installation; existing users retain the old output
  unless they explicitly enable it.
- Character source is original artwork in this repository; do not substitute
  copyrighted TV/movie/game characters or imitate a specific character design.

## Phase 2 — real app assets and evidence ledger
The new `app.services.solo_stack_assets` service:
- Copies user-supplied screenshots, screen recordings, and demonstration media
  into a project-scoped asset directory after extension, size, and path checks.
- Writes a versioned JSON manifest with asset type, product, capture date,
  source page, notes, and SHA-256 digest.
- Keeps source URLs separate from the local file and refuses non-HTTP(S) URLs,
  credentials in URLs, and control characters.
- Records research claims separately with source URL, publisher, checked date,
  claim text, and optional captured value/currency/plan. It does not infer or
  fabricate pricing, limits, feature availability, or test results.
- Supports official product-page evidence and real user-captured application
  screenshots/recordings. It does not scrape authenticated apps or pretend
  generated mockups are real product screenshots.
- During Solo Stack task generation, matching, hash-verified captures are selected
  by product name and prioritized over public product-page visuals; those public
  visuals fill remaining slots when available.

## Suggested asset capture workflow
1. Open the actual product website/app and capture the interface or the real task
   demonstration (browser/desktop screen recording).
2. Save a screenshot or MP4 into the episode's asset folder.
3. Register it with `register_asset` and attach its official source page.
4. Add current price/limit claims with `add_evidence`; include a date checked.
5. Before publishing, review the manifest and verify every displayed claim against
   its cited source. Prices and plan limits must be rechecked on publication day.

## Supported formats
Images: PNG, JPG/JPEG, WEBP. Video: MP4, MOV, WEBM. Maximum individual asset:
100 MiB. Project and asset names are sanitized; symlinks and path traversal are
rejected. No external service, paid API, or model download is required.

## Verification boundary
Unit tests validate the deterministic presenter frames, asset ingestion checks,
manifest integrity, URL validation, and evidence records. They do not prove that
an external product's UI is current; source review remains required. End-to-end
video appearance and GPU inference must be checked in a real Colab run.



## Solo Stack editorial preflight

Generated and operator-supplied scripts receive a channel-specific opening review
before narration. The deterministic preflight checks that the first spoken
sentence is a short question, rejects common generic opening phrases, and looks
for lexical overlap between the question and the episode subject. It records
warnings in the task log and the `solo_stack_review` section of `script.json`.
Topic overlap is only a lightweight signal, not semantic proof. Numeric and
factual claims remain marked `not_independently_verified`; the preflight does
not replace source collection or human fact review and does not silently rewrite
an operator's script.


## Evidence-aware script generation

When a supported product is named in the episode subject, script generation
loads matching operator-recorded evidence from the persistent ledger. Only
records checked within the last 30 days are supplied as prompt context, with
their claim, plan/value, publisher, checked date and source URL. The prompt
treats these records as data rather than instructions and prohibits inventing
additional prices, limits or features. If no current record exists, the prompt
explicitly tells the model not to state exact prices or plan limits as facts.

The full matching evidence set, including stale records, is attached to
`script.json` for editorial review. Freshness is based on the operator's
`checked_at` date; it is not independent source verification. The existing
numeric-claim audit remains active, and every such claim still requires manual
matching to its cited source before publication.


## Final-render technical gate

The final-video inspection now records decoded width/height and aspect ratio,
samples short windows of the audio track, and reports missing/silent audio or
audio/video duration mismatch. Solo Stack runs require an audio stream and pass
the configured output aspect ratio (normally 9:16) into this inspection. Solo Stack blocks task completion when the final file has no audio, effectively
silent/invalid audio, an audio/video duration mismatch, or the wrong output
aspect ratio. Other visual diagnostics remain warnings. A clean technical report
still cannot prove voice quality, app-interface legibility, factual accuracy or
good editing. The full MP4 requires a human watch/listen pass.


## Free-only execution policy

The Colab preset enables `solo_stack_free_only`. Before any provider request,
the task layer enforces these constraints:

- Script and search-term generation: OpenRouter models whose effective model ID
  ends in `:free`, or a loopback-local Ollama endpoint. Paid LLM selections are
  rejected before the request.
- Narration: loopback-local Kokoro only, unless the operator supplies an audio
  file. Paid TTS selections are rejected before the request.
- Visual sources: Pixabay, operator-supplied local media, or the warmed
  loopback-local image server. External OpenAI-compatible image endpoints and
  paid video providers are rejected.
- TwelveLabs term reranking is skipped in free-only mode.
- Sonilo and ElevenLabs music generation is blocked when it would make a
  provider request. The default local/random BGM path remains available.
- SD-Turbo commercial use stays opt-in pending Stability AI registration;
  AnimateDiff stays hidden/blocked until its weight license is reviewed.

The WebUI hides incompatible visual providers, and the task layer repeats the
checks so a stale or manually edited configuration cannot silently trigger a
paid request. A blocked configuration fails with a reason rather than falling
back to a paid service.
