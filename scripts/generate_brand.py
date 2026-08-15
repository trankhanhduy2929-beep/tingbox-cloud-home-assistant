#!/usr/bin/env python3
"""Generate the original Tingbox integration icon without external packages."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "custom_components/tingbox/brand/icon.png"
SIZE = 256


def inside_rounded_rectangle(
    x_position: int,
    y_position: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
) -> bool:
    """Return whether a pixel is inside a rounded rectangle."""
    if left + radius <= x_position <= right - radius:
        return top <= y_position <= bottom
    if top + radius <= y_position <= bottom - radius:
        return left <= x_position <= right
    center_x = left + radius if x_position < left + radius else right - radius
    center_y = top + radius if y_position < top + radius else bottom - radius
    return (x_position - center_x) ** 2 + (y_position - center_y) ** 2 <= radius**2


def inside_circle(
    x_position: int,
    y_position: int,
    center_x: int,
    center_y: int,
    radius: int,
) -> bool:
    """Return whether a pixel is inside a circle."""
    return (x_position - center_x) ** 2 + (y_position - center_y) ** 2 <= radius**2


def pixel(x_position: int, y_position: int) -> tuple[int, int, int, int]:
    """Return the RGBA value for one icon pixel."""
    if not inside_rounded_rectangle(x_position, y_position, 8, 8, 247, 247, 48):
        return 0, 0, 0, 0
    color = (18, 92, 160, 255)
    if inside_rounded_rectangle(x_position, y_position, 70, 30, 186, 226, 28):
        color = (245, 250, 255, 255)
    if inside_circle(x_position, y_position, 128, 88, 26):
        color = (18, 92, 160, 255)
    if inside_circle(x_position, y_position, 128, 172, 42):
        color = (18, 92, 160, 255)
    if inside_circle(x_position, y_position, 128, 172, 20):
        color = (245, 250, 255, 255)
    return color


def chunk(chunk_type: bytes, payload: bytes) -> bytes:
    """Build a PNG chunk."""
    checksum = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", checksum)
    )


def main() -> int:
    """Write the PNG brand icon."""
    raw = bytearray()
    for y_position in range(SIZE):
        raw.append(0)
        for x_position in range(SIZE):
            raw.extend(pixel(x_position, y_position))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
    png += chunk(b"IEND", b"")
    OUTPUT.write_bytes(png)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
