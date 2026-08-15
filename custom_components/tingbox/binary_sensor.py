"""Binary sensors for Tingbox."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TingboxConfigEntry
from .entity import TingboxEntity
from .models import TingboxDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TingboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tingbox binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        TingboxMqttConnectionSensor(coordinator),
        TingboxQrDefaultConfiguredSensor(coordinator),
    ]
    entities.extend(
        TingboxBrightnessCapabilitySensor(coordinator, device)
        for device in coordinator.data.devices
    )
    async_add_entities(entities)
    known_devices = {device.identifier for device in coordinator.data.devices}

    @callback
    def add_new_devices() -> None:
        new_devices = [
            device
            for device in coordinator.data.devices
            if device.identifier not in known_devices
        ]
        if not new_devices:
            return
        known_devices.update(device.identifier for device in new_devices)
        async_add_entities(
            TingboxBrightnessCapabilitySensor(coordinator, device)
            for device in new_devices
        )

    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))


class TingboxMqttConnectionSensor(TingboxEntity, BinarySensorEntity):
    """Report the integration's MQTT cloud connection."""

    _attr_translation_key = "mqtt_connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "mqtt_connection")

    @property
    def is_on(self) -> bool:
        """Return whether MQTT is connected."""
        return bool(self.coordinator.data and self.coordinator.data.mqtt_connected)


class TingboxQrDefaultConfiguredSensor(TingboxEntity, BinarySensorEntity):
    """Report whether the account has a default QR configuration."""

    _attr_translation_key = "qr_default_configured"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "qr_default_configured")

    @property
    def available(self) -> bool:
        """Return whether the cloud exposed QR configuration state."""
        return (
            super().available
            and self.coordinator.data.account.qr_default_configured is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether a default QR is configured."""
        return self.coordinator.data.account.qr_default_configured


class TingboxBrightnessCapabilitySensor(TingboxEntity, BinarySensorEntity):
    """Report whether a speaker advertises brightness support."""

    _attr_translation_key = "brightness_capability"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "brightness_capability", device)

    @property
    def is_on(self) -> bool:
        """Return whether the device supports brightness."""
        device = self._device()
        return bool(device and device.supports_brightness)
