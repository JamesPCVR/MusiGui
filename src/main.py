import sys
import re
import logging
# from logging.handlers import RotatingFileHandler
from concurrent_log_handler import ConcurrentRotatingFileHandler
from PySide6.QtCore import QThread, SignalInstance

import api
import gui

LOG_FILE = "debug.log"
LOG_SIZE_LIMIT = 10 * 1024 # 100 KB file size limit

class ProgressLogger():
    """Repeatedly called during tasks with progress messages."""

    def __init__(self) -> None:
        self.signal = None
        self.data = {
            "partial": 0,
            "total": 0,
            "error": False
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

        # large increments, one for each url in the list
        if msg.startswith("[mushappy] "):
            self.progress["to do"] = int(m[-1])
            self.progress["done"] = int(m[-3])
            self.progress["sub to do"] = 1
            self.progress["sub done"] = 0

        elif msg.startswith("[download] "):
            # smaller increments, one for each item in a url
            if m[1].lower() == "downloading" and m[2] == "item":
                self.progress["sub to do"] = int(m[-1]) + 1
                self.progress["sub done"] = int(m[-3])

            # done, free the UI
            elif m[1].lower() in ["done"]:
                self.data["total"] = 100
                done = True

            # update total number of tasks to do
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
        self.data["error"] = True
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
            "total": 0,
            "error": False
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

    def get_interpolation_methods(self) -> list[str]:
        """Get available interpolation methods."""
        return self.task.get_interpolation_methods()

def main():
    """main task"""
    log_handler = ConcurrentRotatingFileHandler(
        LOG_FILE,
        mode="a",
        maxBytes=LOG_SIZE_LIMIT,
        backupCount=1,
        encoding="utf-8"
    )
    log_handler.setLevel(logging.DEBUG)
    logging.basicConfig(filename="debug.log", level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.addHandler(log_handler)

    # https://stackoverflow.com/questions/6234405
    def handle_exception(exc_type, exc_value, exc_traceback):
        """handle and log uncaught eceptions"""

        # ignore keyboard interrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Uncaught Exception:", exc_info=(exc_type, exc_value, exc_traceback))
        app.exit(1)

    sys.excepthook = handle_exception

    theme_name = None
    if len(sys.argv) > 1:
        theme_name = sys.argv[1]
    app, window = gui.create_ui(TaskThreaded(), theme_name)
    window.update_widgets()
    ret = app.exec()

    if ret != 0:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = f.read()
        ed = gui.ErrorDialog(log)
        ed.exec()
        app.exit(2)

if __name__ == "__main__":
    main()
