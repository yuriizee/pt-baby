"""Switch platform for Baby Cradle."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BabyCradleCoordinator
from .entity import BabyCradleEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Baby Cradle switches."""
    coordinator: BabyCradleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BabyCradlePowerSwitch(coordinator),
        BabyCradleInductionSwitch(coordinator),
    ])

class BabyCradlePowerSwitch(BabyCradleEntity, SwitchEntity):
    """Representation of Baby Cradle power switch."""

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_power"
        self._attr_name = "Живлення"
        self._attr_translation_key = "power"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data.get("is_on", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_turn_off()

class BabyCradleInductionSwitch(BabyCradleEntity, SwitchEntity):
    """Representation of Baby Cradle induction mode switch."""

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_induction"
        self._attr_name = "Індукційний режим"
        self._attr_translation_key = "induction_mode"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data.get("induction_mode", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_set_induction_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_set_induction_mode(False)