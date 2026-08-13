from typing import Any
import logging

import pathlib

import yt_dlp

import options

logger = logging.getLogger(__name__)

BASE_PATH = (
    pathlib.Path(__file__).parent.resolve()
    if __file__ in globals()
    else pathlib.Path.cwd()
)

RELPATH_YDL_CONFIG = pathlib.Path("cfg/yt-dlp.conf")
RELPATH_FFMPEG = pathlib.Path("bin/linux/ffmpeg-linux64-lgpl/bin/ffmpeg")


def dl_hook(d: dict):
    # a download is considered started if it's on the first fragment.
    # this will cause a few signal emissions but it the cleanest way i
    # could think of without tracking whether this is a fresh download.
    if d.get("fragment_index", 1) == 0 or d["status"] == "finished":
        print("DL:", d["status"], round(d["_percent"], 1))


def pp_hook(d: dict):
    print("PP:", d["status"], d["postprocessor"])
    if d["status"] == "finished" and d["postprocessor"] == "MoveFiles":
        print(d["info_dict"]["original_url"])
        print(d["info_dict"]["webpage_url"])


def pt_hook(p: str):
    # p is the absolute path to the final file
    print("PT:", p)


def expand_urls(url: str) -> tuple[list[str],dict[str,Any]]:
    """Resolve a playlist/album into a list of singles.
    Guaranteed to return at least one url and the album infodict."""

    logger.debug(f"Expanding {url}")

    ydl_opts = {
        "clean_infojson": True,
        "skip_download": True,
        "extract_flat": True,
        "noprogress": True,
        "quiet": True,
        "color": {"stderr": "no_color", "stdout": "no_color"},
        "logger": logger,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)

    if "entries" in info:
        logger.debug(f"Expanded into a playlist with {info["playlist_count"]} items")
        urls = [entry["url"] for entry in info["entries"]]
        plist_info = info
    else:
        logger.debug("Expanded into a single")
        urls = [info["webpage_url"]]
        plist_info = {
            "album": info["title"],
            "album_artist": info["artist"],
            "album_artists": info["artists"],
            "uploader": info["uploader"],
            "uploader_id": info["uploader_id"],
            "title": info["title"],
            "_type": "single",
            "webpage_url": info["webpage_url"],
            "original_url": info["original_url"],
            "playlist_count": 1,
        }

    logger.debug(
        "These URLs are extracted flat and may not be fully resolved until the download phase."
    )
    for i, u in enumerate(urls):
        logger.debug(f"URL {i}: {u}")

    return urls, plist_info

ydl_config_opts = {}
def get_opts(id_:int, dl_hook, pp_hook):
    global ydl_config_opts

    if len(ydl_config_opts) <= 0:
        ydl_config_opts = options.from_file(RELPATH_YDL_CONFIG)

    ydl_opts = {
        **ydl_config_opts,
        "clean_infojson": True,
        "noprogress": True,
        "color": {"stderr": "no_color", "stdout": "no_color"},
        "ffmpeg_location": str(RELPATH_FFMPEG),
        "outtmpl": f"tmp/{id_}/%(meta_artist)s - %(file_title)s.%(ext)s",
        "logger": logger,
        "progress_hooks": [dl_hook],
        "postprocessor_hooks": [pp_hook],
    }
    return ydl_opts


def task(id_: int, url: str, dl_hook, pp_hook) -> int:
    ydl_opts = get_opts(id_, dl_hook, pp_hook)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        returncode = ydl.download(url)

    return returncode


def task_start(id_: int, url: str):
    urls = expand_urls(url)
    for url_ in urls:
        task(id_, url_, dl_hook, pp_hook)


def main():
    # task_start(0, "https://soundcloud.com/acloudyskye/shoots") # single
    # task_start(1, "https://soundcloud.com/iprevailband/theres-fear-in-letting-go") # weird character in title
    # task_start(2, "https://soundcloud.com/iprevailband/sets/violent-nature-1") # album test
    # task_start(3, "https://soundcloud.com/inzo_music/sets/inzo-earth-magic-ep-1") # playlist test
    # task_start(4, "https://soundcloud.com/officialcodly/arathain") # comissions string
    task_start(5, "https://soundcloud.com/officialcodly/lie")  # unicode torture-test


if __name__ == "__main__":
    logging.basicConfig(
        filename="debug.log", filemode="wt+", encoding="utf-8", level=logging.DEBUG
    )
    main()
