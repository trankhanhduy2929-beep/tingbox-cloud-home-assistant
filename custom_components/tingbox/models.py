"""Data models for Tingbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class TingboxSession:
    """Authenticated account session."""

    token: str
    merchant_id: str | int
    merchant_username: str
    user_id: str


@dataclass(frozen=True, slots=True)
class TingboxDevice:
    """A speaker assigned to the account."""

    mutb_id: str
    serial: str
    category: str
    status: str | None
    status_code: str | None
    supports_brightness: bool
    channel_description: str | None = None

    @property
    def identifier(self) -> str:
        """Return a stable privacy-preserving identifier."""
        source = f"{self.mutb_id}\0{self.serial}".encode()
        return sha256(source).hexdigest()[:24]

    @property
    def display_name(self) -> str:
        """Return a display name without exposing the full serial."""
        suffix = self.serial[-4:] if self.serial else self.identifier[-4:]
        return f"Tingbox {suffix}"


@dataclass(frozen=True, slots=True)
class TingboxMqttConfig:
    """Cloud MQTT connection data."""

    host: str
    port: int
    username: str
    password: str
    client_id: str
    topic: str


@dataclass(frozen=True, slots=True)
class TingboxAccountConfig:
    """Safe account state and runtime MQTT credentials."""

    mqtt: TingboxMqttConfig
    total_amount: int | None
    transaction_count: int | None
    current_mode: str | None
    qr_default_configured: bool | None
    phone_announcements: bool | None = None


@dataclass(frozen=True, slots=True)
class TingboxPayment:
    """A redacted payment event."""

    amount: int
    broadcast_type: str | None
    request_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class TingboxSnapshot:
    """Coordinator snapshot."""

    devices: tuple[TingboxDevice, ...]
    account: TingboxAccountConfig
    brightness: dict[str, int | None] = field(default_factory=dict)
    mqtt_connected: bool = False
    last_payment_amount: int | None = None
    last_payment_at: datetime | None = None
    last_cloud_update_at: datetime | None = None
    payment_sequence: int = 0


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
