import asyncio
import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from bleak import BleakClient

_LOGGER = logging.getLogger(__name__)

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
        # ВИПРАВЛЕННЯ: Додаємо підтримку TURN_ON та TURN_OFF
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED |
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF
        )
        self._attr_percentage = 0
        self._speed_count = 5
        self._lock = asyncio.Lock() # ВИПРАВЛЕННЯ: Блокування для черги Bluetooth

    @property
    def speed_count(self) -> int:
        return self._speed_count

    async def _write(self, cmd: str):
        """Запис у характеристику з використанням черги."""
        async with self._lock: # Тільки одне підключення одночасно
            try:
                _LOGGER.debug(f"Connecting to {self._address} for command {cmd}")
                async with BleakClient(self._address, timeout=10.0) as client:
                    await client.write_gatt_char(self._char_uuid, cmd.encode('utf-8'))
                    # Даємо пристрою час обробити команду перед розривом зв'язку
                    await asyncio.sleep(0.3)
            except Exception as e:
                _LOGGER.error(f"Error sending command {cmd}: {e}")

    async def async_set_percentage(self, percentage: int):
        """Встановлення швидкості."""
        if percentage == 0:
            await self._write(self._off_cmd)
        else:
            # Якщо люлька була вимкнена - шлемо команду активації
            if self._attr_percentage == 0:
                await self._write(self._on_cmd)
                await asyncio.sleep(0.5)

            speed_idx = int(percentage / 20)
            await self._write(f"{self._prefix}{speed_idx}")

        self._attr_percentage = percentage
        self.async_write_ha_state()

    async def async_turn_on(
            self,
            percentage: int | None = None,
            preset_mode: str | None = None,
            **kwargs,
        ) -> None:
            """Вмикання пристрою. Приймає percentage та preset_mode від HA."""
            # Якщо відсоток не вказано (просто натиснули кнопку ON),
            # встановлюємо першу швидкість (20%)
            target_percentage = percentage or 20
            await self.async_set_percentage(target_percentage)

    async def async_turn_off(self, **kwargs) -> None:
        """Вимкнення пристрою."""
        await self.async_set_percentage(0)