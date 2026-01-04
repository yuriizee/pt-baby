from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Запуск інтеграції після вибору в меню."""
    hass.data.setdefault(DOMAIN, {})
    # Передаємо адресу пристрою далі в fan.py
    await hass.config_entries.async_forward_entry_setups(entry, ["fan"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Вивантаження інтеграції."""
    return await hass.config_entries.async_unload_platforms(entry, ["fan"])