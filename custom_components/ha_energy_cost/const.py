from __future__ import annotations

DOMAIN = "ha_energy_cost"
DEFAULT_NAME = "HA Energy Rates"

CONF_API_URL = "api_url"
CONF_PROVIDER = "provider"

# Fallback providers if /providers endpoint is unavailable
STATIC_PROVIDERS: dict[str, str] = {
    "CEMC": "cemc",
    "NES": "nes",
    "Demo": "demo",
}
