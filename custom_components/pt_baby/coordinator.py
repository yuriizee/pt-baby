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
        self._is_on = False
        self._swing_speed = 0
        self._melody_on = False
        self._current_melody = 1
        self._volume = 50
        self._timer = 0
        self._induction_mode = False

        _LOGGER.info(
            "Initialized PT Baby with service: %s, write: %s, notify: %s",
            self.service_uuid, self.write_char_uuid, self.notify_char_uuid
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if not self._client or not self._client.is_connected:
            await self._ensure_connected()

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

        try:
            self._device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )

            if not self._device:
                raise UpdateFailed(f"Could not find device {self.address}")

            self._client = BleakClient(self._device)
            await self._client.connect()

            # Підписка на повідомлення
            await self._client.start_notify(
                self.notify_char_uuid, self._notification_handler
            )

            _LOGGER.info("Connected to PT Baby Swing: %s", self.address)
        except (BleakError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error connecting to device: {err}") from err

    @callback
    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notification from device."""
        _LOGGER.debug("Received notification: %s", data.hex())
        # Тут можна парсити відповіді від пристрою

    async def _send_command(self, command: str) -> None:
        """Send command to device."""
        try:
            await self._ensure_connected()

            if not self._client:
                raise UpdateFailed("Not connected to device")

            # Конвертуємо команду в bytes (потрібно налаштувати формат)
            cmd_bytes = command.encode()

            await self._client.write_gatt_char(
                self.write_char_uuid, cmd_bytes, response=False
            )

            _LOGGER.debug("Sent command: %s", command)
        except (BleakError, asyncio.TimeoutError) as err:
            _LOGGER.error("Error sending command: %s", err)
            raise UpdateFailed(f"Error sending command: {err}") from err

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        await self._send_command(CMD_POWER_ON)
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        # Потрібно додати команду вимкнення
        self._is_on = False
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_swing_speed(self, speed: int) -> None:
        """Set swing speed (1-5)."""
        if speed not in SWING_SPEEDS:
            raise ValueError(f"Invalid speed: {speed}")

        if not self._is_on:
            await self.async_turn_on()

        await self._send_command(SWING_SPEEDS[speed])
        self._swing_speed = speed
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_melody(self, melody: int) -> None:
        """Set melody (1-9)."""
        from .const import MELODIES, CMD_MELODY_ON

        if melody not in MELODIES:
            raise ValueError(f"Invalid melody: {melody}")

        await self._send_command(MELODIES[melody])
        await self._send_command(CMD_MELODY_ON)
        self._current_melody = melody
        self._melody_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_melody_on(self) -> None:
        """Turn on melody."""
        from .const import CMD_MELODY_ON
        await self._send_command(CMD_MELODY_ON)
        self._melody_on = True
        self.async_set_updated_data(await self._async_update_data())

    async def async_melody_off(self) -> None:
        """Turn off melody."""
        # Потрібно додати команду вимкнення мелодії
        self._melody_on = False
        self.async_set_updated_data(await self._async_update_data())

    async def async_next_melody(self) -> None:
        """Switch to next melody."""
        # Потрібно додати команду наступної мелодії
        pass

    async def async_previous_melody(self) -> None:
        """Switch to previous melody."""
        # Потрібно додати команду попередньої мелодії
        pass

    async def async_volume_up(self) -> None:
        """Increase volume."""
        # Потрібно додати команду збільшення гучності
        pass

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        # Потрібно додати команду зменшення гучності
        pass

    async def async_set_timer(self, minutes: int) -> None:
        """Set timer."""
        # Команда таймера - кожен виклик додає 5 хвилин
        times = minutes // 5
        for _ in range(times):
            # Потрібно додати команду таймера
            pass
        self._timer = minutes
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_induction_mode(self, enabled: bool) -> None:
        """Set induction mode."""
        # Потрібно додати команди ввімкнення/вимкнення індукційного режиму
        self._induction_mode = enabled
        self.async_set_updated_data(await self._async_update_data())

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()