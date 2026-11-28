from pathlib import Path

import pytest

from app.paths import _copy_missing_resource


def test_copy_missing_resource_falls_back_when_hardlinks_are_not_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.ttf"
    target = tmp_path / "drive" / "fonts" / "font.ttf"
    source.write_bytes(b"font-data")

    def unsupported_link(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr("app.paths.os.link", unsupported_link)
    _copy_missing_resource(source, target)

    assert target.read_bytes() == b"font-data"
    assert not list(target.parent.glob(".resource-*"))


def test_copy_missing_resource_does_not_overwrite_existing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.ttf"
    target = tmp_path / "font.ttf"
    source.write_bytes(b"new-font")
    target.write_bytes(b"user-font")

    def unsupported_link(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr("app.paths.os.link", unsupported_link)
    _copy_missing_resource(source, target)

    assert target.read_bytes() == b"user-font"
