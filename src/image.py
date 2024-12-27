import os
import hashlib
import typing
import subprocess
import cv2
import numpy as np
import configure
from handler import BaseHandler, DEBUG, INFO, WARNING, ERROR  #pylint: disable=W0611

PICK_SINGLE_AUTO = 0
PICK_SINGLE_MANUAL = 1

PICK_GROUP_EACH = 0
PICK_GROUP_MOST_COMMON = 1
PICK_GROUP_MANUAL = 2

SCALE_TYPES = [
    [ cv2.INTER_LINEAR,   "Fastest" ],
    [ cv2.INTER_AREA,     "Balanced" ],
    [ cv2.INTER_LANCZOS4, "Best Quality" ],
]

class ImageConfig(configure.Config):
    """
    Configuration data structure for the image modifier.
    """
    def __init__(self) -> None:
        """
        Import configuration from the config json file if it exists,
        otherwise create one.
        """
        self._configdir = "config\\image.json"
        super().__init__()

        self.valid_ai_models = []
        self._check_valid_models()

    def _check_valid_models(self) -> None:
        """Check if the AI model executables exist."""
        # for each configured model
        self.valid_ai_models = []
        for model in self.config["ai_commands"]:
            model_name = model["name"]
            target = model["target"]
            if self._model_is_valid(target):
                self.valid_ai_models.append(model_name)

    def _model_is_valid(self, target:str) -> bool:
        """Checks if a target executable exists."""
        # must exist
        root = self.config["ai_directory"]
        target_path = target.format(root=root)
        if not os.path.exists(target_path):
            return False

        # must have valid file extension
        ext = os.path.splitext(target)[1].lower()
        if ext not in [".exe"]:
            return False

        # it is not invalid, so it must be valid
        return True

    def get_valid_ai_models(self) -> list[str]:
        """Get available ai models."""
        self._check_valid_models()
        return self.valid_ai_models

    def get_interpolation_methods(self) -> list[str]:
        """Get available interpolation methods."""
        return [name for _, name in self.config["interpolation"]]

    def default(self) -> None:
        """Load the default configuration."""
        ais = [{
            "name":    "RealSR",
            "target":  "{root}\\realsr-ncnn-vulkan\\realsr-ncnn-vulkan.exe",
            "options": "-m \"{root}\\models-DF2K\" -i \"{input}\" -o \"{output}\" -s {scale}"
        },{
            "name":    "Waifu2x",
            "target":  "{root}\\waifu2x-ncnn-vulkan\\waifu2x-ncnn-vulkan.exe",
            "options": "-m \"{root}\\models-DF2K\" -i \"{input}\" -o \"{output}\" -s {scale}"
        },{
            "name":    "SRMD",
            "target":  "{root}\\ssrmd-ncnn-vulkan\\srmd-ncnn-vulkan.exe",
            "options": "-m \"{root}\\models-DF2K\" -i \"{input}\" -o \"{output}\" -s {scale}"
        }]

        self.config = {
            "add_image_single":       PICK_SINGLE_AUTO,
            "add_image_group":        PICK_GROUP_MOST_COMMON,
            "image_size_target":      1024,
            "interpolation":          SCALE_TYPES,
            "interpolate_method":     1,
            "ai_method":              0,
            "ai_directory":           "ai\\",
            "ai_commands":            ais
        }

class ImageFormatHandler(BaseHandler):
    """
    Handles instances of `ImageFormatter` to correctly manipulate
    singles, albums, playlists and more.
    """
    def __init__(self) -> None:
        super().__init__(ImageConfig(), ImageFormatter)
        self.hash_frequency:dict[str,dict[str,typing.Any]] = {}
        self.config:ImageConfig
        self.formatters:list[ImageFormatter]

    def post_process(self) -> None:
        """Run the formatting on the images."""
        self.hash_frequency = {}
        seen_hash_crypt = set()
        seen_hash_diff = set()
        seen_hash_lookup = {}

        self.log("[image] Processing images", INFO)
        self.log("[image] Computing similarity hashes", INFO)
        for inst in self.formatters:
            # open the image
            inst.open_image()

            # check for image similarity
            hash_crypt = inst.hash_cryptographic()
            if hash_crypt in seen_hash_crypt:
                # identical image found, do not recompute
                hash_diff = seen_hash_lookup[hash_crypt]
                inst.set_hash_difference(hash_diff)
            else:
                # the image is not identical, but it may look similar
                hash_diff = inst.hash_difference()

                # add this hash to the lookup
                seen_hash_crypt.add(hash_crypt)
                seen_hash_diff.add(hash_diff)
                seen_hash_lookup[hash_crypt] = hash_diff

            if hash_diff in self.hash_frequency:
                # similar already computed, pick from the LUT
                self.hash_frequency[hash_diff]["frequency"] += 1
            else:
                # image is visually distinct and needs to be processed
                stats = {}
                stats["frequency"] = 1
                out_path = f"{inst.get_image_root()}\\{hash_diff}.png"
                stats["output"] = out_path
                stats["processed"] = False
                self.hash_frequency[hash_diff] = stats

        first_hash_item = list(self.hash_frequency.values())[0]
        if len(self.hash_frequency) == 1 \
            and first_hash_item["frequency"] == 1:
            # item is a single
            # add_single = self.config.get_value("add_image_single")
            self.log(
                "[image] Processing image 1 of 1",
                INFO
            )
            self.formatters[0].set_image_output(first_hash_item["output"])
            self.formatters[0].process_image()
        else:
            # item is a group
            add_group = self.config.get_value("add_image_group")

            if add_group == PICK_GROUP_EACH:
                self.process_each_unique()
            elif add_group == PICK_GROUP_MOST_COMMON:
                self.process_most_common()

        self.log("[image] Finished processing images")

    def get_images(self) -> list[str]:
        """Get the directories of the images."""
        _image_paths = []
        for inst in self.formatters:
            _image_paths.append(inst.get_image_output())
        return _image_paths

    def process_each_unique(self) -> None:
        """Process each unique image and attach it."""
        for i, inst in enumerate(self.formatters):
            self.log(
                f"[image] Processing image {i} of {len(self.formatters)}",
                INFO
            )
            hash_diff = inst.get_hash_difference()
            if self.hash_frequency[hash_diff]["processed"] is False:
                # need to process this new image
                inst.process_image()
                self.hash_frequency[hash_diff]["processed"] = True

    def process_most_common(self) -> None:
        """Process only the most common image and attach it."""
        # find the most common image
        most_common = ""
        most_common_freq = 0
        for _hash_freq in self.hash_frequency.values():
            freq = _hash_freq["frequency"]
            if freq > most_common_freq:
                most_common_freq = freq
                most_common = _hash_freq["output"]

        # set the output path
        for inst in self.formatters:
            inst.set_image_output(most_common)

        self.log(
            "[image] Processing image 1 of 1",
            INFO
        )

        self.formatters[0].process_image()

class ImageFormatter:
    """
    Contains all the information needed to handle image files.
    Includes metadata, cover art, etc.
    """
    def __init__(
            self,
            metadata:dict[str,typing.Any],
            config:ImageConfig,
            handler:ImageFormatHandler
        ) -> None:
        """
        Contains all the information needed to handle image files.
        Includes metadata, cover art, etc.
        """
        self.meta = metadata
        self.config = config
        self.handler = handler
        self.image_input_path = self.meta["thumbnails"][-1]["filepath"]
        self.image_output_path = self.image_input_path
        self.image = None

        # initialise empty hashes
        self.hash_crypt = "0" * 64
        self.hash_diff = "0" * 16

    def get_image_input(self) -> str:
        """
        Get the directory of the input image file.

        :returns image_input:
        Path of the input image file.
        """
        return self.image_input_path

    def get_image_root(self) -> str:
        """
        Get the image file root directory.

        :returns image_root:
        Absolute filepath of the image parent directory.
        """
        root = self.meta["requested_downloads"][0]["__finaldir"]
        return root

    def set_image_output(self, image_path:str) -> None:
        """
        Set the output path of the image.

        :param image_path:
        New output image path.
        """
        self.image_output_path = image_path

    def get_image_output(self) -> str:
        """
        Get the output path of the image.

        :returns image_path:
        Output image path.
        """
        return self.image_output_path

    def hash_cryptographic(self) -> str:
        """
        Compute the cryptographic hash of the image file.

        :returns _hex:
        Hash string or `"00...00"` on failure.
        """
        # General-purpose solution that can process large files
        # https://stackoverflow.com/questions/22058048/hashing-a-file-in-python

        sha256 = hashlib.sha256()

        with open(self.image_input_path, "rb") as f:
            while True:
                # reduce RAM use by reading in chunks
                data = f.read(65535)
                if not data:
                    break
                sha256.update(data)

        _hex = sha256.hexdigest()
        self.set_hash_cryptographic(_hex)
        return _hex

    def hash_difference(self, hash_size:int=8) -> str:
        """
        Compute the difference hash of the image file.
        It is much slower than a cryptographic hash.

        :param hash_size:
        The hash will be `2**hash_size` bits long.

        :returns _hex:
        Hash string or `"00...00"` on failure.
        """
        # modified dhash function from this blog post:
        # https://pyimagesearch.com/2017/11/27/image-hashing-opencv-python/

        if self.image is None:
            # the image did not open successfully
            return "0" * (hash_size * 2)

        # compute the difference image
        grayscale = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(grayscale, (hash_size + 1, hash_size))
        diff = resized[:, 1:] > resized[:, :-1]

        # convert the difference image to a hash
        _hash = sum(2 ** i for (i, v) in enumerate(diff.flatten()) if v)

        # return as hex string
        _hex = f"{_hash:0{hash_size*2}x}"
        self.set_hash_difference(_hex)
        return _hex

    def set_hash_cryptographic(self, _hash:str) -> None:
        """Set the sha256 hash."""
        self.hash_diff = _hash

    def get_hash_cryptographic(self) -> str:
        """Get the computed sha256 hash."""
        return self.hash_diff

    def set_hash_difference(self, _hash:str) -> None:
        """Set the hash difference."""
        self.hash_diff = _hash

    def get_hash_difference(self) -> str:
        """Get the computed hash difference."""
        return self.hash_diff

    def process_image(self):
        """Transform the image into the desired format."""
        # image needs to be square
        self.crop_image()

        # check if ai upscaling is enabled
        if self.config.get_value("ai_method") != 0:
            self.upscale_image()

        # do not resize the image if scaling is disabled
        if self.config.get_value("interpolate_method") != 0:
            self.resize_image()

        self.export()

    def open_image(self, path:str=None, reload:bool=False) -> bool:
        """
        Open the image file, if it is not already.

        :param path:
        Image path to load.

        :param reload:
        Force the image object to be overwritten.

        :returns success:
        returns `True` if image opened successfully.
        """
        # if no path is specified, use the internal directory
        if path is None:
            path = self.get_image_input()

        # open the image if not already or forced to
        if reload or self.image is None:
            self.image = cv2.imread(path)

        # image opened without errors
        if self.image is not None:
            return True

        # failed to open image
        return False

    def crop_image(self) -> None:
        """Crop the image square."""
        h, w = np.shape(self.image)[0:2]
        if w > h:
            # landscape
            o = (w - h) // 2
            self.image = self.image[0:h, o:h+o]
        elif w < h:
            # portrait
            o = (h - w) // 2
            self.image = self.image[o:w+o, 0:w]

    def upscale_image(self) -> None:
        """Upscale the input image."""
        # check if ai upscaling is disabled
        model_index = self.config.get_value("ai_method")
        if model_index == 0:
            return
        model_index -= 1

        size = min(self.image.shape[0:2])
        target = self.config.get_value("image_size_target")

        scaled = False
        retries = 3
        dir_to_ai = f"{self.get_image_root()}\\temp.png"
        dir_from_ai = f"{self.get_image_root()}\\temp_out.png"

        if target > size:
            self.export(dir_from_ai)

        # upscale the image in 4x chunks
        while target > size:
            scaled = True
            self.handler.log(
                f"[image] Upscaling from {size}x{size} to {size*4}x{size*4}",
                INFO
            )

            # create input file for ai upscaler
            if os.path.exists(dir_to_ai):
                os.remove(dir_to_ai)
            os.rename(dir_from_ai, dir_to_ai)

            # build the command to run the upscaler
            params = {
                "root": self.config.get_value("ai_directory"),
                "input": dir_to_ai,
                "output": dir_from_ai,
                "scale": 4
            }
            parts = self.config.get_value("ai_commands")[model_index]
            command = parts["target"].format(**params) \
                + " " \
                + parts["options"].format(**params)

            self.handler.log(
                f"[debug] Subprocess: {command}",
                DEBUG
            )

            # upscale image using selected engine
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            size *= 4

            # break if too many errors
            if result.returncode != 0:
                retries -= 1
                if retries < 0:
                    self.handler.log(
                        "[image] Failed to upscale image",
                        ERROR
                    )
                    break
                self.handler.log(
                    f"[image] Error upscaling image, {retries} retry(s) left",
                    WARNING
                )

        if scaled is True:
            self.open_image(dir_from_ai, True)
        else:
            self.handler.log(
                "[image] Size is not smaller than target, skipping",
                INFO
            )

    def resize_image(self) -> None:
        """Resize the image to the target size."""
        _target = self.config.get_value("image_size_target")
        _size = np.shape(self.image)[0:2]
        self.handler.log(
            f"[image] Resizing image from {_size[0]}x{_size[1]} to {_target}x{_target}", #pylint: disable=C0301
            INFO
        )
        self.image = cv2.resize(
            self.image,
            dsize=(_target, _target),
            interpolation=SCALE_TYPES[self.config.get_value("interpolation_method") - 1][0]
        )

    def export(self, directory:str=None) -> None:
        """Save the image."""
        if directory is None:
            directory = self.get_image_output()
        ret = cv2.imwrite(directory, self.image)
        if ret is False:
            self.handler.log(
                f"[export] Failed to save image {directory}",
                ERROR
            )

if __name__ == "__main__":
    dl_cfg = ImageConfig()
