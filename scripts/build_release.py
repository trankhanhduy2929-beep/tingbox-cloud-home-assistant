#!/usr/bin/env python3
"""Build a deterministic GitHub-ready Tingbox source archive."""

from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
DEFAULT_OUTPUT = Path("/opt/apk-lab/input/tingbox/ket_qua")
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
}


def release_files() -> list[Path]:
    """Return files included in the source archive."""
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts):
            continue
        if path.suffix in {".pyc", ".zip"} or path.name.endswith(".sha256"):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    """Validate and build the release archive."""
    sys.path.insert(0, str(ROOT))
    from scripts.validate_release import main as validate_release

    validate_release()
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"tingbox_hass-v{VERSION}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=9) as handle:
        for path in release_files():
            relative = path.relative_to(ROOT).as_posix()
            info = ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            mode = 0o100755 if path.stat().st_mode & 0o111 else 0o100644
            info.external_attr = mode << 16
            handle.writestr(info, path.read_bytes())
    digest = sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n")
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
