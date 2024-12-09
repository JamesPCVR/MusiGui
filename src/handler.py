import typing

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3

class BaseHandler:
    """Base class for class handling."""
    def __init__(self, config:object, child_class:object) -> None:
        self.config = config
        self.logger = None
        self.child = child_class

        self.info:dict[str,typing.Any] = {}
        self.formatters:list = []

    def get_config(self) -> None:
        """Get the currently used configuration."""
        return self.config.get_config()

    def set_config(self, config:dict[str,typing.Any]) -> None:
        """Set the configuration."""
        self.config.set_config(config)

    def save_config(self) -> None:
        """Save changes to the formatting configuration."""
        self.config.save()

    def set_logger(self, logger:object) -> None:
        """
        Set the logger.

        :param logger:
        class object to provide callbacks and progress updates.
        """
        self.logger = logger

    def log(self, message:str, level:int=DEBUG) -> None:
        """
        Send a message through the logger.

        :param message:
        Message to pass through the logger.

        :param level:
        Message warning level, `DEBUG`, `INFO`, `WARNING`, `ERROR`
        """
        # eh, it works
        if self.logger is not None:
            if level == DEBUG:
                self.logger.debug(message)
            elif level == INFO:
                self.logger.info(message)
            elif level == WARNING:
                self.logger.warning(message)
            elif level == ERROR:
                self.logger.error(message)

    def set_info(self, info:dict[str:typing.Any]) -> None:
        """Pass in the metadata to be used in the subclasses."""
        self.info = info
        self.formatters = []
        if info["_type"] == "playlist":
            for meta in self.info["entries"]:
                self.formatters.append(self.child(meta, self.config, self))
        else:
            self.formatters.append(self.child(info, self.config, self))
