import os
import eyed3
from eyed3.id3.frames import ImageFrame
import time
import cv2
import subprocess

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

def format_files(infodict, settings, imagedirectory=None) -> None:
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
        jpgpath = info['thumbnails'][-1]['filename']
        mp3path = jpgpath.replace('.jpg', '.mp3')

        # tag mp3 file
        audio = tag_audio(mp3path, jpgpath, info, settings, single, imagedirectory, first)
        first = False

        # tidy up unused image files as we go
        if imagedirectory and (jpgpath != imagedirectory):
            os.remove(jpgpath)

        # rename the file to allow for same track title by different artists
        newmp3path = os.path.join('\\'.join(mp3path.split('\\')[:-1]), f'{audio.tag.artist} - {audio.tag.title}.mp3')
        try:
            os.rename(mp3path, newmp3path)
        except OSError:
            if settings['overwrite'] == 1:
                os.remove(newmp3path)
                os.rename(mp3path, newmp3path)
            else:
                print(f'[format] Overwrite disabled, cannot save {newmp3path}')

def tag_audio(mp3path, jpgpath, info, settings, single, imagedirectory, first) -> eyed3.AudioFile:
    # initialise mp3 tagging
    audio = eyed3.load(mp3path)
    if (audio.tag == None):
        audio.initTag()

    # correct all images unless a specific one has been chosen
    if (not imagedirectory) or first:
        correct_image(jpgpath, imagedirectory, settings)

    # tag the mp3 file
    audio.tag.title             = info['title']
    audio.tag.artist            = info['uploader']
    audio.tag.album_artist      = info['uploader']
    audio.tag.album             = info['playlist_title'] if not single else info['title']
    audio.tag.recording_date    = time.strftime('%Y', time.localtime(info['timestamp']))
    audio.tag.genre             = tag_genre(info)
    audio.tag.track_num         = info['playlist_index'] if info['playlist_index'] else 1
    audio.tag.images.set(ImageFrame.FRONT_COVER, open(imagedirectory if imagedirectory else jpgpath, 'rb').read(), 'images/jpeg')

    # save changes
    audio.tag.save()
    return audio

def correct_image(jpgpath, imagedirectory, settings):
    # get the current image
    img = cv2.imread(imagedirectory if imagedirectory else jpgpath)
    size = min(img.shape[0:2])
    target = int(min(settings['target_image'].split('x')))

    cv2.imshow('img', img)

    # upscale the image if it is too small
    if target != size:
        cv2.imwrite('in/input.jpg', img)
        retries = UPSCALERETRIES
        upscaled = False

        # upscale the image in 4x chunks
        while target > size:
            upscaled = True
            print(f'[image] Upscaling from {size}x{size} to {size*4}x{size*4} using {settings["upscaler"]}')

            # upscale image using selected engine
            result = subprocess.run(
                f'"{settings["upscaler_directory"] + UPSCALERS[settings["upscaler"]]}" -i "{settings["download_directory"]}/input.jpg" -o "{settings["download_directory"]}/output.jpg" -s 4',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            size *= 4

            # break if too many errors
            if result.returncode != 0:
                print(f'[image] Error upscaling image, {retries} retry(s) left')
                retries -= 1
                if retries < 0:
                    print('[image] code break')
                    break
        
        if upscaled:
            img = cv2.imread('in/output.jpg')

        # downscale image to target size
        print(f'[image] Downscaling {size}x{size} to {target}x{target} using {settings["downscaler"]}')
        res = cv2.resize(
            img,
            dsize=(target, target),
            interpolation=DOWNSCALERS[settings['downscaler']]
        )
        cv2.imwrite(imagedirectory if imagedirectory else jpgpath, res)

def tag_genre(info) -> str:
    try:
        return info['genre']
    except KeyError:
        return ''