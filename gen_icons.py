import zlib, struct, os

def make_png(path, size, rgb=(255, 0, 0)):
    """Gera um PNG sólido usando apenas biblioteca padrão."""
    w = h = size
    # linha de pixels com filtro 0
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            raw.extend(rgb)
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        crc = zlib.crc32(tag + data) & 0xffffffff
        return c + struct.pack('>I', crc)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    idat = chunk(b'IDAT', compressed)
    iend = chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(sig + chunk(b'IHDR', ihdr) + idat + iend)

os.makedirs('static', exist_ok=True)
make_png('static/icon-192.png', 192)
make_png('static/icon-512.png', 512)
print('Ícones gerados')
