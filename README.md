# What is MusiGui?

Pronounced `myou-zi-goo-ee`. It is a GUI wrapper around the legendary [youtube-dl](https://github.com/ytdl-org/youtube-dl) and AI upscalers: RealSR; Waifu2x; and SRMD.

Image scaling can be disabled by selecting `Downscale method` as `None`.

The windows freezes during a download, this application is only single-threaded. If your OS says it's "not responding" you probably just need to wait for the download to finish.

If you ever get stuck or need help; press the handy-dandy `help` button in the program! There are also some tooltips (hover for 1 second).

# Dependencies

### Required

Dependencies `tkinter`, `json`, `ctypes`, `os`, `time`, and `subprocess` are included in the [python standard library](https://docs.python.org/3/library/index.html).

You can easily install `youtube_dl`, `eyed3` and `cv2` using [pip](https://pip.pypa.io/en/stable/).

```bash
pip install youtube-dl
```
```bash
pip install eyed3
```
```bash
pip install opencv-python
```

Windows users may have to add `py -m` to the beginning of each command:
```bash
py -m pip install youtube-dl
```
```bash
py -m pip install eyed3
```
```bash
py -m pip install opencv-python
```

`youtube-dl` requires ffmpeg, follow [this guide](https://phoenixnap.com/kb/ffmpeg-windows) to install it if you haven't already.

### Optional

I would also reccommend downloading [mp3tag](https://www.mp3tag.de/en/download.html) it is really handy for correcting any mistakes the program makes.

# Setup

### First use

- Pick a download folder, this is the working directory for this application, it should be seperate from anything else.
- Pick an upscaler folder, make sure to download at least one of the [supported models](#supported-ai-models) and place it in this directory. Its subfolder should be named "\<model>-ncnn-vulkan".

### Typical use
- launch using `run.bat` (it invokes the GUI by running `py gui.py`)
- Add URLs to the text box in the bottom left, they are seperated with a newline (\<enter>). The URLs can point to single streams or playlists/albums (whole playlists will be downloaded). The URLs can be from any website (e.g. youtube, soundcloud, bandcamp...) so long as it is [supported by youtube-dl](https://github.com/ytdl-org/youtube-dl/blob/master/docs/supportedsites.md).
- Once you've added all the URLs you want, hit the download button in the bottom right to download the files one-by-one. The program will also download the cover art for each item.
- Cover art will be upscaled by the selected AI model if it is smaller than the target image size.

![GUI preview](img/img2.jpg)

# Supported AI models

Be sure to download at least one of these and put it in a folder that the GUI can access.

| Model Download | License |
| --- | --- |
| [realsr-ncnn-vulkan](https://github.com/nihui/realsr-ncnn-vulkan) | [MIT](https://choosealicense.com/licenses/mit/) |
| [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) | [MIT](https://choosealicense.com/licenses/mit/) |
| [srmd-ncnn-vulkan](https://github.com/nihui/srmd-ncnn-vulkan) | [MIT](https://choosealicense.com/licenses/mit/) |

# Credits

[supported models](#supported-ai-models) - nihui and many others

[tooltip.py](tooltip.py) - vegaseat, Victor Zaccardo, Alberto Vanessa & Erik Bethke

# License

[MIT](https://choosealicense.com/licenses/mit/)