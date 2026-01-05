from homeassistant.components.number import NumberEntity
from bleak import BleakClient
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Налаштування гучності."""
    address = config_entry.data["address"]
    # Беремо строго з конфігурації
    char_uuid = config_entry.data["char_uuid"]

    async_add_entities([PTBabyVolume(address, char_uuid)])

class PTBabyVolume(NumberEntity):
    def __init__(self, address, char_uuid):
        self._address = address
        self._char_uuid = char_uuid
        self._attr_name = "Гучність колиски"
        self._attr_unique_id = f"{address}_volume"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 9
        self._attr_native_step = 1
        self._attr_native_value = 5

    async def async_set_native_value(self, value: float) -> None:
        cmd = f"cmd2{int(value)}"
        # Використовуємо UUID, отриманий з налаштувань
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, cmd.encode('utf-8'))
        self._attr_native_value = value
        self.async_write_ha_state()