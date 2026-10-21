# PartRevive content contract (all agents read this)

Site: a clean, fast static site for a one-person 3D-printing shop that makes replacement plastic parts to order.
Business model: every order starts with the customer's photo or part number; we quote within 24 h, then design, print and ship.
We do NOT stock parts and we are NOT affiliated with any brand. Every brand name is used only to say what a part fits.

## Honesty rules (binding)
- Never claim OEM equivalence, certification, food-contact safety, or safety-critical use (brakes, battery contacts, child items).
- Prices are "from $X" estimates for a typical quote, not fixed list prices.
- Lead time wording: "5 to 10 business days after approval".
- Material claims only from the config list (PETG, ASA, PA-CF, TPU). Say ASA for sun and heat, PA-CF for high load, TPU for flexible.
- Use "fits <brand> <model>" wording; never put a brand in the site name, logo, or image text.
- No fake reviews, no fake sales counts, no fabricated testimonials. A page may say "new shop, launched October 2026".

## Product JSON: content/products/<slug>.json
```json
{
  "slug": "rv-window-latch",
  "name": "RV window latch (Elixir, Hehr, Kinro style)",
  "category": "rv-camper",
  "meta_title": "max 60 chars, includes primary keyword",
  "meta_description": "max 155 chars: a direct answer sentence plus a call to action",
  "h1": "...",
  "primary_keyword": "rv window latch replacement",
  "secondary_keywords": ["camper window latch", "..."],
  "answer_first": "One or two plain sentences that directly answer what this is, who it fits, and what we do. Written so an AI assistant can quote it verbatim.",
  "fits": ["Elixir 4-inch window latches", "Hehr ...", "..."],
  "problem": "Why this part breaks, in 2-4 sentences (UV, brittle, assembly-only).",
  "oem_situation": "OEM and aftermarket situation: price, discontinued, sold as assembly. Cite only what RESEARCH_NOTES.md found; mark estimates as 'typically'.",
  "our_part": "How we make it: material, why that material, what we need from the customer (photo with coin or ruler, model number).",
  "price_from_usd": 18,
  "price_note": "per latch; pairs and multi-packs quoted lower per unit",
  "material": "ASA",
  "lead_time": "5 to 10 business days after approval",
  "specs": [{"label": "Material", "value": "ASA (UV and heat resistant)"}, {"label": "Max size", "value": "250 mm"}],
  "how_to_order": ["Step 1 ...", "Step 2 ...", "Step 3 ..."],
  "faqs": [{"q": "...", "a": "..."}],
  "related": ["rv-cabinet-door-latch"],
  "image": "rv-window-latch.jpg",
  "image_alt": "...",
  "sources": [{"label": "...", "url": "..."}]
}
```
Category is one of: rv-camper, kitchen-appliance, tools-toolboxes, automotive. Give 4-6 FAQs, including one on strength versus the original and one on how to measure. Images live in assets/img/<file> at 1200x900.

## Article JSON: content/articles/<slug>.json
```json
{
  "slug": "fridge-door-bin-broken-options",
  "title": "H1 title",
  "meta_title": "...", "meta_description": "...",
  "primary_keyword": "...",
  "answer_first": "Direct 2-sentence answer for AI assistants and featured snippets.",
  "body_html": "<h2>..</h2><p>..</p> 700-1200 words, H2/H3 structure, lists, one comparison table where useful, internal links to /parts/<slug>/ and /request/ (use paths relative to site root with the base path, i.e. href=\"/partrevive/parts/<slug>/\")",
  "faqs": [{"q": "...", "a": "..."}],
  "related_products": ["slug"],
  "image": "article-<slug>.jpg", "image_alt": "...",
  "date_published": "2026-10-21", "author": "PartRevive",
  "sources": [{"label": "...", "url": "..."}]
}
```

## Category JSON: content/categories/<slug>.json
```json
{ "slug": "rv-camper", "name": "RV and camper parts", "meta_title": "...", "meta_description": "...", "intro": "2-3 sentences", "image": "cat-rv-camper.jpg", "image_alt": "..." }
```

## URL layout (build output goes to /docs so GitHub Pages can serve it; site base path is /partrevive/)
- `/` home
- `/parts/<slug>/` product landing pages
- `/parts/` all parts index
- `/category/<slug>/` category pages
- `/guides/<slug>/` articles
- `/guides/` article index
- `/request/` quote request form (posts to the Cloud Run receiver in backend/quote-receiver/)
- `/about/`, `/faq/`, `/404.html`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/llms-full.txt`

## Fixed slugs
Products: rv-window-latch, rv-cabinet-door-latch, whirlpool-kitchenaid-fridge-door-bin, samsung-fridge-door-bin, dewalt-tstak-latch-clip, milwaukee-packout-drawer-latch, bmw-e90-e46-cup-holder, maytag-whirlpool-dryer-knob, bosch-dishwasher-tine-clip, dyson-v11-trigger, custom-replacement-part-from-photo

Articles: fridge-door-bin-broken-options, rv-window-latch-replacement-guide, dewalt-tstak-latch-keeps-breaking, can-this-plastic-part-be-3d-printed, how-to-photograph-a-broken-part-for-a-quote

Categories: rv-camper, kitchen-appliance, tools-toolboxes, automotive

Images (assets/img/): one per product slug `<slug>.jpg`, one per article `article-<slug>.jpg`, one per category `cat-<slug>.jpg`, plus `hero.jpg` (1600x900) and `og-default.jpg` (1200x630).
