"""Common fixtures for the FMD tests."""

from collections.abc import Generator
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.fmd.const import (
    CONF_ALLOW_INACCURATE,
    CONF_FMD_ID,
    DOMAIN,
)
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

MOCK_URL = "https://fmd.example.com"
MOCK_FMD_ID = "mock-fmd-id"
MOCK_PASSWORD = "mock-password"

LOCATION_GPS = json.dumps(
    {
        "lat": 52.520008,
        "lon": 13.404954,
        "bat": 85,
        "provider": "gps",
        "time": "2026-09-30T12:00:00Z",
        "date": 1790000000000,
        "accuracy": 10,
        "altitude": 34.0,
        "speed": 1.4,
        "heading": 180.0,
    }
).encode()

LOCATION_BEACONDB = json.dumps(
    {
        "lat": 52.52,
        "lon": 13.40,
        "provider": "BeaconDB",
        "accuracy": 150,
    }
).encode()


def create_mock_client() -> MagicMock:
    """Create a mock FmdClient."""
    client = MagicMock()
    client.get_locations = AsyncMock(return_value=["blob-gps"])
    client.decrypt_data_blob = MagicMock(return_value=LOCATION_GPS)
    client.export_auth_artifacts = AsyncMock(
        return_value={
            "base_url": MOCK_URL,
            "fmd_id": MOCK_FMD_ID,
            "access_token": "mock-token",
            "private_key": "mock-key",
            "password_hash": "mock-hash",
        }
    )
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Mock the FmdClient used by the integration."""
    client = create_mock_client()
    with (
        patch(
            "homeassistant.components.fmd.FmdClient.from_auth_artifacts",
            AsyncMock(return_value=client),
        ),
        patch(
            "homeassistant.components.fmd.config_flow.FmdClient.create",
            AsyncMock(return_value=client),
        ),
    ):
        yield client


def create_mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock FMD config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_FMD_ID,
        data={
            CONF_URL: MOCK_URL,
            CONF_FMD_ID: MOCK_FMD_ID,
            CONF_ALLOW_INACCURATE: False,
            "artifacts": {
                "base_url": MOCK_URL,
                "fmd_id": MOCK_FMD_ID,
                "access_token": "mock-token",
                "private_key": "mock-key",
                "password_hash": "mock-hash",
            },
        },
        unique_id=MOCK_FMD_ID,
    )
