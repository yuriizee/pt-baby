"""Debug text input for PT Baby Swing."""
from __future__ import annotations

import logging
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from bleak import BleakClient

from .const import DOMAIN
from .coordinator import BabyCradleCoordinator
from .entity import BabyCradleEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the debug text input."""
    coordinator: BabyCradleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PTBabyDebugInput(coordinator)])

class PTBabyDebugInput(BabyCradleEntity, TextEntity):
    """Allows sending raw commands to the swing."""

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Debug Command"
        self._attr_unique_id = f"{coordinator.address}_debug_cmd"
        self._attr_icon = "mdi:console-line"
        self._attr_native_value = "" # Початкове значення пусте

    async def async_set_value(self, value: str) -> None:
        """Send the text command to the device."""
        command = value.strip()

        if not command:
            return

        _LOGGER.info(f"Sending raw debug command: {command}")

        # Беремо UUID з координатора або entry data
        # Припускаємо, що він збережений в coordinator.config_entry.data
        char_uuid = self.coordinator.config_entry.data["char_uuid"]
        address = self.coordinator.address

        try:
            async with BleakClient(address, timeout=10.0) as client:
                await client.write_gatt_char(char_uuid, command.encode('utf-8'))
                _LOGGER.info(f"Command {command} sent successfully")
        except Exception as e:
            _LOGGER.error(f"Failed to send debug command {command}: {e}")

        # Оновлюємо значення в полі (щоб ви бачили, що відправили останнім)
        self._attr_native_value = value
        self.async_write_ha_state()