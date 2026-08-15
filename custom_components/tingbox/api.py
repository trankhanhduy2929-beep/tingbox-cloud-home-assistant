"""Cloud API client for Tingbox."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .const import (
    APP_CORE_BASE_URL,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    MCMN_BASE_URL,
)
from .models import (
    JsonValue,
    TingboxAccountConfig,
    TingboxDevice,
    TingboxMqttConfig,
    TingboxSession,
)

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT = ClientTimeout(total=25)


class TingboxError(Exception):
    """Base Tingbox error."""


class TingboxConnectionError(TingboxError):
    """Raised when the cloud cannot be reached."""


class TingboxAuthenticationError(TingboxError):
    """Raised when credentials are rejected."""


class TingboxResponseError(TingboxError):
    """Raised when the cloud returns an invalid response."""


def _parse_optional_integer(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        if value.strip().startswith("-"):
            return None
        digits = re.sub(r"[^0-9]", "", value)
        if digits and len(digits) <= 18:
            return int(digits)
    return None


def _parse_optional_boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no"}:
            return False
    return None


def _parse_configured_state(value: Any) -> bool:
    """Reduce a potentially sensitive cloud value to a configured flag."""
    parsed = _parse_optional_boolean(value)
    return bool(value) if parsed is None else parsed


def _find_key(value: Any, target: str) -> Any:
    if isinstance(value, Mapping):
        if target in value:
            return value[target]
        for nested in value.values():
            found = _find_key(nested, target)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_key(nested, target)
            if found is not None:
                return found
    return None


def _find_first_key(value: Any, targets: tuple[str, ...]) -> Any:
    for target in targets:
        found = _find_key(value, target)
        if found is not None:
            return found
    return None


class TingboxApi:
    """Minimal Tingbox REST client."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        device_token: str,
    ) -> None:
        """Initialize the API client."""
        self._http = session
        self._username = username
        self._password = password
        self._device_token = device_token
        self._session: TingboxSession | None = None

    @property
    def authenticated_session(self) -> TingboxSession | None:
        """Return the current authenticated session."""
        return self._session

    async def async_login(self) -> TingboxSession:
        """Authenticate and retain only fields required by the integration."""
        response = await self._async_post(
            APP_CORE_BASE_URL,
            "api/auth/login",
            {
                "value": self._username,
                "password": self._password,
                "deviceToken": self._device_token,
                "os": "ANDROID",
            },
            authenticated=False,
        )
        if response.get("success") is not True:
            raise TingboxAuthenticationError("Tingbox rejected the credentials")

        data = response.get("data")
        if not isinstance(data, Mapping):
            raise TingboxResponseError("Login response has no data object")
        merchant = data.get("merchantInfo")
        if not isinstance(merchant, Mapping):
            raise TingboxResponseError("Login response has no merchant information")

        token = data.get("token")
        merchant_id = merchant.get("merchantId")
        merchant_username = merchant.get("username")
        if not isinstance(token, str) or not token:
            raise TingboxResponseError("Login response has no token")
        if not isinstance(merchant_id, (str, int)) or isinstance(merchant_id, bool):
            raise TingboxResponseError("Login response has no merchant identifier")
        if not isinstance(merchant_username, str) or not merchant_username:
            raise TingboxResponseError("Login response has no merchant username")

        user_id_raw = data.get("userId")
        user_id = str(user_id_raw) if isinstance(user_id_raw, (str, int)) else ""
        self._session = TingboxSession(
            token=token,
            merchant_id=merchant_id,
            merchant_username=merchant_username,
            user_id=user_id,
        )
        return self._session

    async def async_get_devices(self) -> tuple[TingboxDevice, ...]:
        """Return assigned speakers."""
        response = await self._async_post_authenticated(
            APP_CORE_BASE_URL,
            "api/transfer-device/list-device",
            {},
        )
        data = response.get("data")
        assigned = data.get("assignedDevices") if isinstance(data, Mapping) else None
        if assigned is None:
            return ()
        if not isinstance(assigned, list):
            raise TingboxResponseError("Device list is not an array")

        devices: list[TingboxDevice] = []
        for raw_device in assigned:
            if not isinstance(raw_device, Mapping):
                continue
            mutb_id = raw_device.get("mutbId")
            serial = raw_device.get("serial")
            category = raw_device.get("category")
            if not all(
                isinstance(value, str) and value
                for value in (mutb_id, serial, category)
            ):
                continue
            status = raw_device.get("status")
            status_code = raw_device.get("statusCode")
            channel_description = raw_device.get("channelDescription")
            devices.append(
                TingboxDevice(
                    mutb_id=mutb_id,
                    serial=serial,
                    category=category,
                    status=status if isinstance(status, str) else None,
                    status_code=status_code if isinstance(status_code, str) else None,
                    supports_brightness=raw_device.get("isBrightness") is True,
                    channel_description=(
                        channel_description
                        if isinstance(channel_description, str)
                        and channel_description.strip()
                        else None
                    ),
                )
            )
        return tuple(devices)

    async def async_get_account_config(self) -> TingboxAccountConfig:
        """Fetch MQTT credentials and safe aggregate account state."""
        session = await self.async_ensure_login()
        response = await self._async_post_authenticated(
            APP_CORE_BASE_URL,
            "Mpos360GetCauHinhByMerchant",
            {
                "merchantId": session.merchant_id,
                "username": session.merchant_username,
                "os": "ANDROID",
                "deviceToken": self._device_token,
                "versionChange": "2",
            },
        )
        data = response.get("data")
        tingbox = data.get("tingbox") if isinstance(data, Mapping) else None
        tingting = tingbox.get("tingting") if isinstance(tingbox, Mapping) else None
        if not isinstance(tingting, Mapping):
            raise TingboxResponseError("Account response has no Tingbox configuration")
        mqtt_auth = tingting.get("mqAuthen")
        if not isinstance(mqtt_auth, Mapping):
            raise TingboxResponseError("Account response has no MQTT authentication")

        broker = mqtt_auth.get("mqtt")
        mqtt_username = mqtt_auth.get("userName")
        mqtt_password = mqtt_auth.get("password")
        client_id = tingting.get("clientId")
        topic = tingting.get("topic")
        required_strings = (broker, mqtt_username, mqtt_password, client_id, topic)
        if not all(isinstance(value, str) and value for value in required_strings):
            raise TingboxResponseError("Account response has incomplete MQTT data")
        if "+" in topic or "#" in topic:
            raise TingboxResponseError("MQTT topic must not contain wildcards")

        parsed = urlparse(broker if "://" in broker else f"mqtts://{broker}")
        if not parsed.hostname:
            raise TingboxResponseError("MQTT broker address is invalid")

        current_mode = (
            tingbox.get("currentMode") if isinstance(tingbox, Mapping) else None
        )
        qr_default_configured = None
        if isinstance(tingbox, Mapping) and "qrDefault" in tingbox:
            qr_default_configured = _parse_configured_state(
                tingbox.get("qrDefault")
            )
        return TingboxAccountConfig(
            mqtt=TingboxMqttConfig(
                host=parsed.hostname,
                port=parsed.port or 8883,
                username=mqtt_username,
                password=mqtt_password,
                client_id=client_id,
                topic=topic,
            ),
            total_amount=_parse_optional_integer(tingting.get("totalAmountCurrent")),
            transaction_count=_parse_optional_integer(tingting.get("transactionCount")),
            current_mode=current_mode if isinstance(current_mode, str) else None,
            qr_default_configured=qr_default_configured,
        )

    async def async_get_phone_announcements(self) -> bool | None:
        """Read whether the mobile app transaction sound is enabled."""
        response = await self._async_post_authenticated(
            APP_CORE_BASE_URL,
            "Mpos360DeviceGetTypeReceiverTingTing",
            {},
        )
        raw_value = _find_first_key(
            response,
            ("type_receiver_tingting", "typeReceiverTingTing"),
        )
        return _parse_optional_boolean(raw_value)

    async def async_set_phone_announcements(self, enabled: bool) -> bool:
        """Enable or disable mobile app transaction announcements."""
        response = await self._async_post_authenticated(
            APP_CORE_BASE_URL,
            "Mpos360DeviceUpdateTypeReceiverTingTing",
            {"type_receiver_tingting": enabled},
        )
        raw_value = _find_first_key(
            response,
            ("type_receiver_tingting", "typeReceiverTingTing"),
        )
        confirmed = _parse_optional_boolean(raw_value)
        return enabled if confirmed is None else confirmed

    async def async_get_brightness(
        self,
        device: TingboxDevice,
        mqtt_config: TingboxMqttConfig,
    ) -> int | None:
        """Read display brightness when the cloud returns device configuration."""
        response = await self._async_post_authenticated(
            MCMN_BASE_URL,
            "api/mc-device/get-info-config",
            {"mcId": device.mutb_id, "clientId": mqtt_config.client_id},
        )
        raw_level = _parse_optional_integer(_find_key(response, "brightLevel"))
        if raw_level is None or not 0 <= raw_level <= 6:
            return None
        return BRIGHTNESS_MAX - raw_level

    async def async_set_brightness(
        self,
        device: TingboxDevice,
        mqtt_config: TingboxMqttConfig,
        level: int,
    ) -> None:
        """Set the user-facing brightness level from one to seven."""
        if not BRIGHTNESS_MIN <= level <= BRIGHTNESS_MAX:
            raise ValueError("Brightness must be between 1 and 7")
        raw_level = BRIGHTNESS_MAX - level
        response = await self._async_post_authenticated(
            MCMN_BASE_URL,
            "api/mc-device/publish-message-config",
            {
                "mcId": device.mutb_id,
                "clientId": mqtt_config.client_id,
                "backlight_level": raw_level,
            },
        )
        if response.get("success") is not True:
            raise TingboxResponseError("Brightness command was not acknowledged")

    async def async_ensure_login(self) -> TingboxSession:
        """Return the current session or authenticate first."""
        if self._session is None:
            return await self.async_login()
        return self._session

    async def _async_post_authenticated(
        self,
        base_url: str,
        endpoint: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        await self.async_ensure_login()
        try:
            return await self._async_post(
                base_url,
                endpoint,
                body,
                authenticated=True,
            )
        except TingboxAuthenticationError:
            self._session = None
            await self.async_login()
            return await self._async_post(
                base_url,
                endpoint,
                body,
                authenticated=True,
            )

    async def _async_post(
        self,
        base_url: str,
        endpoint: str,
        body: dict[str, Any],
        *,
        authenticated: bool,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "HomeAssistant-Tingbox/0.2.0",
        }
        if authenticated:
            session = self._session
            if session is None:
                raise TingboxAuthenticationError("Missing authenticated session")
            headers["Authorization"] = session.token

        try:
            async with self._http.post(
                base_url + endpoint,
                json=body,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            ) as response:
                return await self._async_decode_response(response, authenticated)
        except (ClientError, TimeoutError) as error:
            raise TingboxConnectionError("Unable to reach Tingbox cloud") from error

    async def _async_decode_response(
        self,
        response: ClientResponse,
        authenticated: bool,
    ) -> dict[str, Any]:
        if response.status in (401, 403):
            raise TingboxAuthenticationError("Tingbox authorization expired")
        try:
            decoded: JsonValue = await response.json(content_type=None)
        except (ValueError, UnicodeDecodeError) as error:
            raise TingboxResponseError("Tingbox returned non-JSON data") from error
        if not isinstance(decoded, dict):
            raise TingboxResponseError("Tingbox returned an invalid JSON object")
        result_code = decoded.get("result_code", decoded.get("code"))
        if authenticated and result_code in (401, 403):
            raise TingboxAuthenticationError("Tingbox authorization expired")
        if response.status >= 400:
            _LOGGER.debug("Tingbox request failed with HTTP status %s", response.status)
            raise TingboxResponseError(f"Tingbox returned HTTP {response.status}")
        if authenticated and decoded.get("success") is False:
            raise TingboxResponseError("Tingbox rejected the request")
        return decoded
