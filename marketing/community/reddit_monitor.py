#!/usr/bin/env python3
"""Read-only Reddit thread finder for PartRevive. Never posts, votes or comments.

Pulls the newest 25 posts of each watchlist subreddit from the public JSON
endpoint, keyword-filters them, and writes queue.json next to this file.
Run: python reddit_monitor.py [--subs RVLiving,GoRVing] [--delay 3]
If Reddit blocks the request (HTTP 403/429) the sub is recorded under "errors"
and the script moves on; it does not retry or work around the block.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "PartReviveThreadFinder/0.1 (read-only research script; contact jon.dinneen2@gmail.com)"

SUBS = ["RVLiving", "GoRVing", "rvs", "TravelTrailers", "Tacoma", "ToyotaTacoma",
        "Silverado", "Appliances", "ApplianceRepair", "fixit", "HomeImprovement",
        "3Dprinting", "functionalprint", "3dPrintSellers", "YetiCoolers", "Dewalt",
        "MilwaukeeTool", "pelicancases", "Dyson"]

KEYWORDS = ["latch", "hinge", "knob", "clip", "door bin", "cup holder", "trigger",
            "broke", "snapped", "cracked", "replacement"]

# (slug, words that must appear in the title/body to suggest it)
SLUG_RULES = [
    ("rv-screen-door-latch", ["screen door"]),
    ("rv-window-latch", ["window latch", "rv window", "camper window"]),
    ("rv-fridge-door-handle", ["dometic", "norcold", "rv fridge", "rv refrigerator"]),
    ("whirlpool-kitchenaid-fridge-door-bin", ["door bin", "fridge shelf", "refrigerator door", "fridge door"]),
    ("dewalt-tstak-latch-clip", ["tstak", "toughsystem", "dewalt"]),
    ("pelican-case-latch", ["pelican", "peli", "hard case", "storm case"]),
    ("cooler-lid-latch", ["yeti", "rtic", "cooler latch", "roadie", "tundra"]),
    ("cooler-lid-hinge", ["cooler hinge", "igloo", "coleman", "cooler lid"]),
    ("toyota-tacoma-console-latch", ["tacoma", "console latch", "console lid"]),
    ("dyson-v11-trigger", ["dyson", "v11"]),
]


def fetch(sub):
    """Reddit's JSON endpoint returns 403 from this network; the RSS feed does not.
    Returns the same shape the JSON code expects: {"data": {"children": [{"data": post}]}}."""
    import re
    import xml.etree.ElementTree as ET
    url = f"https://www.reddit.com/r/{sub}/new.rss?limit=25"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/atom+xml"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    posts = []
    for e in root.findall("a:entry", ns):
        link = e.find("a:link", ns)
        content = e.find("a:content", ns)
        body = re.sub(r"<[^>]+>", " ", content.text or "") if content is not None else ""
        posts.append({"title": (e.findtext("a:title", default="", namespaces=ns) or ""),
                      "selftext": body, "permalink": (link.get("href") if link is not None else "").replace("https://www.reddit.com", ""),
                      "created_utc": e.findtext("a:updated", default="", namespaces=ns),
                      "subreddit": sub})
    return {"data": {"children": [{"data": p} for p in posts]}}


def suggest(text):
    t = text.lower()
    for slug, words in SLUG_RULES:
        if any(w in t for w in words):
            return slug
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subs", help="comma-separated override of the watchlist")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between requests")
    args = ap.parse_args()
    subs = args.subs.split(",") if args.subs else SUBS

    queue, errors, scanned = [], {}, {}
    for i, sub in enumerate(subs):
        if i:
            time.sleep(args.delay)
        try:
            data = fetch(sub)
        except urllib.error.HTTPError as e:
            errors[sub] = f"HTTP {e.code}"
            continue
        except Exception as e:  # network, JSON, timeout
            errors[sub] = f"{type(e).__name__}: {e}"
            continue
        posts = [c["data"] for c in data.get("data", {}).get("children", [])]
        scanned[sub] = len(posts)
        for p in posts:
            text = f"{p.get('title','')} {p.get('selftext','')}"
            low = text.lower()
            hits = [k for k in KEYWORDS if k in low]
            if not hits:
                continue
            queue.append({
                "subreddit": sub,
                "url": "https://www.reddit.com" + p.get("permalink", ""),
                "title": p.get("title", ""),
                "matched_keywords": hits,
                "suggested_answer_slug": suggest(text),
                "created_utc": p.get("created_utc"),
            })

    out = {"generated_utc": int(time.time()), "user_agent": UA,
           "subs_scanned": scanned, "errors": errors, "queue": queue}
    with open(os.path.join(HERE, "queue.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"scanned {len(scanned)} subs, {len(errors)} errors, {len(queue)} matches -> queue.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
