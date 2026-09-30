"""The FMD integration."""

from collections.abc import Mapping

from fmd_api import AuthenticationError, FmdApiException, FmdClient

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_FMD_ID
from .coordinator import FmdConfigEntry, FmdCoordinator

_PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def _async_create_client(hass: HomeAssistant, data: Mapping) -> FmdClient:
    """Create an authenticated FMD client.

    Stores auth artifacts (not the password) in the config entry so the
    session can be resumed without keeping the raw password on disk.
    """
    if (artifacts := data.get("artifacts")) is not None:
        try:
            return await FmdClient.from_auth_artifacts(artifacts)
        except Exception as err:
            raise ConfigEntryNotReady(f"Could not resume FMD session: {err}") from err
    return await FmdClient.create(
        data["url"],
        data[CONF_FMD_ID],
        data["password"],
        drop_password=True,
    )


async def async_setup_entry(hass: HomeAssistant, entry: FmdConfigEntry) -> bool:
    """Set up FMD from a config entry."""
    client = await _async_create_client(hass, entry.data)

    # Validate the connection with a real request before storing the client.
    try:
        await client.get_locations(1)
    except AuthenticationError as err:
        await client.close()
        raise ConfigEntryAuthFailed(
            translation_domain="fmd", translation_key="invalid_auth"
        ) from err
    except FmdApiException as err:
        await client.close()
        raise ConfigEntryNotReady(
            f"Error communicating with the FMD server: {err}"
        ) from err

    # Persist password-free auth artifacts so subsequent startups do not
    # need the raw password.
    if "artifacts" not in entry.data:
        try:
            artifacts = await client.export_auth_artifacts()
        except FmdApiException:
            pass
        else:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "artifacts": artifacts}
            )

    entry.runtime_data = coordinator = FmdCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FmdConfigEntry) -> bool:
    """Unload a config entry."""
    if await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        await entry.runtime_data.client.close()
        return True
    return False
