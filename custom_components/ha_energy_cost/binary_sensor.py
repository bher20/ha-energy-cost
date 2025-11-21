from __future__ import annotations

from datetime import datetime, timezone, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyRatesCoordinator

FRESHNESS_HOURS = 48


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergyRatesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RatesUpToDateBinarySensor(coordinator, entry)])


class RatesUpToDateBinarySensor(CoordinatorEntity[EnergyRatesCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether the rates are fresh enough."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: EnergyRatesCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        provider = coordinator.provider
        self._provider_key = provider
        self._provider_label = provider.upper()
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"{self._provider_label} Energy Rates",
            "manufacturer": "eratemanager",
        }

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_rates_up_to_date"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Rates up to date"

    @property
    def is_on(self) -> bool | None:
        """True when there is a problem (rates are too old)."""
        data = self.coordinator.data or {}
        fetched_at = data.get("fetched_at")
        if not fetched_at:
            return None

        try:
            dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age = now - dt
        except Exception:
            return None

        # Sensor is "on" when there is a problem: age > FRESHNESS_HOURS
        return age > timedelta(hours=FRESHNESS_HOURS)
