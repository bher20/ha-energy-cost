from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, CONF_API_URL, CONF_PROVIDER

LOGGER = logging.getLogger(__name__)
DEFAULT_SCAN_INTERVAL = 900  # seconds


class EnergyRatesCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator to fetch rates from the eRateManager backend."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.api_url: str = entry.data[CONF_API_URL].rstrip("/")
        self.provider: str = entry.data[CONF_PROVIDER]

        super().__init__(
            hass,
            LOGGER,
            name="HA Energy Rates",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        url = f"{self.api_url}/rates/{self.provider}/residential"
        session = aiohttp_client.async_get_clientsession(self.hass)

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status} from {url}")
                data = await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching {url}: {err}") from err

        if not isinstance(data, dict):
            raise UpdateFailed("Response is not a JSON object")

        return data
