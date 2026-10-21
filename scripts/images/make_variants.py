"""Create the responsive variants the templates use: <name>-600.jpg, <name>.webp and <name>-600.webp
for every assets/img/<name>.jpg. Idempotent: a variant is rebuilt only when missing or older than its source.
Run by scripts/build.py; safe to run by hand."""
from pathlib import Path

from PIL import Image

IMG = Path(__file__).resolve().parents[2] / "assets" / "img"
SKIP = {"og-default.jpg"}  # social preview must stay a plain 1200x630 JPEG


def stale(src: Path, dst: Path) -> bool:
    return not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime


def main() -> int:
    made = 0
    for src in sorted(IMG.glob("*.jpg")):
        if src.stem.endswith("-600") or src.name in SKIP:
            continue
        small = src.with_name(src.stem + "-600.jpg")
        webp = src.with_suffix(".webp")
        webp_small = src.with_name(src.stem + "-600.webp")
        with Image.open(src) as im:
            im = im.convert("RGB")
            if stale(src, webp):
                im.save(webp, "WEBP", quality=80, method=6); made += 1
            if im.width > 600:
                sm = im.resize((600, round(im.height * 600 / im.width)), Image.LANCZOS)
                if stale(src, small):
                    sm.save(small, "JPEG", quality=82, optimize=True, progressive=True); made += 1
                if stale(src, webp_small):
                    sm.save(webp_small, "WEBP", quality=80, method=6); made += 1
    print(f"image variants: {made} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
