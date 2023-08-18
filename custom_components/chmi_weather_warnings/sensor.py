"""Support for the CHMI service."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from dateutil.parser import parse
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_CUBIC_METER,
    PERCENTAGE,
    UV_INDEX,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client_exceptions import ClientConnectorError
import async_timeout
from datetime import timedelta
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv

import logging
_LOGGER = logging.getLogger(__name__)

from .const import CHMI_URL, DOMAIN, ORP_ID, INTERVAL

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ORP_ID): cv.positive_int,
        vol.Optional(INTERVAL, default=60): cv.positive_int
    }
)

async def async_setup_platform(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Add CHMI entities from a config_entry."""

    websession = async_get_clientsession(hass)

    coordinator = CHMIDataUpdateCoordinator(
        hass, websession, entry
    )
    await coordinator.async_config_entry_first_refresh()

    description = SensorEntityDescription(
        key="{DOMAIN}.events",
        name="Weather Warning Events",
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT
    )

    sensors = [
        CHMISensor(coordinator, description, entry[ORP_ID])
    ]

    add_entities(sensors)

class CHMIDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching CHMI data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        entry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.session = session
        self.device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="ČHMÚ",
            identifiers=DOMAIN,
            name="ČHMÚ",
        )

        update_interval = timedelta(minutes=entry[INTERVAL])
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            async with async_timeout.timeout(10):
                resp: ClientResponse = await self.session.get(
                    url=CHMI_URL, ssl=False
                )
                resp_json = await resp.json(content_type=None)
                return resp_json

        except Exception as e:
            raise UpdateFailed(f"Error communicating with API: {e}")

class CHMISensor(
    CoordinatorEntity[CHMIDataUpdateCoordinator], SensorEntity
):
    """Define an CHMI entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CHMIDataUpdateCoordinator,
        description: SensorEntityDescription,
        orpId: str
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self.orpId = orpId
        self._sensor_data = self.filterData()
        self._attr_unique_id = (
            f"{DOMAIN}-{orpId}".lower()
        )
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state."""
        return len(self._sensor_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {"events": self._sensor_data}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._sensor_data = self.filterData()
        self.async_write_ha_state()

    def filterData(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return []

        events = []
        for alert in self.coordinator.data["vystrahy"]:
            if self.orpId not in alert["csuOrpKod"]:
                continue

            events.append(
                {
                    "name": alert["event"],
                    "description": alert["description"],
                    "severity": alert["stupenNebezpeci"],
                    "start": parse(alert["onset"]),
                    "end": parse(alert["expires"]) if alert["expires"] is not None else None
                }
            )
        return events
