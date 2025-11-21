from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import EnergyRatesCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: EnergyRatesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EnergyPriceSensor(coordinator, entry),
            DailyFixedCostSensor(coordinator, entry),
            MonthlyFixedCostSensor(coordinator, entry),
        ]
    )


def _rs(data: dict) -> dict | None:
    rates = data.get("rates") or {}
    rs = rates.get("residential_standard") or {}
    if not rs.get("is_present"):
        return None
    return rs


class BaseCostSensor(CoordinatorEntity[EnergyRatesCoordinator], SensorEntity):
    _attr_has_entity_name = True

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


class EnergyPriceSensor(BaseCostSensor):
    """Primary cost entity for HA Energy Dashboard (USD/kWh)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_energy_price"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Energy price"

    @property
    def native_value(self) -> float | None:
        rs = _rs(self.coordinator.data or {})
        if not rs:
            return None
        energy = float(rs.get("energy_rate_usd_per_kwh", 0))
        fuel = float(rs.get("tva_fuel_rate_usd_per_kwh", 0))
        return round(energy + fuel, 5)


class DailyFixedCostSensor(BaseCostSensor):
    """Daily fixed cost estimate (USD/day)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_daily_fixed_cost"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Daily fixed cost"

    @property
    def native_value(self) -> float | None:
        rs = _rs(self.coordinator.data or {})
        if not rs:
            return None
        monthly = float(rs.get("customer_charge_monthly_usd", 0))
        return round(monthly / 30.0, 5)


class MonthlyFixedCostSensor(BaseCostSensor):
    """Monthly fixed customer charge (USD/month)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_monthly_fixed_cost"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Monthly fixed cost"

    @property
    def native_value(self) -> float | None:
        rs = _rs(self.coordinator.data or {})
        if not rs:
            return None
        return float(rs.get("customer_charge_monthly_usd", 0))
