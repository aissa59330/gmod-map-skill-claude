import os, sys, struct, glob, io, lzma
W = r"C:/Program Files (x86)/Steam/steamapps/workshop/content/4000"
OUT = r"C:/Users/<UTILISATEUR>/gn_content"
def cstr(f):
    b = bytearray()
    while (c := f.read(1)) not in (b"\0", b""): b += c
    return b.decode("utf-8", "replace")
for name in sys.argv[1:]:
    wid = name.rsplit("_", 1)[1]
    gmas = glob.glob(os.path.join(W, wid, "*.gma"))
    if gmas:
        raw = open(gmas[0], "rb").read()
    else:
        raw = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(open(glob.glob(os.path.join(W, wid, "*.bin"))[0], "rb").read())
    with io.BytesIO(raw) as f:
        assert f.read(4) == b"GMAD"; ver = f.read(1)[0]; f.read(16)
        if ver > 1:
            while cstr(f): pass
        cstr(f); cstr(f); cstr(f); f.read(4)
        ents = []
        while struct.unpack("<I", f.read(4))[0]:
            p = cstr(f); size = struct.unpack("<q", f.read(8))[0]; f.read(4); ents.append((p, size))
        n = 0
        for p, size in ents:
            data = f.read(size)
            if not p.lower().startswith(("models/", "materials/")): continue
            dst = os.path.join(OUT, name, p); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data); n += 1
    print(name, n, "fichiers")
