from homeassistant.components.button import ButtonEntity
from bleak import BleakClient

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    async_add_entities([
        PTBabyMusicButton(data["address"], data["char_uuid"], "cmd01", "Мелодія 1"),
        PTBabyMusicButton(data["address"], data["char_uuid"], "cmd02", "Мелодія 2"),
        PTBabyMusicButton(data["address"], data["char_uuid"], "cmd03", "Мелодія 3"),
    ])

class PTBabyMusicButton(ButtonEntity):
    def __init__(self, address, char_uuid, cmd, name):
        self._address = address
        self._char_uuid = char_uuid
        self._cmd = cmd
        self._attr_name = name

    async def async_press(self) -> None:
        async with BleakClient(self._address) as client:
            await client.write_gatt_char(self._char_uuid, self._cmd.encode('utf-8'))