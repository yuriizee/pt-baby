import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from .const import DOMAIN

class PTBabyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Крок ручного додавання через меню."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        # Скануємо пристрої навколо
        discovery_info = async_discovered_service_info(self.hass)
        devices = {
            info.address: f"{info.name} ({info.address})"
            for info in discovery_info
            if info.name and "BABY" in info.name.upper()
        }

        if not devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("address"): vol.In(devices),
                vol.Required("name", default="Дитяча колиска"): str
            }),
            errors=errors
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Крок автоматичного виявлення (Discovery)."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        return self.async_show_form(
            step_id="user",
            description_placeholders={"name": discovery_info.name}
        )