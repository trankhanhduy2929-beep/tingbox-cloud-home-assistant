"""Base entities for Tingbox."""

from __future__ import annotations

from hashlib import sha256

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TingboxCoordinator
from .models import TingboxDevice


class TingboxEntity(CoordinatorEntity[TingboxCoordinator]):
    """Base Tingbox coordinator entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TingboxCoordinator,
        key: str,
        device: TingboxDevice | None = None,
    ) -> None:
        """Initialize an entity."""
        super().__init__(coordinator)
        self._device_identifier = device.identifier if device is not None else None
        if device is None:
            entry = coordinator.config_entry
            identity = entry.unique_id or entry.entry_id
            account_identifier = sha256(identity.encode()).hexdigest()[:24]
            self._attr_unique_id = f"{account_identifier}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"account_{account_identifier}")},
                name="Tingbox Cloud",
                manufacturer="NextPay",
                model="Tingbox Cloud",
            )
        else:
            self._attr_unique_id = f"{device.identifier}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.identifier)},
                name=device.display_name,
                manufacturer="NextPay",
                model=device.category,
            )

    def _device(self) -> TingboxDevice | None:
        """Return the current matching device."""
        if self._device_identifier is None or self.coordinator.data is None:
            return None
        return next(
            (
                device
                for device in self.coordinator.data.devices
                if device.identifier == self._device_identifier
            ),
            None,
        )

    @property
    def available(self) -> bool:
        """Return availability and account for removed speaker assignments."""
        return super().available and (
            self._device_identifier is None or self._device() is not None
        )
