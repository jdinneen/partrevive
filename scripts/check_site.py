#!/usr/bin/env python
"""Validate the generated site in docs/.  Usage: python scripts/check_site.py
Exit 1 on broken internal links, missing canonical, missing/duplicate h1 (hard errors),
unparseable JSON-LD, missing alt, or sitemap entries not on disk. Title/description length are warnings."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
BASE_URL = cfg["base_url"].rstrip("/")
BASE = urlparse(BASE_URL).path.rstrip("/")  # /partrevive


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.title = ""
        self.in_title = False
        self.desc = None
        self.canonical = None
        self.imgs_noalt = 0
        self.links = []
        self.ld = []
        self._in_ld = False
        self._buf = ""
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "img":
            if a.get("alt") is None:
                self.imgs_noalt += 1
            if a.get("src"):
                self.links.append(a["src"])
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "link" and a.get("href") and a.get("rel") in ("stylesheet", "icon"):
            self.links.append(a["href"])
        elif tag == "script":
            if a.get("src"):
                self.links.append(a["src"])
            if a.get("type") == "application/ld+json":
                self._in_ld = True
                self._buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False
            self.ld.append(self._buf)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self._in_ld:
            self._buf += data


def resolve(href, page_path):
    """Return a docs path to check, or None if external/ignored."""
    href = href.strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None
    if href.startswith(BASE_URL):
        href = href[len(BASE_URL) - len(BASE):]
    elif re.match(r"^[a-z][a-z0-9+.-]*:|^//", href):
        return None
    p = urlparse(href)
    path = unquote(p.path)
    if path.startswith("/"):
        if BASE and not (path == BASE or path.startswith(BASE + "/")):
            return ("ROOTBROKEN", path)
        path = path[len(BASE):] or "/"
    else:
        path = (Path("/" + page_path).parent / path).as_posix()
    target = DOCS / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    return ("OK", target, p.fragment)


def main():
    errors, warns = [], []
    htmls = sorted(DOCS.rglob("*.html"))
    if not htmls:
        print("No HTML in docs/. Run scripts/build.py first.")
        return 1
    id_cache = {}
    for f in htmls:
        rel = f.relative_to(DOCS).as_posix()
        pg = Page()
        pg.feed(f.read_text(encoding="utf-8"))
        id_cache[f] = pg.ids
        if pg.h1 != 1:
            errors.append(f"{rel}: expected exactly 1 h1, found {pg.h1}")
        t = pg.title.strip()
        if not t:
            errors.append(f"{rel}: empty title")
        elif len(t) > 60:
            warns.append(f"{rel}: title is {len(t)} chars (>60)")
        if pg.desc is None or not pg.desc.strip():
            warns.append(f"{rel}: missing meta description")
        elif len(pg.desc) > 155:
            warns.append(f"{rel}: meta description is {len(pg.desc)} chars (>155)")
        if not pg.canonical:
            errors.append(f"{rel}: missing canonical")
        if pg.imgs_noalt:
            errors.append(f"{rel}: {pg.imgs_noalt} img without alt")
        for j in pg.ld:
            try:
                json.loads(j)
            except Exception as exc:
                errors.append(f"{rel}: JSON-LD does not parse ({exc})")
        page_path = "/" + rel
        for href in pg.links:
            r = resolve(href, page_path)
            if r is None:
                continue
            if r[0] == "ROOTBROKEN":
                errors.append(f"{rel}: root-relative link outside base path: {href}")
                continue
            _, target, frag = r
            if not target.exists():
                errors.append(f"{rel}: broken link {href}")
    # fragment check (same pass would need all pages parsed first)
    for f in htmls:
        pg = Page()
        pg.feed(f.read_text(encoding="utf-8"))
        for href in pg.links:
            if "#" in href and not href.startswith("#"):
                r = resolve(href, "/" + f.relative_to(DOCS).as_posix())
                if r and r[0] == "OK" and r[2] and r[1].exists() and r[1].suffix == ".html":
                    ids = id_cache.get(r[1])
                    if ids is not None and r[2] not in ids:
                        warns.append(f"{f.relative_to(DOCS).as_posix()}: fragment not found {href}")
    # sitemap
    sm = DOCS / "sitemap.xml"
    n_sm = 0
    if not sm.exists():
        errors.append("sitemap.xml missing")
    else:
        try:
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for loc in ET.parse(sm).getroot().findall("s:url/s:loc", ns):
                n_sm += 1
                r = resolve(loc.text, "/")
                if r is None or r[0] != "OK" or not r[1].exists():
                    errors.append(f"sitemap: entry not on disk: {loc.text}")
        except ET.ParseError as exc:
            errors.append(f"sitemap.xml invalid: {exc}")
    for name in ("robots.txt", "llms.txt", "llms-full.txt", "404.html", ".nojekyll"):
        if not (DOCS / name).exists():
            errors.append(f"{name} missing")

    for w in warns:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print(f"Checked {len(htmls)} HTML files, {n_sm} sitemap entries: {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
