import os
import time
import subprocess
import eyed3
from eyed3.id3.frames import ImageFrame
import cv2

UPSCALERS = {
    'RealSR':   '/realsr-ncnn-vulkan/realsr-ncnn-vulkan.exe',
    'Waifu2x':  '/waifu2x-ncnn-vulkan/waifu2x-ncnn-vulkan.exe',
    'SRMD':     '/srmd-ncnn-vulkan/srmd-ncnn-vulkan.exe'
}
DOWNSCALERS = {
    'Lanczos 8x8':          cv2.INTER_LANCZOS4,
    'Bicubic 4x4':          cv2.INTER_CUBIC,
    'Area':                 cv2.INTER_AREA,
    'Bilinear':             cv2.INTER_LINEAR,
    'Nearest-neighbour':    cv2.INTER_NEAREST
}
UPSCALERETRIES = 1

def format_files(
        infodict: dict,
        settings: dict,
        imagedirectory: str=None
    ) -> None:
    '''
    Uses infodict data to get and tag mp3 files, also changes filename
    '''
    # prepare metadata
    single = False
    try:
        entries = infodict['entries']
    except KeyError:
        single = True
        entries = [infodict] # don't judge me, it works

    # if a cover has been selected, only correct that one
    first = False
    if imagedirectory:
        first = True

    for info in entries:
        # for each downloaded song
        imagepath = str(info['thumbnails'][-1]['filepath'])
        mp3path = str(info['requested_downloads'][0]['filepath'])

        # tag mp3 file
        audio = tag_audio(
            mp3path,
            imagepath,
            info,
            settings,
            single,
            imagedirectory,
            first
        )
        first = False

        # tidy up unused image files as we go
        if imagedirectory and (imagepath != imagedirectory):
            os.remove(imagepath)

        # rename the file to allow for files with /
        # same track title by different artists
        newmp3path = os.path.join(
            '\\'.join(mp3path.split('\\')[:-1]),
            f'{audio.tag.artist} - {audio.tag.title}.mp3'
        )
        try:
            os.rename(mp3path, newmp3path)
        except OSError:
            if settings['overwrite'] == 1:
                os.remove(newmp3path)
                os.rename(mp3path, newmp3path)
            else:
                print(f'[format] Overwrite disabled, cannot save {newmp3path}')

    try:
        os.remove(f'{settings["download_directory"]}/input.jpg')
        os.remove(f'{settings["download_directory"]}/output.jpg')
    except OSError:
        pass

def tag_audio(
        mp3path: str,
        imagepath: str,
        info: dict,
        settings: dict,
        single: bool,
        imagedirectory: str,
        first: bool
    ) -> eyed3.AudioFile:
    '''
    Initialise mp3 tagging and tag mp3 file with given metadata.\n
    Returns audio object.
    '''
    # initialise mp3 tagging
    eyed3.log.setLevel("ERROR")
    audio = eyed3.load(mp3path)
    if audio.tag is None:
        audio.initTag()

    # correct images if a downscaler is selected,
    # only correct one image if a specific one is selected
    msg = determine_image_correction(imagedirectory, settings, first)
    if msg:
        print(f'[image] {msg}, skipping')
    else:
        correct_image(imagepath, imagedirectory, settings)

    # correct metadata, some artists add their name before the track title
    if info['uploader'] in info['title']:
        info['title'] = info['title'].split(' - ')[1]

    # same as ^ but for album titles
    if 'playlist_title' in info:
        if info['uploader'] in info['playlist_title']:
            info['playlist_title'] = info['playlist_title'].split(' - ')[1]
    else:
        info['playlist_title'] = info['title']

    # tag the mp3 file
    audio.tag.title             = info['title']
    audio.tag.artist            = info['uploader']
    audio.tag.album_artist      = info['uploader']
    audio.tag.album             = info['playlist_title'] if not single else info['title']
    audio.tag.recording_date    = time.strftime(
        '%Y',
        time.localtime(info['timestamp'] if 'timestamp' in info else info['release_timestamp'])
    )
    audio.tag.genre             = tag_genre(info)
    audio.tag.track_num         = info['playlist_index'] if info['playlist_index'] else 1
    audio.tag.images.set(
        ImageFrame.FRONT_COVER,
        open(imagedirectory if imagedirectory else imagepath, 'rb').read(),
        'images/jpeg'
    )

    # save changes
    audio.tag.save()
    return audio

def correct_image(imagepath: str, imagedirectory: str, settings: dict) -> None:
    '''
    Upscale/downscale image to target size.\n
    Requires image path not image object.
    '''
    # get the current image
    img = cv2.imread(imagedirectory if imagedirectory else imagepath)
    size = min(img.shape[0:2])
    target = int(min(settings['target_image'].split('x')))

    # upscale the image if it is too small and upscaling is enabled
    if target != size and settings["upscaler"] != 'None':
        cv2.imwrite(f'{settings["download_directory"]}/input.jpg', img)
        retries = UPSCALERETRIES
        upscaled = False

        # upscale the image in 4x chunks
        while target > size:
            upscaled = True
            print(f'[image] Upscaling from {size}x{size} to {size*4}x{size*4} \
                  using {settings["upscaler"]}')

            # upscale image using selected engine
            result = subprocess.run(
                f'\
                    "{settings["upscaler_directory"] + UPSCALERS[settings["upscaler"]]}" \
                    -i "{settings["download_directory"]}/input.jpg" \
                    -o "{settings["download_directory"]}/output.jpg" -s 4\
                ',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False
            )
            size *= 4

            # break if too many errors
            if result.returncode != 0:
                retries -= 1
                if retries < 0:
                    print('[image] Failed to upscale image')
                    break
                print(f'[image] Error upscaling image, {retries} retry(s) left')

        if upscaled:
            img = cv2.imread(f'{settings["download_directory"]}/output.jpg')

        # downscale image to target size
        print(f'[image] Downscaling {size}x{size} to {target}x{target} \
              using {settings["downscaler"]}')
        res = cv2.resize(
            img,
            dsize=(target, target),
            interpolation=DOWNSCALERS[settings['downscaler']]
        )
        cv2.imwrite(imagedirectory if imagedirectory else imagepath, res)

def tag_genre(info: dict) -> str:
    '''
    Return genre if it exists else empty string ("")
    '''
    try:
        return info['genre']
    except KeyError:
        return ''

def determine_image_correction(
        imagedirectory: str,
        settings: dict,
        first: bool
    ) -> str:
    '''
    determine whether to correct an image or not.\n
    returns `None` if image needs correcting, str with reason not to otherwise
    '''
    if settings['downscaler'] == 'None':
        return 'Image scaling disabled'

    if settings['download_covers'] is False:
        return 'No image to scale'

    if not imagedirectory and first:
        return 'Only album cover image needs scaling'

    return ''
