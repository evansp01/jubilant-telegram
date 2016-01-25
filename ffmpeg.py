import subprocess
import sys


def convert(in_file, out_file, out_format=None, quality=None, no_video=False):
    command = ['ffmpeg', '-y', '-v', 'quiet']
    command += ['-i', in_file]
    if no_video:
        command += ['-nv']
    if quality:
        command += ['-aq', str(quality)]
    if out_format == 'ogg':
        command += ['-acodec', 'libvorbis']
    command += [out_file]
    conv = subprocess.Popen(command,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    stdout, stderr = conv.communicate()
    if stderr:
        raise Exception(stderr)
    return stdout

if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2], bitrate=sys.argv[3])
