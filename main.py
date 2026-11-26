#!/usr/bin/env python3
"""Copy the built front page (entry.png, next to this file) to /output/entry.png.

Stdlib only. No network, no clock, no randomness. The output file is created
with mode 0644.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "entry.png")
OUTDIR = "/output"
DST = os.path.join(OUTDIR, "entry.png")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    fd = os.open(DST, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with open(SRC, "rb") as src:
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                os.write(fd, chunk)
    finally:
        os.close(fd)
    os.chmod(DST, 0o644)


if __name__ == "__main__":
    main()
