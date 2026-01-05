from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .const import DOMAIN

# Список усіх платформ, які ми тепер використовуємо
PLATFORMS = [Platform.FAN, Platform.SELECT, Platform.NUMBER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Запуск інтеграції після вибору в меню."""
    hass.data.setdefault(DOMAIN, {})

    # Завантажуємо всі вказані платформи
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Вивантаження інтеграції."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)