"""Models for bs440btsmart integration."""

from dataclasses import dataclass


from .const import (
    DEFAULT_CURRENT_TEMP_SELECTOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_TEMP_SELECTOR,
    CurrentTemperatureSelector,
    TargetTemperatureSelector,
)


@dataclass(slots=True)
class BS440Config:
    """Config for a single eQ-3 device."""

    mac_address: str
    current_temp_selector: CurrentTemperatureSelector = DEFAULT_CURRENT_TEMP_SELECTOR
    target_temp_selector: TargetTemperatureSelector = DEFAULT_TARGET_TEMP_SELECTOR
    external_temp_sensor: str = ""
    scan_interval: int = DEFAULT_SCAN_INTERVAL
    default_away_hours: float = 0 #DEFAULT_AWAY_HOURS
    default_away_temperature: float = 0 #DEFAULT_AWAY_TEMP


@dataclass(slots=True)
class Eq3ConfigEntryData:
    """Config entry for a single eQ-3 device."""

    bs440_config: BS440Config
    scale: float
