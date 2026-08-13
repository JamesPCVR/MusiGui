import logging

import re
import pathlib
import shlex

import yt_dlp

logger = logging.getLogger(__name__)

def from_file(path:pathlib.Path):
    """Convert command-line arguments from file to config dictionary."""

    with path.open("rt", encoding="utf-8") as f:
        lines = re.findall(
            r"(?mx)^\s*(?!\#)(.+?)\s*(?:\s\#.*)?$",
            f.read()
        )

    argv = []
    logger.debug(f"Reading config from file {path}")
    for line in lines:
        logger.debug(line)
        argv.extend(shlex.split(line))

    ydl_opts = yt_dlp.parse_options(argv).ydl_opts
    return ydl_opts
