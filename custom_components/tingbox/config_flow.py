"""Config flow for Tingbox."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    TingboxApi,
    TingboxAuthenticationError,
    TingboxConnectionError,
    TingboxResponseError,
)
from .const import (
    CONF_ALLOW_INSECURE_MQTT,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)
from .models import TingboxAccountConfig, TingboxSession
from .mqtt import TingboxMqttTlsError, async_validate_mqtt_tls

_LOGGER = logging.getLogger(__name__)


class TingboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Tingbox configuration."""

    VERSION = 1

    _pending_data: dict[str, Any] | None = None
    _pending_title = "Tingbox"
    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial credentials form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            device_token = uuid4().hex
            try:
                session, account = await self._async_validate(
                    username,
                    password,
                    device_token,
                )
            except TingboxAuthenticationError:
                errors["base"] = "invalid_auth"
            except TingboxConnectionError:
                errors["base"] = "cannot_connect"
            except TingboxResponseError:
                errors["base"] = "invalid_response"
            except (OSError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(str(session.merchant_id))
                self._abort_if_unique_id_configured()
                data = {
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_DEVICE_ID: device_token,
                    CONF_ALLOW_INSECURE_MQTT: False,
                }
                try:
                    await async_validate_mqtt_tls(account.mqtt)
                except TingboxMqttTlsError:
                    self._pending_data = data
                    return await self.async_step_mqtt_tls()
                except (OSError, TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title="Tingbox", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_mqtt_tls(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Request explicit consent for the legacy broker certificate."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_ALLOW_INSECURE_MQTT):
                errors["base"] = "mqtt_tls_required"
            elif self._pending_data is not None:
                data = dict(self._pending_data)
                data[CONF_ALLOW_INSECURE_MQTT] = True
                self._pending_data = None
                return self.async_create_entry(title=self._pending_title, data=data)

        return self.async_show_form(
            step_id="mqtt_tls",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ALLOW_INSECURE_MQTT, default=False
                    ): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Start reauthentication for an existing entry."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the reauthentication form."""
        errors: dict[str, str] = {}
        if user_input is not None and self._reauth_entry is not None:
            entry = self._reauth_entry
            username = entry.data[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            device_token = entry.data[CONF_DEVICE_ID]
            try:
                session, _ = await self._async_validate(
                    username,
                    password,
                    device_token,
                )
            except TingboxAuthenticationError:
                errors["base"] = "invalid_auth"
            except (TingboxConnectionError, OSError, TimeoutError):
                errors["base"] = "cannot_connect"
            except TingboxResponseError:
                errors["base"] = "invalid_response"
            else:
                if str(session.merchant_id) != str(entry.unique_id):
                    errors["base"] = "invalid_auth"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_PASSWORD: password},
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    async def _async_validate(
        self,
        username: str,
        password: str,
        device_token: str,
    ) -> tuple[TingboxSession, TingboxAccountConfig]:
        session = async_get_clientsession(self.hass)
        api = TingboxApi(session, username, password, device_token)
        authenticated = await api.async_login()
        await api.async_get_devices()
        account = await api.async_get_account_config()
        return authenticated, account

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Return the options flow."""
        return TingboxOptionsFlow()


class TingboxOptionsFlow(OptionsFlowWithReload):
    """Handle Tingbox options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage MQTT TLS and polling options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ALLOW_INSECURE_MQTT,
                    default=self.config_entry.options.get(
                        CONF_ALLOW_INSECURE_MQTT,
                        self.config_entry.data.get(CONF_ALLOW_INSECURE_MQTT, False),
                    ),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self.config_entry.data.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL_MINUTES,
                        ),
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_SCAN_INTERVAL_MINUTES,
                        max=MAX_SCAN_INTERVAL_MINUTES,
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
