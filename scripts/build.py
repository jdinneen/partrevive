#!/usr/bin/env python
"""PartRevive static site generator.  Usage: python scripts/build.py"""
import datetime
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
import os
CONTENT = Path(os.environ["PARTREVIVE_CONTENT"]) if os.environ.get("PARTREVIVE_CONTENT") else ROOT / "content"  # override for testing
ASSETS = ROOT / "assets"
TODAY = datetime.date.today().isoformat()
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

PRODUCT_ORDER = [
    "rv-window-latch", "rv-cabinet-door-latch", "whirlpool-kitchenaid-fridge-door-bin",
    "samsung-fridge-door-bin", "dewalt-tstak-latch-clip", "milwaukee-packout-drawer-latch",
    "bmw-e90-e46-cup-holder", "maytag-whirlpool-dryer-knob", "bosch-dishwasher-tine-clip",
    "dyson-v11-trigger", "custom-replacement-part-from-photo",
]
CATEGORY_FALLBACK = {
    "rv-camper": ("RV and camper parts", "Replacement latches, handles and trim for RVs and campers."),
    "kitchen-appliance": ("Kitchen appliance parts", "Replacement bins, knobs and clips for fridges, dryers and dishwashers."),
    "tools-toolboxes": ("Tool and toolbox parts", "Replacement latches, clips and small parts for tool storage."),
    "automotive": ("Automotive interior parts", "Replacement interior trim parts for cars, made to order."),
}
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print("WARNING: " + msg, file=sys.stderr)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa
        warn(f"cannot read {path.name}: {exc}")
        return None


def load_dir(sub):
    d = CONTENT / sub
    items = {}
    if not d.is_dir():
        warn(f"content/{sub}/ missing; skipping")
        return items
    files = sorted(d.glob("*.json"))
    if not files:
        warn(f"content/{sub}/ has no JSON yet")
    for f in files:
        data = load_json(f)
        if not isinstance(data, dict):
            continue
        slug = data.get("slug") or f.stem
        if not SLUG_RE.match(slug):
            warn(f"{f.name}: bad slug {slug!r}; skipped")
            continue
        data["slug"] = slug
        items[slug] = data
    return items


cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
BASE_URL = cfg["base_url"].rstrip("/")
BASE = urlparse(BASE_URL).path.rstrip("/")  # "/partrevive"


def u(path):
    return BASE + path


def absu(path):
    return BASE_URL + path


_img_cache = {}


def imginfo(file):
    if not file:
        return None
    if file in _img_cache:
        return _img_cache[file]
    p = ASSETS / "img" / file
    info = None
    if p.is_file():
        try:
            from PIL import Image
            with Image.open(p) as im:
                w, h = im.size
        except Exception:
            w, h = 1200, 900
        info = {"src": u("/assets/img/" + file), "abs": absu("/assets/img/" + file), "w": w, "h": h}
    else:
        warn(f"image missing: assets/img/{file} (image omitted)")
    _img_cache[file] = info
    return info


def ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


# ---------- text extraction for llms-full.txt ----------
class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "form", "svg", "noscript", "figure", "button"}
    BLOCK = {"p", "div", "section", "article", "ul", "ol", "table", "details", "blockquote", "dl"}

    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = 0
        self.cell_first = True

    hid = 0

    def handle_starttag(self, tag, attrs):
        if tag == "span" and dict(attrs).get("aria-hidden") == "true" and not self.skip:
            self.skip += 1
            self.hid = 1
            return
        if tag in self.SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "summary":
            self.out.append("\n\n### ")
        elif tag in ("td", "th"):
            self.out.append("" if self.cell_first else " | ")
            self.cell_first = False
        elif tag == "tr":
            self.out.append("\n")
            self.cell_first = True
        elif tag == "br":
            self.out.append("\n")
        elif tag in self.BLOCK:
            self.out.append("\n\n")

    def handle_endtag(self, tag):
        if tag == "span" and self.hid:
            self.skip -= 1
            self.hid = 0
            return
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "summary", "p"):
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(page_html):
    m = re.search(r"<main\b.*?</main>", page_html, re.S)
    if not m:
        return ""
    t = TextExtractor()
    t.feed(m.group(0))
    text = "".join(t.out)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"^- *\n+(#+ )", r"\1", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------- general content ----------
def general_faqs():
    lead = cfg["lead_time"]
    quote = cfg["quote_turnaround"]
    mats = ", ".join(cfg["materials"])
    return [
        {"q": "How does PartRevive work?",
         "a": f"Send a photo of the broken part, plus the brand and model it came from. We reply with a quote {quote}. Once you approve it we design the part, print it, and ship it. Nothing is stocked; every part is made to order."},
        {"q": "How much does a replacement part cost?",
         "a": "Each part page shows a from-price for a typical quote. The final price depends on size, material and quantity, and we confirm it with you before anything is printed."},
        {"q": "How long does it take?",
         "a": f"You get a quote {quote}. Making and shipping takes {lead}."},
        {"q": "Is a 3D-printed part as strong as the original?",
         "a": "It depends on the material and the part. A part in a stronger material such as PA-CF can be stiffer than the original plastic, while a flexible TPU part will not be. We tell you honestly what to expect in the quote, and we do not claim equivalence with the original maker's part."},
        {"q": "What materials do you use?",
         "a": f"We print in {mats}. PETG suits general indoor parts, ASA suits sun and heat, PA-CF suits high loads, and TPU suits flexible parts."},
        {"q": "What will you not make?",
         "a": "We do not make safety-critical parts such as brake or steering components, battery contacts or other live electrical parts, children's items, or surfaces that touch food. If you are unsure, ask and we will tell you straight."},
        {"q": "Are you affiliated with the brands on your site?",
         "a": "No. Brand and model names are used only to say what a part fits. We are an independent shop."},
        {"q": "How do I photograph and measure the broken part?",
         "a": "Photograph the part from two or three angles on a plain background, with a coin or ruler beside it for scale, and include the model number of the appliance, vehicle or tool. Keep the broken pieces; they help even if they are in several bits."},
        {"q": "What is the largest part you can make?",
         "a": f"About {cfg['max_size_mm']} mm in the longest direction. Larger parts may be possible as an assembly; ask us."},
        {"q": "Where do you ship?",
         "a": f"We currently serve customers in the {cfg['country']}."},
    ]


def faq_ld(faqs):
    faqs = [f for f in (faqs or []) if f.get("q") and f.get("a")]
    if not faqs:
        return None
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": f["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs]}


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": absu(p)}
                                for i, (n, p) in enumerate(items)]}


def org_ld():
    return {"@type": "Organization", "@id": absu("/#organization"), "name": cfg["site_name"],
            "url": absu("/"), "description": cfg["tagline"], "foundingDate": cfg["founded"],
            "areaServed": "US"}


def item_list(entries):
    return {"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "url": absu(url), "name": name}
        for i, (name, url) in enumerate(entries)]}


def main():
    cats = load_dir("categories")
    prods = load_dir("products")
    arts = load_dir("articles")

    order = {s: i for i, s in enumerate(PRODUCT_ORDER)}
    products = sorted(prods.values(), key=lambda p: (order.get(p["slug"], 999), p["slug"]))
    articles = sorted(arts.values(), key=lambda a: a["slug"])
    articles.sort(key=lambda a: a.get("date_published", ""), reverse=True)

    for p in products:
        c = p.get("category")
        if c and c not in cats:
            name, intro = CATEGORY_FALLBACK.get(c, (c.replace("-", " ").title(), ""))
            warn(f"category {c!r} has no JSON; using fallback")
            cats[c] = {"slug": c, "name": name, "intro": intro,
                       "meta_title": name + " | PartRevive", "meta_description": intro}
    keys = list(CATEGORY_FALLBACK)
    categories = sorted(cats.values(), key=lambda c: keys.index(c["slug"]) if c["slug"] in keys else 99)
    for p in products:
        p["_cat"] = cats.get(p.get("category"))
        p["_url"] = f"/parts/{p['slug']}/"
    for c in categories:
        c["_url"] = f"/category/{c['slug']}/"
        c["_products"] = [p for p in products if p.get("category") == c["slug"]]
    for a in articles:
        a["_url"] = f"/guides/{a['slug']}/"

    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    if ASSETS.is_dir():
        shutil.copytree(ASSETS, DOCS / "assets")
    (DOCS / ".nojekyll").write_text("")
    if cfg.get("indexnow_key"):
        (DOCS / f"{cfg['indexnow_key']}.txt").write_text(cfg["indexnow_key"])
    if cfg.get("custom_domain"):
        (DOCS / "CNAME").write_text(cfg["custom_domain"].strip() + "\n")

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.globals.update(u=u, absu=absu, imginfo=imginfo, site=cfg, categories=categories,
                       year=TODAY[:4])

    pages = []

    def render(tpl, path, page, in_sitemap=True, **ctx):
        page.setdefault("path", path)
        page.setdefault("noindex", False)
        page["jsonld"] = [ld(j) for j in page.get("jsonld", []) if j]
        page.setdefault("image", None)
        out = env.get_template(tpl).render(page=page, **ctx)
        target = DOCS / path.lstrip("/")
        if path.endswith("/"):
            target = target / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out, encoding="utf-8")
        pages.append({"path": path, "title": page["title"], "desc": page["description"],
                      "answer": page.get("answer") or page["description"], "text": html_to_text(out),
                      "sitemap": in_sitemap, "group": page.get("group", "Pages")})

    faqs = general_faqs()

    # Home
    render("home.html", "/", {
        "title": f"{cfg['site_name']}: Made-to-order 3D-printed replacement parts",
        "description": "Send a photo of a broken plastic part and get a quote within 24 hours. Made-to-order 3D-printed replacements for appliances, RVs, tools and cars.",
        "answer": "PartRevive makes replacement plastic parts to order by 3D printing. Send a photo of the broken part and get a quote within 24 hours on business days.",
        "nav": "home", "image": "hero.jpg", "group": "Main",
        "jsonld": [
            {"@context": "https://schema.org", "@graph": [
                org_ld(),
                {"@type": "WebSite", "@id": absu("/#website"), "url": absu("/"), "name": cfg["site_name"],
                 "description": cfg["tagline"], "inLanguage": cfg["locale"],
                 "publisher": {"@id": absu("/#organization")},
                 "potentialAction": {"@type": "SearchAction",
                                     "target": {"@type": "EntryPoint", "urlTemplate": absu("/parts/") + "?q={search_term_string}"},
                                     "query-input": "required name=search_term_string"}}]},
            faq_ld(faqs[:6])]},
        products=products, latest=articles[:3], faqs=faqs[:6])

    # Product pages
    for p in products:
        slug = p["slug"]
        rel = [prods[s] for s in p.get("related", []) if s in prods and s != slug]
        for q in products:
            if len(rel) >= 3:
                break
            if q["slug"] != slug and q not in rel and q.get("category") == p.get("category"):
                rel.append(q)
        rel = rel[:4]
        guides = [a for a in articles if slug in a.get("related_products", [])]
        cat = p["_cat"]
        crumbs = [("Home", "/"), ("Parts", "/parts/")]
        if cat:
            crumbs.append((cat["name"], cat["_url"]))
        crumbs.append((p.get("name", slug), p["_url"]))
        img = imginfo(p.get("image"))
        price = p.get("price_from_usd")
        prod_ld = {"@context": "https://schema.org", "@type": "Product", "name": p.get("name", slug),
                   "description": p.get("answer_first", ""), "sku": slug,
                   "brand": {"@type": "Brand", "name": cfg["site_name"]},
                   "category": cat["name"] if cat else None,
                   "url": absu(p["_url"]), "material": p.get("material")}
        if img:
            prod_ld["image"] = [img["abs"]]
        if price is not None:
            prod_ld["offers"] = {
                "@type": "Offer", "url": absu(p["_url"]), "priceCurrency": "USD", "price": price,
                "priceSpecification": {"@type": "PriceSpecification", "priceCurrency": "USD", "minPrice": price},
                "availability": "https://schema.org/PreOrder",
                "itemCondition": "https://schema.org/NewCondition",
                "description": "Made to order. Price is a from-estimate for a typical quote; lead time " + p.get("lead_time", cfg["lead_time"]) + ".",
                "seller": {"@id": absu("/#organization")}}
        prod_ld = {k: v for k, v in prod_ld.items() if v is not None}
        lds = [prod_ld, faq_ld(p.get("faqs")), crumbs_ld(crumbs)]
        if "custom" in slug and p.get("how_to_order"):
            lds.append({"@context": "https://schema.org", "@type": "HowTo",
                        "name": "How to get a replacement part made from a photo",
                        "description": p.get("answer_first", ""),
                        "step": [{"@type": "HowToStep", "position": i + 1, "name": s[:80], "text": s}
                                 for i, s in enumerate(p["how_to_order"])]})
        render("product.html", p["_url"], {
            "title": p.get("meta_title") or p.get("name", slug),
            "description": p.get("meta_description") or p.get("answer_first", ""),
            "answer": p.get("answer_first"), "nav": "parts", "image": p.get("image"),
            "og_type": "product", "jsonld": lds, "crumbs": crumbs, "group": "Parts"},
            p=p, related=rel, guides=guides, cat=cat)

    # Products index
    crumbs = [("Home", "/"), ("Parts", "/parts/")]
    render("products_index.html", "/parts/", {
        "title": "All made-to-order replacement parts | PartRevive",
        "description": "Browse made-to-order 3D-printed replacement parts for RVs, kitchen appliances, tools and cars, or send a photo of any broken part for a quote.",
        "nav": "parts", "group": "Parts", "crumbs": crumbs,
        "jsonld": [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "All parts",
                    "url": absu("/parts/"), "isPartOf": {"@id": absu("/#website")},
                    "mainEntity": item_list([(p.get("name"), p["_url"]) for p in products])},
                   crumbs_ld(crumbs)]},
        products=products)

    # Categories
    for c in categories:
        crumbs = [("Home", "/"), ("Parts", "/parts/"), (c["name"], c["_url"])]
        render("category.html", c["_url"], {
            "title": c.get("meta_title") or c["name"],
            "description": c.get("meta_description") or c.get("intro", ""),
            "nav": "parts", "image": c.get("image"), "group": "Categories", "crumbs": crumbs,
            "jsonld": [{"@context": "https://schema.org", "@type": "CollectionPage", "name": c["name"],
                        "description": c.get("intro", ""), "url": absu(c["_url"]),
                        "isPartOf": {"@id": absu("/#website")},
                        "mainEntity": item_list([(p.get("name"), p["_url"]) for p in c["_products"]])},
                       crumbs_ld(crumbs)]},
            c=c)

    # Articles
    for a in articles:
        crumbs = [("Home", "/"), ("Guides", "/guides/"), (a.get("title", a["slug"]), a["_url"])]
        img = imginfo(a.get("image"))
        art_ld = {"@context": "https://schema.org", "@type": "Article", "headline": a.get("title"),
                  "description": a.get("meta_description") or a.get("answer_first"),
                  "datePublished": a.get("date_published"), "dateModified": a.get("date_published"),
                  "author": {"@type": "Organization", "name": a.get("author", cfg["site_name"]), "url": absu("/")},
                  "publisher": {"@id": absu("/#organization")},
                  "mainEntityOfPage": absu(a["_url"]), "inLanguage": cfg["locale"]}
        if img:
            art_ld["image"] = [img["abs"]]
        render("article.html", a["_url"], {
            "title": a.get("meta_title") or a.get("title"),
            "description": a.get("meta_description") or a.get("answer_first", ""),
            "answer": a.get("answer_first"), "nav": "guides", "image": a.get("image"),
            "og_type": "article", "group": "Guides", "crumbs": crumbs,
            "jsonld": [art_ld, faq_ld(a.get("faqs")), crumbs_ld(crumbs)]},
            a=a, rel_products=[prods[s] for s in a.get("related_products", []) if s in prods])

    crumbs = [("Home", "/"), ("Guides", "/guides/")]
    render("articles_index.html", "/guides/", {
        "title": "Guides to fixing broken plastic parts | PartRevive",
        "description": "Plain-English guides on repairing or replacing broken plastic parts, and when a made-to-order 3D-printed part is the answer.",
        "nav": "guides", "group": "Guides", "crumbs": crumbs,
        "jsonld": [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Guides",
                    "url": absu("/guides/"), "isPartOf": {"@id": absu("/#website")},
                    "mainEntity": item_list([(a.get("title"), a["_url"]) for a in articles])},
                   crumbs_ld(crumbs)]},
        articles=articles)

    # Request, thanks
    parts_map = {p["slug"]: p.get("name", p["slug"]) for p in products}
    crumbs = [("Home", "/"), ("Request a quote", "/request/")]
    render("request.html", "/request/", {
        "title": "Request a quote for a replacement part | PartRevive",
        "description": "Send a photo and the model number of your broken part. We reply with a quote within 24 hours on business days.",
        "nav": "request", "group": "Pages", "crumbs": crumbs,
        "answer": "Send a photo of the broken part and its model number; we reply with a quote within 24 hours on business days.",
        "jsonld": [crumbs_ld(crumbs)]},
        parts_map=parts_map, form_action=cfg["form_action"], next_url=absu("/request/thanks/"),
        photo_guide=arts.get("how-to-photograph-a-broken-part-for-a-quote"))
    render("thanks.html", "/request/thanks/", {
        "title": "Thank you | PartRevive", "description": "Your quote request was sent.",
        "nav": "request", "noindex": True}, in_sitemap=False)

    # About, FAQ, 404
    crumbs = [("Home", "/"), ("About", "/about/")]
    render("about.html", "/about/", {
        "title": "About PartRevive | New made-to-order parts shop",
        "description": "PartRevive is a new one-person shop (launched October 2026) that 3D-prints replacement plastic parts to order. How we work and what we will not make.",
        "nav": "about", "group": "Pages", "crumbs": crumbs,
        "answer": "PartRevive is a new one-person shop, launched October 2026, that 3D-prints replacement plastic parts to order.",
        "jsonld": [{"@context": "https://schema.org", "@type": "AboutPage", "url": absu("/about/"),
                    "mainEntity": {"@type": "Organization", "@id": absu("/#organization"), "name": cfg["site_name"]}},
                   crumbs_ld(crumbs)]})
    crumbs = [("Home", "/"), ("FAQ", "/faq/")]
    render("faq.html", "/faq/", {
        "title": "FAQ: ordering made-to-order 3D-printed parts | PartRevive",
        "description": "Answers on cost, lead time, strength, materials, what we will not make, and how to photograph and measure a broken part.",
        "nav": "faq", "group": "Pages", "crumbs": crumbs, "jsonld": [faq_ld(faqs), crumbs_ld(crumbs)]},
        faqs=faqs)
    render("404.html", "/404.html", {
        "title": "Page not found | PartRevive",
        "description": "That page does not exist. Browse our parts or request a quote.",
        "noindex": True}, in_sitemap=False)

    # sitemap, robots, llms
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pg in pages:
        if pg["sitemap"]:
            sm.append(f"  <url><loc>{html.escape(absu(pg['path']))}</loc><lastmod>{TODAY}</lastmod></url>")
    sm.append("</urlset>")
    (DOCS / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "anthropic-ai",
               "PerplexityBot", "Google-Extended", "Applebot-Extended", "Bingbot", "CCBot", "Amazonbot", "DuckAssistBot"]
    robots = "User-agent: *\nAllow: /\n\n"
    robots += "".join(f"User-agent: {b}\nAllow: /\n\n" for b in ai_bots)
    robots += f"Sitemap: {absu('/sitemap.xml')}\n"
    (DOCS / "robots.txt").write_text(robots)

    L = [f"# {cfg['site_name']}", "",
         f"> {cfg['tagline']}. New shop (launched October 2026). Nothing is stocked: send a photo, "
         f"get a quote {cfg['quote_turnaround']}, lead time {cfg['lead_time']}. "
         "Not affiliated with any brand named; names identify fit only.", ""]
    for g in ["Main", "Parts", "Categories", "Guides", "Pages"]:
        items = [pg for pg in pages if pg["sitemap"] and pg["group"] == g]
        if not items:
            continue
        L.append(f"## {g}")
        for pg in items:
            line = " ".join((pg["answer"] or "").split())
            L.append(f"- [{pg['title']}]({absu(pg['path'])}): {line}")
        L.append("")
    (DOCS / "llms.txt").write_text("\n".join(L), encoding="utf-8")

    F = [f"# {cfg['site_name']}: full site text", "", f"Source: {absu('/')}  Generated: {TODAY}", ""]
    for pg in pages:
        if pg["sitemap"]:
            F += ["", "=" * 70, f"PAGE: {pg['title']}", f"URL: {absu(pg['path'])}", "=" * 70, "", pg["text"], ""]
    (DOCS / "llms-full.txt").write_text("\n".join(F), encoding="utf-8")

    print(f"Built {len(pages)} pages ({len(products)} parts, {len(articles)} guides, "
          f"{len(categories)} categories) -> {DOCS}")
    print(f"{len(WARNINGS)} warning(s)")


if __name__ == "__main__":
    main()
