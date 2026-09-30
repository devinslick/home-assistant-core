"""Test the FMD config entry setup/unload."""

from fmd_api import AuthenticationError, FmdApiException

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .conftest import create_mock_config_entry


async def test_setup_unload(hass: HomeAssistant, mock_client) -> None:
    """Test the config entry sets up and unloads."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert "device_tracker.fmd_mock_fmd_id" in hass.states.async_entity_ids(
        "device_tracker"
    ) or hass.states.async_all("device_tracker")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_client.close.assert_awaited()


async def test_setup_auth_failed(hass: HomeAssistant, mock_client) -> None:
    """Test setup raises ConfigEntryAuthFailed on authentication errors."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    mock_client.get_locations.side_effect = AuthenticationError
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_not_ready(hass: HomeAssistant, mock_client) -> None:
    """Test setup retries on connection errors."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    mock_client.get_locations.side_effect = FmdApiException("boom")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
