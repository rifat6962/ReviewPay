# ══════════════════════════════════════════════════
#  ReviewPay — firebase.py
#  Firebase REST + ImgBB + Groq + Sheets + FCM
# ══════════════════════════════════════════════════

import time, json, base64, random, threading, requests
from config import FIREBASE_API_KEY, FIREBASE_PROJECT_ID

AUTH_URL  = f"https://identitytoolkit.googleapis.com/v1/accounts"
FS_URL    = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
FCM_URL   = "https://fcm.googleapis.com/fcm/send"
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
IMGBB_URL = "https://api.imgbb.com/1/upload"

# ── Session state (global, single user) ──────────────
_token      = {"id": None, "refresh": None, "expiry": 0}
_uid        = {"v": None}
_user_cache = {"v": {}}
_settings   = {"v": {}}

def uid():     return _uid["v"]
def user():    return _user_cache["v"]
def settings(): return _settings["v"]
def logged_in(): return bool(_token["id"])

# ── Auth ─────────────────────────────────────────────

def sign_in(email, password, ok, err):
    def run():
        r = requests.post(f"{AUTH_URL}:signInWithPassword?key={FIREBASE_API_KEY}",
                          json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
        d = r.json()
        if "idToken" in d:
            _token["id"] = d["idToken"]; _token["refresh"] = d["refreshToken"]
            _token["expiry"] = time.time() + 3500; _uid["v"] = d["localId"]
            ok(d)
        else:
            err(d.get("error", {}).get("message", "Login failed"))
    threading.Thread(target=run, daemon=True).start()

def sign_up(email, password, ok, err):
    def run():
        r = requests.post(f"{AUTH_URL}:signUp?key={FIREBASE_API_KEY}",
                          json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
        d = r.json()
        if "idToken" in d:
            _token["id"] = d["idToken"]; _token["refresh"] = d["refreshToken"]
            _token["expiry"] = time.time() + 3500; _uid["v"] = d["localId"]
            ok(d)
        else:
            err(d.get("error", {}).get("message", "Signup failed"))
    threading.Thread(target=run, daemon=True).start()

def reset_password(email, ok, err):
    def run():
        r = requests.post(f"{AUTH_URL}:sendOobCode?key={FIREBASE_API_KEY}",
                          json={"requestType": "PASSWORD_RESET", "email": email}, timeout=10)
        d = r.json()
        (ok if "email" in d else err)(d.get("email", d.get("error", {}).get("message", "Failed")))
    threading.Thread(target=run, daemon=True).start()

def sign_out():
    _token.update({"id": None, "refresh": None, "expiry": 0}); _uid["v"] = None

def _headers():
    if time.time() > _token["expiry"] and _token["refresh"]:
        try:
            r = requests.post(f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}",
                              json={"grant_type": "refresh_token", "refresh_token": _token["refresh"]}, timeout=8)
            _token["id"] = r.json().get("id_token", _token["id"]); _token["expiry"] = time.time() + 3500
        except: pass
    return {"Authorization": f"Bearer {_token['id']}", "Content-Type": "application/json"}

# ── Firestore helpers ─────────────────────────────────

def _enc(v):
    if isinstance(v, bool):  return {"booleanValue": v}
    if isinstance(v, int):   return {"integerValue": str(v)}
    if isinstance(v, float): return {"doubleValue": v}
    if isinstance(v, str):   return {"stringValue": v}
    if isinstance(v, list):  return {"arrayValue": {"values": [_enc(i) for i in v]}}
    if isinstance(v, dict):  return {"mapValue": {"fields": {k: _enc(val) for k, val in v.items()}}}
    return {"nullValue": None}

def _dec(f):
    if "stringValue"  in f: return f["stringValue"]
    if "integerValue" in f: return int(f["integerValue"])
    if "doubleValue"  in f: return float(f["doubleValue"])
    if "booleanValue" in f: return f["booleanValue"]
    if "nullValue"    in f: return None
    if "arrayValue"   in f: return [_dec(v) for v in f["arrayValue"].get("values", [])]
    if "mapValue"     in f: return {k: _dec(v) for k, v in f["mapValue"].get("fields", {}).items()}
    return None

def _wrap(data): return {"fields": {k: _enc(v) for k, v in data.items()}}
def _unwrap(doc):
    d = {k: _dec(v) for k, v in doc.get("fields", {}).items()}
    if "name" in doc: d["_id"] = doc["name"].split("/")[-1]
    return d

def get_doc(col, doc_id, ok=None, err=None):
    def run():
        r = requests.get(f"{FS_URL}/{col}/{doc_id}", headers=_headers(), timeout=10)
        d = r.json()
        if ok: (ok if "fields" in d else (err or (lambda e: None)))(_unwrap(d) if "fields" in d else d.get("error", {}).get("message", "Not found"))
    threading.Thread(target=run, daemon=True).start()

def set_doc(col, doc_id, data, ok=None, err=None):
    def run():
        r = requests.patch(f"{FS_URL}/{col}/{doc_id}", headers=_headers(), json=_wrap(data), timeout=10)
        d = r.json()
        if ok and "name" in d: ok()
        elif err and "error" in d: err(d["error"].get("message", "Failed"))
    threading.Thread(target=run, daemon=True).start()

def add_doc(col, data, ok=None, err=None):
    def run():
        r = requests.post(f"{FS_URL}/{col}", headers=_headers(), json=_wrap(data), timeout=10)
        d = r.json()
        if ok and "name" in d: ok(d["name"].split("/")[-1])
        elif err and "error" in d: err(d["error"].get("message", "Failed"))
    threading.Thread(target=run, daemon=True).start()

def del_doc(col, doc_id, ok=None, err=None):
    def run():
        r = requests.delete(f"{FS_URL}/{col}/{doc_id}", headers=_headers(), timeout=10)
        if ok and r.status_code == 200: ok()
    threading.Thread(target=run, daemon=True).start()

def get_col(col, ok=None, err=None):
    def run():
        r = requests.get(f"{FS_URL}/{col}", headers=_headers(), timeout=15)
        docs = [_unwrap(d) for d in r.json().get("documents", []) if "fields" in d]
        if ok: ok(docs)
    threading.Thread(target=run, daemon=True).start()

def query(col, filters=None, order=None, limit=200, ok=None, err=None):
    def run():
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents:runQuery"
        q = {"structuredQuery": {"from": [{"collectionId": col}], "limit": limit}}
        if filters:
            clauses = [{"fieldFilter": {"field": {"fieldPath": f["field"]}, "op": f["op"],
                        "value": _wrap({f["field"]: f["value"]})["fields"][f["field"]]}} for f in filters]
            q["structuredQuery"]["where"] = clauses[0] if len(clauses) == 1 else \
                {"compositeFilter": {"op": "AND", "filters": clauses}}
        if order:
            desc = order.startswith("-")
            q["structuredQuery"]["orderBy"] = [{"field": {"fieldPath": order.lstrip("-")},
                                                 "direction": "DESCENDING" if desc else "ASCENDING"}]
        r = requests.post(url, headers=_headers(), json=q, timeout=15)
        docs = [_unwrap(i["document"]) for i in r.json() if "document" in i and "fields" in i["document"]]
        if ok: ok(docs)
    threading.Thread(target=run, daemon=True).start()

def incr(col, doc_id, field, delta, ok=None):
    def run():
        r = requests.get(f"{FS_URL}/{col}/{doc_id}", headers=_headers(), timeout=10)
        d = r.json()
        if "fields" not in d: return
        cur = float(_unwrap(d).get(field, 0))
        set_doc(col, doc_id, {field: round(cur + delta, 4)}, ok=ok)
    threading.Thread(target=run, daemon=True).start()

# ── FCM ───────────────────────────────────────────────

def push(fcm_token, title, body, key=""):
    if not fcm_token: return
    def run():
        try:
            requests.post(FCM_URL,
                headers={"Authorization": f"key={key or _settings['v'].get('fcm_server_key','')}",
                         "Content-Type": "application/json"},
                json={"to": fcm_token, "notification": {"title": title, "body": body, "sound": "default"}, "priority": "high"},
                timeout=8)
        except: pass
    threading.Thread(target=run, daemon=True).start()

# ── ImgBB ─────────────────────────────────────────────

def upload_img(path, ok, err):
    def run():
        key = _settings["v"].get("imgbb_api_key", "")
        if not key: err("ImgBB key not set"); return
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            r = requests.post(IMGBB_URL, data={"key": key, "image": data}, timeout=30)
            d = r.json()
            if d.get("success"): ok(d["data"]["url"])
            else: err(d.get("error", {}).get("message", "Upload failed"))
        except Exception as e: err(str(e))
    threading.Thread(target=run, daemon=True).start()

# ── Groq AI Review ────────────────────────────────────

def gen_review(app_name, description, custom_prompt, ok, err):
    def run():
        key = _settings["v"].get("groq_api_key", "")
        if not key: err("Groq key not set"); return
        tones = ["enthusiastic", "satisfied and calm", "pleasantly surprised", "casual and friendly"]
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "max_tokens": 280, "temperature": 0.95,
                      "messages": [
                          {"role": "system", "content": "You are a real Android user writing a Play Store review. Sound human, be specific. Output ONLY the review text."},
                          {"role": "user", "content": f"Write a {random.choice(tones)} Play Store review for '{app_name}'. Description: {description}. Extra: {custom_prompt}. Keep it 2-4 sentences."}
                      ]}, timeout=20)
            d = r.json()
            if "choices" in d: ok(d["choices"][0]["message"]["content"].strip())
            else: err(d.get("error", {}).get("message", "Failed"))
        except Exception as e: err(str(e))
    threading.Thread(target=run, daemon=True).start()

# ── Google Sheets Sync ────────────────────────────────

def sheets_sync(data):
    url = _settings["v"].get("sheets_url", "")
    if not url: return
    def run():
        try: requests.post(url, json=data, timeout=12)
        except: pass
    threading.Thread(target=run, daemon=True).start()

# ── Play Store Check ──────────────────────────────────

def check_play_store(package_id, reviewer_name, found_cb, not_found_cb):
    def run():
        try:
            r = requests.get(f"https://play.google.com/store/apps/details?id={package_id}&hl=en",
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36"},
                timeout=20)
            (found_cb if reviewer_name.strip().lower() in r.text.lower() else not_found_cb)()
        except: not_found_cb()
    threading.Thread(target=run, daemon=True).start()

# ── Unique 6-digit User ID ────────────────────────────

def unique_user_id(cb, attempts=0):
    uid_try = str(random.randint(100000, 999999))
    if attempts > 8: cb(uid_try); return
    query("users", filters=[{"field": "user_id", "op": "EQUAL", "value": uid_try}],
          ok=lambda docs: cb(uid_try) if not docs else unique_user_id(cb, attempts+1),
          err=lambda e: cb(uid_try))

# ── Load settings into cache ──────────────────────────

def load_settings(cb=None):
    get_doc("settings", "app_settings",
            ok=lambda d: (_settings.update({"v": d}), cb(d) if cb else None),
            err=lambda e: None)
