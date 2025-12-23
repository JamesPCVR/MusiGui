import subprocess
import pathlib

BASE_PATH = (
    pathlib.Path(__file__).parent.resolve()
    if __file__ in globals()
    else pathlib.Path.cwd()
)

YT_DLP_PATH = BASE_PATH / pathlib.Path("bin/linux/yt-dlp_linux/yt-dlp_linux")
FFMPEG_PATH = BASE_PATH / pathlib.Path("bin/linux/ffmpeg-linux64-lgpl/bin/ffmpeg")
DEBUG_STDOUT = BASE_PATH / pathlib.Path("debug/stdout")
DEBUG_STDERR = BASE_PATH / pathlib.Path("debug/stderr")


def main():
    link = "https://soundcloud.com/acloudyskye/shoots"

    with DEBUG_STDOUT.open("wt+", encoding="utf-8") as f_stdout:
        with DEBUG_STDERR.open("wt+", encoding="utf-8") as f_stderr:
            ret = subprocess.run(
                [YT_DLP_PATH, "--ffmpeg-location", FFMPEG_PATH, link, "--verbose"], stdout=f_stdout, stderr=f_stderr
            )

    if ret.returncode != 0:
        print(f"Warning: return code {ret.returncode}")


if __name__ == "__main__":
    main()
