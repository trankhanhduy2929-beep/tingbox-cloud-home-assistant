"""Data coordinator for Tingbox."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TingboxApi,
    TingboxAuthenticationError,
    TingboxConnectionError,
    TingboxResponseError,
)
from .const import DOMAIN, EVENT_PAYMENT
from .models import TingboxPayment, TingboxSnapshot
from .mqtt import TingboxMqttManager

_LOGGER = logging.getLogger(__name__)


class TingboxCoordinator(DataUpdateCoordinator[TingboxSnapshot]):
    """Coordinate REST polling and MQTT push updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TingboxApi,
        update_interval: timedelta,
        allow_insecure_mqtt: bool,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=False,
        )
        self.api = api
        self._allow_insecure_mqtt = allow_insecure_mqtt
        self._mqtt: TingboxMqttManager | None = None

    async def async_start(self) -> None:
        """Start the MQTT subscription after the first REST refresh."""
        if self.data is None:
            return
        self._mqtt = TingboxMqttManager(
            self.hass,
            self.data.account.mqtt,
            self._allow_insecure_mqtt,
            self._handle_mqtt_connection,
            self._handle_payment,
        )
        await self._mqtt.async_start()

    async def async_shutdown(self) -> None:
        """Stop runtime resources."""
        if self._mqtt is not None:
            await self._mqtt.async_stop()
            self._mqtt = None

    async def async_set_brightness(self, device_id: str, level: int) -> None:
        """Set brightness and optimistically update state after acknowledgement."""
        if self.data is None:
            raise UpdateFailed("Tingbox data is unavailable")
        device = next(
            (item for item in self.data.devices if item.identifier == device_id),
            None,
        )
        if device is None:
            raise UpdateFailed("Tingbox device is no longer assigned")
        try:
            await self.api.async_set_brightness(device, self.data.account.mqtt, level)
        except TingboxAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                "Tingbox credentials are no longer valid"
            ) from error
        except (TingboxConnectionError, TingboxResponseError) as error:
            raise UpdateFailed("Unable to set Tingbox brightness") from error
        brightness = dict(self.data.brightness)
        brightness[device.identifier] = level
        self.async_set_updated_data(replace(self.data, brightness=brightness))

    async def async_set_phone_announcements(self, enabled: bool) -> None:
        """Set mobile app transaction announcements."""
        if self.data is None:
            raise UpdateFailed("Tingbox data is unavailable")
        try:
            confirmed = await self.api.async_set_phone_announcements(enabled)
        except TingboxAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                "Tingbox credentials are no longer valid"
            ) from error
        except (TingboxConnectionError, TingboxResponseError) as error:
            raise UpdateFailed(
                "Unable to update Tingbox phone announcements"
            ) from error
        account = replace(self.data.account, phone_announcements=confirmed)
        self.async_set_updated_data(replace(self.data, account=account))

    async def _async_update_data(self) -> TingboxSnapshot:
        try:
            await self.api.async_ensure_login()
            devices = await self.api.async_get_devices()
            account = await self.api.async_get_account_config()
            old_phone_announcements = (
                self.data.account.phone_announcements if self.data is not None else None
            )
            try:
                phone_announcements = await self.api.async_get_phone_announcements()
            except TingboxAuthenticationError:
                raise
            except (TingboxConnectionError, TingboxResponseError):
                _LOGGER.debug("Unable to refresh Tingbox phone announcements")
                phone_announcements = old_phone_announcements
            if phone_announcements is None:
                phone_announcements = old_phone_announcements
            account = replace(
                account,
                phone_announcements=phone_announcements,
            )
            brightness: dict[str, int | None] = {}
            old_brightness = self.data.brightness if self.data is not None else {}
            for device in devices:
                if not device.supports_brightness:
                    continue
                try:
                    level = await self.api.async_get_brightness(device, account.mqtt)
                except TingboxAuthenticationError:
                    raise
                except (TingboxConnectionError, TingboxResponseError):
                    _LOGGER.debug(
                        "Unable to refresh brightness for Tingbox device %s",
                        device.identifier,
                    )
                    level = None
                brightness[device.identifier] = level
                if level is None:
                    brightness[device.identifier] = old_brightness.get(
                        device.identifier
                    )
        except TingboxAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                "Tingbox credentials are no longer valid"
            ) from error
        except (TingboxConnectionError, TingboxResponseError) as error:
            raise UpdateFailed("Unable to update Tingbox cloud data") from error

        if self._mqtt is not None:
            await self._mqtt.async_update_config(account.mqtt)
        previous = self.data
        return TingboxSnapshot(
            devices=devices,
            account=account,
            brightness=brightness,
            mqtt_connected=previous.mqtt_connected if previous is not None else False,
            last_payment_amount=(
                previous.last_payment_amount if previous is not None else None
            ),
            last_payment_at=previous.last_payment_at if previous is not None else None,
            last_cloud_update_at=datetime.now(UTC),
            payment_sequence=previous.payment_sequence if previous is not None else 0,
        )

    @callback
    def _handle_mqtt_connection(self, connected: bool) -> None:
        if self.data is None or self.data.mqtt_connected == connected:
            return
        self.async_set_updated_data(replace(self.data, mqtt_connected=connected))

    @callback
    def _handle_payment(self, payment: TingboxPayment) -> None:
        if self.data is None:
            return
        timestamp = datetime.now(UTC)
        self.async_set_updated_data(
            replace(
                self.data,
                last_payment_amount=payment.amount,
                last_payment_at=timestamp,
                payment_sequence=self.data.payment_sequence + 1,
            )
        )
        self.hass.bus.async_fire(
            EVENT_PAYMENT,
            {"amount": payment.amount, "currency": "VND"},
        )
