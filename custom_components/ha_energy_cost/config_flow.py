from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, CONF_API_URL, CONF_PROVIDER, STATIC_PROVIDERS


async def _fetch_providers(hass, api_url: str) -> dict[str, str]:
    """Fetch providers from the backend /providers endpoint.

    Returns a mapping of display_name -> key.
    """
    api_url = api_url.rstrip("/")
    url = f"{api_url}/providers"
    session = aiohttp_client.async_get_clientsession(hass)

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status}")
            data = await resp.json()
    except Exception:
        # Fallback to static providers
        return STATIC_PROVIDERS.copy()

    providers: dict[str, str] = {}
    items = data.get("providers") or []
    for item in items:
        key = item.get("key")
        name = item.get("name") or key
        if key:
            providers[name] = key

    if not providers:
        return STATIC_PROVIDERS.copy()

    return providers


async def _validate_provider(hass, api_url: str, provider_key: str) -> dict:
    """Validate that /rates/{provider}/residential works."""
    api_url = api_url.rstrip("/")
    url = f"{api_url}/rates/{provider_key}/residential"
    session = aiohttp_client.async_get_clientsession(hass)

    async with session.get(url) as resp:
        if resp.status != 200:
            raise ValueError(f"Backend returned HTTP {resp.status}")
        data = await resp.json()

    if "rates" not in data:
        raise ValueError("Response missing 'rates' key")

    return {
        "title": f"HA Energy Rates ({provider_key})",
        "utility": data.get("utility"),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for HA Energy Rates."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_url: str | None = None
        self._providers: dict[str, str] = STATIC_PROVIDERS.copy()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_url = user_input[CONF_API_URL]
            self._api_url = api_url

            # Try to fetch providers dynamically
            try:
                self._providers = await _fetch_providers(self.hass, api_url)
            except Exception:
                self._providers = STATIC_PROVIDERS.copy()

            # Proceed to provider selection
            return await self.async_step_provider()

        schema = vol.Schema(
            {
                vol.Required(CONF_API_URL, default="https://rates.bherville.com"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_provider(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if self._api_url is None:
            return await self.async_step_user()

        if user_input is not None:
            label = user_input[CONF_PROVIDER]
            provider_key = self._providers.get(label)
            if not provider_key:
                errors["base"] = "invalid_provider"
            else:
                try:
                    info = await _validate_provider(self.hass, self._api_url, provider_key)
                except Exception:
                    errors["base"] = "cannot_connect"
                else:
                    # Unique per provider+api_url
                    await self.async_set_unique_id(f"{provider_key}_{self._api_url}")
                    self._abort_if_unique_id_configured()

                    data = {
                        CONF_API_URL: self._api_url,
                        CONF_PROVIDER: provider_key,
                    }
                    return self.async_create_entry(title=info["title"], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_PROVIDER): vol.In(list(self._providers.keys())),
            }
        )
        return self.async_show_form(step_id="provider", data_schema=schema, errors=errors)
