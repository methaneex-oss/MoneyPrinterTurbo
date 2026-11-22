# Local AI video model experiments

These experiments run open model weights on a local CUDA GPU. They do not call paid inference APIs and are not enabled as a production MoneyPrinterTurbo provider.

## AnimateDiff SD 1.5 benchmark

The initial benchmark uses the Diffusers AnimateDiff motion adapter with an SD 1.5 base model. It generates one 16-frame, 512x512 MP4 at 8 FPS. The model uses FP16 weights, VAE slicing, and Accelerate CPU offload to reduce peak VRAM pressure.

Run only in a separate environment. Do not install these dependencies into MoneyPrinterTurbo's main locked environment.

On Colab, the runtime must already have a CUDA-compatible PyTorch installation. Then:

```bash
python -m pip install -r docs/local-video-models/requirements.txt
python docs/local-video-models/animatediff_benchmark.py \
  --output /content/animatediff-benchmark.mp4
```

The script performs an 8 GiB VRAM preflight before downloading model weights. This is a conservative experiment gate, **not a guarantee** that inference will succeed; available system RAM, GPU architecture, model download access, and Colab allocation also matter. A failed preflight or inference does not switch to a paid service.

The benchmark reports GPU name, compute capability, VRAM, model IDs, frame count, resolution, steps, and output size. Inspect the resulting MP4 for motion coherence, flicker, artifacts, and prompt adherence before considering production use.

## Licensing and production gate

The AnimateDiff adapter and SD 1.5 base-model weights have separate licences. Review both for the intended commercial YouTube use before enabling monetized production. This experimental script is not connected to the WebUI or task pipeline; no AI-video capability should be advertised until a generated MP4 has passed a real task integration test.

For the model comparison and the LTX-Video 2B alternative, see [free-ai-video-model-fit.md](../free-ai-video-model-fit.md).
