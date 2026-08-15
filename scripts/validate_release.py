#!/usr/bin/env python3
"""Validate a Tingbox source tree before release."""

from __future__ import annotations

import compileall
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    "README.md",
    "REPORT.md",
    "CHANGELOG.md",
    "LICENSE",
    "hacs.json",
    "custom_components/tingbox/__init__.py",
    "custom_components/tingbox/config_flow.py",
    "custom_components/tingbox/brand/icon.png",
    "custom_components/tingbox/manifest.json",
    "custom_components/tingbox/strings.json",
    "custom_components/tingbox/translations/vi.json",
}
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
FORBIDDEN_NAMES = {
    "tingbox_login.json",
    "tingbox_device_token.txt",
    "tingbox_config_candidate_0.json",
    "tingbox_config_candidate_1.json",
}
FORBIDDEN_TEMP_PREFIX = "/" + "tmp/tingbox_"
SECRET_PATTERNS = {
    "authorization token": re.compile(
        r"(?i)authorization\s*[:=]\s*['\"][A-Za-z0-9._-]{24,}"
    ),
    "Vietnamese phone number": re.compile(r"(?<!\d)0[35789]\d{8}(?!\d)"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def fail(message: str) -> None:
    """Print a validation failure and exit."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def iter_release_files() -> list[Path]:
    """Return release files excluding caches and generated archives."""
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts):
            continue
        if path.suffix in {".pyc", ".zip"} or path.name.endswith(".sha256"):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    """Validate metadata, syntax, and common secret patterns."""
    missing = sorted(path for path in REQUIRED_FILES if not (ROOT / path).is_file())
    if missing:
        fail(f"missing required files: {', '.join(missing)}")

    for path in (ROOT / "custom_components/tingbox").rglob("*.json"):
        json.loads(path.read_text())
    json.loads((ROOT / "hacs.json").read_text())

    if not compileall.compile_dir(ROOT / "custom_components", quiet=1):
        fail("Python compilation failed")

    for path in iter_release_files():
        if path.name in FORBIDDEN_NAMES:
            fail(f"forbidden artifact: {path.relative_to(ROOT)}")
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if FORBIDDEN_TEMP_PREFIX in text:
            fail(f"temporary secret path referenced by {path.relative_to(ROOT)}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                fail(f"possible {label} in {path.relative_to(ROOT)}")

    print(f"Validated {len(iter_release_files())} release files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
