"""PartRevive quote-request receiver (Cloud Run).

Accepts the static site's form POST (multipart, optional photo), stores the lead
in a private Cloud Storage bucket, and writes one structured log line per lead
that a Cloud Monitoring log-based alert turns into an email to Jon.

No third-party form service, no stored secrets.
"""
import datetime
import json
import os
import re
import secrets
import sys
import time
from collections import defaultdict, deque

from flask import Flask, Response, jsonify, redirect, request
from google.cloud import storage

BUCKET = os.environ.get("LEADS_BUCKET", "partrevive-leads-mbl")
SITE = os.environ.get("SITE_ORIGIN", "https://jdinneen.github.io")
SITE_BASE = os.environ.get("SITE_BASE", "https://jdinneen.github.io/partrevive")
THANKS = SITE_BASE + "/request/thanks/"
MAX_BYTES = 12 * 1024 * 1024          # request cap (photo limit is 10 MB on the page)
MAX_PHOTO = 10 * 1024 * 1024
RATE_PER_HOUR = 12                    # per client IP, per instance
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_IMG = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/gif")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES
_hits = defaultdict(deque)
_client = None


def _bucket():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client.bucket(BUCKET)


def log(payload, severity="NOTICE"):
    payload = dict(payload)
    payload["severity"] = severity
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = SITE
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Accept, Content-Type, X-Requested-With"
    resp.headers["Access-Control-Max-Age"] = "86400"
    resp.headers["Vary"] = "Origin"
    return resp


def wants_json():
    return "application/json" in request.headers.get("Accept", "") or request.headers.get("X-Requested-With") == "fetch"


def fail(msg, code=400):
    log({"event": "partrevive_lead_rejected", "reason": msg, "ip": client_ip()}, "WARNING")
    if wants_json():
        return cors(jsonify(ok=False, error=msg)), code
    return cors(redirect(SITE_BASE + "/request/?error=" + re.sub(r"[^a-z0-9_]", "_", msg.lower())[:40], code=303))


def client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or "unknown"


def rate_limited(ip):
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE_PER_HOUR:
        return True
    q.append(now)
    return False


@app.after_request
def add_cors(resp):
    return cors(resp)


@app.route("/", methods=["GET", "POST", "OPTIONS"], provide_automatic_options=False)
def entry():
    if request.method == "GET":
        return Response("partrevive quote receiver: ok\n", mimetype="text/plain")
    if request.method == "OPTIONS":
        return Response("", status=204)
    return receive()


def receive():
    f = request.form
    if f.get("_honey"):                        # honeypot filled: a bot
        return fail("rejected")
    ip = client_ip()
    if rate_limited(ip):
        return fail("too_many_requests", 429)
    name = (f.get("name") or "").strip()[:200]
    email = (f.get("email") or "").strip()[:200]
    part = (f.get("part") or "").strip()[:300]
    broke = (f.get("what_broke") or "").strip()[:5000]
    qty = (f.get("quantity") or "1").strip()[:6]
    if not (name and email and part and broke):
        return fail("missing_fields")
    if not EMAIL_RE.match(email):
        return fail("bad_email")
    try:
        qty_n = max(1, min(500, int(qty)))
    except ValueError:
        qty_n = 1

    now = datetime.datetime.now(datetime.timezone.utc)
    lead_id = now.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    bucket = _bucket()
    photo_uri = ""
    photo = request.files.get("attachment")
    if photo and photo.filename:
        data = photo.read()
        if len(data) > MAX_PHOTO:
            return fail("photo_too_large", 413)
        ctype = (photo.mimetype or "").lower()
        if data and ctype in ALLOWED_IMG:
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic",
                   "image/heif": "heif", "image/gif": "gif"}[ctype]
            blob = bucket.blob(f"leads/{lead_id}/photo.{ext}")
            blob.upload_from_string(data, content_type=ctype)
            photo_uri = f"gs://{BUCKET}/leads/{lead_id}/photo.{ext}"
        elif data:
            log({"event": "partrevive_photo_skipped", "lead_id": lead_id, "mimetype": ctype}, "WARNING")

    record = {
        "lead_id": lead_id, "received_utc": now.isoformat(), "name": name, "email": email,
        "part": part, "what_broke": broke, "quantity": qty_n, "photo": photo_uri, "ip": ip,
        "user_agent": request.headers.get("User-Agent", "")[:300],
        "referer": request.headers.get("Referer", "")[:300],
    }
    bucket.blob(f"leads/{lead_id}/lead.json").upload_from_string(
        json.dumps(record, ensure_ascii=False, indent=2), content_type="application/json")

    # One structured line per lead; the log-based alert emails Jon from this.
    log({"event": "partrevive_lead", "lead_id": lead_id, "name": name, "email": email, "part": part,
         "what_broke": broke[:800], "quantity": str(qty_n), "photo": photo_uri or "(none)",
         "console": f"https://console.cloud.google.com/storage/browser/{BUCKET}/leads/{lead_id}"})

    if wants_json():
        return cors(jsonify(ok=True, id=lead_id))
    nxt = f.get("_next") or THANKS
    if not nxt.startswith(SITE_BASE):
        nxt = THANKS
    return cors(redirect(nxt, code=303))


@app.errorhandler(413)
def too_large(_e):
    return fail("request_too_large", 413)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
