"""Create the app's simple code-mark icons using only Python's standard library."""
import struct
import zlib
from pathlib import Path


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def distance(px, py, ax, ay, bx, by):
    t = max(0, min(1, ((px-ax)*(bx-ax)+(py-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
    return ((px-ax-t*(bx-ax))**2 + (py-ay-t*(by-ay))**2)**0.5


lines = [(0.37,0.35,0.25,0.50),(0.25,0.50,0.37,0.65),(0.63,0.35,0.75,0.50),(0.75,0.50,0.63,0.65),(0.55,0.30,0.45,0.70)]
for size in (192,512):
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            foreground = min(distance(x/size,y/size,*line) for line in lines) < 0.025
            pixels.extend((245,243,233) if foreground else (40,92,80))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',size,size,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(pixels)) + chunk(b'IEND',b'')
    (Path(__file__).resolve().parents[1] / 'static' / f'icon-{size}.png').write_bytes(png)
