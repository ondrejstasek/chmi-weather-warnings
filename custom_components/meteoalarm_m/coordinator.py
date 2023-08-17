"""Coordinator"""

from datetime import *
from dateutil.parser import parse
import logging

import async_timeout

from homeassistant.components.sensor.SensorEntity import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from aiohttp import ClientConnectionError, ClientSession
from aiohttp.client_reqrep import ClientResponse

from .const import DOMAIN, CHMI_URL

_LOGGER = logging.getLogger(__name__)

class CHMICoordinator(DataUpdateCoordinator):
    """CHMI poll coordinator."""

    def __init__(self, hass):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="CHMI",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                resp: ClientResponse = await self.aiohttp_session.get(
                    url=CHMI_URL, ssl=False
                )
                resp_json = await resp.json(content_type=None)
                return resp_json
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

class CHMIEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        events = []
        for alert in self.coordinator.data["vystrahy"]:
            if 2102 not in alert["csuOrpKod"]:
                continue
            events.append(
                WeatherEvent(
                    name=alert["event"],
                    description=alert["description"],
                    severity=alert["stupenNebezpeci"],
                    start=parse(alert["onset"]),
                    end=parse(alert["expires"])
                )
            )

        self._attr_native_value = len(events)
        self._attr_extra_state_attributes = {"events": events}
        self.async_write_ha_state()

class WeatherEvent:
    def __init__(self, name, description, severity, start, end) -> None:
        self.start = start
        self.end = end
        self.name = name
        self.description = description
        self.severity = severity
