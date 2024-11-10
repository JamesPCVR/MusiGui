import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import traceback
import json
import os
import yt_dlp
import formatting
import tooltip
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1)

AUDIOQUALITYOPTIONS = ('320 Kbps', '240 Kbps', '160 Kbps', '128 Kbps', '96 Kbps')
IMAGESIZEOPTIONS    = (256, 8192)
ATTACHIMAGEOPTIONS  = ('youtube-dl', 'Manual select')
UPSCALEROPTIONS     = ('RealSR', 'Waifu2x', 'SRMD', 'None')
DOWNSCALEROPTIONS   = ('Lanczos 8x8', 'Bicubic 4x4', 'Area', 'Bilinear', 'Nearest-neighbour', 'None')

DATAJSON = 'data.json'
JSONDEFAULT = {
    'audio_quality':        AUDIOQUALITYOPTIONS[0],
    'target_image':         1024,
    'attach_single':        ATTACHIMAGEOPTIONS[0],
    'attach_album':         ATTACHIMAGEOPTIONS[1],
    'enable_scaling':       True,
    'upscaler':             UPSCALEROPTIONS[3],
    'downscaler':           DOWNSCALEROPTIONS[0],
    'overwrite':            True,
    'download_covers':      True,
    'download_directory':   '',
    'upscaler_directory':   ''
}
IGNOREDURLS = ['', ' ']

# Thrown in the middle of the progress callback
# if the window has been destroyed and we need to unwind the yt_dlp stack
class CancelDownload(Exception):
    pass

class DownloadUI:
    def __init__(self, parent: tk.Tk) -> None:
        # main setup
        self.parent = parent
        self.mainframe = mainframe  = ttk.Frame(parent)
        mainframe.pack_configure(fill=tk.BOTH, expand=tk.YES, anchor=tk.N)

        self.pad = 5

        # configure
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        kwargs = {'sticky': tk.NSEW, 'padx': self.pad, 'pady': self.pad}

        mainframe.grid_columnconfigure(0, weight=1)
        mainframe.grid_rowconfigure(1, weight=1)

        self.jsondata = self.get_json_data()

        # create widgets
        self.directories    = Directories(mainframe, self.jsondata)
        self.main           = Main(mainframe)
        self.options        = Options(mainframe, self.jsondata)
        self.progressbars   = ProgressBars(mainframe, self)

        # place widgets
        self.directories.grid       (row=0, column=0, **kwargs)
        self.main.grid              (row=1, column=0, **kwargs, rowspan=4)
        self.options.grid           (row=0, column=1, **kwargs, rowspan=2)
        self.progressbars.grid          (row=3, column=1, **kwargs)

        parent.wm_protocol("WM_DELETE_WINDOW", self.exit)
    
    def save_data(self) -> None:
        savedata = {
            'audio_quality':        self.options.audioqualityvariable.get(),
            'target_image':         self.options.imagesizevariable.get(),
            'attach_single':        self.options.attachsingleimagesvariable.get(),
            'attach_album':         self.options.attachalbumimagesvariable.get(),
            'enable_scaling':       self.options.scalingvariable.get(),
            'upscaler':             self.options.upscalervariable.get(),
            'downscaler':           self.options.downscalervariable.get(),
            'overwrite':            self.options.overwritevariable.get(),
            'download_covers':      self.options.downloadcoversvariable.get(),
            'download_directory':   self.directories.downloaddirectoryvariable.get(),
            'upscaler_directory':   self.directories.upscalerdirectoryvariable.get()
        }
        with open(DATAJSON, 'w') as data:
            json.dump(savedata, data, indent=4)
    
    def exit(self) -> None:
        self.save_data()
        self.mainframe = None # frame is nulled, ongoing downloads will cancel
        self.parent.destroy()
    
    def get_json_data(self) -> dict:
        try:
            data = json.load(open(DATAJSON, 'r'))
            # DATAJSON exists
            if set(data) != set(JSONDEFAULT):
                # DATAJSON does not contain correct data
                for key in JSONDEFAULT.keys():
                    if key not in data:
                        data[key] = JSONDEFAULT[key]
            return data
        except FileNotFoundError:
            # DATAJSON does not exist
            return JSONDEFAULT

    def download_songs(self) -> None:
        # check for errors
        if self.options.upscalervariable.get() != 'None' and self.options.downscalervariable.get() != 'None': # upscaling disabled, no need to check for models
            modeldirectory = self.directories.upscalerdirectoryvariable.get() + formatting.UPSCALERS[self.options.upscalervariable.get()]
            if not os.path.exists(modeldirectory):
                action = messagebox.askyesno(title='Could not find upscaler', message=f'Could not find {self.options.upscalervariable.get()} at\n{modeldirectory}\nContinue anyway?')
                if not action:
                    return

        # disable widgets
        for widget in self.options.widgets + self.directories.widgets + self.progressbars.widgets:
            widget.configure(state='disabled')
        self.mainframe.update()

        try:
            # collect urls from gui, pack into list to give to yt-dl
            self.save_data()
            urls = self.main.linkstext.get('1.0', tk.END).split('\n')[:-1]

            cleanedurls = [url for url in urls if url not in IGNOREDURLS]
            if len(cleanedurls) == 0:
                raise ZeroDivisionError('URL list empty')
            
            self.set_progress_bar(0, len(cleanedurls))

            # initialise yt-dl
            ytlogger = YtLogger(self, self.progressbars)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': self.directories.downloaddirectoryvariable.get() + '/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': int(self.options.audioqualityvariable.get().removesuffix(' Kbps')) # ffmpeg issues
                }],
                'writethumbnail': self.options.downloadcoversvariable.get(),
                'progress_hooks': [self.yt_progress],
                'logger': ytlogger
            }
            self.ydl = yt_dlp.YoutubeDL(ydl_opts)
            self.ydl.add_progress_hook(self.yt_progress)

            # download each item in turn
            try:
                for i, url in enumerate(cleanedurls):
                    res = self.download_each(self.ydl, url)
                    if res == 1:
                        break
                    self.set_progress_bar(i+1, len(cleanedurls))

                if res == 0:
                    messagebox.showinfo(title=None, message='Download(s) finished')

                del self.ydl
            
            except yt_dlp.DownloadError as e:
                self.error_message('Youtube-DL Error', e)
        
        except Exception as e:
            self.error_message('Script Error', e)
        
        # enable widgets
        for widget in self.options.widgets + self.directories.widgets + self.progressbars.widgets:
            widget.configure(state='normal')
        self.mainframe.update()
    
    def download_each(self, yt: yt_dlp.YoutubeDL, url: str) -> None:
        try:
            infodict = yt.extract_info(url, download=True)
            with open('dump.json', 'w') as f:
                json.dump(infodict, f, indent=4)
            settings = self.get_json_data()
            directory = None
            linktype = 'album' if infodict.get('entries') else 'single'
            if (
                linktype == 'single' and settings['attach_single'] == ATTACHIMAGEOPTIONS[1]
            ) or (
                linktype == 'album' and settings['attach_album'] == ATTACHIMAGEOPTIONS[1]
            ):
                directory = filedialog.askopenfilename(initialdir=settings['download_directory'], title=f'Cover art {url}', filetypes=(('Image files', '.jpg'), ('Image files', 'png'))).replace('/', '\\')
            formatting.format_files(infodict, settings, directory)
            return 0
        except CancelDownload:
            messagebox.showerror(title=None, message='Download(s) cancelled')
            return 1
        except Exception as e:
            self.error_message('Formatting Error', e)
            messagebox.showinfo(title='Skip', message='Skipping erroneous track')
            return 2

    def yt_progress(self, kwargs: dict[str, object]) -> None:
        # if frame was destroyed, cancel download
        if self.mainframe is None:
            raise CancelDownload()

        # keep the gui somewhat responsive during download
        self.mainframe.update()

    def set_progress_bar(self, position, total) -> None:
        self.progressbars.totalprogresslabelvariable.set(f'{position}/{total}')
        self.progressbars.totalprogressbarvariable.set(position/total*100)
    
    def error_message(self, title: str, e: Exception) -> None:
        tracebackstring = ''.join(traceback.format_tb(e.__traceback__))
        messagebox.showerror(title=title, message=f'{type(e).__name__}: {str(e)}\n\nTRACEBACK:\n{tracebackstring}')

class YtLogger:
    # this is one way to do it
    def __init__(self, parent: ttk.Frame, progressbars: ttk.Frame):
        self.parent = parent
        self.progressbars = progressbars
        self.done = 0
        self.total = 0
    
    def debug(self, msg):
        print(msg)
        if '[download]' in msg:
            if 'Downloading item' in msg:
                indv = msg.split('m')
                self.done = int(indv[2].removesuffix('\x1b[0')) - 1
                self.total = int(indv[4].removesuffix('\x1b[0'))
                self.progressbars.albumprogresslabelvariable.set(f'{self.done}/{self.total}')
                self.progressbars.albumprogressbarvariable.set(self.done/self.total*100)
            if ('100%' in msg) and (self.done+1 == self.total):
                self.progressbars.albumprogresslabelvariable.set(f'{self.total}/{self.total}')
                self.progressbars.albumprogressbarvariable.set(100)
        self.update_frame()
    
    def info(self, msg):
        print('[info]', msg)
        self.update_frame()
    
    def warning(self, msg):
        print('[warning]', msg)
        self.update_frame()
    
    def error(self, msg):
        print('[error]', msg)
        self.update_frame()
    
    def update_frame(self):
        if self.parent.mainframe is None:
            raise CancelDownload()
        self.parent.mainframe.update()

class Main(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent
        self.pad = 5
        self.create_widgets()
    
    def create_widgets(self) -> None:
        # build widgets
        linkslabel = ttk.Label(self, text='Seperate URLs should go on their own line\nIt\'s fine to mix albums/playlists/EPs with singles\nURLs don\'t have to come from the same source')
        helpbutton = ttk.Button(self, text='Help', command=self.show_help)
        tooltip.Tooltip(helpbutton, "Need help? I don't blame you")
        self.linkstext = tk.Text(self)

        # configure
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        kwargs = {'padx': self.pad, 'pady': self.pad}

        # lay out widgets
        linkslabel.grid     (row=0, column=0, sticky=tk.EW, **kwargs)
        helpbutton.grid     (row=0, column=1, sticky=tk.EW, **kwargs)
        self.linkstext.grid (row=1, column=0, sticky=tk.NSEW, **kwargs, columnspan=2)

        self.linkstext.focus_set()
    
    def show_help(self) -> None:
        with open('help.txt', 'rb') as f:
            messagebox.showinfo(title='You cried for help!', message=f.read())

class ProgressBars(ttk.Frame):
    def __init__(self, parent, upperparent) -> None:
        super().__init__(parent)
        self.parent = parent
        self.upperparent = upperparent
        self.pad = 5

        self.albumprogresslabelvariable     = tk.StringVar(value='Album')
        self.albumprogressbarvariable       = tk.IntVar(value=0)
        self.totalprogresslabelvariable     = tk.StringVar(value='Total')
        self.totalprogressbarvariable       = tk.IntVar(value=0)

        self.widgets = self.create_widgets()
    
    def create_widgets(self) -> None:
        # build widgets
        albumprogresslabel  = ttk.Label(self, textvariable=self.albumprogresslabelvariable)
        albumprogressbar    = ttk.Progressbar(self, orient='horizontal', mode='determinate', variable=self.albumprogressbarvariable)

        totalprogresslabel  = ttk.Label(self, textvariable=self.totalprogresslabelvariable)
        totalprogressbar    = ttk.Progressbar(self, orient='horizontal', mode='determinate', variable=self.totalprogressbarvariable)

        downloadbutton = ttk.Button(self, text='Download', command=self.upperparent.download_songs)

        # configure
        self.grid_columnconfigure(1, weight=1)
        kwargs = {'padx': self.pad, 'pady': self.pad, 'sticky': tk.EW}

        # lay out widgets
        albumprogresslabel.grid     (row=0, column=0, **kwargs)
        albumprogressbar.grid       (row=0, column=1, **kwargs)
        totalprogresslabel.grid     (row=1, column=0, **kwargs)
        totalprogressbar.grid       (row=1, column=1, **kwargs)
        downloadbutton.grid         (row=2, column=0, **kwargs, columnspan=2)

        return (
            downloadbutton,
        )
    
    def show_help(self) -> None:
        with open('help.txt', 'rb') as f:
            messagebox.showinfo(title='You cried for help!', message=f.read())

class Directories(ttk.Frame):
    def __init__(self, parent, jsondata) -> None:
        super().__init__(parent)
        self.parent = parent
        self.pad = 5

        self.downloaddirectoryvariable      = tk.StringVar(value=jsondata['download_directory'])
        self.upscalerdirectoryvariable      = tk.StringVar(value=jsondata['upscaler_directory'])

        self.widgets = self.create_widgets()

    def create_widgets(self) -> tuple:
        # create widgets
        downloaddirectorylabel = ttk.Label(self, text='Download directory')
        downloaddirectoryentry = ttk.Entry(self, textvariable = self.downloaddirectoryvariable)
        downloaddirectorybutton = ttk.Button(self, text='Select', command=lambda: self.pick_directory(self.downloaddirectoryvariable, 0))

        upscalerdirectorylabel = ttk.Label(self, text='Upscaler directory')
        upscalerdirectoryentry = ttk.Entry(self, textvariable = self.upscalerdirectoryvariable)
        upscalerdirectorybutton = ttk.Button(self, text='Select', command=lambda: self.pick_directory(self.upscalerdirectoryvariable, 1))

        # configure
        self.grid_columnconfigure(1, weight=1)
        kwargs = {'sticky': tk.EW, 'padx': self.pad, 'pady': self.pad}

        # place widgets
        downloaddirectorylabel.grid     (row=0, column=0, **kwargs)
        downloaddirectoryentry.grid     (row=0, column=1, **kwargs)
        downloaddirectorybutton.grid    (row=0, column=2, **kwargs)
        upscalerdirectorylabel.grid     (row=1, column=0, **kwargs)
        upscalerdirectoryentry.grid     (row=1, column=1, **kwargs)
        upscalerdirectorybutton.grid    (row=1, column=2, **kwargs)

        return (
            downloaddirectoryentry,
            downloaddirectorybutton,
            upscalerdirectoryentry,
            upscalerdirectorybutton
        )

    def pick_directory(self, var: tk.StringVar, type: str) -> str:
        titles = ['Select a download directory', 'Select an upscaler directory']
        var.set(filedialog.askdirectory(title=titles[type]))

class Options(ttk.Frame):
    def __init__(self, parent: ttk.Frame, jsondata: dict) -> None:
        super().__init__(parent)
        self.parent = parent
        self.pad = 5

        self.audioqualityvariable           = tk.StringVar(value=jsondata['audio_quality'])
        self.attachsingleimagesvariable     = tk.StringVar(value=jsondata['attach_single'])
        self.attachalbumimagesvariable      = tk.StringVar(value=jsondata['attach_album'])
        self.imagesizevariable              = tk.StringVar(value=jsondata['target_image'])
        self.upscalervariable               = tk.StringVar(value=jsondata['upscaler'])
        self.downscalervariable             = tk.StringVar(value=jsondata['downscaler'])
        self.scalingvariable                = tk.IntVar(value=jsondata['enable_scaling'])
        self.overwritevariable              = tk.IntVar(value=jsondata['overwrite'])
        self.downloadcoversvariable         = tk.IntVar(value=jsondata['download_covers'])

        self.widgets = self.create_widgets()

    def create_widgets(self) -> tuple:
        # create widgets
        audioqualitylabel = ttk.Label(self, text='Preferred audio quality')
        audioqualityoptionmenu = ttk.OptionMenu(
            self,
            self.audioqualityvariable,
            self.audioqualityvariable.get(),
            *AUDIOQUALITYOPTIONS
        )
        tooltip.Tooltip(audioqualityoptionmenu, "Set the max bitrate, most will be limited to 128Kbps 'stream' quality")

        attachsingleimageslabel = ttk.Label(self, text='Cover art attach\nmethod for singles')
        attachsingleimagesoptionmenu = ttk.OptionMenu(
            self,
            self.attachsingleimagesvariable,
            self.attachsingleimagesvariable.get(),
            *ATTACHIMAGEOPTIONS
        )

        attachalbumimageslabel = ttk.Label(self, text='Cover art attach\nmethod for albums')
        attachalbumimagesoptionmenu = ttk.OptionMenu(
            self,
            self.attachalbumimagesvariable,
            self.attachalbumimagesvariable.get(),
            *ATTACHIMAGEOPTIONS
        )

        enablescalinglabel = ttk.Label(self, text="Enable image scaling")
        enablescalingcheckbutton = ttk.Checkbutton(self, text=None, variable=self.scalingvariable, command=self.enable_scaling)
        tooltip.Tooltip(enablescalingcheckbutton, 'select to enable image scaling')

        imagesizelabel = ttk.Label(self, text='Target image size\n(Square N x N)')
        imagesizespinbox = ttk.Spinbox(
            self,
            from_ = IMAGESIZEOPTIONS[0],
            to = IMAGESIZEOPTIONS[1],
            textvariable = self.imagesizevariable,
            width = 3,
            wrap = False
        )
        imagesizespinbox.bind('<Return>', self.validate_spinbox)
        tooltip.Tooltip(imagesizespinbox, 'Requires "Enable image scaling"')

        upscalerlabel = ttk.Label(self, text='Upscale method\n(NCNN-Vulkan)')
        upscaleroptionmenu = ttk.OptionMenu(
            self,
            self.upscalervariable,
            self.upscalervariable.get(),
            *UPSCALEROPTIONS
        )
        tooltip.Tooltip(upscaleroptionmenu, 'Select the ML model to upscale cover art\nRequires "Enable image scaling"')

        downscalerlabel = ttk.Label(self, text='Downscale method')
        downscaleroptionmenu = ttk.OptionMenu(
            self,
            self.downscalervariable,
            self.downscalervariable.get(),
            *DOWNSCALEROPTIONS
        )
        tooltip.Tooltip(downscaleroptionmenu, '"Area" gives moiré-free results\nRequires "Enable image scaling"')

        overwritelabel = ttk.Label(self, text='Overwrite duplicates')
        overwritecheckbutton = ttk.Checkbutton(self, text=None, variable=self.overwritevariable)
        tooltip.Tooltip(overwritecheckbutton, 'Overwrite duplicate files, otherwise skip. Best left enabled')

        # configure
        kwargs = {'sticky': tk.EW, 'padx': self.pad, 'pady': self.pad}

        # place widgets
        audioqualitylabel.grid              (row=0, column=0, **kwargs)
        audioqualityoptionmenu.grid         (row=0, column=1, **kwargs)
        attachsingleimageslabel.grid        (row=1, column=0, **kwargs)
        attachsingleimagesoptionmenu.grid   (row=1, column=1, **kwargs)
        attachalbumimageslabel.grid         (row=2, column=0, **kwargs)
        attachalbumimagesoptionmenu.grid    (row=2, column=1, **kwargs)
        enablescalinglabel.grid             (row=3, column=0, **kwargs)
        enablescalingcheckbutton.grid       (row=3, column=1, **kwargs)
        imagesizelabel.grid                 (row=4, column=0, **kwargs)
        imagesizespinbox.grid               (row=4, column=1, **kwargs)
        upscalerlabel.grid                  (row=5, column=0, **kwargs)
        upscaleroptionmenu.grid             (row=5, column=1, **kwargs)
        downscalerlabel.grid                (row=6, column=0, **kwargs)
        downscaleroptionmenu.grid           (row=6, column=1, **kwargs)
        overwritelabel.grid                 (row=7, column=0, **kwargs)
        overwritecheckbutton.grid           (row=7, column=1, **kwargs)

        return (
            audioqualityoptionmenu,
            attachsingleimagesoptionmenu,
            attachalbumimagesoptionmenu,
            enablescalingcheckbutton,
            imagesizespinbox,
            upscaleroptionmenu,
            downscaleroptionmenu,
            overwritecheckbutton
        )
    
    def enable_scaling(self):
        state = 'normal' if self.scalingvariable.get() == 1 else 'disabled'
        for widget in self.widgets[4:7]:
            widget.configure(state=state)

    def validate_spinbox(self, a: tk.Event) -> None:
        try:
            value = int(self.imagesizevariable.get())
            if value > IMAGESIZEOPTIONS[1]: # too big
                self.imagesizevariable.set(IMAGESIZEOPTIONS[1])
            elif value < IMAGESIZEOPTIONS[0]: # too smol
                self.imagesizevariable.set(IMAGESIZEOPTIONS[0])

        except ValueError:
            self.imagesizevariable.set(JSONDEFAULT['target_image'])

def main() -> None:
    window = tk.Tk()
    window.title('MusiGui')
    window.iconbitmap('musigui.ico')
    window.geometry('1000x550')
    window.minsize(width=770, height=510)

    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('TSpinbox', arrowsize=16)

    DownloadUI(window).mainframe.mainloop()

if __name__ == '__main__':
    main()
