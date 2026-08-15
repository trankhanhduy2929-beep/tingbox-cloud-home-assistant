"""Event entities for Tingbox."""

from __future__ import annotations

from typing import override

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TingboxConfigEntry
from .entity import TingboxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TingboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tingbox payment event."""
    async_add_entities([TingboxPaymentEvent(entry.runtime_data)])


class TingboxPaymentEvent(TingboxEntity, EventEntity):
    """Emit a redacted payment event."""

    _attr_translation_key = "payment_received"
    _attr_event_types = ["payment"]

    def __init__(self, coordinator) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, "payment_received")
        self._last_sequence = coordinator.data.payment_sequence

    @override
    @callback
    def _handle_coordinator_update(self) -> None:
        """Trigger only when a new redacted payment arrives."""
        data = self.coordinator.data
        if data.payment_sequence > self._last_sequence:
            self._last_sequence = data.payment_sequence
            self._trigger_event(
                "payment",
                {
                    "amount": data.last_payment_amount,
                    "currency": "VND",
                    "received_at": (
                        data.last_payment_at.isoformat()
                        if data.last_payment_at is not None
                        else None
                    ),
                },
            )
        super()._handle_coordinator_update()

