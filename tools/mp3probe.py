import sys
import pathlib

import mutagen.id3 as id3
from mutagen.mp3 import HeaderNotFoundError

def main(path):
    with path.open("rb") as f:
        try:
            tags = id3.ID3(f)
            del tags["APIC:Album cover"]
            print(tags.pprint())

        except (id3.ID3NoHeaderError, HeaderNotFoundError):
            print("No ID3 header")

if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
