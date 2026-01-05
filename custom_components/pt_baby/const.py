"""Constants for the Baby Cradle Bluetooth integration."""
from homeassistant.const import Platform

DOMAIN = "pt_baby"

# UUID (ключі для конфігурації)
CONF_SERVICE_UUID = "service_uuid"
CONF_WRITE_CHAR_UUID = "write_char_uuid"
CONF_NOTIFY_CHAR_UUID = "notify_char_uuid"
CONF_MAC_ADDRESS = "mac_address"
CONF_DEVICE_NAME = "device_name"

# --- КОМАНДИ ---
# Важливо: cmd38 - це пробудження. Без нього нічого не працює.
CMD_POWER_ON = "cmd38"
CMD_POWER_OFF = "cmd39"

# Швидкості (виправлено згідно вашого опису: 1 -> cmd11)
SWING_SPEEDS = {
    1: "cmd11",
    2: "cmd12",
    3: "cmd13",
    4: "cmd14",
    5: "cmd15",
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

CMD_MELODY_OFF = "cmd00" # Команда зупинки музики (якщо є)

# Атрибути для HA
ATTR_SWING_SPEED = "swing_speed"
ATTR_MELODY = "melody"
ATTR_TIMER = "timer"
ATTR_INDUCTION_MODE = "induction_mode"