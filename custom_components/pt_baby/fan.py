from homeassistant.components.fan import FanEntity, FanEntityFeature
from bleak import BleakClient

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Налаштування на основі даних з Config Entry."""
    # Отримуємо всі дані, які ви ввели в UI
    address = config_entry.data["address"]
    name = config_entry.data["name"]
    char_uuid = config_entry.data["char_uuid"]
    prefix = config_entry.data["speed_cmd_prefix"]
    stop_cmd = config_entry.data["stop_cmd"]

    async_add_entities([PTBabyFan(address, name, char_uuid, prefix, stop_cmd)])

class PTBabyFan(FanEntity):
    def __init__(self, address, name, char_uuid, prefix, stop_cmd):
        self._address = address
        self._attr_name = name
        self._char_uuid = char_uuid
        self._prefix = prefix
        self._stop_cmd = stop_cmd

        self._attr_unique_id = f"{address}_swing"
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_percentage = 0

    async def _send_command(self, cmd: str):
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, cmd.encode('utf-8'))

    async def async_set_percentage(self, percentage: int):
        if percentage == 0:
            await self._send_command(self._stop_cmd)
        else:
            step = int(percentage / 20)
            await self._send_command(f"{self._prefix}{step}")

        self._attr_percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.async_set_percentage(0)