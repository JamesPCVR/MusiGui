import os
import json
import cv2

# image scale conditions
NO_SCALE = 0
NO_SMALLER = 1
NO_LARGER = 2
SCALE_EXACT = 3

# image upscale method
STRETCH = 0

class ImageConfig():
    '''
    Configuration data structure for the image modifier
    '''
    _configdir = "config/image.json"

    def __init__(self):
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
        self.image_scale_conditions = NO_SCALE
        self.image_size_target      = 1024
        self.image_upsize_method    = STRETCH
        self.image_downsize_method  = cv2.INTER_LANCZOS4
        self.upscaler_directory     = ""

    def load(self) -> None:
        '''
        Import configuration from the config json file.
        '''
        with open(self._configdir, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.image_scale_conditions = data["image_scale_conditions"]
        self.image_size_target      = data["image_size_target"]
        self.image_upsize_method    = data["image_upsize_method"]
        self.image_downsize_method  = data["image_downsize_method"]
        self.upscaler_directory     = data["upscaler_directory"]

    def export(self) -> None:
        '''
        Export current configuration to the config json file.
        '''
        data = {
            "image_scale_conditions":   self.image_scale_conditions,
            "image_size_target":        self.image_size_target,
            "image_upsize_method":      self.image_upsize_method,
            "image_downsize_method":    self.image_downsize_method,
            "upscaler_directory":       self.upscaler_directory
        }

        with open(self._configdir, "w+", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

if __name__ == "__main__":
    dl_cfg = ImageConfig()
