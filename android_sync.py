#!/usr/bin/env python3

import os
from pydub import AudioSegment
from collections import defaultdict as dd
import multiprocessing
import ffprobe
import shutil
import argparse

def format_size(num, suffix='B'):
    """ Function to display file sizes in a human readable format """
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class Progress:

    def __init__(self, format, initial):
        self.format = format
        self.counter = initial

    def update(self, inc=1):
        self.counter += inc
        print("\r"+self.format.format(self.counter), end="")

    def finish(self):
        print(' Done.')
        return self.counter


class SyncFile:
    """ Class which describes a file which will be synced with the device """

    def __init__(self, path, from_path):
        self.path = path
        self.from_path = from_path
        info = ffprobe.ffprobe(from_path)
        if info:
            self._streams = info['streams']
            self._format = info['format']
        else:
            self._streams = []
            self._format = {}

    def ext(self):
        name, ext = os.path.splitext(self.path)
        return ext.replace('.','')

    def has_audio(self):
        for stream in self._streams:
            if stream.get('codec_type') == 'audio':
                return True
        return False

    def has_video(self):
        for stream in self._streams:
            if stream.get('codec_type') == 'video':
                return True
        return False

    def bitrate(self):
        if 'bit_rate' in self._format:
            return int(self._format['bit_rate'])
        return None

    def format(self):
        return self._format.get('format_name', None)

    def size(self):
        if 'size' in self._format:
            return int(self._format['size'])
        return None

    def duration(self):
        if 'duration' in self._format:
            return int(self._format['duration'])
        return None

class AndroidSync:

    ENCODINGS = {'mp3', 'flac', 'wav', 'aac', 'ogg', 'flv'}

    def __init__(self, from_root, to_root, format='mp3', bitrate='192k'):
        self.from_root = os.path.abspath(from_root)
        self.to_root = os.path.abspath(to_root)
        self.format = format
        self.bitrate = bitrate
        self.synclist = []

    def sync(self):
        self.analyze()
        self.sync_all()

    def analyze(self):
        pathlist = []
        progress = Progress("Found {} files.", 0)
        for root, _, files in os.walk(self.from_root):
            for fn in files:
                from_path = os.path.join(root, fn)
                relpath = os.path.relpath(from_path, self.from_root)
                pathlist.append((relpath, from_path))
                progress.update()
        total = progress.finish()
        # analyze each file in the path list
        progress = Progress("Analyzed {} of " + str(total) + " files.", 0)
        for relpath, from_path in pathlist:
            self.analyze_file(relpath, from_path)
            progress.update()
        progress.finish()

    def analyze_file(self, relpath, from_path):
        sf = SyncFile(relpath, from_path)
        if sf.ext() in self.ENCODINGS:
            self.synclist.append(sf)

    def sync_all(self):
        progress= Progress("Syncing file {} of " + str(len(self.synclist)), 0)
        pool = multiprocessing.Pool()
        for _ in enumerate(pool.imap_unordered(self.sync_file, self.synclist)):
            progress.update()
        progress.finish()

    def sync_file(self, syncfile):
        from_path = self.from_path(syncfile.path)
        to_path = self.to_path(syncfile.path)
        to_dir = os.path.dirname(to_path)
        # if the file we want to create exists, then do nothing
        if os.path.exists(to_path):
            return
        # if not all subdirectorys exist, create them
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
        # attempt to convert the audio
        if syncfile.format() == self.format:
            if syncfile.bitrate() <= self.bitrate:
                self.copy_file(from_path, to_path)
            else:
                self.convert_file(from_path, to_path, self.bitrate,
                                  syncfile.format(), self.format)
        else: # different formats
            if syncfile.bitrate() <= self.bitrate:
                self.convert_file(from_path, to_path, syncfile.bitrate(),
                                  syncfile.format(), self.format)
            else:
                self.convert_file(from_path, to_path, self.bitrate,
                                  syncfile.format(), self.format)

    def copy_file(self, from_path, to_path):
        shutil.copy_file(from_path, to_path)

    def convert_file(self, from_path, to_path, bitrate, from_format, to_format):
        try:
            audio = AudioSegment.from_file(from_path, format=from_format)
        except Exception as e:
            print("Could not open file as audio: {}".format(e))
        try:
            audio.export(to_path, format=to_format, bitrate=str(bitrate))
        except Exception as e:
            print("Failed to export file: {}".format(e))

    def to_path(self, relpath):
        to = os.path.join(self.to_root, relpath)
        name, _ = os.path.splitext(to)
        return "{}.{}".format(name, self.format)

    def from_path(self, relpath):
        return os.path.join(self.from_root, relpath)


def get_arguments():
    OUTPUT_FORMATS = {'mp3', 'ogg'}
    OUTPUT_BITRATES = {64, 80, 128, 160, 192}
    parser = argparse.ArgumentParser(description='Batch convert mp3 files')
    parser.add_argument('-f','--format', metavar='EXT', nargs=1,
                        choices=OUTPUT_FORMATS,
                        help="format to convert to",
                        required=True)
    parser.add_argument('-b','--bitrate', metavar='NUM', nargs=1, type=int,
                        choices=OUTPUT_BITRATES,
                        help="format to convert to",
                        required=True)
    parser.add_argument('-i','--input', metavar='PATH', nargs=1,
                        help="folder to sync to device",
                        required=True)
    parser.add_argument('-o','--output', metavar='PATH', nargs=1,
                        help="device location to sync to",
                        required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = get_arguments()
    in_dir = args.input[0]
    out_dir = args.output[0]
    bitrate = args.bitrate[0]
    format = args.format[0]
    print("Syncing music from {} to {}. Converting to {}k {}"
          .format(in_dir, out_dir, bitrate, format))
    sync = AndroidSync(in_dir, out_dir, bitrate=bitrate*1024, format=format)
    sync.sync()

