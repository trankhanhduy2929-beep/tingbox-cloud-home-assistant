"""Switches for Tingbox."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TingboxConfigEntry
from .entity import TingboxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TingboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tingbox switches."""
    async_add_entities([TingboxPhoneAnnouncementsSwitch(entry.runtime_data)])


class TingboxPhoneAnnouncementsSwitch(TingboxEntity, SwitchEntity):
    """Control transaction announcements in the Tingbox mobile app."""

    _attr_translation_key = "phone_announcements"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "phone_announcements")

    @property
    def available(self) -> bool:
        """Return whether the cloud exposed this setting."""
        return (
            super().available
            and self.coordinator.data.account.phone_announcements is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether phone transaction announcements are enabled."""
        return self.coordinator.data.account.phone_announcements

    async def async_turn_on(self, **kwargs) -> None:
        """Enable transaction announcements."""
        await self.coordinator.async_set_phone_announcements(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable transaction announcements."""
        await self.coordinator.async_set_phone_announcements(False)
