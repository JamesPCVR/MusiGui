import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import youtube_dl
import json
import os
import formatting
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1)

AUDIOQUALITYOPTIONS = ('320 Kbps', '240 Kbps', '160 Kbps', '128 Kbps', '96 Kbps')
IMAGESIZEOPTIONS    = (
    '3000x3000',
    '2560x2560',
    '2048x2048',
    '1920x1920',
    '1600x1600',
    '1200x1200',
    '1024x1024',
    '680x680',
    '512x512',
    '500x500'
)
ATTACHIMAGEOPTIONS  = ('youtube-dl', 'Manual select')
UPSCALEROPTIONS     = ('RealSR', 'Waifu2x', 'SRMD')
DOWNSCALEROPTIONS   = ('Lanczos 8x8', 'Bicubic 4x4', 'Area', 'Bilinear', 'Nearest-neighbour')

DATAJSON = 'data.json'
JSONDEFAULT = {
    'audio_quality':        AUDIOQUALITYOPTIONS[1],
    'target_image':         IMAGESIZEOPTIONS[6],
    'attach_single':        ATTACHIMAGEOPTIONS[0],
    'attach_album':         ATTACHIMAGEOPTIONS[1],
    'upscaler':             UPSCALEROPTIONS[0],
    'downscaler':           DOWNSCALEROPTIONS[0],
    'overwrite':            True,
    'download_directory':   '',
    'upscaler_directory':   ''
}
IGNOREDURLS = ['', ' ']

# Thrown in the middle of the progress callback
# if the window has been destroyed and we need to unwind the youtube_dl stack
class CancelDownload(Exception):
    pass

class DownloadUI:
    def __init__(self, parent: tk.Tk) -> None:
        # main setup
        self.parent = parent
        self.mainframe = mainframe  = ttk.Frame(parent)
        downloadframe               = ttk.Frame(mainframe)
        mainframe.pack_configure(fill=tk.BOTH, expand=tk.YES, anchor=tk.N)
        downloadframe.grid_columnconfigure(0, weight=1)

        self.pad = 5

        # create variables
        self.progresslabelvariable = tk.StringVar(value='Progress')
        self.progressbarvariable   = tk.IntVar(value=0)

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

        multiprogresslabel  = ttk.Label(downloadframe, textvariable=self.progresslabelvariable)
        multiprogressbar    = ttk.Progressbar(downloadframe, orient='horizontal', mode='determinate', variable=self.progressbarvariable)
        self.downloadbutton = ttk.Button(downloadframe, text='Download', command=self.download_songs)

        # place widgets
        self.directories.grid       (row=0, column=0, **kwargs)
        self.main.grid              (row=1, column=0, **kwargs, rowspan=4)
        self.options.grid           (row=0, column=1, **kwargs, rowspan=2)
        downloadframe.grid          (row=3, column=1, **kwargs)

        multiprogresslabel.grid     (row=0, column=0, **kwargs)
        multiprogressbar.grid       (row=1, column=0, **kwargs)
        self.downloadbutton.grid    (row=2, column=0, **kwargs)

        parent.wm_protocol("WM_DELETE_WINDOW", self.exit)
    
    def save_data(self):
        savedata = {
            'audio_quality':        self.options.audioqualityvariable.get(),
            'target_image':         self.options.imagesizevariable.get(),
            'attach_single':        self.options.attachsingleimagesvariable.get(),
            'attach_album':         self.options.attachalbumimagesvariable.get(),
            'upscaler':             self.options.upscalervariable.get(),
            'downscaler':           self.options.downscalervariable.get(),
            'overwrite':            self.options.overwritevariable.get(),
            'download_directory':   self.directories.downloaddirectoryvariable.get(),
            'upscaler_directory':   self.directories.upscalerdirectoryvariable.get()
        }
        with open(DATAJSON, 'w') as data:
            json.dump(savedata, data, indent=4)
    
    def exit(self) -> None:
        self.save_data()
        # frame is nulled to let download jobs know gui is unavailable
        self.mainframe = None
        self.parent.destroy()
    
    def get_json_data(self):
        try:
            data = json.load(open(DATAJSON, 'r'))
            # DATAJSON exists
            if set(data) != set(JSONDEFAULT):
                # DATAJSON does not contain correct data
                return JSONDEFAULT
            return data
        except FileNotFoundError:
            # DATAJSON does not exist
            return JSONDEFAULT
    
    def yt_progress(self, kwargs: dict[str, object]) -> None:
        # if frame was destroyed, cancel download
        if self.mainframe is None:
            raise CancelDownload()

        # keep the gui somewhat responsive during download
        self.mainframe.update()
    
    def download(self, yt: youtube_dl.YoutubeDL, url: str) -> None:
        try:
            infodict = yt.extract_info(url, download=True)
            settings = self.get_json_data()
            directory = None
            linktype = 'album' if infodict.get('entries') else 'single'
            if (
                linktype == 'single' and settings['attach_single'] == ATTACHIMAGEOPTIONS[1]
            ) or (
                linktype == 'album' and settings['attach_album'] == ATTACHIMAGEOPTIONS[1]
            ):
                directory = filedialog.askopenfilename(initialdir='in\\', title=f'Cover art {url}', filetypes=(('Image files', '.jpg'), ('Image files', 'png'))).replace('/', '\\')
            formatting.format_files(infodict, settings, directory)
        except CancelDownload:
            pass

    def download_songs(self) -> None:
        # check for errors
        modeldirectory = self.directories.upscalerdirectoryvariable.get() + formatting.UPSCALERS[self.options.upscalervariable.get()]
        if not os.path.exists(modeldirectory):
            action = messagebox.askyesno(title='Could not find upscaler', message=f'Could not find {self.options.upscalervariable.get()} at\n{modeldirectory}\nContinue anyway?')
            if not action:
                return

        # disable widgets
        self.downloadbutton.configure(state='disabled')
        for widget in self.options.widgets + self.directories.widgets:
            widget.configure(state='disabled')
        self.mainframe.update()

        # collect urls from gui, pack into list to give to yt-dl
        self.save_data()
        urls = self.main.linkstext.get('1.0', tk.END).split('\n')[:-1]

        # initialise yt-dl
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': self.directories.downloaddirectoryvariable.get() + '/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': self.options.audioqualityvariable.get().removesuffix(' Kbps')
            }],
            'writethumbnail': True
        }
        self.yt_song = youtube_dl.YoutubeDL(ydl_opts)
        self.yt_song.__enter__()
        self.yt_song.add_progress_hook(self.yt_progress)

        # download each item in turn
        try:
            for i, url in enumerate(urls):
                if not url in IGNOREDURLS:
                    self.download(self.yt_song, url)
                
                self.progresslabelvariable.set(f'{i+1}/{len(urls)}')
                self.progressbarvariable.set((i+1)/len(urls)*100)
            messagebox.showinfo(title=None, message='Download(s) finished')
        except youtube_dl.DownloadError as e:
            messagebox.showerror(title=None, message=str(e).split('.')[0])
        
        # enable widgets
        self.downloadbutton.configure(state='normal')
        for widget in self.options.widgets + self.directories.widgets:
            widget.configure(state='normal')
        self.mainframe.update()

class Main(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pad = 5
        self.create_widgets()
    
    def create_widgets(self):
        # build widgets
        linkslabel = ttk.Label(self, text='Seperate URLs should go on their own line\nIt\'s fine to mix albums/playlists/EPs with singles\nURLs don\'t have to come from the same source')
        helpbutton = ttk.Button(self, text='Help', command=self.show_help)
        self.linkstext = tk.Text(self)

        # configure
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        kwargs = {'padx': self.pad, 'pady': self.pad}

        # lay out widgets
        linkslabel.grid     (row=0, column=0, sticky=tk.EW, **kwargs)
        helpbutton.grid     (row=0, column=1, sticky=tk.EW, **kwargs)
        self.linkstext.grid (row=1, column=0, sticky=tk.NSEW, **kwargs, columnspan=2)
    
    def show_help(self):
        with open('help.txt', 'rb') as f:
            messagebox.showinfo(title='You cried for help!', message=f.read())

class Directories(ttk.Frame):
    def __init__(self, parent, jsondata):
        super().__init__(parent)
        self.parent = parent
        self.pad = 5

        self.downloaddirectoryvariable      = tk.StringVar(value=jsondata['download_directory'])
        self.upscalerdirectoryvariable      = tk.StringVar(value=jsondata['upscaler_directory'])

        self.widgets = self.create_widgets()

    def create_widgets(self):
        # create widgets
        downloaddirectorylabel = ttk.Label(self, text='Download directory')
        downloaddirectoryentry = ttk.Entry(
            self,
            textvariable = self.downloaddirectoryvariable
        )
        downloaddirectorybutton = ttk.Button(self, text='Select', command=lambda: self.pick_directory(self.downloaddirectoryvariable, 0))


        upscalerdirectorylabel = ttk.Label(self, text='Upscaler directory')
        upscalerdirectoryentry = ttk.Entry(
            self,
            textvariable = self.upscalerdirectoryvariable
        )
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

    def pick_directory(self, var, type) -> str:
        titles = ['Select a download directory', 'Select an upscaler directory']
        var.set(filedialog.askdirectory(title=titles[type]))

class Options(ttk.Frame):
    def __init__(self, parent, jsondata):
        super().__init__(parent)
        self.parent = parent
        self.pad = 5

        self.audioqualityvariable           = tk.StringVar(value=jsondata['audio_quality'])
        self.attachsingleimagesvariable     = tk.StringVar(value=jsondata['attach_single'])
        self.attachalbumimagesvariable      = tk.StringVar(value=jsondata['attach_album'])
        self.imagesizevariable              = tk.StringVar(value=jsondata['target_image'])
        self.upscalervariable               = tk.StringVar(value=jsondata['upscaler'])
        self.downscalervariable             = tk.StringVar(value=jsondata['downscaler'])
        self.overwritevariable              = tk.IntVar(value=jsondata['overwrite'])

        self.widgets = self.create_widgets()

    def create_widgets(self):
        # create widgets
        audioqualitylabel = ttk.Label(self, text='Preferred audio quality')
        audioqualityoptionmenu = ttk.OptionMenu(
            self,
            self.audioqualityvariable,
            self.audioqualityvariable.get(),
            *AUDIOQUALITYOPTIONS
        )

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

        imagesizelabel = ttk.Label(self, text='Target image size')
        imagesizeoptionmenu = ttk.OptionMenu(
            self,
            self.imagesizevariable,
            self.imagesizevariable.get(),
            *IMAGESIZEOPTIONS
        )

        upscalerlabel = ttk.Label(self, text='Upscale method\n(NCNN-Vulkan)')
        upscaleroptionmenu = ttk.OptionMenu(
            self,
            self.upscalervariable,
            self.upscalervariable.get(),
            *UPSCALEROPTIONS
        )

        downscalerlabel = ttk.Label(self, text='Downscale method')
        downscaleroptionmenu = ttk.OptionMenu(
            self,
            self.downscalervariable,
            self.downscalervariable.get(),
            *DOWNSCALEROPTIONS
        )

        overwritelabel = ttk.Label(self, text='Overwrite duplicates')
        overwritecheckbutton = ttk.Checkbutton(self, text=None, variable=self.overwritevariable)

        # configure
        kwargs = {'sticky': tk.EW, 'padx': self.pad, 'pady': self.pad}

        # place widgets
        audioqualitylabel.grid              (row=0, column=0, **kwargs)
        audioqualityoptionmenu.grid         (row=0, column=1, **kwargs)
        attachsingleimageslabel.grid        (row=1, column=0, **kwargs)
        attachsingleimagesoptionmenu.grid   (row=1, column=1, **kwargs)
        attachalbumimageslabel.grid         (row=2, column=0, **kwargs)
        attachalbumimagesoptionmenu.grid    (row=2, column=1, **kwargs)
        imagesizelabel.grid                 (row=3, column=0, **kwargs)
        imagesizeoptionmenu.grid            (row=3, column=1, **kwargs)
        upscalerlabel.grid                  (row=4, column=0, **kwargs)
        upscaleroptionmenu.grid             (row=4, column=1, **kwargs)
        downscalerlabel.grid                (row=5, column=0, **kwargs)
        downscaleroptionmenu.grid           (row=5, column=1, **kwargs)
        overwritelabel.grid                 (row=6, column=0, **kwargs)
        overwritecheckbutton.grid           (row=6, column=1, **kwargs)

        return (
            audioqualityoptionmenu,
            attachsingleimagesoptionmenu,
            attachalbumimagesoptionmenu,
            imagesizeoptionmenu,
            upscaleroptionmenu,
            downscaleroptionmenu,
            overwritecheckbutton
        )

def main():
    window = tk.Tk()
    window.title('MusiGui')
    window.iconbitmap('musigui.ico')
    window.geometry('1000x500')
    window.minsize(width=770, height=460)

    style = ttk.Style(window)
    style.theme_use('clam')

    DownloadUI(window).mainframe.mainloop()

if __name__ == '__main__':
    main()
