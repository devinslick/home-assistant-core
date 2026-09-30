"""Config flow for the FMD integration."""

import logging
from typing import Any

from fmd_api import AuthenticationError, FmdApiException, FmdClient
from probatio import Required, Schema

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_URL
from homeassistant.core import HomeAssistant

from .const import CONF_ALLOW_INACCURATE, CONF_FMD_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = Schema(
    {
        Required(CONF_URL): str,
        Required(CONF_FMD_ID): str,
        Required(CONF_PASSWORD): str,
        Required(CONF_ALLOW_INACCURATE, default=False): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Returns the auth artifacts for password-free session resumption.
    """
    client = await FmdClient.create(
        data[CONF_URL],
        data[CONF_FMD_ID],
        data[CONF_PASSWORD],
        drop_password=True,
    )
    # Test before configure: fetch one location to validate the connection.
    await client.get_locations(1)
    artifacts = await client.export_auth_artifacts()
    await client.close()
    return artifacts


class FmdConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FMD."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                artifacts = await validate_input(self.hass, user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except FmdApiException, TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_FMD_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_FMD_ID],
                    data={
                        CONF_URL: user_input[CONF_URL],
                        CONF_FMD_ID: user_input[CONF_FMD_ID],
                        CONF_ALLOW_INACCURATE: user_input[CONF_ALLOW_INACCURATE],
                        "artifacts": artifacts,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
