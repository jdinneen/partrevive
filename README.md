# PartRevive

Static site for a made-to-order 3D-printed replacement-parts shop. Served by GitHub Pages from `docs/`.

- Content: `content/` (JSON per product, guide, category; contract in `SCHEMA.md`)
- Templates: `templates/` (Jinja2)
- Build: `python scripts/build.py` then `python scripts/check_site.py`
- Images: `assets/img/` (generated locally; `scripts/images/manifest.json` records prompts and seeds)
- Config: `config.json` (site name, base URL, analytics ID, form endpoint)

Brand names on the site identify fit only. PartRevive is not affiliated with any manufacturer.
