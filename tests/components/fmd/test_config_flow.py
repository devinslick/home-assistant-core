"""Test the FMD config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fmd_api import AuthenticationError, FmdApiException
import pytest

from homeassistant import config_entries
from homeassistant.components.fmd.const import (
    CONF_ALLOW_INACCURATE,
    CONF_FMD_ID,
    DOMAIN,
)
from homeassistant.const import CONF_PASSWORD, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import MOCK_FMD_ID, MOCK_PASSWORD, MOCK_URL

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.fmd.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_form(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: MOCK_URL,
            CONF_FMD_ID: MOCK_FMD_ID,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_ALLOW_INACCURATE: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_FMD_ID
    assert result["data"][CONF_URL] == MOCK_URL
    assert result["data"][CONF_FMD_ID] == MOCK_FMD_ID
    assert CONF_PASSWORD not in result["data"]
    assert "artifacts" in result["data"]
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (AuthenticationError, "invalid_auth"),
        (FmdApiException, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_form_errors(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_setup_entry: AsyncMock,
    side_effect: Exception,
    error: str,
) -> None:
    """Test we handle errors."""
    mock_client.get_locations.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: MOCK_URL,
            CONF_FMD_ID: MOCK_FMD_ID,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_form_unique_id(
    hass: HomeAssistant,
    mock_client: MagicMock,
) -> None:
    """Test we abort if the device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_FMD_ID: MOCK_FMD_ID},
        unique_id=MOCK_FMD_ID,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: MOCK_URL,
            CONF_FMD_ID: MOCK_FMD_ID,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
