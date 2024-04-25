"""Base class for all eQ-3 entities."""


from homeassistant.helpers.entity import Entity

from .models import BS440Config


class BS440Entity(Entity):
    """Base class for all eQ-3 entities."""

    _attr_has_entity_name = True

    def __init__(self, bs440_config: BS440Config) -> None:
        """Initialize the bs440 entity."""

        self._bs440_config = bs440_config
