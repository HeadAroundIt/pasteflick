"""Apply PasteFlick updates from GitHub main. Stdlib only.

Chrome will not update an unpacked extension. This overwrites the install
folder (the one Load unpacked already points at), pins the zip to a commit
SHA, and keeps one rollback copy.

Not Chrome Web Store, not a self-hosted CRX, not a GitHub Release per bump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

GITHUB_REPO = "HeadAroundIt/pasteflick"
GITHUB_REF = "main"
USER_AGENT = "PasteFlick-updater"
MAX_ZIP_BYTES = 40 * 1024 * 1024
HOLD_NAME = "dev-hold"
APPLIED_NAME = "applied.json"
CONFIG_NAME = "updates.json"
PREVIOUS_DIR = "previous"
UPDATES_DIR = "updates"
TOKEN_NAME = "api-token.txt"

EXTENSION_FILES = (
    "manifest.json",
    "popup.html",
    "popup.js",
    "background.js",
    "content.js",
    "extractor.js",
    "pasteflick.js",
    "setup.html",
    "setup.js",
)
EXTENSION_ICONS = ("icon16.png", "icon32.png", "icon48.png", "icon128.png")
INSTALLER_FILES = (
    "install.ps1",
    "start-pastehost.ps1",
    "sync-extension.ps1",
    "copy-payload.ps1",
    "Setup.bat",
    "build-helper.ps1",
    "build-release.ps1",
)
ROOT_FILES = ("requirements.txt",)
HELPER_DIR = "helper"
HELPER_EXE = "PasteFlickHelper.exe"

BytesFetcher = Callable[[str], bytes]
JsonFetcher = Callable[[str], dict[str, Any]]


@dataclass
class UpdateResult:
    ok: bool
    applied: bool = False
    skipped: bool = False
    reason: str = ""
    sha: str = ""
    version: str = ""
    rolled_back: bool = False


def default_install_root() -> Path:
    override = (os.environ.get("PASTEFLICK_ROOT") or "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "PasteFlick"


def _utf8_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_api_token(root: Path | None = None) -> str:
    root = default_install_root() if root is None else root
    try:
        token = (root / TOKEN_NAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return token if len(token) >= 32 else ""


def ensure_api_token(root: Path, source: Path | None = None) -> str:
    token = read_api_token(root)
    if not token and source is not None:
        token = read_api_token(source)
    if not token:
        token = secrets.token_urlsafe(32)
    root.mkdir(parents=True, exist_ok=True)
    (root / TOKEN_NAME).write_text(token + "\n", encoding="utf-8")
    return token


def ensure_install_metadata(root: Path | None = None) -> str:
    root = default_install_root() if root is None else root
    ext = root / "extension"
    if not ext.is_dir():
        return ""
    token = ensure_api_token(root)
    _utf8_json(ext / "install-info.json", {"extensionPath": str(ext), "apiToken": token})
    return token


def read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def update_config(root: Path) -> dict[str, str]:
    data = read_json(root / CONFIG_NAME)
    repo = str(data.get("repo") or GITHUB_REPO).strip() or GITHUB_REPO
    ref = str(data.get("ref") or GITHUB_REF).strip() or GITHUB_REF
    return {"repo": repo, "ref": ref}


def read_applied(root: Path) -> dict[str, Any]:
    return read_json(root / APPLIED_NAME)


def write_applied(root: Path, data: dict[str, Any]) -> None:
    _utf8_json(root / APPLIED_NAME, data)


def read_manifest_version(root: Path) -> str:
    manifest = root / "extension" / "manifest.json"
    data = read_json(manifest)
    return str(data.get("version") or "").strip()


def hold_path(root: Path) -> Path:
    return root / HOLD_NAME


def is_held(root: Path) -> bool:
    return hold_path(root).is_file()


def write_hold(root: Path, note: str = "") -> None:
    text = note.strip() or "Local copy. GitHub updates are paused while this file exists."
    hold_path(root).write_text(text + "\n", encoding="utf-8")


def payload_ready(root: Path) -> bool:
    ext = root / "extension"
    if not (ext / "manifest.json").is_file():
        return False
    for name in EXTENSION_FILES:
        if not (ext / name).is_file():
            return False
    icons = ext / "icons"
    for name in EXTENSION_ICONS:
        if not (icons / name).is_file():
            return False
    return True


def copy_helper(src_root: Path, dst_root: Path) -> None:
    """Copy a bundled helper when the source has one. Leave an existing helper otherwise."""
    src = src_root / HELPER_DIR
    exe = src / HELPER_EXE
    if not exe.is_file():
        return
    dst = dst_root / HELPER_DIR
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_payload(src_root: Path, dst_root: Path) -> None:
    """Overwrite install files from a source tree. Leaves .venv, previous/, updates/, and a helper that the source zip did not include."""
    src_root = src_root.resolve()
    dst_root = dst_root.resolve()
    if not payload_ready(src_root):
        raise ValueError("Source is missing required PasteFlick files")

    ext_src = src_root / "extension"
    ext_dst = dst_root / "extension"
    icons_dst = ext_dst / "icons"
    ext_dst.mkdir(parents=True, exist_ok=True)
    icons_dst.mkdir(parents=True, exist_ok=True)
    for name in EXTENSION_FILES:
        shutil.copy2(ext_src / name, ext_dst / name)
    for name in EXTENSION_ICONS:
        shutil.copy2(ext_src / "icons" / name, icons_dst / name)
    leftover_ext_priv = ext_dst / "private"
    if leftover_ext_priv.is_dir():
        shutil.rmtree(leftover_ext_priv)

    app_src = src_root / "app"
    app_dst = dst_root / "app"
    if app_src.is_dir():
        app_dst.mkdir(parents=True, exist_ok=True)
        source_names = {py.name for py in app_src.glob("*.py")}
        for py in app_dst.glob("*.py"):
            if py.name not in source_names:
                py.unlink()
        for py in sorted(app_src.glob("*.py")):
            shutil.copy2(py, app_dst / py.name)
        leftover_app_priv = app_dst / "private"
        if leftover_app_priv.is_dir():
            shutil.rmtree(leftover_app_priv)

    inst_src = src_root / "installer"
    inst_dst = dst_root / "installer"
    if inst_src.is_dir():
        inst_dst.mkdir(parents=True, exist_ok=True)
        for name in INSTALLER_FILES:
            src = inst_src / name
            if src.is_file():
                shutil.copy2(src, inst_dst / name)

    for name in ROOT_FILES:
        src = src_root / name
        if src.is_file():
            shutil.copy2(src, dst_root / name)

    copy_helper(src_root, dst_root)

    version = read_manifest_version(dst_root)
    if version:
        (dst_root / "version.txt").write_text(version + "\n", encoding="utf-8")
    (dst_root / "extension-path.txt").write_text(str(ext_dst) + "\n", encoding="utf-8")
    ensure_api_token(dst_root, src_root)
    ensure_install_metadata(dst_root)


def _venv_python(root: Path) -> Path | None:
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python3",
        root / ".venv" / "bin" / "python",
    )
    return next((path for path in candidates if path.is_file()), None)


def sync_dependencies(root: Path, previous_requirements: bytes | None) -> None:
    requirements = root / "requirements.txt"
    current = requirements.read_bytes() if requirements.is_file() else b""
    if current == (previous_requirements or b""):
        return
    python = _venv_python(root)
    if python is None or not requirements.is_file():
        return
    result = subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(requirements)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "pip failed").strip().splitlines()[-1]
        raise RuntimeError(f"Dependency update failed: {detail}")
    marker = root / ".venv" / "pasteflick-requirements.sha256"
    marker.write_text(hashlib.sha256(current).hexdigest() + "\n", encoding="ascii")


def snapshot_previous(root: Path) -> None:
    if not payload_ready(root):
        return
    prev = root / PREVIOUS_DIR
    if prev.exists():
        shutil.rmtree(prev, ignore_errors=True)
    staging = root / UPDATES_DIR / "previous-staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    copy_payload(root, staging)
    applied = root / APPLIED_NAME
    if applied.is_file():
        shutil.copy2(applied, staging / APPLIED_NAME)
    staging.replace(prev)


def restore_previous(root: Path) -> bool:
    prev = root / PREVIOUS_DIR
    if not payload_ready(prev):
        return False
    copy_payload(prev, root)
    applied = prev / APPLIED_NAME
    if applied.is_file():
        shutil.copy2(applied, root / APPLIED_NAME)
    return True


def find_extracted_root(extract_dir: Path) -> Path:
    if payload_ready(extract_dir):
        return extract_dir
    for child in sorted(extract_dir.iterdir()):
        if child.is_dir() and payload_ready(child):
            return child
    raise ValueError("Downloaded zip is not a PasteFlick tree")


def _urlopen(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json, application/zip, */*",
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as res:
        data = res.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("Download was larger than expected")
    return data


def fetch_main_sha(repo: str, ref: str, fetch_json: JsonFetcher | None = None) -> str:
    url = f"https://api.github.com/repos/{repo}/commits/{ref}"
    if fetch_json is None:
        raw = json.loads(_urlopen(url, timeout=20).decode("utf-8"))
    else:
        raw = fetch_json(url)
    sha = str(raw.get("sha") or "").strip().lower()
    if len(sha) < 12 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("GitHub did not return a commit")
    return sha


def download_sha_zip(repo: str, sha: str, dest: Path, fetch_bytes: BytesFetcher | None = None) -> str:
    """Download the tree at this SHA. Returns hex sha256 of the zip bytes."""
    url = f"https://codeload.github.com/{repo}/zip/{sha}"
    data = fetch_bytes(url) if fetch_bytes is not None else _urlopen(url, timeout=60)
    if len(data) < 64 or data[:2] != b"PK":
        raise ValueError("Download was not a zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def safe_extract(zip_path: Path, dest: Path) -> None:
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("Zip contained an unsafe path")
            target = (dest / name).resolve()
            try:
                target.relative_to(dest)
            except ValueError as exc:
                raise ValueError("Zip contained an unsafe path") from exc
        zf.extractall(dest)


def status_dict(root: Path | None = None) -> dict[str, Any]:
    root = default_install_root() if root is None else root
    applied = read_applied(root)
    version = read_manifest_version(root)
    return {
        "ok": payload_ready(root),
        "app": "pasteflick",
        "version": version,
        "extensionPath": str(root / "extension"),
        "sha": str(applied.get("sha") or ""),
        "ref": str(applied.get("ref") or update_config(root)["ref"]),
        "held": is_held(root),
        "appliedAt": applied.get("applied_at") or 0,
        "zipSha256": str(applied.get("zip_sha256") or ""),
        "reason": str(applied.get("reason") or ""),
    }


def check_and_apply(
    root: Path | None = None,
    *,
    force: bool = False,
    fetch_json: JsonFetcher | None = None,
    fetch_bytes: BytesFetcher | None = None,
) -> UpdateResult:
    root = default_install_root() if root is None else root
    root.mkdir(parents=True, exist_ok=True)
    cfg = update_config(root)

    if is_held(root) and not force:
        version = read_manifest_version(root)
        return UpdateResult(ok=True, skipped=True, reason="held", sha=str(read_applied(root).get("sha") or ""), version=version)

    try:
        sha = fetch_main_sha(cfg["repo"], cfg["ref"], fetch_json=fetch_json)
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return UpdateResult(ok=True, skipped=True, reason=f"check-failed: {exc}")

    current = str(read_applied(root).get("sha") or "").strip().lower()
    if current == sha and payload_ready(root) and not force:
        version = read_manifest_version(root)
        write_applied(
            root,
            {
                **read_applied(root),
                "sha": sha,
                "version": version,
                "ref": cfg["ref"],
                "checked_at": int(time.time()),
                "reason": "current",
            },
        )
        return UpdateResult(ok=True, skipped=True, reason="current", sha=sha, version=version)

    work = root / UPDATES_DIR
    extract = work / "extract"
    zip_path = work / "fetch.zip"
    if extract.exists():
        shutil.rmtree(extract, ignore_errors=True)
    extract.mkdir(parents=True, exist_ok=True)

    try:
        zip_sha = download_sha_zip(cfg["repo"], sha, zip_path, fetch_bytes=fetch_bytes)
        safe_extract(zip_path, extract)
        source = find_extracted_root(extract)
        old_requirements = (root / "requirements.txt").read_bytes() if (root / "requirements.txt").is_file() else b""
        snapshot_previous(root)
        copy_payload(source, root)
        sync_dependencies(root, old_requirements)
        if not payload_ready(root):
            raise ValueError("Update did not leave a usable extension")
        version = read_manifest_version(root)
        write_applied(
            root,
            {
                "sha": sha,
                "version": version,
                "ref": cfg["ref"],
                "repo": cfg["repo"],
                "applied_at": int(time.time()),
                "checked_at": int(time.time()),
                "zip_sha256": zip_sha,
                "reason": "applied",
            },
        )
        cfg_path = root / CONFIG_NAME
        if not cfg_path.is_file():
            _utf8_json(cfg_path, {"repo": cfg["repo"], "ref": cfg["ref"]})
        return UpdateResult(ok=True, applied=True, reason="applied", sha=sha, version=version)
    except Exception as exc:
        rolled = False
        failed_requirements = (
            (root / "requirements.txt").read_bytes() if (root / "requirements.txt").is_file() else b""
        )
        try:
            rolled = restore_previous(root)
            if rolled:
                sync_dependencies(root, failed_requirements)
        except Exception:
            rolled = False
        return UpdateResult(
            ok=False,
            reason=str(exc),
            sha=sha,
            rolled_back=rolled,
        )
    finally:
        shutil.rmtree(extract, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update PasteFlick from GitHub main")
    parser.add_argument("--root", default="", help="Install folder (defaults to the user install)")
    parser.add_argument("--status", action="store_true", help="Print status JSON and exit")
    parser.add_argument("--force", action="store_true", help="Apply even if the SHA already matches")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root.strip() else default_install_root()
    if args.status:
        print(json.dumps(status_dict(root)))
        return 0
    result = check_and_apply(root, force=args.force)
    print(json.dumps(asdict(result)))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
