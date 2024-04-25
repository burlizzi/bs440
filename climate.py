"""Platform for eQ-3 climate entities."""

from http.client import REQUEST_TIMEOUT
import logging
from typing import Any


from bleak import BleakClient
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)

from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
    async_get,
    format_mac,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    DEVICE_MODEL,
    DOMAIN,
    MANUFACTURER,
    SIGNAL_SCALE_CONNECTED,
    SIGNAL_SCALE_DISCONNECTED,
    Preset,
)
from .entity import BS440Entity
from .models import BS440Config, BS440ConfigEntryData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Handle config entry setup."""

    bs440_config_entry: BS440ConfigEntryData = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [BS440Scale(bs440_config_entry.bs440_config, bs440_config_entry.scale)],
    )


class BS440Scale(BS440Entity, SensorEntity):
    """Climate entity to represent a BS440 thermostat."""

    _attr_name = None
    _attr_translation_key = "real_time_weight"
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT

    _attr_precision = PRECISION_HALVES
    _attr_preset_modes = list(Preset)
    _attr_should_poll = False
    _attr_available = False
    _attr_preset_mode: str | None = None
    _target_temperature: float | None = None

    def __init__(self, bs440_config: BS440Config, scale: float) -> None:
        """Initialize the climate entity."""

        super().__init__(bs440_config)
        self._attr_unique_id = format_mac(bs440_config.mac_address)
        self._attr_device_info = DeviceInfo(
            name=slugify(self._bs440_config.mac_address),
            manufacturer=MANUFACTURER,
            model=DEVICE_MODEL,
            connections={(CONNECTION_BLUETOOTH, self._bs440_config.mac_address)},
        )
        


    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""

        self._thermostat.register_update_callback(self._async_on_updated)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_SCALE_DISCONNECTED}_{self._bs440_config.mac_address}",
                self._async_on_disconnected,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_SCALE_CONNECTED}_{self._bs440_config.mac_address}",
                self._async_on_connected,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""

        self._thermostat.unregister_update_callback(self._async_on_updated)

    @callback
    def _async_on_disconnected(self) -> None:
        self._attr_available = False
        self.async_write_ha_state()

    @callback
    def _async_on_connected(self) -> None:
        self._attr_available = True
        self.async_write_ha_state()

    @callback
    def _async_on_updated(self) -> None:
        """Handle updated data from the thermostat."""

        if self._thermostat.status is not None:
            self._async_on_status_updated()

        if self._thermostat.device_data is not None:
            self._async_on_device_updated()

        self.async_write_ha_state()

    @callback
    def _async_on_status_updated(self) -> None:
        """Handle updated status from the thermostat."""


    @callback
    def _async_on_device_updated(self) -> None:
        """Handle updated device data from the thermostat."""

        device_registry = async_get(self.hass)
        if device := device_registry.async_get_device(
            connections={(CONNECTION_BLUETOOTH, self._bs440_config.mac_address)},
        ):
            device_registry.async_update_device(
                device.id,
                sw_version=self._thermostat.device_data.firmware_version,
                serial_number=self._thermostat.device_data.device_serial.value,
            )

    @property
    def suggested_unit_of_measurement(self) -> str | None:
        """Set the suggested unit based on the unit system."""
        if self.hass.config.units is US_CUSTOMARY_SYSTEM:
            return UnitOfMass.POUNDS

        return UnitOfMass.KILOGRAMS
