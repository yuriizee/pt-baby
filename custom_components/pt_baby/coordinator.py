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
        self.service_uuid = entry.data.get(CONF_SERVICE_UUID)
        self.write_char_uuid = entry.data.get(CONF_WRITE_CHAR_UUID)
        self.notify_char_uuid = entry.data.get(CONF_NOTIFY_CHAR_UUID)

        self._client: BleakClientWithServiceCache | None = None
        self._device: BLEDevice | None = None
        self._lock = asyncio.Lock()

        # Стан
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
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Повертаємо поточний стан."""
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
        """Гарантує підключення з агресивним пошуком."""
        if self._client and self._client.is_connected:
            return

        # Спроба 1: Шукаємо "хороший" пристрій (connectable=True)
        self._device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

        # Спроба 2: Якщо не знайшли, шукаємо будь-який (connectable=False).
        # Це допомагає знайти пристрої, які "сплять" або криво рекламують себе.
        if not self._device:
            _LOGGER.debug("Device not found as connectable, trying non-connectable scan...")
            self._device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=False
            )

        if not self._device:
            raise UpdateFailed(f"Device {self.address} not found via Bluetooth scan. Check range or power.")

        _LOGGER.debug("Connecting to %s...", self.address)
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                name=self.address,
                disconnected_callback=self._on_disconnected,
                use_services_cache=True,
                max_attempts=3 # Робимо 3 спроби підключення
            )
            _LOGGER.info("Connected to PT Baby Swing!")
        except Exception as err:
            self._client = None
            raise UpdateFailed(f"Connection failed: {err}") from err

    def _on_disconnected(self, client):
        """Callback при розриві з'єднання."""
        _LOGGER.info("Disconnected from PT Baby Swing")
        self._client = None
        self._is_on = False
        self.async_set_updated_data(self.data)

    async def async_send_command(self, command: str) -> None:
        """Відправка команди (публічний метод)."""
        if not command: return

        async with self._lock:
            try:
                await self._ensure_connected()

                cmd_bytes = command.encode('utf-8')

                await self._client.write_gatt_char(
                    self.write_char_uuid, cmd_bytes, response=False
                )
                _LOGGER.info("Sent command: %s", command)

            except Exception as err:
                _LOGGER.error("Error sending %s: %s", command, err)
                if self._client:
                    await self._client.disconnect()
                self._client = None
                raise UpdateFailed(f"Send failed: {err}") from err

    # --- КЕРУВАННЯ ---

    async def async_turn_on(self) -> None:
        """Увімкнення."""
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
        """Встановлення швидкості."""
        if speed == 0:
            await self.async_turn_off()
            return

        # 1. Пробудження (ігноруємо помилки, якщо вже прокинувся)
        try:
             await self.async_send_command(CMD_POWER_ON)
             await asyncio.sleep(0.5)
        except Exception as e:
            _LOGGER.warning("Wake up command failed (might be already awake): %s", e)

        # 2. Швидкість
        cmd = SWING_SPEEDS.get(speed)
        if cmd:
            await self.async_send_command(cmd)
            self._swing_speed = speed
            self._is_on = True
            self.async_set_updated_data(await self._async_update_data())

    async def async_set_melody(self, melody: int) -> None:
        if melody in MELODIES:
            if not self._is_on:
                 try:
                     await self.async_send_command(CMD_POWER_ON)
                     await asyncio.sleep(0.5)
                 except Exception: pass

            await self.async_send_command(MELODIES[melody])
            self._current_melody = melody
            self._melody_on = True
            self.async_set_updated_data(await self._async_update_data())

    async def async_next_melody(self) -> None:
        next_m = self._current_melody + 1
        if next_m > 9: next_m = 1
        await self.async_set_melody(next_m)

    async def async_shutdown(self) -> None:
        if self._client:
            await self._client.disconnect()