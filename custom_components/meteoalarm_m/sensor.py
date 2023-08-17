from .const import *
from .coordinator import *

async def async_setup_entry(hass, entry, async_add_entities):
    """Config entry"""
    coordinator = CHMICoordinator(hass)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        CHMIEntity(coordinator)
    )
