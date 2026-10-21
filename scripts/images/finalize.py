"""Pick winning candidates, crop/resize, write JPEGs + -600 variants + manifest.json.
Usage: python finalize.py <cand_round1_dir> <cand_round2_dir>"""
import io, json, glob, os, sys
from PIL import Image
D1, D2 = sys.argv[1], sys.argv[2]
IMG = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "img")
os.makedirs(IMG, exist_ok=True)
def meta(d):
    m = {}
    for f in glob.glob(d + "/meta_*.json"): m.update(json.load(open(f)))
    return m
M = {1: meta(D1), 2: meta(D2)}
# name -> (round, candidate index)  (chosen by visual review)
PICK = {
 "rv-window-latch": (2,0), "rv-cabinet-door-latch": (2,3), "whirlpool-kitchenaid-fridge-door-bin": (1,0),
 "samsung-fridge-door-bin": (1,0), "dewalt-tstak-latch-clip": (2,2), "milwaukee-packout-drawer-latch": (2,3),
 "bmw-e90-e46-cup-holder": (2,0), "maytag-whirlpool-dryer-knob": (2,3), "bosch-dishwasher-tine-clip": (2,0),
 "dyson-v11-trigger": (2,1), "custom-replacement-part-from-photo": (1,1),
 "cat-rv-camper": (1,2), "cat-kitchen-appliance": (1,1), "cat-tools-toolboxes": (1,1), "cat-automotive": (1,1),
 "article-fridge-door-bin-broken-options": (2,2), "article-rv-window-latch-replacement-guide": (2,1),
 "article-dewalt-tstak-latch-keeps-breaking": (2,1), "article-can-this-plastic-part-be-3d-printed": (1,1),
 "article-how-to-photograph-a-broken-part-for-a-quote": (2,2), "hero": (1,0),
}
def src(name):
    r, i = PICK[name]
    d = D1 if r == 1 else D2
    suffix = f"__{i}" if r == 1 else f"__r2{i}"
    return Image.open(f"{d}/{name}{suffix}.png").convert("RGB"), M[r][f"{name}__{i}"]
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
manifest = []
def rec(file, w, h, name, m, q, size):
    manifest.append(dict(file=file, width=w, height=h, prompt=m["prompt"], negative_prompt=NEG, seed=m["seed"],
        generator="stabilityai/stable-diffusion-xl-base-1.0 (fp16, 28 steps, cfg 6.5)", jpeg_quality=q, bytes=size))
NEG = "text, letters, logo, watermark, hands, fingers, people, blurry, deformed, multiple copies (+ box, drawer, room, interior, vehicle, giant, tray for round-2 prompts)"
for name in PICK:
    im, m = src(name)
    if name == "hero":
        h = cover(im, 1600, 900); q, s = save(h, f"{IMG}/hero.jpg", 250_000); rec("hero.jpg", 1600, 900, name, m, q, s)
        o = cover(im.crop((0, 0, im.width, im.height)), 1200, 630); q, s = save(o, f"{IMG}/og-default.jpg", 150_000)
        rec("og-default.jpg", 1200, 630, name, m, q, s); continue
    full = cover(im, 1200, 900); q, s = save(full, f"{IMG}/{name}.jpg", 150_000); rec(f"{name}.jpg", 1200, 900, name, m, q, s)
    if not name.startswith("article-"):
        sm = full.resize((600, 450), Image.LANCZOS); q, s = save(sm, f"{IMG}/{name}-600.jpg", 60_000); rec(f"{name}-600.jpg", 600, 450, name, m, q, s)
json.dump(manifest, open(os.path.join(os.path.dirname(__file__), "manifest.json"), "w"), indent=1)
