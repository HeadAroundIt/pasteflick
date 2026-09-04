"""GitHub-main updater: SHA pin, overwrite the install folder, one rollback."""

from __future__ import annotations

import io
import json
import subprocess
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.server import app
from app.update import (
    EXTENSION_FILES,
    EXTENSION_ICONS,
    HELPER_EXE,
    UpdateResult,
    check_and_apply,
    copy_payload,
    ensure_api_token,
    payload_ready,
    read_api_token,
    restore_previous,
    snapshot_previous,
    status_dict,
    sync_dependencies,
    write_hold,
)


def _tree(root: Path, version: str = "1.2.3") -> None:
    ext = root / "extension"
    (ext / "icons").mkdir(parents=True)
    for name in EXTENSION_FILES:
        (ext / name).write_text("file " + name, encoding="utf-8")
    (ext / "manifest.json").write_text(json.dumps({"version": version, "name": "PasteFlick"}), encoding="utf-8")
    for icon in EXTENSION_ICONS:
        (ext / "icons" / icon).write_bytes(b"png")
    (root / "app").mkdir()
    (root / "app" / "update.py").write_text("# update\n", encoding="utf-8")
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "installer").mkdir()
    (root / "installer" / "install.ps1").write_text("# install\n", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi>=0.115.0\n", encoding="utf-8")


def _zip_bytes(version: str, sha: str) -> bytes:
    inner = Path("PasteFlick-" + sha[:8])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        ext = inner / "extension"
        for name in EXTENSION_FILES:
            if name == "manifest.json":
                continue
            zf.writestr((ext / name).as_posix(), "file " + name)
        zf.writestr((ext / "manifest.json").as_posix(), json.dumps({"version": version, "name": "PasteFlick"}))
        for icon in EXTENSION_ICONS:
            zf.writestr((ext / "icons" / icon).as_posix(), b"png")
        zf.writestr((inner / "app" / "update.py").as_posix(), "# update\n")
        zf.writestr((inner / "app" / "__init__.py").as_posix(), "")
        zf.writestr((inner / "installer" / "install.ps1").as_posix(), "# install\n")
        zf.writestr((inner / "requirements.txt").as_posix(), "fastapi>=0.115.0\n")
    return buf.getvalue()


def test_copy_payload_and_rollback(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(src, "1.2.3")
    copy_payload(src, dst)
    assert payload_ready(dst)
    assert not (dst / "extension" / "private").exists()
    assert not (dst / "app" / "private").exists()
    assert (dst / "version.txt").read_text(encoding="utf-8").strip() == "1.2.3"
    info = json.loads((dst / "extension" / "install-info.json").read_text(encoding="utf-8"))
    assert info["extensionPath"]
    assert info["apiToken"] == read_api_token(dst)

    snapshot_previous(dst)
    newer = tmp_path / "newer"
    _tree(newer, "1.2.4")
    copy_payload(newer, dst)
    assert json.loads((dst / "extension" / "manifest.json").read_text(encoding="utf-8"))["version"] == "1.2.4"
    assert restore_previous(dst) is True
    assert json.loads((dst / "extension" / "manifest.json").read_text(encoding="utf-8"))["version"] == "1.2.3"


def test_copy_payload_keeps_helper_when_source_has_none(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(src)
    helper = dst / "helper"
    helper.mkdir(parents=True)
    (helper / HELPER_EXE).write_bytes(b"helper")
    (helper / "readme.txt").write_text("keep me\n", encoding="utf-8")
    copy_payload(src, dst)
    assert (helper / HELPER_EXE).read_bytes() == b"helper"
    assert (helper / "readme.txt").read_text(encoding="utf-8") == "keep me\n"


def test_copy_payload_replaces_helper_when_source_has_one(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(src)
    _tree(dst)
    old = dst / "helper"
    old.mkdir()
    (old / HELPER_EXE).write_bytes(b"old")
    (old / "stale.dll").write_bytes(b"gone")
    new = src / "helper"
    new.mkdir()
    (new / HELPER_EXE).write_bytes(b"new")
    (new / "fresh.dll").write_bytes(b"ok")
    copy_payload(src, dst)
    assert (dst / "helper" / HELPER_EXE).read_bytes() == b"new"
    assert (dst / "helper" / "fresh.dll").read_bytes() == b"ok"
    assert not (dst / "helper" / "stale.dll").exists()


def test_copy_and_rollback_remove_orphan_modules(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(src)
    _tree(dst)
    orphan = dst / "app" / "removed.py"
    orphan.write_text("old code\n", encoding="utf-8")
    priv_dir = dst / "app" / "private"
    priv_dir.mkdir()
    (priv_dir / "stale.py").write_text("old private\n", encoding="utf-8")
    copy_payload(src, dst)
    assert not orphan.exists()
    assert not priv_dir.exists()

    snapshot_previous(dst)
    orphan.write_text("new code\n", encoding="utf-8")
    priv_dir.mkdir()
    (priv_dir / "stale.py").write_text("new private\n", encoding="utf-8")
    assert restore_previous(dst) is True
    assert not orphan.exists()
    assert not priv_dir.exists()


def test_api_token_is_preserved_across_payload_copy(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(src)
    token = ensure_api_token(dst)
    copy_payload(src, dst)
    assert read_api_token(dst) == token
    info = json.loads((dst / "extension" / "install-info.json").read_text(encoding="utf-8"))
    assert info["apiToken"] == token


def test_dependency_sync_runs_only_when_requirements_change(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "install"
    python = root / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"")
    (root / "requirements.txt").write_bytes(b"new requirement\n")
    calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("app.update.subprocess.run", fake_run)
    sync_dependencies(root, b"old requirement\n")
    assert calls and calls[0][1:4] == ["-m", "pip", "install"]
    calls.clear()
    sync_dependencies(root, b"new requirement\n")
    assert calls == []


def test_skip_when_sha_matches(tmp_path: Path) -> None:
    root = tmp_path / "install"
    _tree(root, "1.2.3")
    sha = "a" * 40
    (root / "applied.json").write_text(json.dumps({"sha": sha, "version": "1.2.3"}), encoding="utf-8")

    def fetch_json(_url: str) -> dict:
        return {"sha": sha}

    def fetch_bytes(_url: str) -> bytes:
        raise AssertionError("should not download when current")

    result = check_and_apply(root, fetch_json=fetch_json, fetch_bytes=fetch_bytes)
    assert result == UpdateResult(ok=True, skipped=True, reason="current", sha=sha, version="1.2.3")


def test_hold_skips_github(tmp_path: Path) -> None:
    root = tmp_path / "install"
    _tree(root, "1.2.3")
    write_hold(root)

    def fetch_json(_url: str) -> dict:
        raise AssertionError("held installs should not hit GitHub")

    result = check_and_apply(root, fetch_json=fetch_json)
    assert result.ok is True
    assert result.skipped is True
    assert result.reason == "held"


def test_apply_new_sha(tmp_path: Path) -> None:
    root = tmp_path / "install"
    _tree(root, "1.2.3")
    sha = "b" * 40
    payload = _zip_bytes("1.2.9", sha)

    def fetch_json(_url: str) -> dict:
        return {"sha": sha}

    def fetch_bytes(_url: str) -> bytes:
        return payload

    result = check_and_apply(root, fetch_json=fetch_json, fetch_bytes=fetch_bytes)
    assert result.ok is True
    assert result.applied is True
    assert result.version == "1.2.9"
    assert result.sha == sha
    applied = json.loads((root / "applied.json").read_text(encoding="utf-8"))
    assert applied["sha"] == sha
    assert applied["zip_sha256"]
    assert payload_ready(root / "previous")
    assert json.loads((root / "previous" / "extension" / "manifest.json").read_text(encoding="utf-8"))["version"] == "1.2.3"


def test_bad_zip_rolls_back(tmp_path: Path) -> None:
    root = tmp_path / "install"
    _tree(root, "1.2.3")
    sha = "c" * 40

    def fetch_json(_url: str) -> dict:
        return {"sha": sha}

    def fetch_bytes(_url: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("PasteFlick-cccc/readme.txt", "nope")
        return buf.getvalue()

    result = check_and_apply(root, fetch_json=fetch_json, fetch_bytes=fetch_bytes)
    assert result.ok is False
    assert json.loads((root / "extension" / "manifest.json").read_text(encoding="utf-8"))["version"] == "1.2.3"


def test_unsafe_zip_rejected(tmp_path: Path) -> None:
    root = tmp_path / "install"
    _tree(root, "1.2.3")
    sha = "d" * 40

    def fetch_json(_url: str) -> dict:
        return {"sha": sha}

    def fetch_bytes(_url: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../escape.txt", "nope")
        return buf.getvalue()

    result = check_and_apply(root, fetch_json=fetch_json, fetch_bytes=fetch_bytes)
    assert result.ok is False
    assert not (tmp_path / "escape.txt").exists()
    assert json.loads((root / "extension" / "manifest.json").read_text(encoding="utf-8"))["version"] == "1.2.3"


def test_health_and_update_status_shape(monkeypatch, tmp_path: Path) -> None:
    _tree(tmp_path, "9.9.9")
    monkeypatch.setenv("PASTEFLICK_ROOT", str(tmp_path))
    status = status_dict(tmp_path)
    assert status["ok"] is True
    assert status["version"] == "9.9.9"
    assert status["app"] == "pasteflick"
    assert status["extensionPath"] == str(tmp_path / "extension")

    client = TestClient(app)
    health = client.get("/api/health").json()
    assert health["ok"] is True
    assert health["app"] == "pasteflick"
    assert "version" in health
    assert client.get("/api/update-status").status_code == 200


def test_mutating_api_requires_install_token(monkeypatch, tmp_path: Path) -> None:
    _tree(tmp_path)
    token = ensure_api_token(tmp_path)
    monkeypatch.setenv("PASTEFLICK_ROOT", str(tmp_path))
    client = TestClient(app)
    assert client.post("/api/clear").status_code == 401
    assert client.post("/api/clear", headers={"X-PasteFlick-Token": token}).status_code == 200
