# Solo Stack visual review configuration

Dynamic supporting-media search acquires up to six candidates for a scene, then independently reviews each candidate before selection. The reviewer sees an actual image or a frame extracted from the video and receives the scene requirement plus candidate metadata. It must return a structured relevance judgment. Candidates are rejected when the configured model says they are irrelevant, fail to depict the requested subject, score below 72/100, or the review call fails. Product-authenticity is never inferred from this reviewer; this pipeline is supporting media only and cannot satisfy the product-visual evidence gate.

## Configure an independent vision model

Set these environment variables before launching MoneyPrinterTurbo:

- `SOLO_STACK_VISION_API_BASE`: OpenAI-compatible endpoint (e.g. `http://localhost:11434/v1` for Ollama, or the compatible provider endpoint).
- `SOLO_STACK_VISION_MODEL`: a vision-capable model name, not a text-only model.
- `SOLO_STACK_VISION_API_KEY`: optional for local Ollama; use the provider's key for hosted endpoints. Keep it in Colab Secrets/environment, never in a committed notebook or log.

Example for Ollama (model must already be pulled and vision-capable):
```bash
export SOLO_STACK_VISION_API_BASE=http://localhost:11434/v1
export SOLO_STACK_VISION_MODEL=qwen2.5vl:3b
```

Hosted provider example:
```bash
export SOLO_STACK_VISION_API_BASE=https://openrouter.ai/api/v1
export SOLO_STACK_VISION_MODEL=<provider's current vision-capable model ID>
export SOLO_STACK_VISION_API_KEY=<secret>
```

No reviewer is enabled if base/model are absent. In that mode, retrieval uses a conservative keyword-overlap fallback and marks `visual_review.enabled=false` in the episode manifest. That is not equivalent to AI visual verification; configure the separate vision model for meaningful semantic review.

The episode's `solo_stack/dynamic_visuals/manifest.json` includes each candidate's source, model verdict, score, reason, visible-subject summary, acceptance decision, and the selected candidate's review. Review failures are rejected when a reviewer is configured. Model outputs are untrusted metadata and are not used as instructions.
