from homeassistant.components.fan import FanEntity, FanEntityFeature
from bleak import BleakClient
from .const import CHARACTERISTIC_CTRL

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Додавання колиски на основі вибору в меню."""
    address = config_entry.data["address"]
    name = config_entry.data["name"]
    async_add_entities([PTBabyFan(address, name)])

class PTBabyFan(FanEntity):
    def __init__(self, address, name):
        self._address = address
        self._name = name
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_percentage = 0

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._address

    async def _send_cmd(self, cmd):
        # Використовуємо знайдену команду, наприклад cmd39 або cmd11 [cite: 318, 381]
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(CHARACTERISTIC_CTRL, cmd.encode('utf-8'))

    async def async_set_percentage(self, percentage):
        if percentage == 0:
            await self._send_cmd("cmd10") # Stop
        else:
            # Мапування швидкостей на ваші команди cmd11-cmd15 [cite: 314, 322]
            idx = int(percentage / 20)
            await self._send_cmd(f"cmd1{idx}")
        self._attr_percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.async_set_percentage(0)