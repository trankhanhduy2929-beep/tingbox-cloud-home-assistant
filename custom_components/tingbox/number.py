"""Number controls for Tingbox."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TingboxConfigEntry
from .const import BRIGHTNESS_MAX, BRIGHTNESS_MIN
from .entity import TingboxEntity
from .models import TingboxDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TingboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tingbox number controls."""
    coordinator = entry.runtime_data
    initial_devices = [
        device for device in coordinator.data.devices if device.supports_brightness
    ]
    async_add_entities(
        TingboxBrightnessNumber(coordinator, device) for device in initial_devices
    )
    known_devices = {device.identifier for device in initial_devices}

    @callback
    def add_new_devices() -> None:
        new_devices = [
            device
            for device in coordinator.data.devices
            if device.supports_brightness and device.identifier not in known_devices
        ]
        if not new_devices:
            return
        known_devices.update(device.identifier for device in new_devices)
        async_add_entities(
            TingboxBrightnessNumber(coordinator, device) for device in new_devices
        )

    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))


class TingboxBrightnessNumber(TingboxEntity, NumberEntity):
    """Control Tingbox display brightness."""

    _attr_translation_key = "display_brightness"
    _attr_native_min_value = float(BRIGHTNESS_MIN)
    _attr_native_max_value = float(BRIGHTNESS_MAX)
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, "display_brightness", device)

    @property
    def native_value(self) -> float | None:
        """Return the one-to-seven user-facing brightness."""
        value = self.coordinator.data.brightness.get(self._device_identifier)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set display brightness."""
        await self.coordinator.async_set_brightness(
            self._device_identifier,
            int(round(value)),
        )
