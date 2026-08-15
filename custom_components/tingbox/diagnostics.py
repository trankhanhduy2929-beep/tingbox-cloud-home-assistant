"""Diagnostics for Tingbox with strict redaction."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TingboxConfigEntry

_TO_REDACT = {
    "password",
    "token",
    "device_token",
    "username",
    "unique_id",
    "merchant_id",
    "merchant_username",
    "mqtt",
    "userName",
    "clientId",
    "client_id",
    "topic",
    "serial",
    "serialNumber",
    "mutbId",
    "mcId",
    "qrDefault",
    "qr_type",
    "qr_id",
    "account_number",
    "account_name",
    "bank",
    "money",
    "openAIApiKey",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: TingboxConfigEntry,
) -> dict[str, Any]:
    """Return a deliberately minimal diagnostic snapshot."""
    coordinator = config_entry.runtime_data
    data = coordinator.data
    return async_redact_data(
        {
            "config_entry": dict(config_entry.as_dict()),
            "integration": {
                "device_count": len(data.devices),
                "mqtt_connected": data.mqtt_connected,
                "has_total_amount": data.account.total_amount is not None,
                "has_transaction_count": data.account.transaction_count is not None,
                "has_qr_default_state": (
                    data.account.qr_default_configured is not None
                ),
                "phone_announcements": data.account.phone_announcements,
                "has_last_payment": data.last_payment_amount is not None,
                "last_cloud_update_at": (
                    data.last_cloud_update_at.isoformat()
                    if data.last_cloud_update_at is not None
                    else None
                ),
                "payment_sequence": data.payment_sequence,
                "devices": [
                    {
                        "identifier": device.identifier,
                        "category": device.category,
                        "status_code": device.status_code,
                        "supports_brightness": device.supports_brightness,
                        "has_channel_description": (
                            device.channel_description is not None
                        ),
                        "has_brightness": (
                            data.brightness.get(device.identifier) is not None
                        ),
                    }
                    for device in data.devices
                ],
            },
        },
        _TO_REDACT,
    )
