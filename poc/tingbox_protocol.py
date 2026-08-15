#!/usr/bin/env python3
"""Offline, redacted Tingbox protocol demonstrator."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SafePayment:
    """Payment fields that are safe to retain."""

    amount: int
    broadcast_type: str | None
    request_fingerprint: str | None


def parse_payment(payload: bytes) -> SafePayment | None:
    """Discard QR, bank, account, and mobile-user fields."""
    if not payload or len(payload) > 262_144:
        return None
    try:
        decoded = json.loads(payload.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict) or "money" not in decoded:
        return None
    amount = parse_amount(decoded["money"])
    if amount is None:
        return None
    broadcast_type_raw = decoded.get("broadcast_type")
    broadcast_type = (
        str(broadcast_type_raw)
        if isinstance(broadcast_type_raw, (str, int))
        else None
    )
    request_id = decoded.get("request_id")
    fingerprint = None
    if isinstance(request_id, (str, int)):
        fingerprint = sha256(str(request_id).encode()).hexdigest()
    return SafePayment(amount, broadcast_type, fingerprint)


def parse_amount(value: Any) -> int | None:
    """Parse non-negative integer VND values."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 and value.is_integer() else None
    if isinstance(value, str):
        if value.strip().startswith("-"):
            return None
        digits = re.sub(r"[^0-9]", "", value)
        return int(digits) if digits and len(digits) <= 18 else None
    return None


def home_assistant_to_wire(level: int) -> int:
    """Convert user-facing brightness 1-7 to wire brightness 6-0."""
    if not 1 <= level <= 7:
        raise ValueError("Home Assistant brightness must be in range 1..7")
    return 7 - level


def wire_to_home_assistant(level: int) -> int:
    """Convert wire brightness 0-6 to user-facing brightness 7-1."""
    if not 0 <= level <= 6:
        raise ValueError("Wire brightness must be in range 0..6")
    return 7 - level


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        description="Inspect a local Tingbox payload without printing sensitive fields"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    payment = subparsers.add_parser("payment", help="Parse a local MQTT JSON file")
    payment.add_argument("file", type=Path)
    brightness = subparsers.add_parser("brightness", help="Convert brightness levels")
    group = brightness.add_mutually_exclusive_group(required=True)
    group.add_argument("--ha-level", type=int)
    group.add_argument("--wire-level", type=int)
    return parser


def main() -> int:
    """Run the offline demonstrator."""
    arguments = build_parser().parse_args()
    if arguments.command == "payment":
        payment = parse_payment(arguments.file.read_bytes())
        print(json.dumps(asdict(payment) if payment else {"payment": None}))
        return 0
    if arguments.ha_level is not None:
        print(json.dumps({"wire_level": home_assistant_to_wire(arguments.ha_level)}))
    else:
        print(
            json.dumps(
                {"ha_level": wire_to_home_assistant(arguments.wire_level)}
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
