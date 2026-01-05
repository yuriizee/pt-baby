class PTBabyFan(BabyCradleEntity, FanEntity):
    """Representation of Baby Cradle swing as a fan."""

    # ВИПРАВЛЕННЯ: Додаємо TURN_ON та TURN_OFF до списку можливостей
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED |
        FanEntityFeature.TURN_ON |
        FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 5

    def __init__(self, coordinator: BabyCradleCoordinator) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_swing"
        self._attr_name = "Колисання"
        self._attr_translation_key = "swing"

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        # Перевірка на None важлива, якщо дані ще не прийшли
        return self.coordinator.data.get("swing_speed", 0) > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        speed = self.coordinator.data.get("swing_speed", 0)
        if speed == 0:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        speed = int(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.coordinator.async_set_swing_speed(speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is None:
            percentage = 20  # Default to speed 1 (20%)
        await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.async_set_swing_speed(0)