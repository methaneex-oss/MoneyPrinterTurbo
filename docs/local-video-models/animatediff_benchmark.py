"""Run a small, no-paid-API AnimateDiff text-to-video benchmark.

This is an isolated experiment, not a MoneyPrinterTurbo production provider.
Install its dependencies in a separate environment before running it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_ADAPTER = "guoyww/animatediff-motion-adapter-v1-5-2"
DEFAULT_BASE_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
DEFAULT_PROMPT = (
    "Cinematic documentary footage of powerful ocean waves rolling toward "
    "a rugged coastline at golden hour, natural realistic motion, "
    "photorealistic, atmospheric light, stable camera"
)


def check_runtime(torch_module, minimum_vram_gib: float = 8.0) -> dict:
    """Return a hardware report or raise before downloading model weights."""
    if not torch_module.cuda.is_available():
        raise RuntimeError(
            "AnimateDiff benchmark requires a CUDA GPU; no paid API fallback exists"
        )
    device = torch_module.cuda.current_device()
    props = torch_module.cuda.get_device_properties(device)
    vram_gib = props.total_memory / (1024**3)
    capability = torch_module.cuda.get_device_capability(device)
    report = {
        "device": props.name,
        "compute_capability": ".".join(map(str, capability)),
        "vram_gib": round(vram_gib, 2),
        "minimum_vram_gib": minimum_vram_gib,
        "precision": "float16",
    }
    if vram_gib < minimum_vram_gib:
        raise RuntimeError(
            f"GPU has {vram_gib:.1f} GiB VRAM; benchmark gate is "
            f"{minimum_vram_gib:.1f} GiB"
        )
    return report


def generate_benchmark(
    output_path: str,
    prompt: str = DEFAULT_PROMPT,
    seed: int = 20261122,
    adapter_id: str = DEFAULT_ADAPTER,
    base_model_id: str = DEFAULT_BASE_MODEL,
    num_frames: int = 16,
    steps: int = 12,
    width: int = 512,
    height: int = 512,
) -> dict:
    """Generate one short MP4 using open weights and local GPU inference."""
    if num_frames != 16 or width != 512 or height != 512:
        raise ValueError("Initial benchmark is fixed at 16 frames and 512x512")
    if not 1 <= steps <= 25:
        raise ValueError("steps must be between 1 and 25")
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")

    import torch
    from diffusers import AnimateDiffPipeline, DDIMScheduler, MotionAdapter
    from diffusers.utils import export_to_video

    hardware = check_runtime(torch)
    adapter = MotionAdapter.from_pretrained(
        adapter_id, torch_dtype=torch.float16, variant="fp16"
    )
    pipe = AnimateDiffPipeline.from_pretrained(
        base_model_id,
        motion_adapter=adapter,
        torch_dtype=torch.float16,
    )
    pipe.scheduler = DDIMScheduler.from_pretrained(
        base_model_id,
        subfolder="scheduler",
        clip_sample=False,
        beta_schedule="linear",
        timestep_spacing="linspace",
        steps_offset=1,
    )
    pipe.vae.enable_slicing()
    pipe.enable_model_cpu_offload()

    generator = torch.Generator(device="cpu").manual_seed(int(seed))
    result = pipe(
        prompt=prompt,
        negative_prompt="low quality, worst quality, blurry, flicker, distorted motion",
        num_frames=num_frames,
        num_inference_steps=steps,
        guidance_scale=7.5,
        width=width,
        height=height,
        generator=generator,
    )
    frames = result.frames[0]
    if len(frames) != num_frames:
        raise RuntimeError(f"Model returned {len(frames)} frames; expected {num_frames}")

    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(target), fps=8)
    if not target.is_file() or target.stat().st_size < 16_384:
        raise RuntimeError("Video export did not produce a plausible MP4 file")

    return {
        **hardware,
        "model": "AnimateDiff SD 1.5",
        "adapter": adapter_id,
        "base_model": base_model_id,
        "frames": len(frames),
        "resolution": f"{width}x{height}",
        "inference_steps": steps,
        "fps": 8,
        "output": str(target),
        "output_bytes": target.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="storage/animatediff-benchmark.mp4")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--seed", type=int, default=20261122)
    args = parser.parse_args()

    import torch

    print(f"GPU preflight passed: {check_runtime(torch)}")
    print(generate_benchmark(args.output, prompt=args.prompt, seed=args.seed))


if __name__ == "__main__":
    main()
