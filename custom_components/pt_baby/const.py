"""Constants for the Baby Cradle Bluetooth integration."""
from homeassistant.const import Platform

DOMAIN = "pt_baby"

# Bluetooth UUID constants
CONF_SERVICE_UUID = "service_uuid"
CONF_WRITE_CHAR_UUID = "write_char_uuid"
CONF_NOTIFY_CHAR_UUID = "notify_char_uuid"

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