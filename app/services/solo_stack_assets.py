"""Evidence-first local asset library for Solo Stack episodes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

MAX_ASSET_BYTES = 100 * 1024 * 1024
_ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class SoloStackAssetError(ValueError):
    """Invalid asset or evidence record."""


def _safe_name(value: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise SoloStackAssetError("Name must use 1–80 letters, digits, dots, underscores or hyphens.")
    if value in {".", ".."}:
        raise SoloStackAssetError("Invalid name.")
    return value


def _safe_product(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
        raise SoloStackAssetError("Product name must contain 1–120 characters.")
    if _CONTROL.search(value):
        raise SoloStackAssetError("Product name contains invalid control characters.")
    return value.strip()


def validate_source_url(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or _CONTROL.search(value):
        raise SoloStackAssetError("Source URL contains invalid characters.")
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SoloStackAssetError("Source URL must be an absolute HTTP(S) URL.")
    if parsed.username is not None or parsed.password is not None:
        raise SoloStackAssetError("Credentials are not allowed in source URLs.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _manifest_path(project_dir: Path) -> Path:
    return project_dir / "solo_stack_manifest.json"


def _load_manifest(project_dir: Path) -> dict:
    path = _manifest_path(project_dir)
    if not path.exists():
        return {"schema_version": 1, "assets": [], "evidence": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SoloStackAssetError("The Solo Stack manifest is unreadable.") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise SoloStackAssetError("Unsupported Solo Stack manifest schema.")
    if not isinstance(payload.get("assets"), list) or not isinstance(payload.get("evidence"), list):
        raise SoloStackAssetError("Malformed Solo Stack manifest collections.")
    return payload


def _save_manifest(project_dir: Path, payload: dict) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    destination = _manifest_path(project_dir)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)


def register_asset(
    source_path: str | Path,
    project_dir: str | Path,
    *,
    asset_id: str,
    product: str,
    asset_type: str,
    source_url: str | None = None,
    captured_at: str | None = None,
    notes: str = "",
) -> dict:
    """Copy one genuine local capture into the episode library and record provenance."""
    asset_id = _safe_name(asset_id)
    product = _safe_product(product)
    if asset_type not in {"screenshot", "screen_recording", "demo_media", "logo"}:
        raise SoloStackAssetError("Unsupported asset type.")
    source = Path(source_path)
    if source.is_symlink() or not source.is_file():
        raise SoloStackAssetError("Asset must be a regular file, not a symlink.")
    suffix = source.suffix.lower()
    if suffix not in _ALLOWED:
        raise SoloStackAssetError("Unsupported asset format.")
    size = source.stat().st_size
    if size <= 0 or size > MAX_ASSET_BYTES:
        raise SoloStackAssetError("Asset must be between 1 byte and 100 MiB.")
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image
            with Image.open(source) as image:
                image.verify()
        except Exception as exc:
            raise SoloStackAssetError("Image asset is not a valid decodable image.") from exc
    else:
        with source.open("rb") as media:
            header = media.read(16)
        is_mp4 = suffix in {".mp4", ".mov"} and len(header) >= 8 and header[4:8] == b"ftyp"
        is_webm = suffix == ".webm" and header.startswith(b"\\x1a\\x45\\xdf\\xa3")
        if not (is_mp4 or is_webm):
            raise SoloStackAssetError("Video asset does not have a valid MP4/MOV or WebM container header.")
    if captured_at:
        try:
            date.fromisoformat(captured_at)
        except ValueError as exc:
            raise SoloStackAssetError("captured_at must be an ISO date (YYYY-MM-DD).") from exc
    source_url = validate_source_url(source_url)
    if not isinstance(notes, str) or len(notes) > 2000 or _CONTROL.search(notes):
        raise SoloStackAssetError("Notes must be plain text of at most 2,000 characters.")
    project = Path(project_dir).resolve()
    assets_dir = project / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = assets_dir / f"{asset_id}{suffix}"
    if target.exists():
        raise SoloStackAssetError("An asset with this ID already exists; choose a new ID.")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    temporary = target.with_name(target.name + ".tmp")
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
        manifest = _load_manifest(project)
        if any(item.get("asset_id") == asset_id for item in manifest["assets"]):
            target.unlink(missing_ok=True)
            raise SoloStackAssetError("Asset ID already exists in the manifest.")
        record = {
            "asset_id": asset_id, "product": product, "asset_type": asset_type,
            "file": f"assets/{target.name}", "sha256": digest, "bytes": size,
            "source_url": source_url, "captured_at": captured_at,
            "notes": notes.strip(),
        }
        manifest["assets"].append(record)
        _save_manifest(project, manifest)
        return record
    except Exception:
        temporary.unlink(missing_ok=True)
        if target.exists():
            target.unlink(missing_ok=True)
        raise


def add_evidence(
    project_dir: str | Path,
    *,
    claim_id: str,
    product: str,
    claim: str,
    source_url: str,
    publisher: str,
    checked_at: str,
    value: str | None = None,
    currency: str | None = None,
    plan: str | None = None,
) -> dict:
    """Record a sourced claim; never treats an unverified assertion as evidence."""
    claim_id, product = _safe_name(claim_id), _safe_product(product)
    if not isinstance(claim, str) or not claim.strip() or len(claim) > 2000:
        raise SoloStackAssetError("Evidence claim must contain 1–2,000 characters.")
    if not isinstance(publisher, str) or not publisher.strip() or len(publisher) > 160:
        raise SoloStackAssetError("Publisher is required.")
    source_url = validate_source_url(source_url)
    try:
        date.fromisoformat(checked_at)
    except (TypeError, ValueError) as exc:
        raise SoloStackAssetError("checked_at must be an ISO date (YYYY-MM-DD).") from exc
    for field_name, field_value in (("value", value), ("currency", currency), ("plan", plan)):
        if field_value is not None and (not isinstance(field_value, str) or len(field_value) > 160):
            raise SoloStackAssetError(f"{field_name} must be plain text of at most 160 characters.")
    project = Path(project_dir).resolve()
    manifest = _load_manifest(project)
    if any(item.get("claim_id") == claim_id for item in manifest["evidence"]):
        raise SoloStackAssetError("Evidence claim ID already exists.")
    record = {
        "claim_id": claim_id, "product": product, "claim": claim.strip(),
        "source_url": source_url, "publisher": publisher.strip(),
        "checked_at": checked_at, "value": value, "currency": currency, "plan": plan,
    }
    manifest["evidence"].append(record)
    _save_manifest(project, manifest)
    return record


def verify_asset(project_dir: str | Path, asset_id: str) -> bool:
    """Verify stored asset bytes against their immutable manifest digest."""
    asset_id = _safe_name(asset_id)
    project = Path(project_dir).resolve()
    manifest = _load_manifest(project)
    record = next((item for item in manifest["assets"] if item.get("asset_id") == asset_id), None)
    if record is None:
        raise SoloStackAssetError("Asset ID was not found.")
    relative = Path(record["file"])
    if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "assets":
        raise SoloStackAssetError("Manifest contains an unsafe asset path.")
    target = (project / relative).resolve()
    if project not in target.parents or not target.is_file():
        return False
    return hashlib.sha256(target.read_bytes()).hexdigest() == record.get("sha256")
