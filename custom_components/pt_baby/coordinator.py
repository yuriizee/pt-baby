"""DataUpdateCoordinator for Baby Cradle."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any
from time import monotonic

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
    WAKE_DELAY,
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

        self._notify_started = False
        self._last_wake: float | None = None

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

        # Спроба 2: Якщо не знайшли, шукаємо будь-який (connectable=False)
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
                max_attempts=3
            )
            _LOGGER.info("Connected to PT Baby Swing at %s", self.address)
            await self._maybe_start_notify()
        except Exception as err:
            self._client = None
            raise UpdateFailed(f"Connection failed: {err}") from err

    def _on_disconnected(self, client):
        """Callback при розриві з'єднання."""
        _LOGGER.info("Disconnected from PT Baby Swing")
        self._client = None
        self._is_on = False
        self.async_set_updated_data(self.data)

    async def _maybe_start_notify(self) -> None:
        """Start notify stream if characteristic is known."""
        if not self._client or not self.notify_char_uuid or self._notify_started:
            return

        try:
            await self._client.start_notify(
                self.notify_char_uuid, self._handle_notification
            )
            self._notify_started = True
            _LOGGER.debug(
                "Started notify on %s for %s",
                self.notify_char_uuid,
                self.address,
            )
        except Exception as err:
            # Не блокуюча помилка: повідомляємо, але продовжуємо роботу
            _LOGGER.debug("Notify unavailable on %s: %s", self.notify_char_uuid, err)

    def _handle_notification(self, sender: int, data: bytearray) -> None:
        """Log incoming notifications for debugging."""
        _LOGGER.debug("Notification from %s: %s", sender, data.hex())

    async def _write_command(self, command: str) -> None:
        """Low-level write helper."""
        if not self._client:
            raise UpdateFailed("Client is not connected")
        if not self.write_char_uuid:
            raise UpdateFailed("Write characteristic UUID is missing")

        cmd_bytes = command.encode("utf-8")
        await self._client.write_gatt_char(
            self.write_char_uuid,
            cmd_bytes,
            response=False,
        )
        _LOGGER.info("Sent command: %s", command)

    async def _wake_device(self) -> None:
        """Send wake-up before other commands."""
        # throttle wake-ups a little to avoid spamming
        now = monotonic()
        if self._last_wake and now - self._last_wake < 2:
            _LOGGER.debug("Wake skipped (recent wake %.2fs ago)", now - self._last_wake)
            return

        _LOGGER.debug("Sending wake command %s", CMD_POWER_ON)
        await self._write_command(CMD_POWER_ON)
        self._last_wake = now
        self._is_on = True
        await asyncio.sleep(WAKE_DELAY)

    async def async_send_command(self, command: str, *, ensure_wake: bool = True) -> None:
        """Public command sender with wake/lock/connection handling."""
        if not command:
            _LOGGER.debug("Empty command ignored")
            return

        async with self._lock:
            try:
                await self._ensure_connected()

                if ensure_wake and command != CMD_POWER_ON:
                    await self._wake_device()

                await self._write_command(command)
            except Exception as err:
                _LOGGER.error("Error sending %s: %s", command, err)
                if self._client:
                    await self._client.disconnect()
                self._client = None
                raise UpdateFailed(f"Send failed: {err}") from err

    # --- КЕРУВАННЯ ---

    async def async_turn_on(self) -> None:
        """Увімкнення."""
        await self.async_send_command(CMD_POWER_ON, ensure_wake=False)
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

        cmd = SWING_SPEEDS.get(speed)
        if not cmd:
            _LOGGER.error("Unknown swing speed %s", speed)
            return

        _LOGGER.debug("Setting swing speed %s via %s", speed, cmd)
        await self.async_send_command(cmd)
        self._swing_speed = speed
        self._is_on = True
        self.async_set_updated_data(await self._async_update_data())

    # --- МЕЛОДІЇ ---

    async def async_set_melody(self, melody: int) -> None:
        if melody in MELODIES:
            await self.async_send_command(MELODIES[melody])
            self._current_melody = melody
            self._melody_on = True
            self.async_set_updated_data(await self._async_update_data())

    async def async_melody_on(self) -> None:
        await self.async_set_melody(self._current_melody)

    async def async_melody_off(self) -> None:
        # Якщо відома команда вимкнення музики - розкоментуйте
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

    # --- ДОДАТКОВІ ФУНКЦІЇ (які викликали помилку) ---

    async def async_set_induction_mode(self, enabled: bool) -> None:
        """Вмикання/вимикання індукційного режиму."""
        # Тут можна додати команду, якщо вона відома
        self._induction_mode = enabled
        self.async_set_updated_data(await self._async_update_data())

    async def async_set_timer(self, minutes: int) -> None:
        """Встановлення таймера."""
        self._timer = minutes
        self.async_set_updated_data(await self._async_update_data())

    async def async_volume_up(self) -> None:
        """Збільшення гучності."""
        self._volume = min(100, self._volume + 10)
        # Додати команду гучності
        self.async_set_updated_data(await self._async_update_data())

    async def async_volume_down(self) -> None:
        """Зменшення гучності."""
        self._volume = max(0, self._volume - 10)
        # Додати команду гучності
        self.async_set_updated_data(await self._async_update_data())

    async def async_shutdown(self) -> None:
        if self._client:
            await self._client.disconnect()