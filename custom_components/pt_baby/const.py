"""Constants for the Baby Cradle Bluetooth integration."""
from homeassistant.const import Platform

DOMAIN = "pt_baby"

# Bluetooth UUID constants
CONF_SERVICE_UUID = "service_uuid"
CONF_WRITE_CHAR_UUID = "write_char_uuid"
CONF_NOTIFY_CHAR_UUID = "notify_char_uuid"

# Команди керування
CMD_POWER_ON = "cmd38"   # Пробудження / Ввімкнення
CMD_POWER_OFF = "cmd39"  # Повне вимкнення (Stop)

# Швидкості колисання (cmd11 - cmd15)
SWING_SPEEDS = {
    1: "cmd11",
    2: "cmd12",
    3: "cmd13",
    4: "cmd14",
    5: "cmd15",
}

# Мелодії (cmd01 - cmd09)
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

CMD_MELODY_OFF = "cmd00" # Припускаємо команду зупинки музики, якщо відома

# Налаштування
CONF_MAC_ADDRESS = "mac_address"
CONF_DEVICE_NAME = "device_name"

# Атрибути
ATTR_SWING_SPEED = "swing_speed"
ATTR_MELODY = "melody"
ATTR_TIMER = "timer"
ATTR_INDUCTION_MODE = "induction_mode"