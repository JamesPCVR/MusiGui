import os
import json
import typing

class Config:
    """Base class for the configuration managers."""
    
    _configdir = "config\\empty.json"
    config = {}

    def __init__(self) -> None:
        """
        Import configuration from the config json file if it exists,
        otherwise create one.
        """
        if os.path.exists(os.path.abspath(self._configdir)):
            self.load()

        else:
            direc = self._configdir.split('\\', maxsplit=1)[0]
            if not os.path.exists(direc):
                os.makedirs(direc)

            self.default()
            self.save()

    def default(self) -> None:
        """Empty default declaration."""
        self.config = {}

    def load(self) -> None:
        """Import configuration from the config json file."""
        with open(self._configdir, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.config = data

    def save(self) -> None:
        """Export current configuration to the config json file."""
        with open(self._configdir, "w+", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get_config(self) -> dict[str,typing.Any]:
        """Get the currently used configuration."""
        return self.config

    def set_config(self, config:dict[str,typing.Any]) -> None:
        """Set the configuration."""
        self.config = config

    def get_value(self, key:str) -> typing.Any:
        """
        Get a single value from the config.

        :param key:
        The key to the value.

        :returns value:
        returns the value or `0` if failed.
        """
        try:
            return self.config[key]
        except KeyError:
            return 0
