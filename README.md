# HA Energy Rates (domain: ha_energy_cost)

Custom Home Assistant integration that fetches electric utility rates from an **eRateManager**
backend (your Go service) and exposes:

- Total residential rate (energy + fuel) in USD/kWh
- Fixed monthly customer charge
- Last refresh timestamp and age (hours)
- A binary sensor indicating whether rates are "up to date"
- Dedicated cost entities for the **Energy Dashboard**:
  - `Energy price` (USD/kWh)
  - `Daily fixed cost` (USD/day)
  - `Monthly fixed cost` (USD/month)
- A button to **force-refresh** rates on demand (calls `/internal/refresh/{provider}`).

## Provider-prefixed entity names

All entities are prefixed with the selected provider key. For example, for `cemc`:

- `CEMC Total energy rate`
- `CEMC Energy price`
- `CEMC Daily fixed cost`
- `CEMC Monthly fixed cost`
- `CEMC Rates last refresh`
- `CEMC Rates age (hours)`
- `CEMC Rates up to date`
- `CEMC Force rates refresh`

Entity IDs will look like:

- `sensor.cemc_energy_price`
- `sensor.cemc_monthly_fixed_cost`
- `binary_sensor.cemc_rates_up_to_date`
- `button.cemc_force_rates_refresh`

## Configuration

When you add the integration, you will be asked for:

1. **API base URL** – e.g. `https://rates.bherville.com`
2. The integration will then query `/providers` to build the list of available utilities.
3. Select your **Provider** (e.g. `CEMC`, `NES`, or `Demo`).

Multiple instances are supported, so you can add one config entry per provider.

## Energy Dashboard

In **Settings → Energy → Electricity grid → Grid consumption**:

- Set **Energy price** to the provider-specific `Energy price` sensor this integration creates
  (unit: `USD/kWh`, device class: `monetary`, state class: `measurement`).

In **Fixed costs**, you can use:

- The provider-specific `Monthly fixed cost` or `Daily fixed cost` sensor.

The Energy Dashboard will then use these entities to compute your energy costs.
