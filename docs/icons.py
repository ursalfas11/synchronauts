"""The app icons of the board (ui/icon-*.png): the mark of the favicon, a ring with a green dot, on a dark tile.
Python only, no image library: python3 docs/icons.py"""
import struct
import zlib
from pathlib import Path

BG, RING, DOT = (17, 17, 20), (255, 255, 255), (74, 222, 128)


def png(path, size, rounded):
    n = 4  # n×n samples per pixel against jagged edges
    pad = round(0.09 * size) if rounded else 0  # a tile with room around it, like the other icons in a dock
    s, corner = size - 2 * pad, 0.225 * (size - 2 * pad) if rounded else 0
    rows = []
    for y in range(-pad, s + pad):
        row = bytearray([0])
        for x in range(-pad, s + pad):
            r = g = b = covered = 0
            for sy in range(n):
                for sx in range(n):
                    px, py = x + (sx + 0.5) / n, y + (sy + 0.5) / n
                    qx, qy = max(corner - px, px - (s - corner), 0), max(corner - py, py - (s - corner), 0)
                    if not (0 <= px <= s and 0 <= py <= s) or corner and qx * qx + qy * qy > corner * corner:
                        continue  # outside the rounded corner
                    d = ((px - s / 2) ** 2 + (py - s / 2) ** 2) ** 0.5 / s
                    c = DOT if d < 0.1 else RING if 0.25 < d < 0.32 else BG
                    r, g, b, covered = r + c[0], g + c[1], b + c[2], covered + 1
            row += bytes([round(r / covered), round(g / covered), round(b / covered)] if covered else [0, 0, 0])
            row.append(round(255 * covered / (n * n)))
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    ui = Path(__file__).resolve().parent.parent / 'ui'
    png(ui / 'icon-192.png', 192, True)
    png(ui / 'icon-512.png', 512, True)
    png(ui / 'icon-maskable.png', 512, False)
