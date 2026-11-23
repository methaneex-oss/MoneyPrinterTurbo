"""Persistent, loopback-only AnimateDiff server for Colab.

The model is loaded once per runtime and kept behind a single-generation lock.
The server never calls a hosted inference API. The Stable Diffusion safety
checker is left enabled (the pipeline default).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

DEFAULT_ADAPTER = "guoyww/animatediff-motion-adapter-v1-5-2"
DEFAULT_BASE_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
MINIMUM_VRAM_GIB = float(os.environ.get("ANIMATEDIFF_MIN_VRAM_GIB", "12"))
PIPELINE = None
GENERATION_LOCK = threading.Lock()
MODEL_NAME = "AnimateDiff SD 1.5"


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=1200)
    aspect: str = Field(default="portrait", pattern="^(portrait|landscape|square)$")
    seed: int = Field(default=20261122, ge=0, le=2**32 - 1)
    steps: int = Field(default=12, ge=8, le=20)


def load_pipeline():
    if not torch.cuda.is_available():
        raise RuntimeError("AnimateDiff requires a CUDA GPU; no paid API fallback is configured")
    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    vram_gib = props.total_memory / (1024**3)
    if vram_gib < MINIMUM_VRAM_GIB:
        raise RuntimeError(
            f"AnimateDiff requires at least {MINIMUM_VRAM_GIB:.0f} GiB VRAM; "
            f"this runtime has {vram_gib:.1f} GiB"
        )

    from diffusers import AnimateDiffPipeline, DDIMScheduler, MotionAdapter

    adapter = MotionAdapter.from_pretrained(
        DEFAULT_ADAPTER,
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipeline = AnimateDiffPipeline.from_pretrained(
        DEFAULT_BASE_MODEL,
        motion_adapter=adapter,
        torch_dtype=torch.float16,
    )
    pipeline.scheduler = DDIMScheduler.from_pretrained(
        DEFAULT_BASE_MODEL,
        subfolder="scheduler",
        clip_sample=False,
        beta_schedule="linear",
        timestep_spacing="linspace",
        steps_offset=1,
    )
    pipeline.vae.enable_slicing()
    pipeline.enable_attention_slicing("max")
    pipeline.enable_model_cpu_offload()
    return pipeline, {
        "device": props.name,
        "vram_gib": round(vram_gib, 2),
        "model": MODEL_NAME,
        "adapter": DEFAULT_ADAPTER,
        "base_model": DEFAULT_BASE_MODEL,
        "precision": "float16",
        "safety_checker": "enabled",
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global PIPELINE, HARDWARE_REPORT
    PIPELINE, HARDWARE_REPORT = load_pipeline()
    yield
    PIPELINE = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(title="MoneyPrinterTurbo Local AnimateDiff", lifespan=lifespan)
HARDWARE_REPORT = {}


@app.get("/health")
def health():
    return {
        "status": "ready" if PIPELINE is not None else "loading",
        "backend": MODEL_NAME,
        "hardware": HARDWARE_REPORT,
    }


@app.post("/generate")
def generate(request: GenerateRequest):
    if PIPELINE is None:
        raise HTTPException(status_code=503, detail="AnimateDiff model is not ready")
    dimensions = {
        "portrait": (512, 768),
        "landscape": (768, 512),
        "square": (512, 512),
    }
    width, height = dimensions[request.aspect]
    if not GENERATION_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="AnimateDiff is already generating another scene")

    work_dir = Path(tempfile.mkdtemp(prefix="mpt-animatediff-"))
    raw_path = work_dir / "raw.mp4"
    final_path = work_dir / "scene.mp4"
    try:
        from diffusers.utils import export_to_video

        generator = torch.Generator(device="cpu").manual_seed(request.seed)
        result = PIPELINE(
            prompt=request.prompt,
            negative_prompt=(
                "text, captions, subtitles, watermark, logo, low quality, "
                "worst quality, blurry, flicker, distorted anatomy, unstable geometry"
            ),
            num_frames=16,
            num_inference_steps=request.steps,
            guidance_scale=7.5,
            width=width,
            height=height,
            generator=generator,
        )
        frames = result.frames[0]
        if len(frames) != 16:
            raise RuntimeError(f"AnimateDiff returned {len(frames)} frames instead of 16")
        export_to_video(frames, str(raw_path), fps=8)
        # 1.5x slow motion plus optical interpolation gives the short 16-frame
        # generation a more usable 3-second, 24-fps editorial clip.
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw_path),
                "-vf",
                "setpts=1.5*PTS,minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir",
                "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(final_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=240,
        )
        if not final_path.is_file() or final_path.stat().st_size < 16_384:
            raise RuntimeError("AnimateDiff did not produce a valid MP4 clip")
        return FileResponse(
            str(final_path),
            media_type="video/mp4",
            filename="animatediff-scene.mp4",
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="Video interpolation timed out") from exc
    except Exception as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"AnimateDiff generation failed: {type(exc).__name__}: {exc}",
        ) from exc
    finally:
        GENERATION_LOCK.release()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ANIMATEDIFF_PORT", "7862")))
