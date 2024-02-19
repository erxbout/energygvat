from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

import async_timeout
import requests

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, StateType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

apiEndpoint = "https://energie.gv.at/api/gd/store/renewable_electricity_now_bars.json"
labels = {
    "Wasser",
    "Sonne",
    "Wind",
    "Biomasse",
    "Erdgas",
    "Nettoimporte",
    "Sonstige",
    "Nichtvorhanden",
}


async def async_setup_platform(
    hass: HomeAssistant, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(EnergyProductionSensor(), True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = MyCoordinator(hass, apiEndpoint, config_entry.data["PollingInterval"])

    await coordinator.async_config_entry_first_refresh()

    entities = []

    for x in config_entry.data:
        for label in labels:
            if label == x and config_entry.data[x] is True:
                entities.append(EnergyProductionSensor(coordinator, label))

    async_add_entities(entities)


class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, apiEndpoint, pollingInterval):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            # Name of the data. For logging purposes.
            _LOGGER,
            name="My sensor",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=pollingInterval * 60),
        )
        self.apiEndpoint = apiEndpoint
        self.hass = hass

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                listening_idx = set(self.async_contexts())
                return await self.hass.async_add_executor_job(self.update)
        # except ApiAuthError as err:
        # Raising ConfigEntryAuthFailed will cancel future updates
        # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        # raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        # raise UpdateFailed(f"Error communicating with API: {err}")
        finally:
            print("finally hi")

    def update(self) -> None:
        resp = requests.get(self.apiEndpoint)
        resp_dict = resp.json()

        return resp_dict


class EnergyProductionSensor(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    timestamp: StateType | date | datetime | Decimal = None

    def __init__(self, coordinator, label):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=label)
        self._name = "EnergyGridAT_" + label
        self._label = label
        self._state = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updateDone = False

        for x in self.coordinator.data:
            if x["label"] == self._label:
                updateDone = True
                self._state = round(x["percentage"], 2)
                self.timestamp = x["date"]

        if updateDone == False:
            self._state = 0

        print(self._state)
        print(self._label)
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the name of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the name of the sensor."""
        result = {"date": self.timestamp}

        return result

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def suggested_display_precision(self):
        return 2
