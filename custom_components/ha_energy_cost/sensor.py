from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyRatesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergyRatesCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    entities.append(EnergyRateSensor(coordinator, entry))
    entities.append(FixedChargeSensor(coordinator, entry))
    entities.append(RatesLastRefreshSensor(coordinator, entry))
    entities.append(RatesAgeHoursSensor(coordinator, entry))
    # Cost sensors for Energy Dashboard integration
    entities.append(EnergyPriceSensor(coordinator, entry))
    entities.append(DailyFixedCostSensor(coordinator, entry))
    entities.append(MonthlyFixedCostSensor(coordinator, entry))

    async_add_entities(entities)


def _get_residential_standard(data: dict) -> dict | None:
    rates = data.get("rates") or {}
    rs = rates.get("residential_standard") or {}
    if not rs.get("is_present"):
        return None
    return rs


class BaseEnergyRatesSensor(CoordinatorEntity[EnergyRatesCoordinator], SensorEntity):
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

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class EnergyRateSensor(BaseEnergyRatesSensor):
    """Sensor for total energy rate (energy + fuel) in USD/kWh."""

    _attr_native_unit_of_measurement = "USD/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = None  # Use cost_sensors.EnergyPriceSensor for Energy Dashboard

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_total_rate"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Total energy rate"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        rs = _get_residential_standard(data)
        if not rs:
            return None
        energy = rs.get("energy_rate_usd_per_kwh") or 0.0
        fuel = rs.get("tva_fuel_rate_usd_per_kwh") or 0.0
        try:
            return float(energy) + float(fuel)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        rs = _get_residential_standard(data) or {}
        attrs: dict[str, object] = {}
        attrs["energy_rate_usd_per_kwh"] = rs.get("energy_rate_usd_per_kwh")
        attrs["tva_fuel_rate_usd_per_kwh"] = rs.get("tva_fuel_rate_usd_per_kwh")
        attrs["customer_charge_monthly_usd"] = rs.get("customer_charge_monthly_usd")

        fetched_at = data.get("fetched_at")
        if fetched_at:
            attrs["last_refresh"] = fetched_at
        source = data.get("source")
        if source:
            attrs["source"] = source
        source_url = data.get("source_url")
        if source_url:
            attrs["source_url"] = source_url
        pdf_url = data.get("pdf_url")
        if pdf_url:
            attrs["pdf_url"] = pdf_url
        attrs["last_refresh_ok"] = self.coordinator.last_update_success
        attrs["utility"] = data.get("utility")
        attrs["provider"] = self.coordinator.provider
        return attrs


class FixedChargeSensor(BaseEnergyRatesSensor):
    """Monthly fixed customer charge in USD."""

    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = None  # monetary + measurement is not allowed in HA

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_fixed_charge"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Fixed customer charge"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        rs = _get_residential_standard(data)
        if not rs:
            return None
        val = rs.get("customer_charge_monthly_usd")
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None


class RatesLastRefreshSensor(BaseEnergyRatesSensor):
    """Timestamp of last refresh from backend."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_state_class = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_last_refresh"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Rates last refresh"

    @property
    def native_value(self) -> datetime | None:
        data = self.coordinator.data or {}
        fetched_at = data.get("fetched_at")
        if not fetched_at:
            return None
        try:
            dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None


class RatesAgeHoursSensor(BaseEnergyRatesSensor):
    """Age of rates in hours since last refresh."""

    _attr_native_unit_of_measurement = "h"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_{self._provider_key}_age_hours"

    @property
    def name(self) -> str:
        return f"{self._provider_label} Rates age (hours)"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        fetched_at = data.get("fetched_at")
        if not fetched_at:
            return None
        try:
            dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - dt
            return delta.total_seconds() / 3600.0
        except Exception:
            return None


# ============================================================================
# Cost Sensors for Home Assistant Energy Dashboard Integration
# ============================================================================


class EnergyPriceSensor(BaseEnergyRatesSensor):
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
        rs = _get_residential_standard(self.coordinator.data or {})
        if not rs:
            return None
        energy = float(rs.get("energy_rate_usd_per_kwh", 0))
        fuel = float(rs.get("tva_fuel_rate_usd_per_kwh", 0))
        return round(energy + fuel, 5)


class DailyFixedCostSensor(BaseEnergyRatesSensor):
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
        rs = _get_residential_standard(self.coordinator.data or {})
        if not rs:
            return None
        monthly = float(rs.get("customer_charge_monthly_usd", 0))
        return round(monthly / 30.0, 5)


class MonthlyFixedCostSensor(BaseEnergyRatesSensor):
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
        rs = _get_residential_standard(self.coordinator.data or {})
        if not rs:
            return None
        return float(rs.get("customer_charge_monthly_usd", 0))
