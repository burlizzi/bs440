"""Support for bs440 devices."""

import asyncio
from http.client import REQUEST_TIMEOUT
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_SCALE_CONNECTED, SIGNAL_SCALE_DISCONNECTED
from .models import BS440Config, BS440ConfigEntryData

PLATFORMS = [
    Platform.CLIMATE,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle config entry setup."""

    mac_address: str | None = entry.unique_id

    if TYPE_CHECKING:
        assert mac_address is not None

    bs440_config = BS440Config(
        mac_address=mac_address,
    )

    device = bluetooth.async_ble_device_from_address(
        hass, mac_address.upper(), connectable=True
    )

    if device is None:
        raise ConfigEntryNotReady(
            f"[{bs440_config.mac_address}] Device could not be found"
        )

    #thermostat = Thermostat(
    #    thermostat_config=ThermostatConfig(
    #        mac_address=mac_address,
    #    ),
    #    ble_device=device,
    #)
    conn: BleakClient = BleakClient(
            bs440_config.mac_address,
            #disconnected_callback=lambda client: self._on_connection_changed(False),
            timeout=REQUEST_TIMEOUT,
        )

    bs440_config_entry = BS440ConfigEntryData(bs440_config=bs440_config, conn=conn)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = bs440_config_entry

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_create_background_task(
        hass, _async_run_thermostat(hass, entry), entry.entry_id
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle config entry unload."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        bs440_config_entry: BS440ConfigEntryData = hass.data[DOMAIN].pop(entry.entry_id)
        await bs440_config_entry.thermostat.async_disconnect()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry update."""

    await hass.config_entries.async_reload(entry.entry_id)


async def _async_run_thermostat(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Run the thermostat."""

    bs440_config_entry: BS440ConfigEntryData = hass.data[DOMAIN][entry.entry_id]
    mac_address = bs440_config_entry.bs440_config.mac_address
    conn = bs440_config_entry.conn
    scan_interval = bs440_config_entry.bs440_config.scan_interval

    await _async_reconnect_thermostat(hass, entry)

    while True:
        try:
            await conn.connect()
        except Exception as e:
            if not conn.is_connected:
                _LOGGER.error(
                    "[%s] BS440 device disconnected",
                    mac_address,
                )
                async_dispatcher_send(
                    hass,
                    f"{SIGNAL_SCALE_DISCONNECTED}_{mac_address}",
                )
                await _async_reconnect_thermostat(hass, entry)
                continue

            _LOGGER.error(
                "[%s] Error updating BS440 device: %s",
                mac_address,
                e,
            )

        await asyncio.sleep(scan_interval)


async def _async_reconnect_thermostat(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reconnect the thermostat."""

    bs440_config_entry: BS440ConfigEntryData = hass.data[DOMAIN][entry.entry_id]
    conn = bs440_config_entry.conn
    mac_address = bs440_config_entry.bs440_config.mac_address
    scan_interval = bs440_config_entry.bs440_config.scan_interval

    while True:
        try:
            conn.connect()
        except Exception:
            await asyncio.sleep(scan_interval)
            continue

        _LOGGER.debug(
            "[%s] BS440 device connected",
            mac_address,
        )

        async_dispatcher_send(
            hass,
            f"{SIGNAL_SCALE_CONNECTED}_{mac_address}",
        )

        return
