"""DataUpdateCoordinator for Baby Cradle."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_SERVICE_UUID,
    CONF_WRITE_CHAR_UUID,
    CONF_NOTIFY_CHAR_UUID,
    CMD_POWER_ON,
    SWING_SPEEDS,
)

_LOGGER = logging.getLogger(__name__)

class PTBabyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Baby Cradle data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.address = entry.data[CONF_MAC_ADDRESS]
        self.service_uuid = entry.data[CONF_SERVICE_UUID]
        self.write_char_uuid = entry.data[CONF_WRITE_CHAR_UUID]
        self.notify_char_uuid = entry.data[CONF_NOTIFY_CHAR_UUID]
        self._client: BleakClient | None = None
        self._device: BLEDevice | None = None
        self._lock = asyncio.Lock()  # Черга для команд

        # Внутрішній стан
        self._is_on = False
        self._swing_speed = 0
        self._melody_on = False
        self._current_melody = 1
        self._volume = 50
        self._timer = 0
        self._induction_mode = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        # Для Bluetooth пристроїв, які самі не шлють стан,
        # ми просто повертаємо останній відомий стан
        return {
            "is_on": self._is_on,
            "swing_speed": self._swing_speed,
            "melody_on": self._melody_on,
            "current_melody": self._current_melody,
            "volume": self._volume,
            "timer": self._timer,
            "induction_mode": self._induction_mode,
        }

    async def _ensure_connected(self) -> None:
        """Ensure connection to device."""
        if self._client and self._client.is_connected:
            return

        # Шукаємо пристрій через HA Bluetooth API
        self._device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

        if not self._device:
            raise UpdateFailed(f"Device {self.address} not found")

        self._client = BleakClient(self._device)
        await self._client.connect()

        # Спробуємо підписатися, якщо це можливо
        try:
            await self._client.start_notify(
                self.notify_char_uuid, self._notification_handler
            )
        except Exception as e:
            _LOGGER.warning("Could not subscribe to notifications: %s", e)

        _LOGGER.info("Connected to PT Baby Swing: %s", self.address)

    @callback
    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notification from device."""
        _LOGGER.debug("Received notification: %s", data.hex())

    async def async_send_command(self, command: str) -> None:
        """Send command to device (Public method)."""
        if not command:
            return

        async with self._lock:  # Блокування для уникнення конфліктів
            try:
                await self._ensure_connected()

                if not self._client:
                     raise UpdateFailed("Connection failed")

                cmd_bytes = command.encode('utf-8')
                await self._client.write_gatt_char(
                    self.write_char_uuid, cmd_bytes, response=False
                )
                await asyncio.sleep(0.3) # Пауза для стабільності
                _LOGGER.debug("Sent command: %s", command)

            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.error("Error sending command %s: %s", command, err)
                # Скидаємо клієнт, щоб наступного разу перепідключитися
                if self._client:
                    await self._client.disconnect()
                self._client = None
                raise UpdateFailed(f"Communication error: {err}") from err

    async def async_turn_on(self) -> None:
        await self.async_send_command(CMD_POWER_ON)
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_turn_off(self) -> None:
        await self.async_send_command("cmd39") # Перевірте правильність команди вимкнення
        self._is_on = False
        self._swing_speed = 0
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_swing_speed(self, speed: int) -> None:
        if speed not in SWING_SPEEDS:
             # Якщо 0 - вимикаємо
            if speed == 0:
                await self.async_turn_off()
                return
            raise ValueError(f"Invalid speed: {speed}")

        if not self._is_on:
            await self.async_turn_on()
            await asyncio.sleep(0.5)

        await self.async_send_command(SWING_SPEEDS[speed])
        self._swing_speed = speed
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    # --- Методи для медіа плеєра та іншого ---
    async def async_set_melody(self, melody: int) -> None:
        from .const import MELODIES, CMD_MELODY_ON
        if melody in MELODIES:
            await self.async_send_command(MELODIES[melody])
            self._current_melody = melody
            self._melody_on = True
            self.async_set_updated_data(await self._async_update_data())

    async def async_melody_on(self) -> None:
        from .const import CMD_MELODY_ON
        await self.async_send_command(CMD_MELODY_ON)
        self._melody_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_melody_off(self) -> None:
        # Якщо є команда зупинки мелодії, додайте її тут.
        # Часто це "cmd00" або повторне натискання.
        self._melody_on = False
        self.async_set_updated_data(await self._async_update_data())

    async def async_next_melody(self) -> None:
        # Логіка наступної мелодії
        next_m = self._current_melody + 1
        if next_m > 9: next_m = 1
        await self.async_set_melody(next_m)

    async def async_previous_melody(self) -> None:
        prev_m = self._current_melody - 1
        if prev_m < 1: prev_m = 9
        await self.async_set_melody(prev_m)

    async def async_volume_up(self) -> None:
        # Додати команду гучності якщо відома
        pass

    async def async_volume_down(self) -> None:
        pass

    async def async_set_timer(self, minutes: int) -> None:
        self._timer = minutes
        # Реалізація команд таймера
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_induction_mode(self, enabled: bool) -> None:
        self._induction_mode = enabled
        self.async_set_updated_data(await self._async_update_data())

    async def async_shutdown(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()