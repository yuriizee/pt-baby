"""Base entity for PT Baby Swing."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_NAME
# ВИПРАВЛЕННЯ: Імпортуємо правильний клас PTBabyCoordinator
from .coordinator import PTBabyCoordinator

class PTBabyEntity(CoordinatorEntity[PTBabyCoordinator]):
    """Base class for PT Baby Swing entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PTBabyCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        # Отримуємо ім'я пристрою з конфігурації або ставимо дефолтне
        device_name = coordinator.entry.data.get(CONF_DEVICE_NAME, "PT Baby Swing")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=device_name,
            manufacturer="PT Baby",
            model="Bluetooth Swing",
            sw_version="1.0",
        )