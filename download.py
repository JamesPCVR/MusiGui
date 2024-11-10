import os
import json

PICK_AUTO = 0
PICK_MANUAL = 1

class DownloadConfig():
    '''
    Configuration data structure for the downloader.
    '''
    _configdir = "config/download.json"

    def __init__(self) -> None:
        '''
        Import configuration from the config json file if it exists,
        otherwise create one.
        '''

        self.default()

        try:
            self.load()

        except FileNotFoundError:
            direc = self._configdir.split('/', maxsplit=1)[0]
            if not os.path.exists(direc):
                os.makedirs(direc)

            self.export()

    def default(self) -> None:
        '''
        Load the default configuration.
        '''
        self.overwrite              = False
        self.audio_quality_target   = 128 # Kbps
        self.add_image_single       = PICK_AUTO
        self.add_image_album        = PICK_MANUAL
        self.output_directory       = ""

    def load(self) -> None:
        '''
        Import configuration from the config json file.
        '''
        with open(self._configdir, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.overwrite              = data["overwrite"]
        self.audio_quality_target   = data["audio_quality_target"]
        self.add_image_single       = data["add_image_single"]
        self.add_image_album        = data["add_image_album"]
        self.output_directory       = data["output_directory"]

    def export(self) -> None:
        '''
        Export current configuration to the config json file.
        '''
        data = {
            "overwrite":            self.overwrite,
            "audio_quality_target": self.audio_quality_target,
            "add_image_single":     self.add_image_single,
            "add_image_album":      self.add_image_album,
            "output_directory":     self.output_directory
        }

        with open(self._configdir, "w+", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

if __name__ == "__main__":
    dl_cfg = DownloadConfig()
