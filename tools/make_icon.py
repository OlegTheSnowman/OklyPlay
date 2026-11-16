"""Write assets/oklyplay.ico from the logo drawn in src/branding.py.

The exe icon must be a file at build time, while the window icon is drawn at
runtime; generating one from the other keeps them identical. Run it again
after changing the logo:

    python tools/make_icon.py
"""

import io
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import wx  # noqa: E402
import branding  # noqa: E402

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def png_bytes(size):
    stream = io.BytesIO()
    branding.draw_logo(size).ConvertToImage().SaveFile(stream, wx.BITMAP_TYPE_PNG)
    return stream.getvalue()


def main():
    app = wx.App(False)  # noqa: F841  wx needs an app to draw
    images = [(s, png_bytes(s)) for s in SIZES]
    # ICO container with PNG-compressed entries (supported since Windows Vista)
    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    for size, data in images:
        dim = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    out += b"".join(data for _, data in images)
    path = os.path.join(ROOT, "assets", "oklyplay.ico")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(out)
    print(f"Wrote {path} ({len(out)} bytes)")


if __name__ == "__main__":
    main()
