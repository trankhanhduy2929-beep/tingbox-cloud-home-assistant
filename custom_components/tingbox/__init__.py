"""Tingbox integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TingboxApi
from .const import (
    CONF_ALLOW_INSECURE_MQTT,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)
from .coordinator import TingboxCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
]

TingboxConfigEntry = ConfigEntry[TingboxCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TingboxConfigEntry) -> bool:
    """Set up Tingbox from a config entry."""
    scan_interval_minutes = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
        )
    )
    scan_interval_minutes = max(
        MIN_SCAN_INTERVAL_MINUTES,
        min(MAX_SCAN_INTERVAL_MINUTES, scan_interval_minutes),
    )
    allow_insecure_mqtt = bool(
        entry.options.get(
            CONF_ALLOW_INSECURE_MQTT,
            entry.data.get(CONF_ALLOW_INSECURE_MQTT, False),
        )
    )
    api = TingboxApi(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_DEVICE_ID],
    )
    coordinator = TingboxCoordinator(
        hass,
        entry,
        api,
        timedelta(minutes=scan_interval_minutes),
        allow_insecure_mqtt,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TingboxConfigEntry) -> bool:
    """Unload a Tingbox config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant,
    entry: TingboxConfigEntry,
) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
