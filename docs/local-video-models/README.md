# Local AI video generation

The AnimateDiff backend runs locally on a CUDA GPU attached to Google Colab. It does not call paid inference APIs. The production path is exposed in MoneyPrinterTurbo as **Local AnimateDiff (Free GPU)** only after the local service is ready.

## Architecture

- The local server loads the AnimateDiff motion adapter and Stable Diffusion 1.5 base model once, keeps the pipeline in memory, and exposes a loopback-only HTTP API on 127.0.0.1:7862.
- The MoneyPrinterTurbo client calls that service, validates MP4 responses, writes clips into the task directory, and records scene source metadata.
- The task orchestrator routes the animatediff video source through the local generator. The existing compositor still handles scene ordering, duration trimming/reuse, subtitles, narration, music, graphics and final encoding.
- The WebUI shows the source and local service status. If the service is unavailable, the task fails with a clear local-service error; it never switches to a paid provider.
- The Colab notebook checks GPU, VRAM, system RAM and disk before installing the isolated environment. Hugging Face weights are cached on Google Drive. The server is not exposed through the ngrok tunnel.
- The notebook stops the local image model only after video-GPU preflight succeeds. If AnimateDiff startup fails, it restarts and warms the local image model; if that recovery fails, it returns to the configured Pixabay source. No paid fallback is used.

## Runtime profile

The initial profile uses FP16 weights, VAE slicing and Accelerate CPU offload. The server requires at least 12 GiB of GPU VRAM, generates 16 frames at 384x672 portrait / 672x384 landscape / 512x512 square, then slows the clip 1.5x and interpolates to 24 FPS. This profile is a conservative experiment gate, not a guarantee that every Colab GPU or free runtime allocation will complete inference.

## Model and licensing boundary

The adapter (guoyww/animatediff-motion-adapter-v1-5-2) and base model (stable-diffusion-v1-5/stable-diffusion-v1-5) have separate model licences. The base model metadata identifies CreativeML OpenRAIL-M. The adapter metadata does not expose a clear licence in the inspected model record, so its commercial-use permission is unresolved. Do not use this backend for monetized production until the adapter's authoritative licence is located and reviewed. The Stable Diffusion safety checker is left enabled. Do not disable it for production.

LTX-Video 2B remains a separate candidate; it is not silently installed or selected because its runtime/precision path and model-weight licence have not been validated for this Colab setup.

## Validation boundary

Automated tests cover the source routing, HTTP response handling, manifest persistence, Colab preflight/setup syntax, and provider visibility. They do not prove model inference, visual quality, or successful end-to-end rendering on a live Colab GPU. Those require the GPU runtime to be attached and a real MP4 to be generated and inspected.