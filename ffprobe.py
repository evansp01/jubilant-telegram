import subprocess
import json
import sys

command = ["ffprobe", "-v", "quiet", "-show_format", "-show_streams",
           "-print_format", "json"]


def probe(filename):
    probe = subprocess.Popen(command + [filename],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True)
    stdout, stderr = probe.communicate()
    if stderr:
        raise Exception(stderr)
    else:
        info = json.loads(stdout)
    return info

if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1]), indent=4))
