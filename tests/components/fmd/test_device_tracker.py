"""Test the FMD device tracker."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from .conftest import LOCATION_BEACONDB, LOCATION_GPS, create_mock_config_entry


async def test_tracker(hass: HomeAssistant, mock_client) -> None:
    """Test the device tracker gets coordinator data."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.fmd_mock_fmd_id")
    assert state is not None
    assert state.attributes["latitude"] == pytest.approx(52.520008)
    assert state.attributes["longitude"] == pytest.approx(13.404954)
    assert state.attributes["battery_level"] == 85
    assert state.attributes["gps_accuracy"] == 10
    assert state.attributes["provider"] == "gps"


async def test_tracker_filters_inaccurate(hass: HomeAssistant, mock_client) -> None:
    """Test BeaconDB fixes are skipped when filtering is enabled."""
    mock_client.get_locations = AsyncMock(return_value=["blob-beacondb", "blob-gps"])
    mock_client.decrypt_data_blob = MagicMock(
        side_effect=[LOCATION_BEACONDB, LOCATION_GPS]
    )
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.fmd_mock_fmd_id")
    assert state is not None
    assert state.attributes["provider"] == "gps"


async def test_tracker_allows_inaccurate(hass: HomeAssistant, mock_client) -> None:
    """Test inaccurate fixes are used when allow_inaccurate is true."""
    mock_client.get_locations = AsyncMock(return_value=["blob-beacondb"])
    mock_client.decrypt_data_blob = MagicMock(return_value=LOCATION_BEACONDB)
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "allow_inaccurate": True}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.fmd_mock_fmd_id")
    assert state is not None
    assert state.attributes["provider"] == "BeaconDB"
