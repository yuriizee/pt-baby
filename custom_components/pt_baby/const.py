"""Constants for the Baby Cradle Bluetooth integration."""
from homeassistant.const import Platform

DOMAIN = "pt_baby"

# Bluetooth service UUID (потрібно замінити на реальний UUID вашого пристрою)
# Основний сервіс (Main Service)
SERVICE_UUID = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"

# Характеристика для запису команд (Write) - Handle 0x0003
# Сюди шлемо cmd38, cmd11 і т.д.
WRITE_CHARACTERISTIC_UUID = "7772e5db-3868-4112-a1a9-f2669d106bf3"

# Характеристика для отримання статусу (Notify)
# Зазвичай це вона шле відповіді, якщо підписатися
NOTIFY_CHARACTERISTIC_UUID = "49535343-8841-43f4-a8d4-ecbe34729bb3"

# Команди
CMD_POWER_ON = "cmd38"
CMD_MELODY_ON = "cmd39"

# Швидкості колисання
SWING_SPEEDS = {
    1: "cmd10",
    2: "cmd11",
    3: "cmd12",
    4: "cmd13",
    5: "cmd14",
}

# Мелодії
MELODIES = {
    1: "cmd01",
    2: "cmd02",
    3: "cmd03",
    4: "cmd04",
    5: "cmd05",
    6: "cmd06",
    7: "cmd07",
    8: "cmd08",
    9: "cmd09",
}

# Налаштування
CONF_MAC_ADDRESS = "mac_address"
CONF_DEVICE_NAME = "device_name"

# Атрибути
ATTR_SWING_SPEED = "swing_speed"
ATTR_MELODY = "melody"
ATTR_TIMER = "timer"
ATTR_INDUCTION_MODE = "induction_mode"