# ══════════════════════════════════════════════════
#  ReviewPay — server.py  (Railway Backend)
#  Flask + APScheduler midnight cron + APK serving
# ══════════════════════════════════════════════════

import os, time, json, logging, threading, requests
from flask import Flask, jsonify, request, send_file, abort
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PROJECT_ID  = os.environ.get("FIREBASE_PROJECT_ID", "")
SA_KEY      = os.environ.get("FIREBASE_SA_KEY", "")
FCM_KEY     = os.environ.get("FCM_SERVER_KEY", "")
SECRET      = os.environ.get("BACKEND_SECRET", "reviewpay2024")
BD_TZ       = pytz.timezone("Asia/Dhaka")
FS_BASE     = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

app = Flask(__name__)

# ── Firebase admin token ──────────────────────────

_tok = {"v": None, "exp": 0}

def _admin_token():
    if time.time() < _tok["exp"]: return _tok["v"]
    try:
        import google.oauth2.service_account as sa
        import google.auth.transport.requests as gtr
        creds = sa.Credentials.from_service_account_info(
            json.loads(SA_KEY),
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(gtr.Request())
        _tok["v"] = creds.token; _tok["exp"] = time.time() + 3400
        return creds.token
    except Exception as e:
        log.error(f"Token error: {e}"); return ""

def _hdr(): return {"Authorization": f"Bearer {_admin_token()}", "Content-Type": "application/json"}

# ── Firestore helpers ─────────────────────────────

def _enc(v):
    if isinstance(v, bool):  return {"booleanValue": v}
    if isinstance(v, int):   return {"integerValue": str(v)}
    if isinstance(v, float): return {"doubleValue": v}
    if isinstance(v, str):   return {"stringValue": v}
    if isinstance(v, list):  return {"arrayValue": {"values": [_enc(i) for i in v]}}
    if isinstance(v, dict):  return {"mapValue": {"fields": {k: _enc(val) for k, val in v.items()}}}
    return {"nullValue": None}

def _dec(f):
    for t, fn in [("stringValue", str), ("integerValue", int), ("doubleValue", float),
                  ("booleanValue", bool), ("nullValue", lambda x: None)]:
        if t in f: return fn(f[t])
    if "arrayValue"  in f: return [_dec(v) for v in f["arrayValue"].get("values", [])]
    if "mapValue"    in f: return {k: _dec(v) for k, v in f["mapValue"].get("fields", {}).items()}
    return None

def _wrap(d): return {"fields": {k: _enc(v) for k, v in d.items()}}
def _unwrap(doc):
    r = {k: _dec(v) for k, v in doc.get("fields", {}).items()}
    if "name" in doc: r["_id"] = doc["name"].split("/")[-1]
    return r

def fs_get(col, doc_id):
    r = requests.get(f"{FS_BASE}/{col}/{doc_id}", headers=_hdr(), timeout=10).json()
    return _unwrap(r) if "fields" in r else {}

def fs_set(col, doc_id, data):
    requests.patch(f"{FS_BASE}/{col}/{doc_id}", headers=_hdr(), json=_wrap(data), timeout=10)

def fs_query(col, filters=None, limit=500):
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:runQuery"
    q = {"structuredQuery": {"from": [{"collectionId": col}], "limit": limit}}
    if filters:
        clauses = [{"fieldFilter": {"field": {"fieldPath": f["field"]}, "op": f["op"],
                    "value": _wrap({f["field"]: f["value"]})["fields"][f["field"]]}} for f in filters]
        q["structuredQuery"]["where"] = clauses[0] if len(clauses) == 1 else \
            {"compositeFilter": {"op": "AND", "filters": clauses}}
    r = requests.post(url, headers=_hdr(), json=q, timeout=15).json()
    return [_unwrap(i["document"]) for i in r if "document" in i and "fields" in i["document"]]

def fs_incr(col, doc_id, field, delta):
    doc = fs_get(col, doc_id)
    if doc: fs_set(col, doc_id, {field: round(float(doc.get(field, 0)) + delta, 4)})

def fcm_push(token, title, body, key=""):
    if not token: return
    try:
        requests.post("https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={key or FCM_KEY}", "Content-Type": "application/json"},
            json={"to": token, "notification": {"title": title, "body": body, "sound": "default"}, "priority": "high"},
            timeout=8)
    except: pass

# ── Midnight Auto-Approval ────────────────────────

def midnight_auto_approval():
    log.info("🕛 Midnight auto-approval started")
    try:
        settings = fs_get("settings", "app_settings")
        if not settings.get("auto_approve", True):
            log.info("Auto-approve disabled"); return

        now = int(time.time()); cutoff = now - 86400
        pending = fs_query("submissions", filters=[{"field": "status", "op": "EQUAL", "value": "pending"}])
        eligible = [s for s in pending if s.get("timestamp", now) <= cutoff]
        log.info(f"Eligible: {len(eligible)} submissions")

        for sub in eligible:
            pkg = sub.get("package_id", ""); name = sub.get("reviewer_name", "")
            doc_id = sub.get("_id", ""); uid = sub.get("user_id", "")
            amt = float(sub.get("amount", 0))

            if not pkg or not name:
                continue

            # Scrape Play Store
            found = False
            try:
                r = requests.get(f"https://play.google.com/store/apps/details?id={pkg}&hl=en",
                    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12)"},
                    timeout=20)
                found = name.strip().lower() in r.text.lower()
            except Exception as e:
                log.warning(f"Play Store check failed: {e}")

            if found:
                log.info(f"✓ Auto-approving {doc_id}")
                fs_set("submissions", doc_id, {"status": "approved", "auto_approved": True})
                fs_incr("users", uid, "balance", amt)
                fs_incr("users", uid, "total_earned", amt)
                fs_incr("users", uid, "pending_balance", -amt)

                # Sheets sync
                sheets_url = settings.get("sheets_url", "")
                if sheets_url:
                    try:
                        requests.post(sheets_url, json={
                            "username": sub.get("username", ""), "gmail": sub.get("reviewer_gmail", ""),
                            "app_name": sub.get("app_name", ""), "screenshot_url": sub.get("screenshot_url", ""),
                            "timestamp": sub.get("timestamp", 0), "amount": amt, "auto_approved": True
                        }, timeout=10)
                    except: pass

                # FCM
                user = fs_get("users", uid)
                if user.get("fcm_token"):
                    fcm_push(user["fcm_token"], "Review Auto-Approved! 🎉",
                             f"Your review for {sub.get('app_name','')} was verified. ৳{amt:.0f} added!",
                             settings.get("fcm_server_key", ""))
                time.sleep(2)
            else:
                log.info(f"✗ Not found on Play Store: {doc_id}")

    except Exception as e:
        log.error(f"Auto-approval error: {e}", exc_info=True)
    log.info("🕛 Auto-approval done")

# ── Scheduler ─────────────────────────────────────

scheduler = BackgroundScheduler(timezone=BD_TZ)
scheduler.add_job(midnight_auto_approval, CronTrigger(hour=0, minute=0, timezone=BD_TZ),
                  id="midnight", replace_existing=True, max_instances=1)

# ── Flask Routes ──────────────────────────────────

@app.get("/")
def index():
    return jsonify({"app": "ReviewPay Backend", "status": "running",
                    "time_bd": __import__("datetime").datetime.now(BD_TZ).strftime("%Y-%m-%d %H:%M:%S")})

@app.get("/health")
def health(): return jsonify({"status": "ok"})

@app.get("/download")
def download_page():
    return """<!DOCTYPE html><html><head><title>ReviewPay Download</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:sans-serif;background:#0C1018;color:#EFF1F5;display:flex;
    align-items:center;justify-content:center;min-height:100vh;margin:0}
    .card{background:#1E2636;border-radius:16px;padding:40px;max-width:380px;text-align:center}
    h1{color:#08C88C;font-size:28px}
    .btn{background:#127B75;color:white;border:none;border-radius:12px;padding:16px 40px;
    font-size:18px;cursor:pointer;text-decoration:none;display:inline-block;margin-top:16px}
    .v{color:#929CB1;font-size:12px;margin-top:10px}</style></head>
    <body><div class="card"><h1>ReviewPay</h1><p>Earn money reviewing apps</p>
    <a href="/download/apk" class="btn">⬇ Download APK</a>
    <p class="v">Android 7.0+ · Latest version</p></div></body></html>""", 200, {"Content-Type": "text/html"}

@app.get("/download/apk")
def serve_apk():
    path = os.path.join(os.path.dirname(__file__), "dist", "ReviewPay.apk")
    if os.path.exists(path): return send_file(path, as_attachment=True, download_name="ReviewPay.apk")
    return jsonify({"error": "APK not available yet"}), 404

@app.get("/api/version")
def version():
    try:
        s = fs_get("settings", "app_settings")
        return jsonify({"version": s.get("app_version", "1.0.0"), "download_url": f"{request.host_url}download"})
    except:
        return jsonify({"version": "1.0.0", "download_url": f"{request.host_url}download"})

@app.post("/api/trigger-approval")
def trigger():
    if request.headers.get("X-Secret") != SECRET: abort(403)
    threading.Thread(target=midnight_auto_approval, daemon=True).start()
    return jsonify({"status": "triggered"})

# ── Start ─────────────────────────────────────────

if __name__ == "__main__":
    scheduler.start()
    log.info("⏰ Scheduler running — midnight BD auto-approval active")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
