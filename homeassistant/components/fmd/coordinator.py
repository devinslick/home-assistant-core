"""DataUpdateCoordinator for the FMD integration."""

from datetime import timedelta
import json
from typing import TypedDict

from fmd_api import AuthenticationError, FmdApiException, FmdClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

SCAN_INTERVAL = timedelta(minutes=30)

# Number of recent locations to inspect when filtering inaccurate ones.
MAX_LOCATIONS_TO_CHECK = 5

# Providers whose fixes are considered accurate; BeaconDB fixes and fixes
# from unknown providers are treated as inaccurate.
ACCURATE_PROVIDERS = {"fused", "gps", "network"}


class FmdLocationData(TypedDict, total=False):
    """Location data decrypted from an FMD location blob."""

    lat: float
    lon: float
    bat: int
    provider: str
    time: str
    date: int
    accuracy: float
    altitude: float
    speed: float
    heading: float


type FmdConfigEntry = ConfigEntry[FmdCoordinator]


class FmdCoordinator(DataUpdateCoordinator[FmdLocationData]):
    """FMD location coordinator."""

    config_entry: FmdConfigEntry
    client: FmdClient

    def __init__(
        self, hass: HomeAssistant, entry: FmdConfigEntry, client: FmdClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
            request_refresh_debouncer=Debouncer(
                hass,
                LOGGER,
                cooldown=5,
                immediate=True,
            ),
        )
        self.client = client
        self.allow_inaccurate = entry.data.get("allow_inaccurate", False)

    async def _async_update_data(self) -> FmdLocationData:
        """Fetch the latest device location from the FMD server."""
        num_locations = 1 if self.allow_inaccurate else MAX_LOCATIONS_TO_CHECK
        try:
            blobs = await self.client.get_locations(num_locations)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except FmdApiException as err:
            raise UpdateFailed(
                f"Error communicating with the FMD server: {err}"
            ) from err

        for blob in blobs:
            if not blob:
                continue
            decrypted = await self.hass.async_add_executor_job(
                self.client.decrypt_data_blob, blob
            )
            location: FmdLocationData = json.loads(decrypted)
            if self.allow_inaccurate or self._is_accurate(location):
                return location

        # No usable location among the blobs; keep the previous data.
        return self.data

    def _is_accurate(self, location: FmdLocationData) -> bool:
        """Return whether a location fix is considered accurate."""
        provider = str(location.get("provider", "")).lower()
        if provider in ACCURATE_PROVIDERS:
            return True
        if provider in {"beacondb", ""}:
            return False
        LOGGER.warning(
            "Unknown location provider '%s', treating as inaccurate", provider
        )
        return False
