"""Config flow for Baby Cradle Bluetooth integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from bleak import BleakError
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
    async_ble_device_from_address,
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
        self._discovered_device_address: str | None = None
        self._discovered_device_name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self._discovered_device_address = discovery_info.address
        self._discovered_device_name = discovery_info.name
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            # Переходимо до вибору UUID
            return await self.async_step_uuid_selection()

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or self._discovery_info.address
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Крок 1: Вибір пристрою зі списку."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            self._discovered_device_address = address
            # Пробуємо знайти ім'я, якщо є
            device = async_ble_device_from_address(self.hass, address)
            self._discovered_device_name = device.name if device else address

            # Переходимо до кроку вибору UUID
            return await self.async_step_uuid_selection()

        # Скануємо пристрої
        current_addresses = self._async_current_ids()
        discovered_devices = {}

        for discovery_info in async_discovered_service_info(self.hass, False):
            if discovery_info.address in current_addresses:
                continue
            # Показуємо всі пристрої, або фільтруємо по імені якщо хочете
            name = discovery_info.name or "Unknown"
            discovered_devices[discovery_info.address] = f"{name} ({discovery_info.address})"

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(discovered_devices),
                }
            ),
        )

    async def async_step_uuid_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Крок 2: Вибір UUID зі списку доступних на пристрої."""
        errors = {}

        if user_input is not None:
            # Користувач вибрав UUID, створюємо інтеграцію
            return self.async_create_entry(
                title=self._discovered_device_name or "PT Baby Swing",
                data={
                    CONF_MAC_ADDRESS: self._discovered_device_address,
                    CONF_DEVICE_NAME: self._discovered_device_name,
                    CONF_SERVICE_UUID: user_input[CONF_SERVICE_UUID],
                    CONF_WRITE_CHAR_UUID: user_input[CONF_WRITE_CHAR_UUID],
                    CONF_NOTIFY_CHAR_UUID: user_input[CONF_NOTIFY_CHAR_UUID],
                },
            )

        # Підключаємось до пристрою, щоб отримати список UUID
        address = self._discovered_device_address
        device = async_ble_device_from_address(self.hass, address, connectable=True)

        if not device:
            return self.async_abort(reason="cannot_connect")

        # Списки для Dropdown меню
        services_list = {}
        write_chars_list = {}
        notify_chars_list = {}

        try:
            _LOGGER.debug("Connecting to %s to fetch UUIDs", address)
            client = await establish_connection(
                BleakClientWithServiceCache, device, name=address
            )

            try:
                # Перебираємо всі сервіси та характеристики
                for service in client.services:
                    srv_uuid = service.uuid.lower()
                    services_list[srv_uuid] = f"{srv_uuid} ({service.description or 'Service'})"

                    for char in service.characteristics:
                        uuid = char.uuid.lower()
                        props = ",".join(char.properties)
                        label = f"{uuid} [{props}]"

                        # Розподіляємо по списках залежно від властивостей
                        if "write" in char.properties or "write-without-response" in char.properties:
                            write_chars_list[uuid] = label

                        if "notify" in char.properties or "indicate" in char.properties:
                            notify_chars_list[uuid] = label

                        # Також додаємо у списки "все підряд", якщо властивості не чіткі
                        # (опціонально, але краще мати вибір)

            finally:
                await client.disconnect()

        except Exception as err:
            _LOGGER.error("Error fetching services: %s", err)
            errors["base"] = "cannot_connect"
            # Якщо не вдалося підключитися, дамо можливість ввести вручну (текстові поля)
            services_list = {}
            write_chars_list = {}
            notify_chars_list = {}

        # Формуємо схему. Якщо списки пусті - Text Input, якщо є - Select
        schema_dict = {}

        # 1. Service UUID
        if services_list:
            schema_dict[vol.Required(CONF_SERVICE_UUID)] = vol.In(services_list)
        else:
            schema_dict[vol.Required(CONF_SERVICE_UUID)] = str

        # 2. Write Characteristic UUID
        if write_chars_list:
            schema_dict[vol.Required(CONF_WRITE_CHAR_UUID)] = vol.In(write_chars_list)
        else:
            schema_dict[vol.Required(CONF_WRITE_CHAR_UUID)] = str

        # 3. Notify Characteristic UUID
        if notify_chars_list:
            schema_dict[vol.Required(CONF_NOTIFY_CHAR_UUID)] = vol.In(notify_chars_list)
        else:
            schema_dict[vol.Required(CONF_NOTIFY_CHAR_UUID)] = str

        return self.async_show_form(
            step_id="uuid_selection",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "device_name": self._discovered_device_name
            }
        )