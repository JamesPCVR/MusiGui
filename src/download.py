import os
import shutil
import typing
import json
import yt_dlp
import configure
from handler import BaseHandler, DEBUG, INFO, WARNING, ERROR #pylint: disable=W0611

class DownloadConfig(configure.Config):
    """Configuration data structure for the downloader."""
    def __init__(self) -> None:
        """
        Import configuration from the config json file if it exists,
        otherwise create one.
        """
        self._configdir = "config\\download.json"
        super().__init__()

    def default(self) -> None:
        """Load the default configuration."""
        self.config = {
            "output_directory": "out"
        }

class DownloadHandler(yt_dlp.YoutubeDL, BaseHandler):
    """Handles downloading files using yt-dlp."""
    def __init__(self) -> None:
        """Handles downloading files using yt-dlp."""
        super().__init__()
        self.config = DownloadConfig()
        self.logger = None
        self._build_opts()

    def get_config(self) -> None:
        """Get the currently used configuration."""
        return self.config.get_config()

    def set_config(self, config:dict[str,typing.Any]) -> None:
        """Set the configuration."""
        self.config.set_config(config)

    def set_logger(self, logger:object) -> None:
        """
        Set the logger.

        :param logger:
        class object to provide callbacks and progress updates.
        """
        self.logger = logger

    def download_url(self, url) -> dict[str,typing.Any]:
        """
        Starts the download of a song or playlist from a url.
        
        :param url:
        The url to fetch from.

        :returns info_clean:
        A dictionary with all the metadata for the download task.
        """
        self._build_opts()
        try:
            with yt_dlp.YoutubeDL(self.opts) as ydl:
                info = ydl.extract_info(url, download=True)
                info_clean = ydl.sanitize_info(info)
                with open("down\\data.json", "w+", encoding="utf-8") as f:
                    json.dump(info_clean, f, indent=4)
        except yt_dlp.DownloadError:
            info_clean = {}

        return info_clean

    def _build_opts(self) -> None:
        """Create the configuration dictionary for yt-dlp."""
        # Extract audio using ffmpeg
        postprocessor = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }
        self.opts = {
            "format": "mp3/bestaudio/best",
            "outtmpl": {
                "default": os.getcwd()
                + "\\down\\%(extractor)s-%(id)s-%(title)s.%(ext)s"
            },
            "restrictfilenames": True,
            "writethumbnail": True,
            "clean_infojson": True,
            "logger": self.logger,
            "postprocessors": [postprocessor]
        }

    def save_config(self) -> None:
        """Save changes to the download configuration."""
        self.config.save()

    def clean(self) -> None:
        """Move files to final location and remove temporary files."""
        self.log("[download] Cleaning up", INFO)
        src_path = os.path.abspath("down")
        src_files = os.listdir(src_path)
        dest_path = self.config.get_value("output_directory")

        if not os.path.exists(dest_path):
            os.mkdir(dest_path)

        for file in src_files:
            if file.endswith('.mp3'):
                shutil.move(
                    os.path.join(src_path,file),
                    os.path.join(dest_path,file)
                )

        shutil.rmtree(src_path)
        self.log("[download] Done", INFO)

if __name__ == "__main__":
    dl_cfg = DownloadConfig()
