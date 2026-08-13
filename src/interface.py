from __future__ import annotations
import logging
import traceback

import sys
import pathlib

from configparser import ConfigParser
from PySide6.QtCore import Qt, QObject, QThreadPool, QRunnable, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QProgressBar,
)

import download


logger = logging.getLogger(__name__)


RELPATH_CONFIG = pathlib.Path("cfg/musigui.cfg")
RELPATH_ASSETS = pathlib.Path("assets")
RELPATH_NOIMAGE = RELPATH_ASSETS / "musigui.png"

DEFAULT_CONFIG = {"output": "tmp"}

META_READY = "MetadataParser"
IMAGE_READY = "ThumbnailsConvertor"
FINISHED = "finished"

# progress stages in name, display name, weight groups
# where weight is how finished it is once that stage is done
PROGRESS_STAGES: list[str, str, float] = [
    ("MetadataParser", "Processing metadata", 0.05),
    ("ThumbnailsConvertor", "Converting thumbnail", 0.15),
    ("Download", "Downloading", 0.55),
    ("FixupM4a", "Remuxing Stream", 0.6),
    ("FixupM3u8", "Remuxing Stream", 0.6),
    ("ExtractAudio", "Processing Audio", 0.8),
    ("Metadata", "Attaching Metadata", 0.85),
    ("EmbedThumbnail", "Attaching Image", 0.9),
    ("MoveFiles", "Moving Files", 1),
]


def calculate_progress(stage: str, fraction: float = 0) -> tuple[float, str]:
    """returns a 0-1 float representing total progress."""
    _, name, weight = next(
        (s for s in PROGRESS_STAGES if s[0].startswith(stage)), ("", "Unknown", 0)
    )

    if weight == 0:
        logger.error("Unknown progress stage %s", stage)
        return 0.0, name

    index = next((i for i, s in enumerate(PROGRESS_STAGES) if s[0] == stage), None)
    weight_prev = 0 if index is None or index == 0 else PROGRESS_STAGES[index - 1][2]

    diff = weight - weight_prev
    progress = weight_prev + diff * fraction

    return progress, name


class ScrollableWidget(QWidget):
    def __init__(self, text="ScrollableWidget", parent=None):
        super().__init__(parent)

        self._container = QWidget()

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._container)

        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(text)

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._scroll)

        self.setLayout(self._main_layout)

    def setText(self, text: str):
        self._label.setText(text)

    def addWidget(self, widget: QWidget):
        self._layout.addWidget(widget)


class TaskWidget(QWidget):
    """A dumb widget purely to show thread progress."""

    _height = 30

    def __init__(self, url: str, parent=None):
        super().__init__(parent)

        self.url = url

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._image_lbl = QLabel()
        self.setImage(RELPATH_NOIMAGE)
        self._layout.addWidget(self._image_lbl)

        self._name_lbl = QLabel("...")
        self._name_lbl.setFixedWidth(150)
        self._layout.addWidget(self._name_lbl)

        self._progress_bar = QProgressBar()
        self._layout.addWidget(self._progress_bar)

        self._process_lbl = QLabel("Waiting to start")
        self._process_lbl.setFixedWidth(140)
        self._layout.addWidget(self._process_lbl)

    def setTitle(self, title: str):
        """Change the title."""
        self._name_lbl.setText(title)

    def setImage(self, path: pathlib.Path):
        """Change the cover art image shown."""
        image = QPixmap(path)
        image_scaled = image.scaledToHeight(self._height)
        self._image_lbl.setPixmap(image_scaled)

    def progressUpdate(self, progress: tuple[float, str]):
        """Display updates to the progress bar."""

        fraction, process = progress
        self._progress_bar.setValue(fraction * 100)
        self._process_lbl.setText(process)


class GroupTaskWidget(QWidget):
    """Handles task setup and queues tasks on the main threadpool."""

    def __init__(self, mainapp: MainApp, parent=None):
        super().__init__(parent)

        self.mainapp = mainapp
        self._task_widgets = []
        self._group_info = {}

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._header_layout)

        self._id_lbl = QLabel("ID here")
        self._header_layout.addWidget(self._id_lbl)

        self._url_lbl = QLabel("URL here")
        self._header_layout.addWidget(self._url_lbl)

    def configure(self, id_: int, url: str):
        logger.debug("Creating GroupTask id %s", id_)
        urls, group_info = download.expand_urls(url)
        self._group_info = group_info

        self._id_lbl.setText(f"Task {id_}")
        self._url_lbl.setText(group_info["title"])

        for i, url_ in enumerate(urls):
            logger.debug("Creating Task id %s index %s %s", id_, i, url_)
            tw = TaskWidget(url_)

            self._layout.addWidget(tw)
            self._task_widgets.append(tw)

            self.mainapp.queue_task(id_, url_, group_info, tw)


# modified example code
# https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class WorkerSignals(QObject):
    """Signals from a running worker thread.

    finished: int return code

    progress: tuple (progress_fraction, stage)

    meta_title_ready: str literal song title

    meta_image_ready: str relative image path"""

    finished = Signal(int)  # return code
    progress = Signal(tuple)  # (progress, stage)
    meta_title_ready = Signal(str)  # literal title
    meta_image_ready = Signal(str)  # image path


class DownloadWorker(QRunnable):
    """Inherits from QRunnable to handler worker thread setup, signals and wrap-up."""

    def __init__(self, id_: int, url: str, group_info: dict):
        super().__init__()

        self.id_ = id_
        self.url = url
        self.group_info = group_info
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """Initialise the runner function with passed args"""

        try:
            retcode = download.task(self.id_, self.url, self.dl_hook, self.pp_hook)
        except Exception as e:
            logger.error(
                "Thread working on job id %d has an uncaught exception\n%s", self.id_, e
            )
        finally:
            self.signals.progress.emit((1, "Done"))
            self.signals.finished.emit(retcode)

    def dl_hook(self, d: dict):
        progress = calculate_progress("Download", d["_percent"] / 100.0)
        self.signals.progress.emit(progress)

    def pp_hook(self, d: dict):
        process = d["postprocessor"]
        status = d["status"]

        if status == FINISHED:
            if process == META_READY:
                title = d["info_dict"]["title"]
                self.signals.meta_title_ready.emit(title)

            elif process == IMAGE_READY:
                path = None
                for thumb in d["info_dict"]["thumbnails"]:
                    if "filepath" in thumb:
                        path = thumb["filepath"]
                if path:
                    self.signals.meta_image_ready.emit(path)

        progress = calculate_progress(process, 1.0 if status == FINISHED else 0.0)
        self.signals.progress.emit(progress)


class MainApp(QMainWindow):
    def __init__(self, config: ConfigParser, w, h):
        super().__init__()

        self.resize(w, h)
        self.setWindowTitle("MusiGui")

        self.config = config
        self.threadpool = QThreadPool()
        logger.debug(
            "Created threadpool with %d threads", self.threadpool.maxThreadCount()
        )

        self._layout = QVBoxLayout()
        self._widget = QWidget()
        self._widget.setLayout(self._layout)
        self.setCentralWidget(self._widget)

        self.url_ledit = QLineEdit()
        self.url_ledit.setPlaceholderText("Paste URL here")
        self.url_ledit.editingFinished.connect(self.on_url_entered)
        self._layout.addWidget(self.url_ledit)

        self._task_scroll = ScrollableWidget("Tasks")
        self._layout.addWidget(self._task_scroll)

    def on_url_entered(self):
        url = self.url_ledit.text().strip()
        if url == "":
            return

        logger.debug("URL entered %s", url)

        _id = self.next_id()
        gtw = GroupTaskWidget(mainapp=self)
        self._task_scroll.addWidget(gtw)
        gtw.configure(_id, url)

    def next_id(self):
        out_path = pathlib.Path(self.config.get("User", "output"))
        if not out_path.exists():
            return 1
        try:
            free_id = 1 + max(
                int(p.name)
                for p in out_path.iterdir()
                if p.is_dir() and p.name.isdigit()
            )
        except ValueError:
            free_id = 1

        return free_id

    def queue_task(self, id_, url, group_info, widget: TaskWidget):
        logger.debug("Queueing thread")
        worker = DownloadWorker(id_, url, group_info)
        worker.signals.progress.connect(widget.progressUpdate)
        worker.signals.meta_title_ready.connect(widget.setTitle)
        worker.signals.meta_image_ready.connect(widget.setImage)
        self.threadpool.start(worker)
        logger.debug("There are %d active threads", self.threadpool.activeThreadCount())


def read_config():
    config = ConfigParser()
    config["User"] = DEFAULT_CONFIG

    if RELPATH_CONFIG.exists():
        config.read(RELPATH_CONFIG)
    else:
        with RELPATH_CONFIG.open("wt+", encoding="utf-8") as f:
            config.write(f)

    return config


def start_app(w: int = 400, h: int = 600):
    config = read_config()

    app = QApplication()
    win = MainApp(config, w, h)
    win.show()
    app.exec()
