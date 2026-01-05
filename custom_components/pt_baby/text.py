"""Debug text input for PT Baby Swing."""
from __future__ import annotations

import logging
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PTBabyCoordinator
from .entity import PTBabyEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the debug text input."""
    coordinator: PTBabyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PTBabyDebugInput(coordinator)])

class PTBabyDebugInput(PTBabyEntity, TextEntity):
    """Allows sending raw commands to the swing."""

    def __init__(self, coordinator: PTBabyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Debug Command"
        self._attr_unique_id = f"{coordinator.address}_debug_cmd"
        self._attr_icon = "mdi:console-line"
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """Send the text command to the device."""
        command = value.strip()

        if not command:
            return

        _LOGGER.info(f"Sending raw debug command: {command}")

        # Використовуємо метод координатора замість створення нового підключення
        try:
            await self.coordinator.async_send_command(command)
        except Exception as e:
             _LOGGER.error("Failed to send command via coordinator: %s", e)

        # Оновлюємо значення в полі
        self._attr_native_value = value
        self.async_write_ha_state()