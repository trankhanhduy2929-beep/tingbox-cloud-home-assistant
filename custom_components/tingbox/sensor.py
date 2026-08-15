"""Sensors for Tingbox."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up Tingbox sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        TingboxTotalAmountSensor(coordinator),
        TingboxTransactionCountSensor(coordinator),
        TingboxCurrentModeSensor(coordinator),
        TingboxLastPaymentAmountSensor(coordinator),
        TingboxLastPaymentTimeSensor(coordinator),
        TingboxDeviceCountSensor(coordinator),
        TingboxBrightnessDeviceCountSensor(coordinator),
        TingboxLastCloudUpdateSensor(coordinator),
    ]
    for device in coordinator.data.devices:
        entities.extend(
            (
                TingboxDeviceStatusSensor(coordinator, device),
                TingboxDeviceStatusTextSensor(coordinator, device),
                TingboxDeviceCategorySensor(coordinator, device),
                TingboxDeviceChannelSensor(coordinator, device),
            )
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
        entities: list[SensorEntity] = []
        for device in new_devices:
            entities.extend(
                (
                    TingboxDeviceStatusSensor(coordinator, device),
                    TingboxDeviceStatusTextSensor(coordinator, device),
                    TingboxDeviceCategorySensor(coordinator, device),
                    TingboxDeviceChannelSensor(coordinator, device),
                )
            )
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))


class TingboxTotalAmountSensor(TingboxEntity, SensorEntity):
    """Total amount reported by the Tingbox account configuration."""

    _attr_translation_key = "total_amount"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "VND"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "total_amount")

    @property
    def native_value(self) -> int | None:
        """Return the total amount."""
        return self.coordinator.data.account.total_amount


class TingboxTransactionCountSensor(TingboxEntity, SensorEntity):
    """Transaction count reported by Tingbox."""

    _attr_translation_key = "transaction_count"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "transaction_count")

    @property
    def native_value(self) -> int | None:
        """Return the transaction count."""
        return self.coordinator.data.account.transaction_count


class TingboxCurrentModeSensor(TingboxEntity, SensorEntity):
    """Current server-side Tingbox mode."""

    _attr_translation_key = "current_mode"

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "current_mode")

    @property
    def native_value(self) -> str | None:
        """Return the current mode."""
        return self.coordinator.data.account.current_mode


class TingboxLastPaymentAmountSensor(TingboxEntity, SensorEntity):
    """Last payment amount received over MQTT."""

    _attr_translation_key = "last_payment_amount"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "VND"

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "last_payment_amount")

    @property
    def native_value(self) -> int | None:
        """Return the last payment amount."""
        return self.coordinator.data.last_payment_amount


class TingboxLastPaymentTimeSensor(TingboxEntity, SensorEntity):
    """Timestamp of the last payment event."""

    _attr_translation_key = "last_payment_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "last_payment_time")

    @property
    def native_value(self) -> datetime | None:
        """Return the last payment timestamp."""
        return self.coordinator.data.last_payment_at


class TingboxDeviceCountSensor(TingboxEntity, SensorEntity):
    """Count assigned Tingbox speakers."""

    _attr_translation_key = "device_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_count")

    @property
    def native_value(self) -> int:
        """Return the assigned speaker count."""
        return len(self.coordinator.data.devices)


class TingboxBrightnessDeviceCountSensor(TingboxEntity, SensorEntity):
    """Count speakers that advertise display brightness support."""

    _attr_translation_key = "brightness_device_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "brightness_device_count")

    @property
    def native_value(self) -> int:
        """Return the brightness-capable speaker count."""
        return sum(
            device.supports_brightness for device in self.coordinator.data.devices
        )


class TingboxLastCloudUpdateSensor(TingboxEntity, SensorEntity):
    """Timestamp of the last successful REST refresh."""

    _attr_translation_key = "last_cloud_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "last_cloud_update")

    @property
    def native_value(self) -> datetime | None:
        """Return the last successful refresh timestamp."""
        return self.coordinator.data.last_cloud_update_at


class TingboxDeviceStatusSensor(TingboxEntity, SensorEntity):
    """Assigned device status."""

    _attr_translation_key = "device_status"

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_status", device)

    @property
    def native_value(self) -> str | None:
        """Return the device status code."""
        device = self._device()
        return device.status_code if device is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return safe status attributes."""
        device = self._device()
        if device is None:
            return None
        return {
            "status_text": device.status,
            "category": device.category,
            "supports_brightness": device.supports_brightness,
            "channel_description": device.channel_description,
        }


class TingboxDeviceStatusTextSensor(TingboxEntity, SensorEntity):
    """Human-readable assigned device status."""

    _attr_translation_key = "device_status_text"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_status_text", device)

    @property
    def native_value(self) -> str | None:
        """Return the human-readable status."""
        device = self._device()
        return device.status if device is not None else None


class TingboxDeviceCategorySensor(TingboxEntity, SensorEntity):
    """Device category reported by Tingbox."""

    _attr_translation_key = "device_category"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_category", device)

    @property
    def native_value(self) -> str | None:
        """Return the device category."""
        device = self._device()
        return device.category if device is not None else None


class TingboxDeviceChannelSensor(TingboxEntity, SensorEntity):
    """Device channel description reported by Tingbox."""

    _attr_translation_key = "device_channel"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device: TingboxDevice) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_channel", device)

    @property
    def native_value(self) -> str | None:
        """Return the channel description."""
        device = self._device()
        return device.channel_description if device is not None else None
