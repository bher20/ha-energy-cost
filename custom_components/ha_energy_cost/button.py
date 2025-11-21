from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN
from .coordinator import EnergyRatesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergyRatesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ForceRefreshButton(coordinator, entry)])


class ForceRefreshButton(CoordinatorEntity[EnergyRatesCoordinator], ButtonEntity):
    """Button to trigger an on-demand PDF refresh via backend."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"

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
        return f"{self._entry.entry_id}_{self._provider_key}_force_refresh"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Force rates refresh"

    async def async_press(self) -> None:
        """Call backend /internal/refresh/{provider} then refresh coordinator."""
        session = aiohttp_client.async_get_clientsession(self.coordinator.hass)
        url = f"{self.coordinator.api_url}/internal/refresh/{self.coordinator.provider}"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    self.coordinator.logger.warning(
                        "Force refresh returned HTTP %s from %s", resp.status, url
                    )
        except Exception as err:
            self.coordinator.logger.error("Force refresh failed: %s", err)

        await self.coordinator.async_request_refresh()
