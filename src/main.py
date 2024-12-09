import sys
import re
from PySide6.QtCore import QThread, SignalInstance

import api
import gui

class ProgressLogger():
    """Repeatedly called during tasks with progress messages."""

    def __init__(self) -> None:
        self.signal = None
        self.data = {
            "partial": 0,
            "total": 0
        }
        self.progress = {
            "to do": 0,
            "done": 0,
            "sub to do": 0,
            "sub done": 0
        }

    def update(self, msg:str) -> None:
        """emit a signal to the ui for a progress update."""
        if self.signal is None:
            return

        self.signal.emit(msg, self.data)

    def debug(self, msg:str):
        """debug string"""
        # For compatibility with youtube-dl,
        # both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)
            self.update(msg)

    def info(self, msg:str):
        """info string"""
        # remove ansi escape sequences
        done = False
        msg = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", '', msg)
        m = msg.split(" ")
        m = [s for s in m if s != ""]
        if msg.startswith("[mushappy] "):
            self.progress["to do"] = int(m[-1])
            self.progress["done"] = int(m[-3])
            self.progress["sub to do"] = 1
            self.progress["sub done"] = 0
        elif msg.startswith("[download] "):
            if m[1].lower() == "downloading" and m[2] == "item":
                self.progress["sub to do"] = int(m[-1]) + 1
                self.progress["sub done"] = int(m[-3])
            elif m[1].lower() in ["done"]:
                self.data["total"] = 100
                done = True
            else:
                try:
                    self.data["partial"] = int(float(m[1][:-1]))
                except ValueError:
                    pass

        if not done:
            self.data["total"] = self.calculate_progress()

        print(msg)
        self.update(msg)

    def warning(self, msg:str):
        """warning string"""
        print("WARNING: " + msg)
        self.update(msg)

    def error(self, msg:str):
        """error string"""
        print("ERROR: " + msg)
        self.update(msg)

    def set_signal(self, signal:SignalInstance) -> None:
        """Set the emission signal."""
        self.signal = signal

    def calculate_progress(self) -> None:
        """Calculate total progression"""
        to_do = self.progress["to do"]
        done = self.progress["done"]
        sub_to_do = self.progress["sub to do"]
        sub_done = self.progress["sub done"]
        return (100 / to_do) * (done + ((sub_done-1)/sub_to_do))

    def reset(self) -> None:
        """reset the progress tracker."""
        self.data = {
            "partial": 0,
            "total": 0
        }
        self.progress = {
            "to do": 0,
            "done": 0,
            "sub to do": 0,
            "sub done": 0
        }

class TaskThreaded(QThread):
    """Threaded task for the UI to run."""
    def __init__(self) -> None:
        self.logger = ProgressLogger()
        self.urls = []
        self.task = api.MusHappy()
        self.task.set_logger(self.logger)
        super().__init__()

    def set_signal(self, signal:SignalInstance) -> None:
        """Set the emission signal."""
        self.logger.set_signal(signal)

    def set_urls(self, urls:list) -> None:
        """Pass configuration data to the thread."""
        self.urls = urls

    def run(self) -> None:
        """Run MusHappy as a background task."""
        self.task.download_and_tag(self.urls)

    def get_valid_ai_models(self) -> list[str]:
        """Get available ai models."""
        return self.task.get_valid_ai_models()

def main() -> None:
    """Main script."""
    theme_name = None
    if len(sys.argv) > 1:
        theme_name = sys.argv[1]
    app, window = gui.create_ui(TaskThreaded(), theme_name)
    window.update_widgets()
    app.exec()

def test() -> None:
    """Test the backend with various scenarios."""
    mus_api = api.MusHappy()
    mus_api.set_logger(ProgressLogger())

    cfg = mus_api.get_config()
    print(cfg)
    mus_api.set_config(cfg) # test setting the configuration
    mus_api.save_config()

    mus_api.download_and_tag([
        # single with one artist
        "https://soundcloud.com/acloudyskye/spill"
        # single with two artists
        #"https://soundcloud.com/inzo_music/digital-night-drive"
        # single with no artists and non-ascii title
        #"https://soundcloud.com/officialcodly/forged-in-darkest-abyss"
        # album with one artist
        #"https://soundcloud.com/geoxor/sets/identity"
        # album with many artists and some different cover art
        #"https://soundcloud.com/inzo_music/sets/visionquest-6"
        # single with "low-quality" cover art
        #"https://soundcloud.com/acloudyskye/runaway"
    ])

if __name__ == "__main__":
    main()
