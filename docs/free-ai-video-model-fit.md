# Free AI video model fit for MoneyPrinterTurbo

**Status: research checkpoint — no AI-video backend is enabled yet.**

This note records the model-selection decision for the Colab workflow. The requirement is real generated motion, not a still image with a Ken Burns camera move. Any candidate must run without a paid API, avoid accidental provider charges, and degrade cleanly to the existing Pixabay/local-image workflow.

## Findings

### Candidate A — LTX-Video 2B distilled (preferred quality experiment)

Official model: [Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video)  
Official code: [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video)

- The official model card lists `ltxv-2b-0.9.8-distilled` as the small/light-VRAM model and also lists an FP8 checkpoint.
- The published file listing shows approximately 6.34 GB for the 2B distilled checkpoint and 4.46 GB for the FP8 variant. Those are checkpoint sizes, **not** total runtime VRAM.
- The 0.9.8 inference config uses a PixArt-XL text encoder and a spatial upscaler. It uses BF16 precision by default.
- The official inference implementation supports CPU offload when GPU memory is below 30 GiB. That does not guarantee it will fit or finish on a free Colab T4.
- The FP8 path in the official inference implementation requires Lightricks Q8 kernels. Do not select FP8 merely because its checkpoint is smaller; kernel compatibility must be checked against the actual Colab GPU architecture.
- The model card describes text-to-video and image-to-video, but no Hugging Face Inference Provider currently serves this model. It therefore needs local GPU execution, not a free hosted API.
- The model's weight licence is listed as **other**. The exact 0.9.8 weight licence must be reviewed before enabling monetized channel use. The repository's Apache-2.0 code licence does not automatically license the model weights.

**Assessment:** best first experiment for genuine scene animation, but not a safe always-on default for free Colab. Use a short image-to-video benchmark, reduced resolution/frame count, and explicit GPU capability checks before production integration.

### Candidate B — AnimateDiff SD 1.5 (lower-footprint alternative)

Official implementation: [guoyww/AnimateDiff](https://github.com/guoyww/animatediff/)  
Diffusers adapter: [guoyww/animatediff-motion-adapter-v1-5-2](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2)  
Diffusers documentation: [AnimateDiff pipeline](https://huggingface.co/docs/diffusers/main/en/api/pipelines/animatediff)

- The Diffusers example combines a Stable Diffusion 1.5 image model with a motion adapter.
- The adapter repository provides an FP16 checkpoint of approximately 1.82 GB (the full-precision file is approximately 3.63 GB).
- The documented memory-saving path enables VAE slicing and model CPU offload.
- The documented example produces 16 frames at a 512-class resolution. This is short motion footage, not a long coherent video.
- FP16 support makes it a more plausible test on a T4-class Colab GPU than a BF16-only path, but successful generation and speed still need a live benchmark.
- The adapter and chosen SD 1.5 base-model weight licences must be checked independently for commercial use. Do not assume the code licence covers the weights.

**Assessment:** likely the more practical low-VRAM experiment. Quality and motion coherence may be lower than newer video diffusion models; benchmark before choosing it as the default.

## Selection and safety rules

1. Do not call any external paid video API. No provider fallback may be enabled implicitly.
2. Do not download multi-gigabyte checkpoints on a runtime that fails the preflight checks.
3. Check GPU name, compute capability, VRAM, available system RAM, and free disk before installation.
4. Use a separate virtual environment for video-model dependencies. Do not mutate the main MoneyPrinterTurbo environment or its locked dependencies.
5. Use a short benchmark first: one 16-frame scene, 512-class output, one fixed seed, and an existing script-matched still as the conditioning image when supported.
6. Record model ID/revision, weight licence, package versions, GPU, peak VRAM, elapsed time, output dimensions, and whether the output file decodes.
7. Only expose the model in the production WebUI after the benchmark passes and the generated clip is successfully inserted into a real MoneyPrinterTurbo task.
8. If any preflight, download, inference, decode, or integration step fails, keep the current Pixabay/local-image workflow unchanged and report the reason. Never label a still-image camera move as AI-generated video.

## Implementation gate

**Next implementation target:** an isolated local image-to-video adapter, initially benchmarking LTX-Video 2B distilled on a capable Colab GPU. If the free runtime is incompatible with its BF16/configuration requirements, benchmark AnimateDiff SD 1.5 using FP16 and CPU offload instead.

The adapter must return an ordinary local MP4 path to the existing task pipeline. It must not change the default video source, existing API-provider settings, OpenRouter configuration, or the current Pixabay fallback until end-to-end validation succeeds.

## Source references

- LTX-Video model card and model variants: https://huggingface.co/Lightricks/LTX-Video
- LTX-Video official inference implementation: https://github.com/Lightricks/LTX-Video
- LTX-Video official 2B 0.9.8 distilled config: https://github.com/Lightricks/LTX-Video/blob/main/configs/ltxv-2b-0.9.8-distilled.yaml
- AnimateDiff official implementation and motion-module notes: https://github.com/guoyww/animatediff/
- AnimateDiff FP16 adapter and Diffusers example: https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2
- Diffusers AnimateDiff usage and CPU-offload example: https://huggingface.co/docs/diffusers/main/en/api/pipelines/animatediff
