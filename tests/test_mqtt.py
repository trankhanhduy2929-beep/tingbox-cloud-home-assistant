"""MQTT lifecycle tests."""

from __future__ import annotations

import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as mqtt

from custom_components.tingbox.models import TingboxMqttConfig
from custom_components.tingbox.mqtt import (
    TingboxMqttManager,
    async_validate_mqtt_tls,
)


def _mqtt_config() -> TingboxMqttConfig:
    credential = "-".join(("fixture", "value"))
    return TingboxMqttConfig(
        host="mqtt.example.invalid",
        port=8883,
        username="test-user",
        password=credential,
        client_id="test-client",
        topic="test/private/topic",
    )


class TingboxMqttTests(unittest.IsolatedAsyncioTestCase):
    """Verify MQTT setup does not perform blocking SSL initialization."""

    async def test_tls_validation_uses_home_assistant_context(self) -> None:
        context = MagicMock(spec=ssl.SSLContext)
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        with (
            patch(
                "custom_components.tingbox.mqtt.client_context",
                return_value=context,
            ) as context_factory,
            patch(
                "custom_components.tingbox.mqtt.asyncio.open_connection",
                new=AsyncMock(return_value=(MagicMock(), writer)),
            ) as open_connection,
            patch(
                "custom_components.tingbox.mqtt.ssl.create_default_context",
                side_effect=AssertionError("blocking SSL context creation"),
            ),
        ):
            await async_validate_mqtt_tls(_mqtt_config())

        context_factory.assert_called_once_with()
        open_connection.assert_awaited_once_with(
            "mqtt.example.invalid",
            8883,
            ssl=context,
            server_hostname="mqtt.example.invalid",
        )
        writer.close.assert_called_once_with()
        writer.wait_closed.assert_awaited_once_with()

    async def test_mqtt_start_uses_cached_strict_context(self) -> None:
        await self._assert_start_uses_expected_context(insecure=False)

    async def test_mqtt_start_uses_cached_insecure_context(self) -> None:
        await self._assert_start_uses_expected_context(insecure=True)

    async def _assert_start_uses_expected_context(self, *, insecure: bool) -> None:
        strict_context = MagicMock(spec=ssl.SSLContext)
        insecure_context = MagicMock(spec=ssl.SSLContext)
        client = MagicMock()
        hass = SimpleNamespace()
        manager = TingboxMqttManager(
            hass,
            _mqtt_config(),
            insecure,
            MagicMock(),
            MagicMock(),
        )

        with (
            patch(
                "custom_components.tingbox.mqtt.client_context",
                return_value=strict_context,
            ) as strict_factory,
            patch(
                "custom_components.tingbox.mqtt.client_context_no_verify",
                return_value=insecure_context,
            ) as insecure_factory,
            patch(
                "custom_components.tingbox.mqtt.ssl.create_default_context",
                side_effect=AssertionError("blocking SSL context creation"),
            ),
            patch(
                "custom_components.tingbox.mqtt.mqtt.Client",
                return_value=client,
            ),
        ):
            await manager.async_start()

        expected_context = insecure_context if insecure else strict_context
        client.tls_set_context.assert_called_once_with(expected_context)
        client.connect_async.assert_called_once_with(
            "mqtt.example.invalid",
            port=8883,
            keepalive=60,
            clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
        )
        client.loop_start.assert_called_once_with()
        if insecure:
            insecure_factory.assert_called_once_with()
            strict_factory.assert_not_called()
        else:
            strict_factory.assert_called_once_with()
            insecure_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
