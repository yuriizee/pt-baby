import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info
from .const import DOMAIN

class PTBabyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Крок 1: Вибір пристрою."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_params()

        discovery_info = async_discovered_service_info(self.hass)
        devices = {
            info.address: f"{info.name or 'Невідомий'} ({info.address})"
            for info in discovery_info
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("address"): vol.In(devices),
                vol.Required("name", default="PT Baby Swing"): str
            })
        )

    async def async_step_params(self, user_input=None):
        """Крок 2: Налаштування UUID та параметрів."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data["name"], data=self._data)

        return self.async_show_form(
            step_id="params",
            data_schema=vol.Schema({
                vol.Required("char_uuid", default="7772e5db-3868-4112-a1a9-f2669d106bf3"): str,
                vol.Required("speed_cmd_prefix", default="cmd1"): str,
                vol.Required("stop_cmd", default="cmd10"): str,
            })
        )