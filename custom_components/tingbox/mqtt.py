"""MQTT client and payload redaction for Tingbox."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from hashlib import sha256
from typing import Any

import paho.mqtt.client as mqtt
from homeassistant.core import HomeAssistant
from homeassistant.util.ssl import client_context, client_context_no_verify

from .models import TingboxMqttConfig, TingboxPayment

_LOGGER = logging.getLogger(__name__)
_MAX_PAYLOAD_BYTES = 262_144
_MAX_DEDUPLICATION_IDS = 128


class TingboxMqttTlsError(Exception):
    """Raised when strict MQTT TLS validation fails."""


def parse_payment_payload(payload: bytes) -> TingboxPayment | None:
    """Extract only payment amount and non-sensitive routing metadata."""
    if not payload or len(payload) > _MAX_PAYLOAD_BYTES:
        return None
    try:
        decoded = json.loads(payload.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict) or "money" not in decoded:
        return None

    amount = _parse_amount(decoded.get("money"))
    if amount is None:
        return None
    broadcast_type_raw = decoded.get("broadcast_type")
    broadcast_type = (
        str(broadcast_type_raw)
        if isinstance(broadcast_type_raw, (str, int))
        else None
    )
    request_id = decoded.get("request_id")
    request_fingerprint = None
    if isinstance(request_id, (str, int)):
        request_fingerprint = sha256(str(request_id).encode()).hexdigest()
    return TingboxPayment(
        amount=amount,
        broadcast_type=broadcast_type,
        request_fingerprint=request_fingerprint,
    )


def _parse_amount(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 and value.is_integer() else None
    if not isinstance(value, str):
        return None
    if value.strip().startswith("-"):
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if not digits or len(digits) > 18:
        return None
    return int(digits)


async def async_validate_mqtt_tls(config: TingboxMqttConfig) -> None:
    """Validate the broker certificate without sending MQTT credentials."""
    context = client_context()
    writer: asyncio.StreamWriter | None = None
    try:
        async with asyncio.timeout(12):
            _, writer = await asyncio.open_connection(
                config.host,
                config.port,
                ssl=context,
                server_hostname=config.host,
            )
    except ssl.SSLCertVerificationError as error:
        raise TingboxMqttTlsError("MQTT certificate validation failed") from error
    finally:
        if writer is not None:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()


class TingboxMqttManager:
    """Maintain the Tingbox MQTT v5 subscription."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: TingboxMqttConfig,
        allow_insecure_tls: bool,
        on_connection: Callable[[bool], None],
        on_payment: Callable[[TingboxPayment], None],
    ) -> None:
        """Initialize the MQTT manager."""
        self._hass = hass
        self._config = config
        self._allow_insecure_tls = allow_insecure_tls
        self._on_connection = on_connection
        self._on_payment = on_payment
        self._client: mqtt.Client | None = None
        self._recent_request_ids: deque[str] = deque()
        self._recent_request_id_set: set[str] = set()

    @property
    def config(self) -> TingboxMqttConfig:
        """Return the active MQTT configuration."""
        return self._config

    async def async_start(self) -> None:
        """Start MQTT networking."""
        if self._client is not None:
            return
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._config.client_id,
            protocol=mqtt.MQTTv5,
        )
        client.username_pw_set(self._config.username, self._config.password)
        context = (
            client_context_no_verify()
            if self._allow_insecure_tls
            else client_context()
        )
        client.tls_set_context(context)
        client.reconnect_delay_set(min_delay=1, max_delay=300)
        client.on_connect = self._handle_connect
        client.on_disconnect = self._handle_disconnect
        client.on_message = self._handle_message
        client.on_subscribe = self._handle_subscribe
        self._client = client
        client.connect_async(
            self._config.host,
            port=self._config.port,
            keepalive=60,
            clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
        )
        client.loop_start()

    async def async_update_config(self, config: TingboxMqttConfig) -> None:
        """Restart MQTT when cloud credentials rotate."""
        if config == self._config:
            return
        await self.async_stop()
        self._config = config
        await self.async_start()

    async def async_stop(self) -> None:
        """Stop MQTT networking."""
        client = self._client
        self._client = None
        if client is None:
            return
        await self._hass.async_add_executor_job(self._stop_client, client)
        self._dispatch_connection(False)

    @staticmethod
    def _stop_client(client: mqtt.Client) -> None:
        with suppress(Exception):
            client.disconnect()
        client.loop_stop()

    def _handle_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if client is not self._client:
            return
        if bool(getattr(reason_code, "is_failure", True)):
            _LOGGER.warning("Tingbox MQTT connection was rejected")
            self._dispatch_connection(False)
            return
        result, _ = client.subscribe(self._config.topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.warning("Unable to subscribe to the Tingbox MQTT topic")
            self._dispatch_connection(False)
            return

    def _handle_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_codes: Any,
        properties: Any,
    ) -> None:
        if client is not self._client:
            return
        if any(
            bool(getattr(reason_code, "is_failure", True))
            for reason_code in reason_codes
        ):
            _LOGGER.warning("Tingbox MQTT subscription was rejected")
            self._dispatch_connection(False)
            return
        self._dispatch_connection(True)

    def _handle_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if client is not self._client:
            return
        self._dispatch_connection(False)

    def _handle_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        if client is not self._client:
            return
        if message.topic != self._config.topic:
            return
        payment = parse_payment_payload(message.payload)
        if payment is None:
            return
        if payment.request_fingerprint is not None:
            if payment.request_fingerprint in self._recent_request_id_set:
                return
            self._remember_request_id(payment.request_fingerprint)
        self._hass.loop.call_soon_threadsafe(self._on_payment, payment)

    def _remember_request_id(self, request_fingerprint: str) -> None:
        self._recent_request_ids.append(request_fingerprint)
        self._recent_request_id_set.add(request_fingerprint)
        while len(self._recent_request_ids) > _MAX_DEDUPLICATION_IDS:
            removed = self._recent_request_ids.popleft()
            self._recent_request_id_set.discard(removed)

    def _dispatch_connection(self, connected: bool) -> None:
        self._hass.loop.call_soon_threadsafe(self._on_connection, connected)
