"""Config flow for Baby Cradle Bluetooth integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
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
    LOCAL_NAME_PREFIX,
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
        self._cached_gatt: tuple[str, str, str | None] | None = None

    def _is_pt_baby(self, name: str | None) -> bool:
        """Check if bluetooth name matches PT-BABY prefix."""
        if not name:
            return False
        return name.upper().startswith(LOCAL_NAME_PREFIX)

    async def _detect_gatt(
        self,
        address: str,
    ) -> tuple[str, str, str | None]:
        """Try to autodetect service and characteristics."""
        device = async_ble_device_from_address(self.hass, address, connectable=True)
        if not device:
            raise ValueError("Device not available for GATT inspection")

        _LOGGER.debug("Connecting to %s to autodetect services", address)
        client = await establish_connection(
            BleakClientWithServiceCache, device, name=address
        )

        service_uuid: str | None = None
        write_char: str | None = None
        notify_char: str | None = None

        try:
            for service in client.services:
                candidate_write: str | None = None
                candidate_notify: str | None = None
                for char in service.characteristics:
                    props = set(char.properties)
                    uuid = char.uuid.lower()

                    if "write-without-response" in props or "write" in props:
                        candidate_write = candidate_write or uuid
                    if "notify" in props or "indicate" in props:
                        candidate_notify = candidate_notify or uuid

                if candidate_write:
                    service_uuid = service.uuid.lower()
                    write_char = candidate_write
                    notify_char = candidate_notify
                    _LOGGER.debug(
                        "Selected service %s write %s notify %s",
                        service_uuid,
                        write_char,
                        notify_char,
                    )
                    break
        finally:
            await client.disconnect()

        if not service_uuid or not write_char:
            raise ValueError("No writable characteristic found")

        return service_uuid, write_char, notify_char

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        if not self._is_pt_baby(discovery_info.name):
            return self.async_abort(reason="not_pt_baby_device")

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
            if not self._is_pt_baby(discovery_info.name):
                continue
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

        # Спроба автоматичного визначення
        try:
            self._cached_gatt = await self._detect_gatt(self._discovered_device_address)
            service_uuid, write_char, notify_char = self._cached_gatt
            _LOGGER.info(
                "Auto-detected GATT for %s: service=%s write=%s notify=%s",
                self._discovered_device_address,
                service_uuid,
                write_char,
                notify_char,
            )
            return self.async_create_entry(
                title=self._discovered_device_name or "PT Baby Swing",
                data={
                    CONF_MAC_ADDRESS: self._discovered_device_address,
                    CONF_DEVICE_NAME: self._discovered_device_name,
                    CONF_SERVICE_UUID: service_uuid,
                    CONF_WRITE_CHAR_UUID: write_char,
                    CONF_NOTIFY_CHAR_UUID: notify_char,
                },
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Autodetect failed, falling back to manual: %s", err)

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