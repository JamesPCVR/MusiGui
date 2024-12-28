import typing
import download
import formatting
import image

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3

# name originates from mispronounciation of MusAPI
class MusHappy:
    """API to handle downloading and tagging of music files."""

    def __init__(self) -> None:
        self.download_handler = download.DownloadHandler()
        self.music_handler = formatting.MusicFormatHandler()
        self.image_handler = image.ImageFormatHandler()
        self.logger = None

    def get_config(self) -> dict[str, typing.Any]:
        """
        :returns configs:
        the config dictionaries used by the modules
        """
        configs = {
            "download": self.download_handler.get_config(),
            "formatting": self.music_handler.get_config(),
            "image": self.image_handler.get_config()
        }
        return configs

    def set_config(self, configs:dict[str,typing.Any]) -> None:
        """Set the configurations."""
        self.download_handler.set_config(configs["download"])
        self.music_handler.set_config(configs["formatting"])
        self.image_handler.set_config(configs["image"])

    def set_logger(self, logger:object) -> None:
        """
        Set the logger.

        :param logger:
        class object to provide callbacks and progress updates.
        """
        self.download_handler.set_logger(logger)
        self.music_handler.set_logger(logger)
        self.image_handler.set_logger(logger)
        self.logger = logger

    def save_config(self) -> None:
        """Save the modified configuration."""
        self.download_handler.save_config()
        self.music_handler.save_config()
        self.image_handler.save_config()

    def get_valid_ai_models(self) -> list[str]:
        """Get available ai models."""
        return self.image_handler.config.get_valid_ai_models()

    def get_interpolation_methods(self) -> list[str]:
        """Get interpolation methods."""
        return self.image_handler.config.get_interpolation_methods()

    def download_and_tag(self, url_list:list[str]) -> None:
        """
        Download the URLs from the list
        and perform all the appropriate tagging.

        :param url_list:
        The list of URLs as strings to be downloaded.
        """
        for i, url in enumerate(url_list):
            self.log(f"[mushappy] Downloading item {i} of {len(url_list)}")
            info_clean = self.download_handler.download_url(url)
            if info_clean == {}:
                continue

            # handle metadata
            self.music_handler.set_info(info_clean)
            self.music_handler.correct_metadata()
            self.music_handler.tag_audio()

            # handle images
            self.image_handler.set_info(info_clean)
            self.image_handler.post_process()

            # write images
            _images = self.image_handler.get_images()
            self.music_handler.tag_image(_images)

            # write changes
            self.music_handler.save()
            self.music_handler.rename()

        # clean up
        self.download_handler.clean()

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
