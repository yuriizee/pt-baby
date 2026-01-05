from homeassistant.components.number import NumberEntity
from bleak import BleakClient
import asyncio

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    async_add_entities([PTBabyVolume(data["address"], data["char_uuid"])])

class PTBabyVolume(NumberEntity):
    def __init__(self, address, char_uuid):
        self._address = address
        self._char_uuid = char_uuid
        self._attr_name = "Гучність колиски"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 9
        self._attr_native_step = 1
        self._attr_native_value = 5

    async def async_set_native_value(self, value: float) -> None:
        volume_cmd = f"cmd2{int(value)}"
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, volume_cmd.encode('utf-8'))
        self._attr_native_value = value
        self.async_write_ha_state()