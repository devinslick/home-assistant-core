"""Device tracker platform for the FMD integration."""

from typing import override

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FmdConfigEntry
from .const import CONF_FMD_ID
from .coordinator import FmdCoordinator

# The coordinator handles polling; the platform must not create its own.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FmdConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the FMD device tracker."""
    async_add_entities([FmdDeviceTracker(entry.runtime_data)])


class FmdDeviceTracker(TrackerEntity):
    """FMD device tracker."""

    _attr_has_entity_name = False
    _attr_name = None

    def __init__(self, coordinator: FmdCoordinator) -> None:
        """Initialize the tracker."""
        self.coordinator = coordinator
        self._attr_unique_id = coordinator.config_entry.data[CONF_FMD_ID]

    @property
    @override
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        if (bat := self.coordinator.data.get("bat")) is not None:
            return int(bat)
        return None

    @property
    @override
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.coordinator.data.get("lat")

    @property
    @override
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.coordinator.data.get("lon")

    @property
    @override
    def location_accuracy(self) -> float:
        """Return the location accuracy of the device (meters)."""
        return float(self.coordinator.data.get("accuracy", 0))

    @property
    @override
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        data = self.coordinator.data
        attributes: dict[str, object] = {}
        if "provider" in data:
            attributes["provider"] = data["provider"]
        if "time" in data:
            attributes["device_timestamp"] = data["time"]
        if "date" in data:
            attributes["device_timestamp_ms"] = str(data["date"])
        if "altitude" in data:
            attributes["altitude"] = data["altitude"]
        if "speed" in data:
            attributes["speed"] = data["speed"]
        if "heading" in data:
            attributes["heading"] = data["heading"]
        return attributes
