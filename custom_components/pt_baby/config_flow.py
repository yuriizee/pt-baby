"""Config flow for Baby Cradle Bluetooth integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from bleak import BleakScanner, BleakClient

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_DEVICE_NAME,
    CONF_SERVICE_UUID,
    CONF_WRITE_CHAR_UUID,
    CONF_NOTIFY_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)

class PTBabyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Baby Cradle."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._device_services: dict[str, Any] = {}

    async def _discover_device_services(self, address: str) -> dict[str, str] | None:
        """Discover services and characteristics of the device."""
        try:
            async with BleakClient(address) as client:
                services = {}

                # Отримуємо всі сервіси
                for service in client.services:
                    service_uuid = service.uuid.lower()
                    _LOGGER.debug("Found service: %s", service_uuid)

                    write_char = None
                    notify_char = None

                    # Шукаємо характеристики для запису та нотифікацій
                    for char in service.characteristics:
                        char_uuid = char.uuid.lower()
                        _LOGGER.debug("  Characteristic: %s, properties: %s", char_uuid, char.properties)

                        # Шукаємо характеристику для запису
                        if "write" in char.properties or "write-without-response" in char.properties:
                            if write_char is None:
                                write_char = char_uuid

                        # Шукаємо характеристику для нотифікацій
                        if "notify" in char.properties or "indicate" in char.properties:
                            if notify_char is None:
                                notify_char = char_uuid

                    # Якщо знайшли обидві характеристики в одному сервісі
                    if write_char and notify_char:
                        services = {
                            CONF_SERVICE_UUID: service_uuid,
                            CONF_WRITE_CHAR_UUID: write_char,
                            CONF_NOTIFY_CHAR_UUID: notify_char,
                        }
                        _LOGGER.info("Found suitable service: %s with write: %s and notify: %s",
                                   service_uuid, write_char, notify_char)
                        return services

                # Якщо не знайшли в одному сервісі, шукаємо окремо
                if not services:
                    write_char = None
                    notify_char = None
                    first_service = None

                    for service in client.services:
                        if first_service is None:
                            first_service = service.uuid.lower()

                        for char in service.characteristics:
                            if write_char is None and ("write" in char.properties or "write-without-response" in char.properties):
                                write_char = char.uuid.lower()
                            if notify_char is None and ("notify" in char.properties or "indicate" in char.properties):
                                notify_char = char.uuid.lower()

                    if write_char and notify_char and first_service:
                        services = {
                            CONF_SERVICE_UUID: first_service,
                            CONF_WRITE_CHAR_UUID: write_char,
                            CONF_NOTIFY_CHAR_UUID: notify_char,
                        }
                        _LOGGER.info("Found characteristics across services: write: %s, notify: %s",
                                   write_char, notify_char)
                        return services

                _LOGGER.warning("Could not find suitable service/characteristics for device %s", address)
                return None

        except Exception as err:
            _LOGGER.error("Error discovering device services: %s", err)
            return None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None
        discovery_info = self._discovery_info

        if user_input is not None:
            # Виявляємо сервіси перед створенням entry
            services = await self._discover_device_services(discovery_info.address)

            if not services:
                return self.async_abort(reason="cannot_discover_services")

            return self.async_create_entry(
                title=discovery_info.name or "PT Baby Swing",
                data={
                    CONF_MAC_ADDRESS: discovery_info.address,
                    CONF_DEVICE_NAME: discovery_info.name,
                    **services,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": discovery_info.name or discovery_info.address
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initiated flow."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            # Виявляємо сервіси
            services = await self._discover_device_services(address)

            if not services:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_ADDRESS): vol.In(
                                {
                                    addr: f"{info.name} ({addr})"
                                    for addr, info in self._discovered_devices.items()
                                }
                            ),
                        }
                    ),
                    errors={"base": "cannot_discover_services"},
                )

            device_info = self._discovered_devices.get(address)

            return self.async_create_entry(
                title=device_info.name if device_info else "PT Baby Swing",
                data={
                    CONF_MAC_ADDRESS: address,
                    CONF_DEVICE_NAME: device_info.name if device_info else "PT Baby Swing",
                    **services,
                },
            )

        current_addresses = self._async_current_ids()

        for discovery_info in async_discovered_service_info(self.hass, False):
            if (
                discovery_info.address in current_addresses
                or discovery_info.address in self._discovered_devices
            ):
                continue

            # Фільтр для пошуку пристрою PT Baby
            if discovery_info.name and "pt" in discovery_info.name.lower():
                self._discovered_devices[discovery_info.address] = discovery_info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{info.name} ({address})"
                            for address, info in self._discovered_devices.items()
                        }
                    ),
                }
            ),
        )