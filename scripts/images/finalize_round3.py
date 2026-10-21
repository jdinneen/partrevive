"""Finalize round-3 candidates: python finalize_round3.py <cand_dir> <picks.json>
picks.json: {"<name>": <candidate index>}  (candidate files are <name>__r3<i>.png)."""
import glob, io, json, os, sys
from PIL import Image
D, PICKS = sys.argv[1], json.load(open(sys.argv[2]))
IMG = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "img")
MAN = os.path.join(os.path.dirname(__file__), "manifest.json")
meta = {}
for f in glob.glob(D + "/meta_*.json"):
    meta.update(json.load(open(f)))
NEG = "text, letters, logo, watermark, hands, fingers, people, blurry, deformed, multiple copies, box, drawer, room, interior, vehicle, giant, tray"
def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))
def save(im, path, limit):
    for q in (82, 78, 74, 70, 65):
        b = io.BytesIO(); im.save(b, "JPEG", quality=q, progressive=True, optimize=True)
        if b.tell() <= limit: break
    open(path, "wb").write(b.getvalue()); return q, b.tell()
manifest = json.load(open(MAN))
manifest = [m for m in manifest if m["file"].rsplit("-600", 1)[0].replace(".jpg", "") not in PICKS and m["file"].replace(".jpg", "") not in PICKS]
def rec(file, w, h, m, q, size):
    manifest.append(dict(file=file, width=w, height=h, prompt=m["prompt"], negative_prompt=NEG, seed=m["seed"],
        generator="stabilityai/stable-diffusion-xl-base-1.0 (fp16, 28 steps, cfg 6.5)", jpeg_quality=q, bytes=size))
for name, i in PICKS.items():
    im = Image.open(f"{D}/{name}__r3{i}.png").convert("RGB"); m = meta[f"{name}__{i}"]
    full = cover(im, 1200, 900); q, s = save(full, f"{IMG}/{name}.jpg", 150_000); rec(f"{name}.jpg", 1200, 900, m, q, s)
    if not name.startswith("article-"):
        sm = full.resize((600, 450), Image.LANCZOS); q, s = save(sm, f"{IMG}/{name}-600.jpg", 60_000); rec(f"{name}-600.jpg", 600, 450, m, q, s)
    print("wrote", name)
json.dump(manifest, open(MAN, "w"), indent=1)
