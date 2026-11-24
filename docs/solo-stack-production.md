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
