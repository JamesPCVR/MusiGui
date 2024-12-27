import sys
import re
import json
import typing
import ctypes

from PySide6.QtCore import (
    QThread, Signal
)
from PySide6.QtGui import (
    QCloseEvent, QIcon
)
from PySide6.QtWidgets import (
    QApplication, QWidget,
    QDialog, QFileDialog,
    QSizePolicy,
    QLineEdit, QTextEdit, QLabel,
    QPushButton, QComboBox, QSpinBox,
    QGroupBox, QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout,
    QProgressBar
)

from showinfm import show_in_file_manager

MARGINS = 10
WIDTH = 1000
HEIGHT = 400

RET_CANCEL = 0
RET_CLOSE = 1

TITLE = "MusiGui"
ICON_DIR = "assets\\musigui.ico"
STYLE_PATH = "assets\\style.qss"
THEMES_PATH = "assets\\themes.json"

COVER_ATTACH_SINGLE = [
    "Automatic"
]
COVER_ATTACH_GROUP = [
    "Individual",
    "Most Common"
]

class DownloadUI(QWidget):
    """Main application."""
    progress_changed = Signal(str, dict)

    def __init__(self, task:QThread) -> None:
        super().__init__()
        self.task = task
        if task is not None:
            self.task.set_signal(self.progress_changed)

        self.text_edit:QTextEdit = None
        self.bar_partial:QProgressBar = None
        self.bar_total:QProgressBar = None
        self.button_down:QPushButton = None
        self.label_updates:QLabel = None

        self.widgets = []

        icon = QIcon(ICON_DIR)
        self.setWindowIcon(icon)
        self.setWindowTitle(TITLE)
        self.build()
        self.progress_changed.connect(self.update_progress)
        self.resize(WIDTH, HEIGHT)
        self.text_edit.setFocus()

    def build(self) -> None:
        """Create the UI."""
        widget_dirs = self._build_directories()
        widget_url = self._build_url()

        layout_left = QVBoxLayout()
        layout_left.addWidget(widget_dirs)
        layout_left.addSpacing(MARGINS)
        layout_left.addWidget(widget_url)

        layout_image = self._build_image()
        layout_download = self._build_download()

        layout_right = QVBoxLayout()
        layout_right.addWidget(layout_image)
        layout_right.addWidget(QWidget())
        layout_right.addSpacing(MARGINS)
        layout_right.addWidget(layout_download)

        layout_sides = QHBoxLayout()
        layout_sides.addLayout(layout_left)
        layout_sides.addSpacing(MARGINS)
        layout_sides.addLayout(layout_right)

        self.setLayout(layout_sides)

    def _build_directories(self) -> QGroupBox:
        """Build the directory editor of the UI."""
        title = QLabel("Output")
        title.setObjectName("title")
        title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        button_dir_out = QPushButton("Select")
        button_dir_out.setFixedWidth(80)
        button_dir_out.clicked.connect(
            lambda: self.update_content(button_dir_out)
        )
        self._add_active_widget(
            button_dir_out,
            "button",
            "directories",
            ("download", "output_directory")
        )

        line_edit_dir_out = QLineEdit()
        line_edit_dir_out.setMinimumWidth(250)
        line_edit_dir_out.editingFinished.connect(
            lambda: self.update_content(line_edit_dir_out)
        )
        line_edit_dir_out.setToolTip("Directory to download files to")
        self._add_active_widget(
            line_edit_dir_out,
            "line",
            "directories", 
            ("download", "output_directory")
        )

        button_dir_open = QPushButton("Open")
        button_dir_open.setFixedWidth(80)
        button_dir_open.clicked.connect(
            lambda: show_in_file_manager(line_edit_dir_out.text())
        )
        self._add_active_widget(
            button_dir_out,
            "button",
            "directories",
            ("download", "output_directory")
        )

        grid = QGridLayout()
        grid.addWidget(button_dir_out, 0, 0)
        grid.addWidget(line_edit_dir_out, 0, 1)
        grid.addWidget(button_dir_open, 0, 2)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(grid)

        group = QGroupBox()
        group.setLayout(layout)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return group

    def _build_url(self) -> QGroupBox:
        """Build the URL editor of the UI."""
        title = QLabel("URL List")
        title.setObjectName("title")
        title.setToolTip("Skill issue")
        title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlaceholderText("Paste links here")
        self._add_active_widget(
            self.text_edit,
            "text",
            "url",
            None
        )

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.text_edit)

        group = QGroupBox()
        group.setLayout(layout)
        return group

    def _build_image(self) -> QGroupBox:
        """Build the image settings editor of the UI."""
        title = QLabel("Image")
        title.setObjectName("title")
        title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        combo_attach_single = QComboBox()
        combo_attach_single.addItems(COVER_ATTACH_SINGLE)
        combo_attach_single.setToolTip(
            """Manual mode will return in a future update.
Select how to choose cover art for singles:
Automatic - Use the original image."""
        )
        combo_attach_single.currentIndexChanged.connect(
            lambda: self.update_content(combo_attach_single)
        )
        self._add_active_widget(
            combo_attach_single,
            "combo",
            "image",
            ("image", "add_image_single"),
            COVER_ATTACH_GROUP
        )

        combo_attach_group = QComboBox()
        combo_attach_group.addItems(COVER_ATTACH_GROUP)
        combo_attach_group.setToolTip(
            """Manual mode will return in a future update.
Select how to choose cover art for albums or playlists:
Individual - Use the original image for each song.
Most common - Use the most common image for all the
    songs in the group."""
        )
        combo_attach_group.currentIndexChanged.connect(
            lambda: self.update_content(combo_attach_group)
        )
        self._add_active_widget(
            combo_attach_group,
            "combo",
            "image", 
            ("image", "add_image_group"),
            COVER_ATTACH_GROUP
        )

        spin_target_image = QSpinBox()
        spin_target_image.setRange(100, 9999)
        spin_target_image.setValue(1024)
        spin_target_image.setSuffix("px")
        spin_target_image.setSingleStep(100)
        spin_target_image.valueChanged.connect(
            lambda: self.update_content(spin_target_image)
        )
        self._add_active_widget(
            spin_target_image,
            "spin",
            "image", 
            ("image", "image_size_target")
        )

        ai_method = ["None"]
        if self.task is not None:
            ai_method.extend(self.task.get_valid_ai_models())
        combo_ai_method = QComboBox()
        combo_ai_method.addItems(ai_method)
        combo_ai_method.currentIndexChanged.connect(
            lambda: self.update_content(combo_ai_method)
        )
        self._add_active_widget(
            combo_ai_method,
            "combo",
            "image", 
            ("image", "ai_method"),
            ai_method
        )

        scale_methods = ["Do not Scale"]
        if self.task is not None:
            scale_methods.extend(self.task.get_interpolation_methods())
        combo_scale_method = QComboBox()
        combo_scale_method.addItems(scale_methods)
        combo_scale_method.currentIndexChanged.connect(
            lambda: self.update_content(combo_scale_method)
        )
        self._add_active_widget(
            combo_scale_method,
            "combo",
            "image", 
            ("image", "interpolate_method"),
            scale_methods
        )

        form = QFormLayout()
        form.addRow(self.tr("&Attach art for singles:"), combo_attach_single)
        form.addRow(self.tr("&Attach art for groups:"), combo_attach_group)
        form.addRow(self.tr("&Image size:"), spin_target_image)
        form.addRow(self.tr("&AI upscaling model:"), combo_ai_method)
        form.addRow(self.tr("Image scaling:"), combo_scale_method)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(form)

        group = QGroupBox()
        group.setLayout(layout)
        group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        group.setFixedWidth(350)
        return group

    def _build_download(self) -> QGroupBox:
        """Build the download interface of the UI."""
        title = QLabel("Download")
        title.setObjectName("title")
        title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.bar_partial = QProgressBar()
        # self.bar_partial.setFixedWidth(250)
        self.bar_partial.setMaximum(100)
        self.bar_partial.setTextVisible(False)

        self.bar_total = QProgressBar()
        # self.bar_total.setFixedWidth(250)
        self.bar_total.setMaximum(100)
        self.bar_total.setTextVisible(False)

        self.label_updates = QLabel()

        self.button_down = QPushButton("Start")
        self.button_down.setObjectName("accent")
        self.button_down.clicked.connect(self.run_task)
        self._add_active_widget(
            self.button_down,
            "button",
            "download",
            None
        )

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.bar_partial)
        layout.addWidget(self.bar_total)
        layout.addWidget(self.label_updates)
        layout.addWidget(self.button_down)

        group = QGroupBox()
        group.setLayout(layout)
        group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        group.setFixedWidth(350)
        return group

    def _add_active_widget(
            self,
            ref:QWidget,
            _type:str,
            loc:str,
            var:tuple[str],
            opt:list=None
        ) -> None:
        """Append the widget to the UI list of active widgets."""
        self.widgets.append({
            "object": ref,
            "type": _type,
            "location": loc,
            "variable": var,
            "options": opt
        })

    def update_content(self, obj:QWidget|None=None) -> None:
        """Update the parameters for the download task."""
        data = self.task.task.get_config()
        for widget_data in self.widgets:
            widget = widget_data["object"]

            # set all if `None`, otherwise only specified
            if obj is not None and widget != obj:
                continue

            dl = widget_data["variable"]
            if dl is None:
                continue

            d = None

            match widget_data["type"]:
                case "line":
                    widget:QLineEdit
                    d = widget.text()
                case "combo":
                    widget:QComboBox
                    d = widget.currentIndex()
                case "spin":
                    widget:QSpinBox
                    d = widget.value()
                case "button":
                    widget:QPushButton
                    dialog = QFileDialog(self)
                    dialog.setFileMode(QFileDialog.FileMode.Directory)
                    dialog.setViewMode(QFileDialog.ViewMode.List)
                    if dialog.exec():
                        d = dialog.selectedFiles()[0].replace("/", "\\")
                    else:
                        return

            if d is not None:
                data[dl[0]][dl[1]] = d

            # if single object is specified, no need to check others
            if obj is not None:
                break

        self.task.task.set_config(data)
        self.task.task.save_config()

        # needed for when a widget sets another
        self.update_widgets(obj)

    def update_widgets(self, except_:QWidget=None) -> None:
        """update the widget content with data"""
        data = self.task.task.get_config()
        for widget_data in self.widgets:
            widget = widget_data["object"]
            if widget == except_:
                continue

            dl = widget_data["variable"]
            if dl is None:
                continue

            d = data[dl[0]][dl[1]]

            match widget_data["type"]:
                case "line":
                    widget:QLineEdit
                    widget.setText(str(d))
                case "combo":
                    widget:QComboBox
                    if dl == ("image", "ai_method"):
                        for _ in data["image"]["ai_commands"]:
                            widget.removeItem(1)
                        items = self.task.get_valid_ai_models()
                        widget.addItems(items)
                    widget.setCurrentIndex(int(d))
                case "spin":
                    widget:QSpinBox
                    widget.setValue(int(d))

    def run_task(self) -> None:
        """Final checks and run task."""
        # check a task exists
        if self.task is None:
            return

        # check url list is not empty
        urls = self._get_urls()
        if len(urls) == 0:
            return

        self.set_read_only(True)
        self.bar_partial.setValue(0)
        self.bar_total.setValue(0)

        self.task.set_urls(urls)
        self.task.start()

    def _get_urls(self) -> list[str]:
        """get url list from th UI."""
        text = self.text_edit.toPlainText()
        split_text = text.split("\n")
        urls = [url for url in split_text if url != ""]
        return urls

    def update_progress(self, msg:str, data:dict[str,int]) -> None:
        """Update the progress bars."""
        if data["error"] is True:
            self.set_read_only(False)
            return

        self.bar_partial.setValue(data["partial"])
        self.bar_total.setValue(data["total"])

        # remove ansi escape sequences
        msg = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", '', msg)
        # remove "[...]" prefix (and other)
        msg = re.sub(r"\[.*?\]", "", msg)

        max_len = 40
        if len(msg) > max_len:
            self.label_updates.setText(msg[:max_len] + "...")
        else:
            self.label_updates.setText(msg)

        if data["total"] == 100:
            self.set_read_only(False)

    def set_read_only(self, state:bool=False) -> None:
        """Set all the UI widget read-only state."""
        for widget_data in self.widgets:
            widget = widget_data["object"]
            match widget_data["type"]:
                case "line":
                    widget:QLineEdit
                    widget.setReadOnly(state)
                case "combo":
                    widget:QComboBox
                    widget.setDisabled(state)
                case "spin":
                    widget:QSpinBox
                    widget.setDisabled(state)
                case "text":
                    widget:QTextEdit
                    # widget.setReadOnly(state)
                    widget.setDisabled(state)
                case "button":
                    widget:QPushButton
                    widget.setDisabled(state)

    def closeEvent(self, event:QCloseEvent) -> None: #pylint: disable=C0103
        """Close running tasks and exit."""
        if self.task is None:
            event.accept()

        condition = RET_CLOSE
        if self.task.isRunning():
            dialog = CloseDialog(self.task)
            dialog.quit_task()
            dialog.exec()
            condition = dialog.result()

        if condition is RET_CLOSE:
            event.accept()
        else:
            event.ignore()

class CloseDialog(QDialog):
    """Close Dialog."""

    def __init__(self, task:QThread):
        super().__init__()

        self.task = task

        self.setWindowTitle("Quit")
        message = QLabel("Stopping process: Download")

        progress_bar = QProgressBar()
        progress_bar.setMaximum(0)

        terminate_button = QPushButton("Terminate")
        terminate_button.setObjectName("warn")
        terminate_button.clicked.connect(self.kill_task)

        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addWidget(progress_bar)
        layout.addWidget(terminate_button)

        group = QGroupBox()
        group.setLayout(layout)
        layout2 = QVBoxLayout()
        layout2.addWidget(group)
        self.setLayout(layout2)

    def quit_task(self) -> None:
        """Stop a task with a popup."""
        self.task.finished.connect(self.accept)
        self.task.destroyed.connect(self.accept)

        self.task.exit(1)
        self.setResult(RET_CLOSE)

    def kill_task(self) -> None:
        """Kill the program."""
        self.task.setTerminationEnabled(True)
        self.task.terminate()
        self.task.wait()

    def closeEvent(self, event:QCloseEvent) -> None: #pylint: disable=C0103
        """Close window is closed, cancel"""
        self.setResult(RET_CANCEL)
        event.accept()

def get_style(theme_name:str|None=None) -> str:
    """
    Get the stylesheet and set the variables based on a theme.
    
    :param sheet_path:
        Path to the style sheet.

    :returns:
        Style sheet with variables replaced with values or empty if failed.
    """
    with open(THEMES_PATH, "r", encoding="utf-8") as f:
        themes = json.load(f)

    if theme_name is None:
        theme_name = themes["selected"]

    themes:dict[str,dict[str,typing.Any]]
    if theme_name not in themes:
        print(f"[startup] {theme_name} theme not found, defaulting to light.")
        theme_name = "light"

    with open(STYLE_PATH, "r", encoding="utf-8") as f:
        style_sheet = f.read()

    theme = themes[theme_name]
    for name in theme:
        var = f"<{name}>"
        style_sheet = style_sheet.replace(var, str(theme[name]))

    return style_sheet

def create_ui(task, theme_name:str=None) -> tuple[QApplication,DownloadUI]:
    """Create the `DownloadUI`."""
    # set taskbar icon correctly, taken from:
    # https://stackoverflow.com/questions/1551605
    app_id = "jamespcvr.musigui.1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id) #pylint: disable=C0301

    _app = QApplication(sys.argv)
    _window = DownloadUI(task)
    _window.show()

    _style = get_style(theme_name)
    _app.setStyleSheet(_style)

    return _app, _window

if __name__ == "__main__":
    app, wind = create_ui(None, "light")
    app.exec()
