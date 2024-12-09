import os
import re
import time
import typing
import eyed3
from eyed3.id3.frames import ImageFrame
import configure
from handler import BaseHandler, DEBUG, INFO, WARNING, ERROR #pylint: disable=W0611

class FormatConfig(configure.Config):
    """Configuration data structure for the formatters."""
    _configdir = "config\\format.json"

    def __init__(self) -> None:
        super().__init__()
        self.default()

    def default(self) -> None:
        """Load the default configuration."""
        self.config = {
            # keep all until the first non-ASCII character
            "title_regex": r"[^\x00-\x7F].*"
        }

class MusicFormatHandler(BaseHandler):
    """
    Handles instances of `MusicFormatter` to correctly manipulate
    singles, albums, playlists and more.
    """
    def __init__(self) -> None:
        """
        Handles instances of `MusicFormatter` to correctly manipulate
        singles, albums and playlists.
        """
        super().__init__(FormatConfig(), MusicFormatter)
        self.config:FormatConfig
        self.formatters:list[MusicFormatter]

    def get_config(self) -> None:
        """Get the currently used configuration."""
        return self.config.get_config()

    def set_config(self, config:dict[str,typing.Any]) -> None:
        """Set the configuration."""
        self.config.set_config(config)

    def set_logger(self, logger:object) -> None:
        """
        Set the logger.

        :param logger:
        class object to provide callbacks and progress updates.
        """
        self.logger = logger

    # The following works, but it feels repetitive and wrong.
    # I am almost certain there exists a better way to do this,
    # but I have no idea where to even begin looking for it.

    # "this" being a wrapper class that calls the methods of
    # another class from a list of class objects in the wrapper class.

    def correct_metadata(self) -> None:
        """Correct the metadata."""
        for inst in self.formatters:
            inst.correct_metadata()

    def tag_audio(self) -> None:
        """Attach the metadata to the files."""
        for inst in self.formatters:
            inst.tag_audio()

    def tag_image(self, images:list) -> None:
        """Attach the appropriate images."""
        for i, inst in enumerate(self.formatters):
            inst.tag_image(images[i])

    def save(self) -> None:
        """Save changes to the audio files."""
        for inst in self.formatters:
            inst.save()

    def rename(self) -> None:
        """Rename the audio files."""
        for inst in self.formatters:
            inst.rename()

class MusicFormatter:
    """
    Contains all the information needed to handle music files.
    Includes metadata, cover art, etc.
    """
    def __init__(
            self,
            metadata:dict[str,typing.Any],
            config:FormatConfig,
            handler:MusicFormatHandler
        ) -> None:
        """
        Contains all the information needed to handle music files.
        Includes metadata, cover art, etc.
        """
        self.meta = metadata
        self.config = config
        self.handler = handler
        self.audio = self._load_music()

    def _load_music(self) -> eyed3.AudioFile:
        """
        Open the music file and initialise tagging.

        :returns audio:
        :class:`eyed3.AudioFile`
        """
        audio = eyed3.load(self.get_music_path())
        if audio.tag is None:
            audio.initTag()
        return audio

    def get_music_path(self) -> str:
        """
        Get the music file location.

        :returns music_path:
        Absolute filepath of the music file.
        """
        return self.meta["requested_downloads"][0]["filepath"]

    def correct_metadata(self) -> None:
        """Correct the metadata."""
        # some artists add their name before the track title
        title:str = self.meta['title']
        if self.meta['uploader'] in title:
            self.meta['title'] = title.split(' - ', maxsplit=2)[1]

        # some artists add their name before the album title
        if 'playlist_title' in self.meta:
            pl_title:str = self.meta['playlist_title']
            if self.meta['uploader'] in pl_title:
                corrected = pl_title.split(' - ', maxsplit=2)[1]
                self.meta['playlist_title'] = corrected

        # apply regex to title if available
        regex = self.config.get_value("title_regex")
        if regex != "":
            self.meta["title"] = re.sub(regex, "", self.meta["title"])

    def tag_audio(self) -> None:
        """Attach the metadata to the file."""
        self.handler.log(
            f"[music] Tagging metadata for {self._get_title()}",
            INFO
        )
        self.audio.tag.title            = self._get_title()
        self.audio.tag.artist           = self._get_artists()
        self.audio.tag.album_artist     = self._get_album_artist()
        self.audio.tag.album            = self._get_album()
        self.audio.tag.recording_date   = self._get_date()
        self.audio.tag.genre            = self._get_genres()
        self.audio.tag.track_num        = self._get_track_num()
        self.audio.tag.audio_source_url = self._get_source()

    def _try_key(self, key:str) -> typing.Any:
        """
        Try to get a key from `self.meta`
        
        :param key:
        Keyword to find in metadata.
        
        :returns value:
        Value of metadata at the key or `None` it does not exist.
        """
        item = None
        if key in self.meta:
            item = self.meta[key]
        return item

    def _get_title(self) -> str:
        """
        Get formatted title.
        
        :returns title:
        Track title or empty string if failed.
        """
        # try track title
        if (track_title := self._try_key("title")) is not None:
            return track_title

        # failed to get track title
        return ""

    def _get_artists(self) -> str:
        """
        Get formatted artists.
        
        :returns artists:
        Artists or empty string if failed.
        """
        # try artists
        if (artists := self._try_key("artists")) is not None:
            return ", ".join(artists)

        # try uploader
        if (uploader := self._try_key("uploader")) is not None:
            return uploader

        # failed to get artists
        return ""

    def _get_album_artist(self) -> str:
        """
        Get formatted album artist.

        :returns album_artist:
        Album artist or empty string if failed.
        """
        # try album artist
        if (album_artist := self._try_key("album_artist")) is not None:
            return album_artist

        # try creator
        if (creator := self._try_key("creator")) is not None:
            return creator

        # try uploader
        if (uploader := self._try_key("uploader")) is not None:
            return uploader

        # failed to get album artist
        return ""

    def _get_album(self) -> str:
        """
        Get formatted album title.
        
        :returns album_title:
        Album title or empty string if failed.
        """
        # try album title
        if (album_title := self._try_key("album")) is not None:
            return album_title

        # try playlist title
        if (playlist_title := self._try_key("playlist")) is not None:
            return playlist_title

        # return single title
        return self._get_title()

    def _get_date(self) -> str:
        """
        Get the year the music was released.
        
        :returns release_year:
        Release year or empty string if failed.
        """
        # try release year
        if (release_year := self._try_key("release_year")) is not None:
            return release_year

        # try upload date
        if (upload_date := self._try_key("upload_date")) is not None:
            return upload_date[:4]

        # try unix timestamp
        if (timestamp := self._try_key("timestamp")) is not None:
            return time.strftime('%Y', time.localtime(timestamp))

        # failed to get timestamp
        return ""

    def _get_genres(self, total:int=1) -> str:
        """
        Get formatted genres.

        :param total:
        Max number of genres to return.
        
        :returns genres:
        Genres or empty string if failed.
        """
        # try single genre if chosen and not empty
        if total == 1:
            # try single genre
            if (genre := self._try_key("genre")) is not None:
                return genre

        # try all genres
        genres:str
        if (genres := self._try_key("genres")) is not None:
            genre_split = genres.split(',', maxsplit=total)[:total]
            genre_string = ", ".join(genre_split)
            return genre_string

        # failed to get genres
        return ""

    def _get_track_num(self, digits:int=2) -> str:
        """
        Get the formatted track number.

        :param digits:
        Pad the number with zeroes to this length.

        :returns track_num:
        Track number or `"01"` if failed.
        """
        # try track number
        if (track_num := self._try_key("track_number")) is not None:
            return f"{track_num:>0{digits}}"

        # try playlist index
        if (playlist_index := self._try_key("playlist_index")) is not None:
            return f"{playlist_index:>0{digits}}"

        # failed to get track number (likely single)
        return "0"*(digits-1) + "1"

    def _get_source(self) -> str:
        """Get the url where the music file originated."""
        # try original url
        if (original_url := self._try_key("original_url")) is not None:
            return original_url

        # try webpage url
        if (webpage_url := self._try_key("webpage_url")) is not None:
            return webpage_url

        # failed to get source url
        return ""

    def tag_image(self, image_path:str) -> None:
        """
        Attach image to audio file.

        :param image_path:
        Directory of the image to attach.
        """
        with open(image_path, 'rb') as f:
            self.audio.tag.images.set(
                ImageFrame.FRONT_COVER,
                f.read(),
                'images/jpeg'
            )

    def save(self) -> None:
        """Save changes to the audio file."""
        self.audio.tag.save()

    def rename(self) -> None:
        """Rename the audio file."""
        old_path = self.get_music_path()
        cwd, _ = os.path.split(old_path)
        _, ext = os.path.splitext(old_path)

        new_name = \
            self._get_artists() \
            + " - " \
            + self._get_title() \
            + ext
        new_path = os.path.join(cwd, new_name)

        if os.path.exists(new_path):
            os.remove(new_path)

        try:
            os.rename(old_path, new_path)
        except OSError as e:
            self.handler.log(f"[error] {old_path} -X-> {new_path}", ERROR)
            print(e)
