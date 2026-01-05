import asyncio
from homeassistant.components.fan import FanEntity, FanEntityFeature
from bleak import BleakClient

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    async_add_entities([PTBabyFan(
        data["address"],
        data["name"],
        data["char_uuid"],
        data["on_cmd"],
        data["off_cmd"],
        data["speed_prefix"]
    )])

class PTBabyFan(FanEntity):
    def __init__(self, address, name, char_uuid, on_cmd, off_cmd, prefix):
        self._address = address
        self._attr_name = name
        self._char_uuid = char_uuid
        self._on_cmd = on_cmd
        self._off_cmd = off_cmd
        self._prefix = prefix

        self._attr_unique_id = f"{address}_swing"
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_percentage = 0
        self._speed_count = 5 # 5 швидкостей: cmd11-cmd15

    @property
    def speed_count(self) -> int:
        return self._speed_count

    async def _write(self, cmd: str):
        """Прямий запис у характеристику."""
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, cmd.encode('utf-8'))

    async def async_set_percentage(self, percentage: int):
        """Встановлення швидкості (0-100%)."""
        if percentage == 0:
            await self._write(self._off_cmd)
        else:
            # Якщо люлька вимкнена, спочатку вмикаємо її
            if self._attr_percentage == 0:
                await self._write(self._on_cmd)
                await asyncio.sleep(0.5)

            # Розрахунок швидкості: 20%=cmd11, 40%=cmd12, ..., 100%=cmd15
            speed_idx = int(percentage / 20)
            await self._write(f"{self._prefix}{speed_idx}")

        self._attr_percentage = percentage
        self.async_write_ha_state()

    async def async_turn_on(self, percentage=None, **kwargs):
        await self.async_set_percentage(percentage or 20)

    async def async_turn_off(self, **kwargs):
        await self.async_set_percentage(0)