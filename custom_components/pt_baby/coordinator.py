"""DataUpdateCoordinator for Baby Cradle."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

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
    CMD_POWER_OFF,
    SWING_SPEEDS,
    MELODIES,
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
        self._client: BleakClientWithServiceCache | None = None
        self._device: BLEDevice | None = None
        self._lock = asyncio.Lock()

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
        """Update data."""
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

        self._device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

        if not self._device:
            raise UpdateFailed(f"Device {self.address} not found")

        _LOGGER.debug("Connecting to %s", self.address)
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                name=self.address,
            )

            # Спроба підписки (не критично, якщо не вдасться)
            try:
                await self._client.start_notify(
                    self.notify_char_uuid, self._notification_handler
                )
            except Exception:
                pass

            _LOGGER.info("Connected to PT Baby Swing: %s", self.address)
        except Exception as err:
            raise UpdateFailed(f"Error connecting: {err}") from err

    @callback
    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notification."""
        _LOGGER.debug("Notification: %s", data.hex())

    async def async_send_command(self, command: str) -> None:
        """Send raw command to device."""
        if not command: return

        async with self._lock:
            try:
                await self._ensure_connected()
                if not self._client or not self._client.is_connected:
                    raise UpdateFailed("Connection lost")

                cmd_bytes = command.encode('utf-8')
                await self._client.write_gatt_char(
                    self.write_char_uuid, cmd_bytes, response=False
                )
                await asyncio.sleep(0.3) # Пауза після команди
                _LOGGER.debug("Sent command: %s", command)

            except Exception as err:
                _LOGGER.error("Error sending %s: %s", command, err)
                if self._client:
                    await self._client.disconnect()
                self._client = None
                raise UpdateFailed(f"Communication error: {err}") from err

    # --- Основні методи керування ---

    async def async_turn_on(self) -> None:
        """Увімкнення (пробудження)."""
        await self.async_send_command(CMD_POWER_ON)
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_turn_off(self) -> None:
        """Вимкнення."""
        await self.async_send_command(CMD_POWER_OFF)
        self._is_on = False
        self._swing_speed = 0
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_swing_speed(self, speed: int) -> None:
        """Встановлення швидкості (1-5)."""
        if speed == 0:
            await self.async_turn_off()
            return

        if speed not in SWING_SPEEDS:
            _LOGGER.error("Invalid speed: %s", speed)
            return

        # ВАЖЛИВО: Завжди шлемо команду пробудження перед зміною швидкості,
        # щоб гарантувати, що пристрій слухає.
        await self.async_send_command(CMD_POWER_ON)
        await asyncio.sleep(0.5) # Пауза на пробудження

        await self.async_send_command(SWING_SPEEDS[speed])

        self._swing_speed = speed
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    # --- Мелодії ---

    async def async_set_melody(self, melody: int) -> None:
        if melody in MELODIES:
            # Для мелодій теж бажано розбудити
            if not self._is_on:
                 await self.async_turn_on()

            await self.async_send_command(MELODIES[melody])
            self._current_melody = melody
            self._melody_on = True
            self.async_set_updated_data(await self._async_update_data())

    async def async_melody_on(self) -> None:
        # Вмикаємо останню мелодію або першу
        await self.async_set_melody(self._current_melody)

    async def async_melody_off(self) -> None:
        # Якщо є команда стоп для музики - додайте її в const.py
        # await self.async_send_command("cmd00")
        self._melody_on = False
        self.async_set_updated_data(await self._async_update_data())

    async def async_next_melody(self) -> None:
        next_m = self._current_melody + 1
        if next_m > 9: next_m = 1
        await self.async_set_melody(next_m)

    async def async_previous_melody(self) -> None:
        prev_m = self._current_melody - 1
        if prev_m < 1: prev_m = 9
        await self.async_set_melody(prev_m)

    # --- Інше ---

    async def async_set_timer(self, minutes: int) -> None:
        self._timer = minutes
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_induction_mode(self, enabled: bool) -> None:
        self._induction_mode = enabled
        self.async_set_updated_data(await self._async_update_data())

    async def async_volume_up(self) -> None:
        pass

    async def async_volume_down(self) -> None:
        pass

    async def async_shutdown(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()