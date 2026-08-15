"""Buttons for Tingbox."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up Tingbox buttons."""
    async_add_entities([TingboxRefreshCloudButton(entry.runtime_data)])


class TingboxRefreshCloudButton(TingboxEntity, ButtonEntity):
    """Request an immediate cloud refresh."""

    _attr_translation_key = "refresh_cloud_data"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "refresh_cloud_data")

    async def async_press(self) -> None:
        """Refresh account and speaker data."""
        await self.coordinator.async_request_refresh()
