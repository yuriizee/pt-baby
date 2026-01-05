"""Base entity for Baby Cradle."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_NAME
from .coordinator import BabyCradleCoordinator

class PTBabyEntity(CoordinatorEntity[PTBabyCoordinator]):
    """Base class for Baby Cradle entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PTBabyCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.entry.data.get(CONF_DEVICE_NAME, "PT Baby Swing"),
            manufacturer="PT Baby",
            model="Bluetooth Swing",
            sw_version="1.0",
        )