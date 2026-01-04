from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Налаштування пристрою з меню налаштувань."""
    hass.data.setdefault("pt_baby", {})
    hass.data["pt_baby"][entry.entry_id] = entry.data["address"]

    # Реєструємо платформу fan (вентилятор)
    await hass.config_entries.async_forward_entry_setups(entry, ["fan"])
    return True