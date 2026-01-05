"""Media player platform for Baby Cradle melodies."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MELODIES
from .coordinator import BabyCradleCoordinator
from .entity import BabyCradleEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Baby Cradle media player."""
    coordinator: BabyCradleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BabyCradleMelodyPlayer(coordinator)])

class BabyCradleMelodyPlayer(BabyCradleEntity, MediaPlayerEntity):
    """Representation of Baby Cradle melody player."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_melody"
        self._attr_name = "Мелодії"
        self._attr_translation_key = "melody"

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the player."""
        if self.coordinator.data.get("melody_on"):
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def source(self) -> str:
        """Return the current melody."""
        melody = self.coordinator.data.get("current_melody", 1)
        return f"Мелодія {melody}"

    @property
    def source_list(self) -> list[str]:
        """Return list of available melodies."""
        return [f"Мелодія {i}" for i in MELODIES.keys()]

    async def async_turn_on(self) -> None:
        """Turn on the melody."""
        await self.coordinator.async_melody_on()

    async def async_turn_off(self) -> None:
        """Turn off the melody."""
        await self.coordinator.async_melody_off()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self.coordinator.async_next_melody()

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self.coordinator.async_previous_melody()

    async def async_select_source(self, source: str) -> None:
        """Select melody source."""
        # Extract melody number from "Мелодія X"
        try:
            melody_num = int(source.split()[-1])
            await self.coordinator.async_set_melody(melody_num)
        except (ValueError, IndexError):
            _LOGGER.error("Invalid melody source: %s", source)

    async def async_volume_up(self) -> None:
        """Turn volume up."""
        await self.coordinator.async_volume_up()

    async def async_volume_down(self) -> None:
        """Turn volume down."""
        await self.coordinator.async_volume_down()