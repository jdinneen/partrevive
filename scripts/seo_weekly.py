#!/usr/bin/env python
"""Weekly search loop for PartRevive.

Pulls Google Search Console and GA4 data for the last 28 days, writes a Markdown
report under reports/seo/, picks the queries and pages worth acting on, and opens
(or updates) a GitHub issue so Jon gets an email. Run by the scheduled task
"PartRevive-SEO-Weekly" (see scripts/install_seo_task.ps1); safe to run by hand.

Auth: impersonates ga-reader@monterey-bay-lab via the logged-in gcloud account.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://jdinneen.github.io/partrevive/"
PROPERTY = "properties/560119783"
SA = "ga-reader@monterey-bay-lab.iam.gserviceaccount.com"
SCOPES = "https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/analytics.readonly"
REPO = "jdinneen/partrevive"
OUT = ROOT / "reports" / "seo"


def token():
    cmd = ["gcloud", "auth", "print-access-token", f"--impersonate-service-account={SA}", f"--scopes={SCOPES}"]
    r = subprocess.run(cmd, capture_output=True, text=True, shell=(sys.platform == "win32"))
    t = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if not t:
        raise SystemExit("no access token: " + r.stderr[-400:])
    return t


def post(url, body, tok):
    req = Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        return json.load(urlopen(req, timeout=60))
    except HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:300]}


def gsc(tok, start, end, dim):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/searchAnalytics/query"
    body = {"startDate": start, "endDate": end, "dimensions": [dim], "rowLimit": 250, "dataState": "all"}
    r = post(url, body, tok)
    return r.get("rows", []), r.get("error")


def ga4(tok, start, end):
    url = f"https://analyticsdata.googleapis.com/v1beta/{PROPERTY}:runReport"
    body = {"dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": "pagePath"}, {"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}, {"name": "totalUsers"}, {"name": "eventCount"}],
            "limit": 200}
    r = post(url, body, tok)
    rows = []
    for row in r.get("rows", []):
        d = [x["value"] for x in row["dimensionValues"]]
        m = [x["value"] for x in row["metricValues"]]
        rows.append((d[0], d[1], int(m[0]), int(m[1]), int(m[2])))
    leads = post(url, {"dateRanges": [{"startDate": start, "endDate": end}],
                       "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}]}, tok)
    events = {row["dimensionValues"][0]["value"]: int(row["metricValues"][0]["value"]) for row in leads.get("rows", [])}
    return rows, events, r.get("error")


def main():
    today = dt.date.today()
    end = (today - dt.timedelta(days=2)).isoformat()
    start = (today - dt.timedelta(days=30)).isoformat()
    tok = token()
    queries, qerr = gsc(tok, start, end, "query")
    pages, perr = gsc(tok, start, end, "page")
    ga_rows, events, gerr = ga4(tok, start, end)

    total_clicks = sum(r["clicks"] for r in queries)
    total_impr = sum(r["impressions"] for r in queries)
    sessions = sum(r[2] for r in ga_rows)

    # Opportunities: showing in Google but not winning the click.
    opp = [r for r in queries if r["impressions"] >= 5 and (r["position"] > 7 or r["ctr"] < 0.03)]
    opp.sort(key=lambda r: -r["impressions"])
    zero = [r for r in pages if r["impressions"] >= 5 and r["clicks"] == 0]

    L = [f"# PartRevive search report, {start} to {end}", ""]
    L += [f"- Google impressions: {total_impr}, clicks: {total_clicks}, queries seen: {len(queries)}",
          f"- Site sessions (GA4): {sessions}; quote form sends: {events.get('generate_lead', 0)}; quote-button clicks: {events.get('select_content', 0)}", ""]
    if qerr or perr or gerr:
        L += ["**API errors:** " + json.dumps({"queries": qerr, "pages": perr, "ga4": gerr})[:500], ""]
    L += ["## Top queries", "", "| query | impressions | clicks | avg position |", "|---|---:|---:|---:|"]
    for r in sorted(queries, key=lambda r: -r["impressions"])[:25]:
        L.append(f"| {r['keys'][0]} | {r['impressions']} | {r['clicks']} | {r['position']:.1f} |")
    L += ["", "## Queries to act on (seen, not clicked)", ""]
    if not opp:
        L.append("- none yet (a new site needs weeks of impressions before this list fills)")
    for r in opp[:15]:
        L.append(f"- **{r['keys'][0]}**: {r['impressions']} impressions, position {r['position']:.1f}. "
                 "Action: if no page targets this phrase, draft a guide or product page for it; "
                 "if one does, put the phrase in its title and first sentence.")
    L += ["", "## Pages shown but never clicked", ""] + ([f"- {r['keys'][0]} ({r['impressions']} impressions, position {r['position']:.1f})" for r in zero[:15]] or ["- none"])
    L += ["", "## Traffic by page and channel (GA4)", "", "| page | channel | sessions | users |", "|---|---|---:|---:|"]
    for p, ch, s, u, _ in sorted(ga_rows, key=lambda r: -r[2])[:25]:
        L.append(f"| {p} | {ch} | {s} | {u} |")
    L += ["", "## Standing weekly checklist", "",
          "1. Answer 2-3 fresh forum or Reddit threads from marketing/community/queue.json (run reddit_monitor.py).",
          "2. Post one short video from marketing/video/.",
          "3. Draft one new guide for the top unanswered query above (content/articles/), rebuild, push.",
          "4. Reply to every quote request within 24 hours."]
    OUT.mkdir(parents=True, exist_ok=True)
    rep = OUT / f"{today.isoformat()}.md"
    rep.write_text("\n".join(L), encoding="utf-8")
    print(rep)

    body = "\n".join(L)
    title = f"Weekly search report {today.isoformat()}: {total_impr} impressions, {total_clicks} clicks, {sessions} sessions"
    r = subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body, "--label", "seo-weekly"],
                       capture_output=True, text=True, shell=(sys.platform == "win32"))
    if r.returncode != 0 and "label" in r.stderr:
        subprocess.run(["gh", "label", "create", "seo-weekly", "--repo", REPO, "--color", "0E8A16"], capture_output=True, shell=(sys.platform == "win32"))
        r = subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body, "--label", "seo-weekly"],
                           capture_output=True, text=True, shell=(sys.platform == "win32"))
    print(r.stdout.strip() or r.stderr.strip()[-300:])


if __name__ == "__main__":
    main()
