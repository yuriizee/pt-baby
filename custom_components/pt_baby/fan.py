"""Fan platform for Baby Cradle (swing control)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .coordinator import BabyCradleCoordinator
from .entity import BabyCradleEntity

_LOGGER = logging.getLogger(__name__)

SPEED_RANGE = (1, 5)  # 5 швидкостей

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Baby Cradle fan."""
    coordinator: BabyCradleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BabyCradleSwingFan(coordinator)])

class BabyCradleSwingFan(BabyCradleEntity, FanEntity):
    """Representation of Baby Cradle swing as a fan."""

    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_speed_count = 5

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_swing"
        self._attr_name = "Колисання"
        self._attr_translation_key = "swing"

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        return self.coordinator.data.get("swing_speed", 0) > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        speed = self.coordinator.data.get("swing_speed", 0)
        if speed == 0:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        speed = int(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.coordinator.async_set_swing_speed(speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is None:
            percentage = 20  # Default to speed 1
        await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.async_set_swing_speed(0)