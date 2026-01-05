from homeassistant.components.select import SelectEntity
from bleak import BleakClient
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    # Беремо дані, які ви ввели в інтерфейсі при налаштуванні
    address = config_entry.data["address"]
    char_uuid = config_entry.data["char_uuid"]
    async_add_entities([PTBabyMusicSelect(address, char_uuid)])

class PTBabyMusicSelect(SelectEntity):
    def __init__(self, address, char_uuid):
        self._address = address
        self._char_uuid = char_uuid
        self._attr_name = "Мелодія колиски"
        self._attr_unique_id = f"{address}_music"
        self._attr_options = ["Вимкнути", "Мелодія 1", "Мелодія 2", "Мелодія 3"]
        self._attr_current_option = "Вимкнути"

        self._mapping = {
            "Вимкнути": "cmd00",
            "Мелодія 1": "cmd01",
            "Мелодія 2": "cmd02",
            "Мелодія 3": "cmd03"
        }

    async def async_select_option(self, option: str) -> None:
        cmd = self._mapping.get(option)
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, cmd.encode('utf-8'))
        self._attr_current_option = option
        self.async_write_ha_state()