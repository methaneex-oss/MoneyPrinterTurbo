# MoneyPrinterTurbo Core Pipeline Restoration Audit — 2026-11-27

## Authority and safety boundary

- Main branch remains unchanged.
- Audit workspace branch: `audit/restore-core-pipeline-20261127`, created from main SHA `a9f887ffc174ffa5dba2a3ddd2c622c7e102f7e3`.
- Existing upgrade stack remains open/draft and unmerged. No merge, rebase, reset, force-push, or acceptance performed.
- This is an audit checkpoint, not a claim of runtime verification.

## Objective

Restore and preserve MoneyPrinterTurbo's original production mechanisms. Integrate Solo Stack upgrades as optional enhancements that cannot silently replace, disable, or destabilize the base pipeline. Keep generic MoneyPrinterTurbo behavior and provider choices intact outside Solo Stack.

## Repository facts checked

- Default branch: `main`, at SHA `a9f887ffc174ffa5dba2a3ddd2c622c7e102f7e3`.
- PR #12 is open, draft, unmerged; head `feat/solo-stack-presenter-quality-20261124` at `36531b37bdd57706a7f5ba78e952c7fd593f1996`.
- The feature head is **432 commits ahead of main**, with 64 changed files and approximately 10,417 additions/deletions in compare metadata. The stacked feature PRs #1 and #3–#12 are not merged; PR #2 is closed but unmerged.
- The feature stack is not a clean, isolated set of Solo Stack patches. Treat it as a large integration branch; verify ancestry and changes by function/file before adopting.
- Branch #12 notebook is 22 cells and is materially different from main notebook (13,520 bytes vs 66,847 bytes).
- Original main task pipeline and core render function remain recognizable. The inspected preflight/provider-validation section is substantially unchanged. Feature-specific additions enter around script policy, materials, visual evidence, presenter/composition, final quality gates, Colab configuration, and UI.
- A fresh audit branch was created from main as a safe workspace. No code migration has been made yet.

## Initial risk findings (not yet fully audited)

5. **Shared-render behavior changed globally:** the feature branch inserts the new vector scene graphic in `video.combine_videos()` whenever a scene label exists, without gating it to Solo Stack. Main previously rendered the animated chapter tag but did not add this new graphic panel. This is a default-render change and must be made opt-in (or Solo Stack-only) to preserve baseline output. Presenter itself is explicitly gated by its enable flag.
6. **Product capture failure changed behavior:** the original integration treated public official-source capture as supplemental and continued on failure; current feature branch marks capture failure and fails the task in Solo Stack mode. This strict gate should not be the default production behavior; distinguish a missing evidence warning/fallback from an explicit director-required evidence gate.
7. **New retrieval path is mostly optional/fail-soft:** dynamic supporting visuals are feature-flagged and exceptions are logged/skipped; no replacement of the base stock retrieval is intended. Review candidate acquisition, license policy, relevance fallback, and cache handling in detail before adopting.
8. **Colab intentionally enables Solo Stack policy:** the notebook writes `solo_stack_mode=true` and `solo_stack_free_only=true`, and configures a Drive-backed task-state directory with Redis disabled. This is intentional for this channel notebook, but must not leak into ordinary installs or default configs. File-backed task state is documented as single-process only.
9. **Original task lifecycle/preflight is retained in the inspected section:** supported-provider checks and credential validation before expensive generation appear unchanged between main and feature head. Added features occur after/around the original stages rather than replacing the whole pipeline. Continue auditing later stages, UI provider selection, and rendering before accepting this conclusion.


1. **Stack/merge risk:** stacked PR ancestry and a 432-commit delta make reviewing or merging PR #12 as a single upgrade unsafe.
2. **Feature coupling:** Solo Stack-specific behavior is wired into shared task/render paths. Every injection point must be checked for strict mode gating and for preserving the original non-Solo Stack behavior.
3. **Fail-closed gates:** authentic-product-visual coverage and some Solo Stack quality/provider gates can intentionally abort production. These are channel policy decisions, not baseline MoneyPrinterTurbo requirements; they must be scoped to Solo Stack and have actionable diagnostics.
4. **Colab risk:** notebook setup has been extensively rewritten and requires line-by-line auditing for install, cache/config persistence, server startup/health, secrets, tunnel, and restart idempotence. The notebook has not been executed in Colab.
5. **Verification gap:** current feature stack's stated tests, lint, CI, Colab preflight, actual MP4 render, and human audio/visual inspection are not verified in this session.

## Core mechanism preservation checklist

- [ ] Task lifecycle/state transitions, cancellation, progress, retries, partial-output recording, and exception reporting.
- [ ] Script and search-term generation; provider routing, prompt limits, and error sentinel behavior.
- [ ] Audio/TTS/custom audio, timing, subtitle generation and synchronization.
- [ ] Material retrieval from every supported provider, local assets, ordering, matching, retries, and fallbacks.
- [ ] Original compositor/encoder, transitions, aspect ratios, captions, overlays, BGM, and output files.
- [ ] Batch video count and material allocation.
- [ ] API/CLI/WebUI parity and parameter handling.
- [ ] Publishing/export/post-upload outcomes, without treating generated files as published.
- [ ] Configuration, secrets, paths, cache persistence and Colab restart behavior.
- [ ] Optional Solo Stack presenter/acting, hook/script checks, real product evidence, topic-aware retrieval, vision relevance review, motion graphics, local image/video models and final quality inspection.

## Integration principle

Preserve original pipeline functions and default behavior. Add enhancement stages through explicit optional flags/configuration and fail-open for optional editorial/supporting visuals; fail-closed only for narrowly defined authenticity/safety requirements explicitly enabled for Solo Stack. Do not make presenter, dynamic web retrieval, vision-review model, local generative models, or product capture mandatory for ordinary MoneyPrinterTurbo jobs.

## Next audit steps

1. Compare all altered core modules against main by function, not only file-level diff.
2. Identify removals, changed defaults, provider restrictions, and failure paths.
3. Map feature additions to their injection points and document a compatibility matrix.
4. Audit test quality and missing integration tests; then run checks in a local reproducible environment if repository access/runtime can be established.
5. Propose and implement the smallest migration on this main-based audit branch; preserve original functions and keep optional upgrades behind configuration.
6. Verify source/diff, tests, CI, notebook checks, and a Colab end-to-end render separately. Do not claim runtime success without evidence.

## Status

**Audit in progress.** The root cause of the prior `video_script` NameError has not been established. No fix for that runtime error has been committed.
