"""Number platform for Baby Cradle timer."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
    """Set up the Baby Cradle number entities."""
    coordinator: PTBabyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PTBabyTimer(coordinator)])

class PTBabyTimer(PTBabyEntity, NumberEntity):
    """Representation of Baby Cradle timer."""

    _attr_native_min_value = 0
    _attr_native_max_value = 120  # 2 години
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: PTBabyCoordinator) -> None:
        """Initialize the timer."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_timer"
        self._attr_name = "Таймер"
        self._attr_translation_key = "timer"

    @property
    def native_value(self) -> float:
        """Return the current timer value."""
        return self.coordinator.data.get("timer", 0)

    async def async_set_native_value(self, value: float) -> None:
        """Set new timer value."""
        await self.coordinator.async_set_timer(int(value))