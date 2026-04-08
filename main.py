# ══════════════════════════════════════════════════════════════════
#  ReviewPay — main.py
#  সব screen এক ফাইলে: Splash, Auth, Dashboard, ProjectDetail,
#  ReviewGen, Withdraw, Profile, Chat,
#  Admin: Dashboard, Projects, Submissions, Users, Withdrawals, Chat, Settings
# ══════════════════════════════════════════════════════════════════

import os, json, time, threading
from kivy.config import Config
Config.set("graphics", "width", "390")
Config.set("graphics", "height", "844")

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.screen import Screen
from kivy.uix.screenmanager import ScreenManager, FadeTransition, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line

import firebase as FB
from config import *

Window.clearcolor = BG

SESSION_FILE = os.path.expanduser("~/.reviewpay_session.json")

# ══════════════════════════════════════════════════
#  SESSION
# ══════════════════════════════════════════════════

def save_session(uid, id_token, refresh, user_data, is_admin=False):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"uid": uid, "id_token": id_token, "refresh": refresh,
                       "user_data": user_data, "is_admin": is_admin}, f)
    except: pass

def load_session():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE) as f:
                return json.load(f)
    except: pass
    return None

def clear_session():
    try:
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
    except: pass

# ══════════════════════════════════════════════════
#  REUSABLE WIDGETS
# ══════════════════════════════════════════════════

def card_bg(widget, color=CARD, radius=14):
    with widget.canvas.before:
        Color(*color); r = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    widget.bind(pos=lambda *a: setattr(r, "pos", widget.pos),
                size=lambda *a: setattr(r, "size", widget.size))

def surface_bg(widget, color=BG_S):
    with widget.canvas.before:
        Color(*color); r = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda *a: setattr(r, "pos", widget.pos),
                size=lambda *a: setattr(r, "size", widget.size))

def Btn(text, color=WHITE, bg=GREEN, h=50, bold=True, radius=12, **kw):
    b = Button(text=text, color=color, background_color=(0,0,0,0),
               font_size=sp(14), bold=bold, size_hint_y=None, height=dp(h), **kw)
    with b.canvas.before:
        Color(*bg); rr = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(radius)])
    b.bind(pos=lambda *a: setattr(rr, "pos", b.pos),
           size=lambda *a: setattr(rr, "size", b.size),
           on_press=lambda *a: Animation(opacity=0.6, duration=0.05).start(b),
           on_release=lambda *a: Animation(opacity=1, duration=0.1).start(b))
    return b

def OutBtn(text, h=46, **kw):
    b = Button(text=text, color=GREEN_L, background_color=(0,0,0,0),
               font_size=sp(13), size_hint_y=None, height=dp(h), **kw)
    with b.canvas.before:
        Color(*GREEN_L); Line(rounded_rectangle=(b.x, b.y, b.width, b.height, dp(10)), width=dp(1.2))
    return b

def Inp(hint="", pw=False, h=50, **kw):
    return TextInput(hint_text=hint, password=pw,
                     background_color=BG_S, foreground_color=T1,
                     cursor_color=GREEN_L, hint_text_color=T3,
                     font_size=sp(14), multiline=False,
                     padding=[dp(14), dp(13)],
                     size_hint_y=None, height=dp(h), **kw)

def Lbl(text, color=T1, size=15, bold=False, align="left", h=None, **kw):
    l = Label(text=text, color=color, font_size=sp(size), bold=bold,
              halign=align, **kw)
    if h: l.size_hint_y = None; l.height = dp(h)
    l.bind(size=lambda *a: setattr(l, "text_size", (l.width, None)))
    return l

def field_wrap(label, widget, h=76):
    b = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None, height=dp(h))
    lbl = Lbl(label, color=T2, size=12, h=18)
    b.add_widget(lbl); b.add_widget(widget)
    return b

def header_bar(title, on_back=None, admin=False):
    bg = NAVY_S if admin else BG_S
    h = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(58),
                  padding=[dp(14), dp(9)], spacing=dp(10), pos_hint={"top": 1})
    surface_bg(h, bg)
    if on_back:
        b = Button(text="← Back", color=GREEN_L, background_color=(0,0,0,0),
                   font_size=sp(13), size_hint=(None, None), size=(dp(80), dp(40)))
        b.bind(on_press=lambda *a: on_back())
        h.add_widget(b)
    h.add_widget(Lbl(title, color=WHITE if admin else T1, size=15, bold=True))
    return h

def toast(parent, msg, ok=True, dur=2.5):
    color = OK if ok else ERR
    t = Label(text=msg, color=WHITE, font_size=sp(13), size_hint=(None, None),
              padding=(dp(16), dp(8)), pos_hint={"center_x": 0.5})
    with t.canvas.before:
        Color(*color); rr = RoundedRectangle(pos=t.pos, size=t.size, radius=[dp(22)])
    t.bind(pos=lambda *a: setattr(rr, "pos", t.pos),
           size=lambda *a: setattr(rr, "size", t.size))
    t.texture_update()
    t.size = (t.texture_size[0] + dp(32), dp(40))
    t.y = dp(72)
    parent.add_widget(t)
    def rm(dt):
        an = Animation(opacity=0, duration=0.3)
        an.bind(on_complete=lambda *a: parent.remove_widget(t) if t.parent else None)
        an.start(t)
    Clock.schedule_once(rm, dur)

def status_badge(status):
    colors = {"approved": (OK, (0.06, 0.20, 0.13, 1)),
              "rejected": (ERR, (0.21, 0.08, 0.08, 1)),
              "pending":  (WARN, (0.20, 0.12, 0.04, 1))}
    fg, bg_col = colors.get(status, (T2, BG_S))
    b = BoxLayout(size_hint=(None, None), size=(dp(82), dp(24)), padding=[dp(8), dp(3)])
    with b.canvas.before:
        Color(*bg_col); RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(12)])
    b.bind(pos=lambda *a: None, size=lambda *a: None)
    b.add_widget(Label(text=status.upper(), color=fg, font_size=sp(10), bold=True))
    return b

# ══════════════════════════════════════════════════
#  SCREEN: SPLASH
# ══════════════════════════════════════════════════

class SplashScreen(Screen):
    def on_enter(self):
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        box = BoxLayout(orientation="vertical", spacing=dp(14), size_hint=(None, None),
                        size=(dp(220), dp(180)), pos_hint={"center_x": 0.5, "center_y": 0.55})
        # Logo circle
        logo = Label(text="RP", color=WHITE, font_size=sp(36), bold=True,
                     size_hint=(None, None), size=(dp(90), dp(90)), pos_hint={"center_x": 0.5})
        with logo.canvas.before:
            Color(*GREEN_D); Ellipse(pos=logo.pos, size=logo.size)
            Color(*GREEN_L, 0.3); Line(circle=(logo.center_x, logo.center_y, dp(46)), width=dp(2))
        logo.bind(pos=lambda *a: None, size=lambda *a: None)
        box.add_widget(logo)
        box.add_widget(Lbl("ReviewPay", color=WHITE, size=28, bold=True, align="center", h=40))
        box.add_widget(Lbl("Earn. Review. Grow.", color=GREEN_L, size=13, align="center", h=20))
        box.opacity = 0; root.add_widget(box)
        Animation(opacity=1, duration=0.8).start(box)
        Clock.schedule_once(self._route, 2.0)

    def _route(self, dt):
        sess = load_session()
        if sess:
            FB._token["id"] = sess["id_token"]; FB._token["refresh"] = sess["refresh"]
            FB._token["expiry"] = time.time() + 3000; FB._uid["v"] = sess["uid"]
            FB._user_cache["v"] = sess["user_data"]
            FB.load_settings()
            self.manager.current = "admin_dash" if sess.get("is_admin") else "dashboard"
        else:
            self.manager.current = "auth"

# ══════════════════════════════════════════════════
#  SCREEN: AUTH (Login / Signup / Forgot)
# ══════════════════════════════════════════════════

class AuthScreen(Screen):
    def on_enter(self):
        self._mode = "login"; self._build()

    def _build(self):
        self.clear_widgets()
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(26), dp(55), dp(26), dp(30)], spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))

        # Logo
        logo_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(150))
        logo = Label(text="RP", color=WHITE, font_size=sp(30), bold=True,
                     size_hint=(None, None), size=(dp(72), dp(72)), pos_hint={"center_x": 0.5})
        with logo.canvas.before:
            Color(*GREEN_D); Ellipse(pos=logo.pos, size=logo.size)
        logo.bind(pos=lambda *a: None)
        logo_box.add_widget(logo)
        logo_box.add_widget(Lbl("ReviewPay", WHITE, 26, True, "center", 38))
        logo_box.add_widget(Lbl("Earn money reviewing apps", GREEN_L, 12, align="center", h=18))
        body.add_widget(logo_box)

        # Tabs
        tabs = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self._ltab = Button(text="Login", color=WHITE, background_color=(0,0,0,0),
                            font_size=sp(15), bold=True)
        self._stab = Button(text="Sign Up", color=T2, background_color=(0,0,0,0), font_size=sp(15))
        self._ltab.bind(on_press=lambda *a: self._switch("login"))
        self._stab.bind(on_press=lambda *a: self._switch("signup"))
        tabs.add_widget(self._ltab); tabs.add_widget(self._stab)
        body.add_widget(tabs)

        self._form = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(11))
        self._form.bind(minimum_height=self._form.setter("height"))
        body.add_widget(self._form)

        self._forgot_btn = Button(text="Forgot Password?", color=GREEN_L,
                                  background_color=(0,0,0,0), font_size=sp(13),
                                  size_hint_y=None, height=dp(36))
        self._forgot_btn.bind(on_press=lambda *a: self._switch("forgot"))
        body.add_widget(self._forgot_btn)

        scroll.add_widget(body)
        self._overlay = FloatLayout(size_hint=(1,1), opacity=0)
        with self._overlay.canvas.before:
            Color(0,0,0,0.65); r = Rectangle(pos=self._overlay.pos, size=self._overlay.size)
        self._overlay.bind(pos=lambda *a: setattr(r,"pos",self._overlay.pos),
                           size=lambda *a: setattr(r,"size",self._overlay.size))
        self._overlay.add_widget(Lbl("Please wait...", WHITE, 15, align="center",
                                      pos_hint={"center_x":0.5,"center_y":0.5},
                                      size_hint=(None,None), size=(dp(200),dp(40))))
        root.add_widget(scroll); root.add_widget(self._overlay)
        self._switch(self._mode)

    def _switch(self, mode):
        self._mode = mode
        self._ltab.bold = mode == "login"; self._stab.bold = mode == "signup"
        self._ltab.color = WHITE if mode == "login" else T2
        self._stab.color = WHITE if mode == "signup" else T2
        self._forgot_btn.opacity = 0 if mode == "forgot" else 1
        self._form.clear_widgets()
        if mode == "login":   self._login_form()
        elif mode == "signup": self._signup_form()
        else:                  self._forgot_form()

    def _login_form(self):
        self.e = Inp("Email address"); self.p = Inp("Password", pw=True)
        btn = Btn("Log In")
        btn.bind(on_press=self._do_login)
        for w in [field_wrap("Email", self.e), field_wrap("Password", self.p), btn]:
            self._form.add_widget(w)

    def _signup_form(self):
        self.n = Inp("Full Name"); self.e = Inp("Email address")
        self.tg = Inp("Telegram (e.g. @username)"); self.p = Inp("Password", pw=True)
        self.cp = Inp("Confirm Password", pw=True)
        btn = Btn("Create Account"); btn.bind(on_press=self._do_signup)
        for label, w in [("Full Name", self.n), ("Email", self.e), ("Telegram", self.tg),
                         ("Password", self.p), ("Confirm Password", self.cp)]:
            self._form.add_widget(field_wrap(label, w))
        self._form.add_widget(btn)

    def _forgot_form(self):
        self._form.add_widget(Lbl("Enter email to reset password.\nType 2808 for admin access.",
                                   T2, 12, h=42))
        self.e = Inp("Email or code 2808")
        btn = Btn("Continue"); btn.bind(on_press=self._do_forgot)
        self._form.add_widget(field_wrap("Email / Code", self.e))
        self._form.add_widget(btn)

    def _loading(self, on):
        self._overlay.opacity = 1 if on else 0

    def _do_login(self, *a):
        email, pw = self.e.text.strip(), self.p.text.strip()
        if not email or not pw: toast(self, "Fill all fields", False); return
        self._loading(True)
        FB.sign_in(email, pw, self._after_login, lambda e: Clock.schedule_once(lambda dt: (self._loading(False), toast(self, self._clean_err(e), False)), 0))

    def _after_login(self, data):
        uid = data["localId"]
        FB.get_doc("users", uid,
                   ok=lambda u: Clock.schedule_once(lambda dt: self._finish_login(u, data), 0),
                   err=lambda e: Clock.schedule_once(lambda dt: (self._loading(False), toast(self, "User not found", False)), 0))

    def _finish_login(self, u, data):
        if u.get("blocked"): self._loading(False); toast(self, "Account suspended", False); return
        FB._user_cache["v"] = u
        FB.load_settings()
        is_admin = u.get("is_admin", False)
        save_session(data["localId"], data["idToken"], data["refreshToken"], u, is_admin)
        self._loading(False)
        self.manager.current = "admin_dash" if is_admin else "dashboard"

    def _do_signup(self, *a):
        name, email = self.n.text.strip(), self.e.text.strip()
        tg, pw, cp  = self.tg.text.strip(), self.p.text.strip(), self.cp.text.strip()
        if not all([name, email, tg, pw, cp]): toast(self, "Fill all fields", False); return
        if pw != cp: toast(self, "Passwords don't match", False); return
        if len(pw) < 6: toast(self, "Password too short (min 6)", False); return
        self._loading(True)
        def make_account(uid6):
            doc = {"name": name, "email": email, "telegram": tg, "user_id": uid6,
                   "balance": 0.0, "total_earned": 0.0, "pending_balance": 0.0,
                   "profile_pic": "", "address": "", "facebook_id": "", "fcm_token": "",
                   "is_admin": False, "blocked": False, "created_at": int(time.time())}
            FB.sign_up(email, pw,
                on_success=lambda d: FB.set_doc("users", d["localId"], doc,
                    ok=lambda: self._finish_login(doc, d)),
                on_error=lambda e: Clock.schedule_once(lambda dt: (self._loading(False), toast(self, self._clean_err(e), False)), 0))
        FB.unique_user_id(make_account)

    def _do_forgot(self, *a):
        val = self.e.text.strip()
        if val == "2808":
            admin_doc = {"name": "Admin", "email": "admin@reviewpay.com", "user_id": "000000",
                         "balance": 0.0, "total_earned": 0.0, "is_admin": True, "blocked": False}
            FB._user_cache["v"] = admin_doc; FB._uid["v"] = "ADMIN_MASTER"
            FB._token["id"] = "admin_token"; FB._token["refresh"] = "admin_refresh"
            FB._token["expiry"] = time.time() + 86400
            FB.load_settings()
            save_session("ADMIN_MASTER", "admin_token", "admin_refresh", admin_doc, True)
            self.manager.current = "admin_dash"; return
        if not val or "@" not in val: toast(self, "Enter valid email", False); return
        self._loading(True)
        FB.reset_password(val, ok=lambda *a: Clock.schedule_once(lambda dt: (self._loading(False), toast(self, "Reset email sent!")), 0),
                          err=lambda e: Clock.schedule_once(lambda dt: (self._loading(False), toast(self, self._clean_err(e), False)), 0))

    def _clean_err(self, e):
        e = str(e)
        if "INVALID_LOGIN" in e or "EMAIL_NOT_FOUND" in e: return "Invalid email or password"
        if "EMAIL_EXISTS" in e: return "Email already registered"
        return e[:60]

# ══════════════════════════════════════════════════
#  SCREEN: USER DASHBOARD
# ══════════════════════════════════════════════════

class DashboardScreen(Screen):
    def on_enter(self):
        self._build(); self._load()

    def _build(self):
        self.clear_widgets()
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        # Header
        hdr = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(60),
                        padding=[dp(18), dp(10)], spacing=dp(10), pos_hint={"top": 1})
        surface_bg(hdr, BG_S)
        u = FB.user()
        name = u.get("name", "User").split()[0]
        greet = BoxLayout(orientation="vertical", spacing=dp(1))
        greet.add_widget(Lbl(f"Hello, {name} 👋", WHITE, 16, True, h=22))
        greet.add_widget(Lbl("Find your next review job", T3, 11, h=16))
        chat_btn = Button(text="💬", font_size=sp(22), background_color=(0,0,0,0),
                          size_hint=(None, None), size=(dp(40), dp(44)))
        chat_btn.bind(on_press=lambda *a: setattr(self.manager, "current", "chat"))
        hdr.add_widget(greet); hdr.add_widget(chat_btn)
        root.add_widget(hdr)

        # Bottom nav
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(62),
                        padding=[dp(4), dp(6)], pos_hint={"y": 0})
        surface_bg(nav, BG_S)
        nav_items = [("🏠", "Home", None), ("🤖", "AI Review", "review_gen"),
                     ("💸", "Withdraw", "withdraw"), ("👤", "Profile", "profile")]
        for icon, lbl, target in nav_items:
            col = BoxLayout(orientation="vertical", spacing=dp(2))
            col.add_widget(Label(text=icon, font_size=sp(20), size_hint_y=None, height=dp(28)))
            col.add_widget(Lbl(lbl, GREEN_L if target is None else T3, 10, align="center", h=14))
            if target:
                btn = Button(background_color=(0,0,0,0), size_hint_x=1)
                btn.add_widget(col)
                _t = target
                btn.bind(on_press=lambda inst, t=_t: setattr(self.manager, "current", t))
                nav.add_widget(btn)
            else:
                nav.add_widget(col)
        root.add_widget(nav)

        # Scrollable body
        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(14), dp(70), dp(14), dp(76)], spacing=dp(16))
        body.bind(minimum_height=body.setter("height"))

        # Balance cards
        bal_row = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(90))
        self._avail = self._bal_card("Available", 0, GREEN_L)
        self._earned = self._bal_card("Total Earned", 0, OK)
        self._pending_bal = self._bal_card("Pending", 0, WARN)
        for c in [self._avail, self._earned, self._pending_bal]: bal_row.add_widget(c)
        body.add_widget(bal_row)

        # Stats
        body.add_widget(Lbl("My Activity", T1, 16, True, h=28))
        self._stats_grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(72))
        body.add_widget(self._stats_grid)

        # Projects
        body.add_widget(Lbl("Available Projects", T1, 16, True, h=28))
        self._proj_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        self._proj_box.bind(minimum_height=self._proj_box.setter("height"))
        body.add_widget(self._proj_box)

        scroll.add_widget(body)
        root.add_widget(scroll)

    def _bal_card(self, label, amount, color):
        c = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(10))
        card_bg(c)
        val = Lbl(f"৳{amount:,.0f}", color, 18, True, "left", h=28)
        c.add_widget(Lbl(label, T3, 11, h=16))
        c.add_widget(val)
        c._val = val; return c

    def _load(self):
        u = FB.user()
        Clock.schedule_once(lambda dt: self._update_balance(u), 0)
        FB.get_doc("users", FB.uid(), ok=lambda d: Clock.schedule_once(lambda dt: self._update_balance(d), 0))
        FB.query("projects", filters=[{"field": "active", "op": "EQUAL", "value": True}],
                 ok=lambda docs: Clock.schedule_once(lambda dt: self._render_projects(docs), 0))
        FB.query("submissions", filters=[{"field": "user_id", "op": "EQUAL", "value": FB.uid()}],
                 ok=lambda docs: Clock.schedule_once(lambda dt: self._render_stats(docs), 0))

    def _update_balance(self, u):
        FB._user_cache["v"] = u
        self._avail._val.text   = f"৳{float(u.get('balance', 0)):,.0f}"
        self._earned._val.text  = f"৳{float(u.get('total_earned', 0)):,.0f}"
        self._pending_bal._val.text = f"৳{float(u.get('pending_balance', 0)):,.0f}"

    def _render_stats(self, subs):
        self._stats_grid.clear_widgets()
        counts = {"Total": len(subs), "Approved": 0, "Pending": 0, "Rejected": 0}
        colors  = {"Total": WHITE, "Approved": OK, "Pending": WARN, "Rejected": ERR}
        for s in subs:
            st = s.get("status", "pending").capitalize()
            if st in counts: counts[st] += 1
        for k, v in counts.items():
            b = BoxLayout(orientation="vertical", spacing=dp(3), padding=dp(8))
            card_bg(b, CARD, 10)
            b.add_widget(Lbl(str(v), colors[k], 20, True, "center", h=28))
            b.add_widget(Lbl(k, T3, 10, align="center", h=16))
            self._stats_grid.add_widget(b)

    def _render_projects(self, projects):
        self._proj_box.clear_widgets()
        if not projects:
            self._proj_box.add_widget(Lbl("No active projects right now.", T3, 13, h=50))
            return
        for p in projects:
            self._proj_box.add_widget(self._proj_card(p))

    def _proj_card(self, p):
        c = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14),
                      size_hint_y=None, height=dp(190))
        card_bg(c)
        top = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        info.add_widget(Lbl(p.get("app_name", "App"), T1, 14, True, h=22))
        info.add_widget(Lbl(f"⏰ {p.get('start_time','09:00')} – {p.get('end_time','21:00')}", T3, 11, h=16))
        price_box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(65), dp(44)))
        price_box.add_widget(Lbl(f"৳{p.get('price',0):.0f}", GREEN_L, 20, True, "center", h=28))
        price_box.add_widget(Lbl("/review", T3, 10, "center", h=14))
        top.add_widget(info); top.add_widget(price_box)
        c.add_widget(top)
        desc = Lbl(p.get("description", "")[:100] + "...", T2, 12, h=30)
        c.add_widget(desc)
        # Progress bar
        slots = int(p.get("slots_taken", 0)); limit = int(p.get("daily_limit", 100))
        slot_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(22))
        slot_row.add_widget(Lbl(f"Slots: {slots}/{limit}", T3, 11, h=20, size_hint_x=0.4))
        from kivy.uix.widget import Widget
        bar_outer = Widget(size_hint_y=None, height=dp(6))
        with bar_outer.canvas:
            Color(*BG_S); RoundedRectangle(pos=bar_outer.pos, size=bar_outer.size, radius=[dp(3)])
            pct = min(slots / max(limit, 1), 1.0)
            Color(*GREEN); RoundedRectangle(pos=bar_outer.pos, size=(bar_outer.width * pct, bar_outer.height), radius=[dp(3)])
        slot_row.add_widget(bar_outer)
        c.add_widget(slot_row)
        btn = Btn("View Details", h=40)
        btn.bind(on_press=lambda *a, proj=p: self._open(proj))
        c.add_widget(btn)
        return c

    def _open(self, project):
        self.manager.get_screen("project_detail").proj = project
        self.manager.current = "project_detail"

# ══════════════════════════════════════════════════
#  SCREEN: PROJECT DETAIL + SUBMISSION
# ══════════════════════════════════════════════════

class ProjectDetailScreen(Screen):
    proj = {}
    def on_pre_enter(self): self._shot_path = ""; self._build()

    def _build(self):
        self.clear_widgets(); p = self.proj
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        root.add_widget(header_bar(p.get("app_name","Project"), lambda: setattr(self.manager,"current","dashboard")))
        scroll = ScrollView(size_hint=(1,1))
        body = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(14), dp(70), dp(14), dp(30)], spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))

        # Info card
        info = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14), size_hint_y=None, height=dp(130))
        card_bg(info)
        info.add_widget(Lbl(f"৳{p.get('price',0):.0f} per review", GREEN_L, 22, True, h=32))
        info.add_widget(Lbl(p.get("description","")[:180], T2, 12, h=40))
        slots = int(p.get("slots_taken",0)); limit = int(p.get("daily_limit",100))
        info.add_widget(Lbl(f"Slots: {slots}/{limit}", T3, 12, h=18))
        body.add_widget(info)

        body.add_widget(Lbl("Submit Your Review", T1, 16, True, h=28))
        self._name = Inp("Your full name (as on Play Store)")
        self._gmail = Inp("Gmail used for review")
        self._shot_btn = OutBtn("📷 Upload Screenshot")
        self._shot_btn.bind(on_press=self._pick)
        self._shot_lbl = Lbl("No screenshot selected", T3, 12, h=20)
        sub_btn = Btn("Submit Review")
        sub_btn.bind(on_press=self._submit)

        for lbl, w in [("Reviewer Name", self._name), ("Reviewer Gmail", self._gmail)]:
            body.add_widget(field_wrap(lbl, w))
        body.add_widget(Lbl("Screenshot", T2, 12, h=18))
        body.add_widget(self._shot_btn)
        body.add_widget(self._shot_lbl)
        body.add_widget(sub_btn)

        self._loading_ov = FloatLayout(size_hint=(1,1), opacity=0)
        with self._loading_ov.canvas.before:
            Color(0,0,0,0.7); r = Rectangle(pos=self._loading_ov.pos, size=self._loading_ov.size)
        self._loading_ov.bind(pos=lambda *a: setattr(r,"pos",self._loading_ov.pos),
                              size=lambda *a: setattr(r,"size",self._loading_ov.size))
        self._loading_ov.add_widget(Lbl("Submitting...", WHITE, 16, align="center",
                                        pos_hint={"center_x":0.5,"center_y":0.5},
                                        size_hint=(None,None),size=(dp(200),dp(40))))
        self._success_ov = self._build_success()
        self._success_ov.opacity = 0

        scroll.add_widget(body)
        root.add_widget(scroll)
        root.add_widget(self._loading_ov)
        root.add_widget(self._success_ov)

    def _build_success(self):
        ov = FloatLayout(size_hint=(1,1))
        with ov.canvas.before:
            Color(*BG, 0.96); r = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda *a: setattr(r,"pos",ov.pos), size=lambda *a: setattr(r,"size",ov.size))
        box = BoxLayout(orientation="vertical", spacing=dp(14), size_hint=(None,None),
                        size=(dp(280),dp(220)), pos_hint={"center_x":0.5,"center_y":0.55})
        box.add_widget(Label(text="✅", font_size=sp(64), size_hint_y=None, height=dp(80)))
        box.add_widget(Lbl("Submitted!", WHITE, 26, True, "center", h=36))
        box.add_widget(Lbl("You'll be notified when approved.", T2, 13, "center", h=36))
        back = Btn("Back to Dashboard")
        back.bind(on_press=lambda *a: setattr(self.manager,"current","dashboard"))
        box.add_widget(back); ov.add_widget(box); return ov

    def _pick(self, *a):
        chooser = FileChooserIconView(filters=["*.png","*.jpg","*.jpeg"], size_hint=(1,None), height=dp(400))
        content = BoxLayout(orientation="vertical")
        content.add_widget(chooser)
        ok_btn = Btn("Select", h=46)
        content.add_widget(ok_btn)
        pop = Popup(title="Choose Screenshot", content=content, size_hint=(0.95, 0.85))
        def _sel(*a):
            if chooser.selection:
                self._shot_path = chooser.selection[0]
                self._shot_lbl.text = f"✓ {self._shot_path.split('/')[-1]}"
                self._shot_lbl.color = GREEN_L
            pop.dismiss()
        ok_btn.bind(on_press=_sel); pop.open()

    def _submit(self, *a):
        name = self._name.text.strip(); gmail = self._gmail.text.strip()
        if not name or not gmail: toast(self, "Fill all fields", False); return
        if not self._shot_path: toast(self, "Upload a screenshot", False); return
        self._loading_ov.opacity = 1
        FB.upload_img(self._shot_path, ok=lambda url: self._create_sub(url, name, gmail),
                      err=lambda e: Clock.schedule_once(lambda dt: (setattr(self._loading_ov,"opacity",0), toast(self,f"Upload failed: {e}",False)),0))

    def _create_sub(self, url, name, gmail):
        p = self.proj
        doc = {"user_id": FB.uid(), "username": FB.user().get("name",""),
               "project_id": p.get("_id",""), "app_name": p.get("app_name",""),
               "package_id": p.get("package_id",""), "reviewer_name": name,
               "reviewer_gmail": gmail, "screenshot_url": url,
               "amount": float(p.get("price",0)), "status": "pending",
               "timestamp": int(time.time())}
        FB.add_doc("submissions", doc, ok=lambda doc_id: self._after_sub())

    def _after_sub(self):
        p = self.proj
        FB.incr("projects", p.get("_id",""), "slots_taken", 1)
        FB.incr("users", FB.uid(), "pending_balance", float(p.get("price",0)))
        Clock.schedule_once(lambda dt: (setattr(self._loading_ov,"opacity",0),
                                        Animation(opacity=1,duration=0.4).start(self._success_ov)),0)

# ══════════════════════════════════════════════════
#  SCREEN: AI REVIEW GENERATOR
# ══════════════════════════════════════════════════

class ReviewGenScreen(Screen):
    def on_enter(self): self._review = ""; self._profiles = []; self._build(); self._load_profiles()

    def _build(self):
        self.clear_widgets()
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        root.add_widget(header_bar("AI Review Generator", lambda: setattr(self.manager,"current","dashboard")))
        scroll = ScrollView(size_hint=(1,1))
        body = BoxLayout(orientation="vertical",size_hint_y=None,
                         padding=[dp(14),dp(72),dp(14),dp(30)],spacing=dp(16))
        body.bind(minimum_height=body.setter("height"))
        # Spinner
        body.add_widget(Lbl("Select App", T2, 12, h=18))
        self._spin = Spinner(text="Choose an app...", values=[],
                             background_color=CARD, color=T1, font_size=sp(13),
                             size_hint_y=None, height=dp(50))
        body.add_widget(self._spin)
        gen_btn = Btn("✨ Generate Review"); gen_btn.bind(on_press=self._gen)
        body.add_widget(gen_btn)
        # Review card (hidden)
        self._rev_box = BoxLayout(orientation="vertical",spacing=dp(10),size_hint_y=None,height=dp(0),opacity=0)
        rc = BoxLayout(orientation="vertical",spacing=dp(8),padding=dp(14),size_hint_y=None,height=dp(220))
        card_bg(rc)
        self._rev_lbl = Lbl("",T1,14,h=160)
        self._char_lbl = Lbl("",T3,11,align="right",h=16)
        rc.add_widget(self._rev_lbl); rc.add_widget(self._char_lbl)
        self._copy_btn = Btn("📋 Copy Review", h=44); self._copy_btn.bind(on_press=self._copy)
        self._regen_btn = OutBtn("🔄 Regenerate", h=44); self._regen_btn.bind(on_press=lambda *a: self._gen())
        self._regen_btn.opacity = 0
        btn_row = BoxLayout(spacing=dp(10),size_hint_y=None,height=dp(44))
        btn_row.add_widget(self._copy_btn); btn_row.add_widget(self._regen_btn)
        self._rev_box.add_widget(rc); self._rev_box.add_widget(btn_row)
        body.add_widget(self._rev_box)
        # Tips
        tips = BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(14),size_hint_y=None,height=dp(110))
        card_bg(tips)
        tips.add_widget(Lbl("💡 Tips", GREEN_L, 14, True, h=22))
        for t in ["1. Post from your designated Gmail", "2. Wait 5–10 min, then screenshot",
                  "3. Screenshot must show your name + review"]:
            tips.add_widget(Lbl(t, T2, 12, h=22))
        body.add_widget(tips)
        self._loading_ov = FloatLayout(size_hint=(1,1),opacity=0)
        with self._loading_ov.canvas.before:
            Color(0,0,0,0.65); r = Rectangle(pos=self._loading_ov.pos,size=self._loading_ov.size)
        self._loading_ov.bind(pos=lambda *a: setattr(r,"pos",self._loading_ov.pos),
                              size=lambda *a: setattr(r,"size",self._loading_ov.size))
        self._loading_ov.add_widget(Lbl("Generating...",WHITE,15,align="center",
                                        pos_hint={"center_x":0.5,"center_y":0.5},
                                        size_hint=(None,None),size=(dp(200),dp(40))))
        scroll.add_widget(body); root.add_widget(scroll); root.add_widget(self._loading_ov)

    def _load_profiles(self):
        profiles = FB.settings().get("app_profiles", [])
        self._profiles = profiles
        names = [p.get("app_name","App") for p in profiles] if profiles else []
        if not names:
            FB.query("projects", filters=[{"field":"active","op":"EQUAL","value":True}],
                     ok=lambda docs: Clock.schedule_once(lambda dt: setattr(self._spin,"values",[d.get("app_name","") for d in docs]),0))
        else:
            self._spin.values = names

    def _get_profile(self):
        name = self._spin.text
        for p in self._profiles:
            if p.get("app_name") == name: return p
        return {"app_name": name, "description": "", "custom_prompt": ""}

    def _gen(self, *a):
        if self._spin.text == "Choose an app...": toast(self,"Select an app first",False); return
        pf = self._get_profile()
        self._loading_ov.opacity = 1
        FB.gen_review(pf.get("app_name",""), pf.get("description",""), pf.get("custom_prompt",""),
                      ok=lambda rev: Clock.schedule_once(lambda dt: self._show(rev),0),
                      err=lambda e: Clock.schedule_once(lambda dt: (setattr(self._loading_ov,"opacity",0), toast(self,f"Error: {e}",False)),0))

    def _show(self, review):
        self._loading_ov.opacity = 0; self._review = review
        self._rev_lbl.text = review; self._char_lbl.text = f"{len(review)} chars"
        self._copy_btn.opacity = 1; self._regen_btn.opacity = 0
        self._rev_box.height = dp(260)
        Animation(opacity=1,duration=0.3).start(self._rev_box)

    def _copy(self, *a):
        Clipboard.copy(self._review)
        self._rev_lbl.text = ""; self._char_lbl.text = ""
        self._copy_btn.opacity = 0; self._regen_btn.opacity = 1
        toast(self,"✓ Copied!",True)

# ══════════════════════════════════════════════════
#  SCREEN: WITHDRAW
# ══════════════════════════════════════════════════

class WithdrawScreen(Screen):
    def on_enter(self): self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        root.add_widget(header_bar("Withdraw Earnings", lambda: setattr(self.manager,"current","dashboard")))
        scroll = ScrollView(size_hint=(1,1))
        body = BoxLayout(orientation="vertical",size_hint_y=None,
                         padding=[dp(14),dp(72),dp(14),dp(30)],spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))
        # Balance
        bc = BoxLayout(orientation="vertical",spacing=dp(4),padding=dp(14),size_hint_y=None,height=dp(80))
        card_bg(bc)
        bc.add_widget(Lbl("Available Balance", T2, 12, h=18))
        self._bal_lbl = Lbl(f"৳{float(FB.user().get('balance',0)):,.2f}", GREEN_L, 30, True, h=40)
        bc.add_widget(self._bal_lbl)
        body.add_widget(bc)
        body.add_widget(Lbl("Withdraw via bKash", T1, 15, True, h=26))
        self._amt = Inp("Amount (min ৳100)", input_filter="float")
        self._bkash = Inp("bKash number (01XXXXXXXXX)")
        btn = Btn("Request Withdrawal"); btn.bind(on_press=self._request)
        body.add_widget(field_wrap("Amount", self._amt))
        body.add_widget(field_wrap("bKash Number", self._bkash))
        body.add_widget(btn)
        body.add_widget(Lbl("History", T1, 15, True, h=26))
        self._hist = BoxLayout(orientation="vertical",spacing=dp(8),size_hint_y=None)
        self._hist.bind(minimum_height=self._hist.setter("height"))
        body.add_widget(self._hist)
        scroll.add_widget(body); root.add_widget(scroll)

    def _load(self):
        FB.get_doc("users", FB.uid(), ok=lambda u: Clock.schedule_once(lambda dt: setattr(self._bal_lbl,"text",f"৳{float(u.get('balance',0)):,.2f}"),0))
        FB.query("withdrawals", filters=[{"field":"user_id","op":"EQUAL","value":FB.uid()}],
                 order="-timestamp", ok=lambda docs: Clock.schedule_once(lambda dt: self._render_hist(docs),0))

    def _render_hist(self, withdrawals):
        self._hist.clear_widgets()
        for w in withdrawals:
            row = BoxLayout(orientation="horizontal",spacing=dp(10),padding=dp(10),size_hint_y=None,height=dp(54))
            card_bg(row, CARD, 10)
            info = BoxLayout(orientation="vertical",spacing=dp(2))
            info.add_widget(Lbl(f"৳{w.get('amount',0):,.2f} → {w.get('bkash_number','')}", T1, 13, True, h=22))
            info.add_widget(Lbl(time.strftime('%d %b %Y', time.localtime(w.get('timestamp',0))), T3, 11, h=16))
            row.add_widget(info); row.add_widget(status_badge(w.get("status","pending")))
            self._hist.add_widget(row)

    def _request(self, *a):
        try: amt = float(self._amt.text.strip() or "0")
        except: toast(self,"Enter valid amount",False); return
        bkash = self._bkash.text.strip()
        if amt < 100: toast(self,"Minimum ৳100",False); return
        if len(bkash) < 11: toast(self,"Invalid bKash number",False); return
        bal = float(FB.user().get("balance",0))
        if amt > bal: toast(self,"Insufficient balance",False); return
        doc = {"user_id":FB.uid(),"username":FB.user().get("name",""),
               "user_6id":FB.user().get("user_id",""),"amount":amt,
               "bkash_number":bkash,"status":"pending","timestamp":int(time.time())}
        FB.incr("users",FB.uid(),"balance",-amt,
            ok=lambda: FB.add_doc("withdrawals",doc,
                ok=lambda _: Clock.schedule_once(lambda dt: (toast(self,f"Withdrawal ৳{amt:,.0f} submitted!"),
                                                              self._load()),0)))

# ══════════════════════════════════════════════════
#  SCREEN: PROFILE
# ══════════════════════════════════════════════════

class ProfileScreen(Screen):
    def on_enter(self): self._build()

    def _build(self):
        self.clear_widgets(); u = FB.user()
        root = FloatLayout(); surface_bg(root, BG); self.add_widget(root)
        root.add_widget(header_bar("My Profile", lambda: setattr(self.manager,"current","dashboard")))
        scroll = ScrollView(size_hint=(1,1))
        body = BoxLayout(orientation="vertical",size_hint_y=None,
                         padding=[dp(14),dp(72),dp(14),dp(40)],spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))
        # Avatar
        av_box = BoxLayout(size_hint_y=None,height=dp(90),padding=[0,dp(5)])
        initials = "".join(w[0].upper() for w in u.get("name","U").split())[:2]
        av = Label(text=initials,color=WHITE,font_size=sp(28),bold=True,
                   size_hint=(None,None),size=(dp(72),dp(72)),pos_hint={"center_x":0.5})
        with av.canvas.before:
            Color(*GREEN); Ellipse(pos=av.pos,size=av.size)
        av.bind(pos=lambda *a: None)
        av_box.add_widget(av); body.add_widget(av_box)
        # Read-only
        for lbl,val in [("Email",u.get("email","")),("Telegram",u.get("telegram","")),("User ID",u.get("user_id",""))]:
            row = BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(40),padding=dp(10))
            card_bg(row,CARD,8)
            row.add_widget(Lbl(lbl,T3,13,size_hint_x=0.35)); row.add_widget(Lbl(val,T1,13,align="right",size_hint_x=0.65))
            body.add_widget(row)
        # Editable
        body.add_widget(Lbl("Edit Profile", T1, 15, True, h=26))
        self._n = Inp(u.get("name","")); self._n.text = u.get("name","")
        self._addr = Inp(u.get("address","") or "Address"); self._addr.text = u.get("address","")
        self._fb = Inp(u.get("facebook_id","") or "Facebook ID"); self._fb.text = u.get("facebook_id","")
        for lbl,w in [("Full Name",self._n),("Address",self._addr),("Facebook ID",self._fb)]:
            body.add_widget(field_wrap(lbl,w))
        save = Btn("Save Changes"); save.bind(on_press=self._save); body.add_widget(save)
        logout = Button(text="Log Out",color=ERR,background_color=(0,0,0,0),
                        font_size=sp(14),bold=True,size_hint_y=None,height=dp(50))
        logout.bind(on_press=self._logout); body.add_widget(logout)
        scroll.add_widget(body); root.add_widget(scroll)

    def _save(self,*a):
        FB.set_doc("users",FB.uid(),{"name":self._n.text.strip(),"address":self._addr.text.strip(),"facebook_id":self._fb.text.strip()},
            ok=lambda: Clock.schedule_once(lambda dt: toast(self,"Profile updated!"),0))

    def _logout(self,*a):
        FB.sign_out(); clear_session(); self.manager.current = "auth"

# ══════════════════════════════════════════════════
#  SCREEN: CHAT
# ══════════════════════════════════════════════════

class ChatScreen(Screen):
    def on_enter(self): self._msgs = []; self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root = FloatLayout(); surface_bg(root,BG); self.add_widget(root)
        root.add_widget(header_bar("Support Chat", lambda: setattr(self.manager,"current","dashboard")))
        self._scroll = ScrollView(size_hint=(1,None),pos_hint={"top":0.88},height=self.height*0.74 if self.height else dp(520))
        self._msg_box = BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(12),dp(6)],spacing=dp(8))
        self._msg_box.bind(minimum_height=self._msg_box.setter("height"))
        self._scroll.add_widget(self._msg_box)
        inp_row = BoxLayout(size_hint=(1,None),height=dp(56),padding=[dp(10),dp(6)],spacing=dp(8),pos_hint={"y":0})
        surface_bg(inp_row,BG_S)
        self._inp = TextInput(hint_text="Type a message...",background_color=CARD,foreground_color=T1,
                               cursor_color=GREEN_L,font_size=sp(14),multiline=False,size_hint_x=0.8)
        send = Button(text="Send",background_color=GREEN,color=WHITE,font_size=sp(13),bold=True,size_hint_x=0.2)
        send.bind(on_press=self._send)
        inp_row.add_widget(self._inp); inp_row.add_widget(send)
        root.add_widget(self._scroll); root.add_widget(inp_row)

    def _load(self):
        FB.get_doc("chats",FB.uid(),ok=lambda d: Clock.schedule_once(lambda dt: self._render(d.get("messages",[])),0),err=lambda e: None)

    def _render(self,msgs):
        self._msgs = msgs; self._msg_box.clear_widgets()
        for m in msgs: self._bubble(m)
        Clock.schedule_once(lambda dt: setattr(self._scroll,"scroll_y",0),0.1)

    def _bubble(self,msg):
        is_user = msg.get("sender") == "user"
        bubble = BoxLayout(orientation="vertical",size_hint=(0.75,None),
                           pos_hint={"right":1} if is_user else {"x":0},
                           padding=[dp(10),dp(8)],spacing=dp(2))
        bg_col = GREEN_D if is_user else CARD
        with bubble.canvas.before:
            Color(*bg_col); rr = RoundedRectangle(pos=bubble.pos,size=bubble.size,radius=[dp(14)])
        bubble.bind(pos=lambda *a: setattr(rr,"pos",bubble.pos),size=lambda *a: setattr(rr,"size",bubble.size))
        lbl = Lbl(msg.get("text",""),WHITE if is_user else T1,13,h=None)
        ts = Lbl(time.strftime("%H:%M",time.localtime(msg.get("timestamp",0))),T3,10,"right" if is_user else "left",h=16)
        bubble.add_widget(lbl); bubble.add_widget(ts)
        bubble.height = dp(56)
        self._msg_box.add_widget(bubble)

    def _send(self,*a):
        text = self._inp.text.strip()
        if not text: return
        self._inp.text = ""
        msg = {"text":text,"sender":"user","timestamp":int(time.time())}
        self._msgs.append(msg); self._bubble(msg)
        Clock.schedule_once(lambda dt: setattr(self._scroll,"scroll_y",0),0.1)
        FB.set_doc("chats",FB.uid(),{"user_id":FB.uid(),"username":FB.user().get("name",""),
            "messages":self._msgs,"unread_admin":True,"last_message":text,"last_timestamp":msg["timestamp"]},merge=False)

# ══════════════════════════════════════════════════
#  ADMIN SCREENS
# ══════════════════════════════════════════════════

def admin_root(screen):
    root = FloatLayout()
    with root.canvas.before:
        Color(*NAVY); r = Rectangle(pos=root.pos, size=root.size)
    root.bind(pos=lambda *a: setattr(r,"pos",root.pos), size=lambda *a: setattr(r,"size",root.size))
    screen.add_widget(root); return root

def admin_hdr(title, on_back=None):
    return header_bar(title, on_back, admin=True)

# ── Admin Dashboard ───────────────────────────────

class AdminDashScreen(Screen):
    def on_enter(self): self._build(); self._load()

    def _build(self):
        self.clear_widgets()
        root = admin_root(self)
        root.add_widget(admin_hdr("Admin Command Center"))
        scroll = ScrollView(size_hint=(1,1))
        body = BoxLayout(orientation="vertical",size_hint_y=None,
                         padding=[dp(14),dp(70),dp(14),dp(24)],spacing=dp(16))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(Lbl("ReviewPay Admin", WHITE, 22, True, h=34))
        body.add_widget(Lbl(time.strftime("Today: %A, %d %b %Y"), T2, 12, h=20))

        self._stats = GridLayout(cols=2,spacing=dp(10),size_hint_y=None,height=dp(300))
        self._stat_cards = {}
        for key,lbl,color in [
            ("users","Total Users",    "#41A6FC"),
            ("new",  "New Today",      "#20C987"),
            ("pending_r","Pending Reviews","#FA9314"),
            ("approved_t","Approved Today","#20C987"),
            ("income","Total Income",   "#08C88C"),
            ("w_pending","Pending Payouts","#FA9314"),
        ]:
            c = BoxLayout(orientation="vertical",spacing=dp(4),padding=dp(12))
            with c.canvas.before:
                Color(*NAVY_C); rr = RoundedRectangle(pos=c.pos,size=c.size,radius=[dp(12)])
            c.bind(pos=lambda *a,r=None: None,size=lambda *a: None)
            val = Label(text="0",color=(*[int(color[i:i+2],16)/255 for i in (1,3,5)],1),
                        font_size=sp(24),bold=True,size_hint_y=None,height=dp(34),halign="left")
            val.bind(size=lambda *a: setattr(val,"text_size",(val.width,None)))
            c.add_widget(val)
            c.add_widget(Lbl(lbl,T2,11,h=18))
            c._val = val; self._stat_cards[key] = c
            self._stats.add_widget(c)
        body.add_widget(self._stats)

        body.add_widget(Lbl("Management", WHITE, 15, True, h=26))
        nav_g = GridLayout(cols=2,spacing=dp(10),size_hint_y=None,height=dp(280))
        for icon,lbl,target in [
            ("📋","Submissions","admin_subs"),("📦","Projects","admin_proj"),
            ("👥","Users","admin_users"),("💸","Withdrawals","admin_w"),
            ("💬","Chat","admin_chat"),("🤖","AI Profiles","admin_prof"),
            ("⚙️","Settings","admin_set"),("🔒","Logout","__logout__"),
        ]:
            btn = Button(background_color=(0,0,0,0),size_hint=(1,None),height=dp(126))
            with btn.canvas.before:
                Color(*NAVY_C); rr = RoundedRectangle(pos=btn.pos,size=btn.size,radius=[dp(12)])
            btn.bind(pos=lambda *a: None,size=lambda *a: None)
            inner = BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(10))
            inner.add_widget(Label(text=icon,font_size=sp(26),size_hint_y=None,height=dp(34)))
            inner.add_widget(Lbl(lbl,NAVY_TEXT if 0 else WHITE,13,True,"center",h=20))
            btn.add_widget(inner)
            def _go(inst, t=target):
                if t == "__logout__": FB.sign_out(); clear_session(); self.manager.current = "auth"
                else: self.manager.current = t
            btn.bind(on_press=_go)
            nav_g.add_widget(btn)
        body.add_widget(nav_g)
        scroll.add_widget(body); root.add_widget(scroll)

    def _load(self):
        today = int(time.time()) - (int(time.time()) % 86400)
        FB.get_col("users", ok=lambda docs: Clock.schedule_once(lambda dt: (
            setattr(self._stat_cards["users"]._val,"text",str(len(docs))),
            setattr(self._stat_cards["new"]._val,"text",str(sum(1 for u in docs if u.get("created_at",0)>=today))),
        ),0))
        FB.get_col("submissions", ok=lambda docs: Clock.schedule_once(lambda dt: (
            setattr(self._stat_cards["pending_r"]._val,"text",str(sum(1 for s in docs if s.get("status")=="pending"))),
            setattr(self._stat_cards["approved_t"]._val,"text",str(sum(1 for s in docs if s.get("status")=="approved" and s.get("timestamp",0)>=today))),
            setattr(self._stat_cards["income"]._val,"text",f"৳{sum(float(s.get('amount',0)) for s in docs if s.get('status')=='approved'):,.0f}"),
        ),0))
        FB.get_col("withdrawals", ok=lambda docs: Clock.schedule_once(lambda dt:
            setattr(self._stat_cards["w_pending"]._val,"text",f"৳{sum(float(w.get('amount',0)) for w in docs if w.get('status')=='pending'):,.0f}"),0))

# ── Admin Submissions ─────────────────────────────

class AdminSubsScreen(Screen):
    def on_enter(self): self._all = []; self._filter = "all"; self._build(); self._load()

    def _build(self):
        self.clear_widgets()
        root = admin_root(self)
        root.add_widget(admin_hdr("Submissions", lambda: setattr(self.manager,"current","admin_dash")))
        fbar = BoxLayout(size_hint=(1,None),height=dp(46),pos_hint={"top":0.88},padding=[dp(10),dp(5)],spacing=dp(8))
        surface_bg(fbar,NAVY_S)
        self._search = TextInput(hint_text="Search...",background_color=NAVY_C,foreground_color=WHITE,
                                  font_size=sp(13),multiline=False,size_hint_x=0.45)
        self._search.bind(text=lambda inst,val: self._apply())
        self._spin = Spinner(text="All",values=["All","pending","approved","rejected"],
                              background_color=NAVY_C,color=WHITE,font_size=sp(13),size_hint_x=0.3)
        self._spin.bind(text=lambda inst,val: setattr(self,"_filter",val.lower()) or self._apply())
        ref = Button(text="↺",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(18),size_hint=(None,None),size=(dp(38),dp(38)))
        ref.bind(on_press=lambda *a: self._load())
        fbar.add_widget(self._search); fbar.add_widget(self._spin); fbar.add_widget(ref)
        root.add_widget(fbar)
        scroll = ScrollView(size_hint=(1,None),pos_hint={"top":0.78})
        self._list = BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(10))
        self._list.bind(minimum_height=self._list.setter("height"))
        scroll.add_widget(self._list); root.add_widget(scroll)

    def _load(self):
        FB.get_col("submissions",ok=lambda docs: Clock.schedule_once(lambda dt: self._on_loaded(docs),0))

    def _on_loaded(self,docs):
        self._all = sorted(docs,key=lambda d: -d.get("timestamp",0)); self._apply()

    def _apply(self):
        q = self._search.text.lower(); f = self._filter
        res = [s for s in self._all
               if (f in("all","all") or s.get("status")==f)
               and (not q or q in s.get("username","").lower() or q in s.get("app_name","").lower())]
        self._render(res[:60])

    def _render(self,subs):
        self._list.clear_widgets()
        for s in subs: self._list.add_widget(self._card(s))

    def _card(self,s):
        c = BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(12),size_hint_y=None,height=dp(140))
        with c.canvas.before:
            Color(*NAVY_C); RoundedRectangle(pos=c.pos,size=c.size,radius=[dp(12)])
        r1 = BoxLayout(size_hint_y=None,height=dp(26))
        r1.add_widget(Lbl(s.get("username","?"),WHITE,14,True,h=24)); r1.add_widget(status_badge(s.get("status","pending")))
        r2 = BoxLayout(size_hint_y=None,height=dp(20))
        r2.add_widget(Lbl(s.get("app_name",""),T2,12)); r2.add_widget(Lbl(f"৳{s.get('amount',0):.0f}",GREEN_L,13,True,"right"))
        r3 = Lbl(f"Reviewer: {s.get('reviewer_name','')} · {time.strftime('%d %b %H:%M',time.localtime(s.get('timestamp',0)))}",T3,11,h=18)
        brow = BoxLayout(spacing=dp(6),size_hint_y=None,height=dp(38))
        status = s.get("status","pending")
        if status != "approved":
            ab = Button(text="✓ Approve",background_color=OK,color=WHITE,font_size=sp(12),bold=True)
            ab.bind(on_press=lambda *a,sub=s: self._approve(sub)); brow.add_widget(ab)
        if status != "rejected":
            rb = Button(text="✗ Reject",background_color=ERR,color=WHITE,font_size=sp(12),bold=True)
            rb.bind(on_press=lambda *a,sub=s: self._reject(sub)); brow.add_widget(rb)
        if status == "approved":
            pb = Button(text="↺ Set Pending",background_color=WARN,color=WHITE,font_size=sp(11))
            pb.bind(on_press=lambda *a,sub=s: self._set_pending(sub)); brow.add_widget(pb)
        for w in [r1,r2,r3,brow]: c.add_widget(w)
        return c

    def _approve(self,s):
        doc_id=s.get("_id",""); uid=s.get("user_id",""); amt=float(s.get("amount",0))
        FB.set_doc("submissions",doc_id,{"status":"approved"},
            ok=lambda: (FB.incr("users",uid,"balance",amt), FB.incr("users",uid,"total_earned",amt),
                        FB.incr("users",uid,"pending_balance",-amt),
                        FB.sheets_sync({"user_id":s.get("user_id",""),"username":s.get("username",""),
                            "gmail":s.get("reviewer_gmail",""),"app_name":s.get("app_name",""),
                            "screenshot_url":s.get("screenshot_url",""),"timestamp":s.get("timestamp",0),"amount":amt}),
                        FB.get_doc("users",uid,ok=lambda u: FB.push(u.get("fcm_token",""),"Review Approved! 🎉",
                            f"Your review for {s.get('app_name','')} was approved. ৳{amt:.0f} added.")),
                        Clock.schedule_once(lambda dt: (toast(self,"Approved ✓"),self._load()),0)))

    def _reject(self,s):
        doc_id=s.get("_id",""); uid=s.get("user_id",""); amt=float(s.get("amount",0))
        FB.set_doc("submissions",doc_id,{"status":"rejected"},
            ok=lambda: (FB.incr("users",uid,"pending_balance",-amt),
                        FB.get_doc("users",uid,ok=lambda u: FB.push(u.get("fcm_token",""),"Review Not Approved",
                            f"Your {s.get('app_name','')} review was not approved.")),
                        Clock.schedule_once(lambda dt: (toast(self,"Rejected",False),self._load()),0)))

    def _set_pending(self,s):
        doc_id=s.get("_id",""); uid=s.get("user_id",""); amt=float(s.get("amount",0))
        FB.set_doc("submissions",doc_id,{"status":"pending"},
            ok=lambda: (FB.incr("users",uid,"balance",-amt), FB.incr("users",uid,"total_earned",-amt),
                        FB.incr("users",uid,"pending_balance",amt),
                        Clock.schedule_once(lambda dt: (toast(self,"Set to pending"),self._load()),0)))

# ── Admin Projects ────────────────────────────────

class AdminProjScreen(Screen):
    def on_enter(self): self._editing=None; self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("Projects", lambda: setattr(self.manager,"current","admin_dash")))
        add_btn=Btn("+ Add Project",h=42,size_hint=(None,None),size=(dp(160),dp(42)),pos_hint={"right":0.97,"top":0.89})
        add_btn.bind(on_press=lambda *a: self._open_form()); root.add_widget(add_btn)
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.80})
        self._list=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(10))
        self._list.bind(minimum_height=self._list.setter("height"))
        scroll.add_widget(self._list)
        self._form=self._build_form()
        self._form.opacity=0
        root.add_widget(scroll); root.add_widget(self._form)

    def _build_form(self):
        panel=FloatLayout(size_hint=(1,0.88),pos_hint={"y":0})
        with panel.canvas.before:
            Color(*NAVY_S); r=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a: setattr(r,"pos",panel.pos),size=lambda *a: setattr(r,"size",panel.size))
        scroll=ScrollView(size_hint=(1,1))
        body=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(16),dp(16)],spacing=dp(10))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(Lbl("Project Details",WHITE,16,True,h=28))
        self._fi={}
        for key,lbl in [("app_name","App Name *"),("package_id","Package ID *"),
                         ("price","Price (৳) *"),("daily_limit","Daily Limit"),
                         ("start_time","Start Time (HH:MM)"),("end_time","End Time (HH:MM)"),
                         ("description","Description"),("logo_url","Logo URL (ImgBB)")]:
            inp=TextInput(hint_text=lbl,background_color=NAVY_C,foreground_color=WHITE,
                           cursor_color=GREEN_L,font_size=sp(13),multiline=key=="description",
                           size_hint_y=None,height=dp(80) if key=="description" else dp(46))
            self._fi[key]=inp
            body.add_widget(Lbl(lbl,T2,12,h=16)); body.add_widget(inp)
        tog=BoxLayout(size_hint_y=None,height=dp(44))
        tog.add_widget(Lbl("Active",WHITE,14)); self._active_sw=Switch(active=True)
        tog.add_widget(self._active_sw); body.add_widget(tog)
        brow=BoxLayout(spacing=dp(10),size_hint_y=None,height=dp(50))
        cancel=OutBtn("Cancel"); cancel.bind(on_press=lambda *a: setattr(self._form,"opacity",0))
        save=Btn("Save Project"); save.bind(on_press=self._save)
        brow.add_widget(cancel); brow.add_widget(save); body.add_widget(brow)
        scroll.add_widget(body); panel.add_widget(scroll); return panel

    def _open_form(self,proj=None):
        self._editing=proj.get("_id") if proj else None
        for k,inp in self._fi.items(): inp.text=str(proj.get(k,"")) if proj else ""
        if proj: self._active_sw.active=proj.get("active",True)
        self._form.opacity=1

    def _save(self,*a):
        data={k:v.text.strip() for k,v in self._fi.items()}
        if not data.get("app_name") or not data.get("package_id") or not data.get("price"):
            toast(self,"Fill required (*) fields",False); return
        try: data["price"]=float(data["price"]); data["daily_limit"]=int(data.get("daily_limit") or 100)
        except: toast(self,"Price must be a number",False); return
        data["active"]=self._active_sw.active; data["slots_taken"]=0
        if not self._editing: data["created_at"]=int(time.time())
        action=(lambda: FB.set_doc("projects",self._editing,data,ok=self._after_save)) if self._editing \
               else (lambda: FB.add_doc("projects",data,ok=lambda _: self._after_save()))
        action()

    def _after_save(self,*a):
        Clock.schedule_once(lambda dt: (setattr(self._form,"opacity",0), toast(self,"Saved!"), self._load()),0)

    def _load(self):
        FB.get_col("projects",ok=lambda docs: Clock.schedule_once(lambda dt: self._render(docs),0))

    def _render(self,projects):
        self._list.clear_widgets()
        for p in sorted(projects,key=lambda x: x.get("app_name","")):
            row=BoxLayout(orientation="horizontal",spacing=dp(10),padding=dp(12),size_hint_y=None,height=dp(64))
            with row.canvas.before:
                Color(*NAVY_C); RoundedRectangle(pos=row.pos,size=row.size,radius=[dp(10)])
            info=BoxLayout(orientation="vertical",spacing=dp(3))
            info.add_widget(Lbl(p.get("app_name",""),WHITE,14,True,h=22))
            info.add_widget(Lbl(f"{'● Active' if p.get('active') else '○ Inactive'} · ৳{p.get('price',0):.0f} · {p.get('slots_taken',0)}/{p.get('daily_limit',0)} slots",
                                 OK if p.get("active") else ERR,11,h=16))
            bx=BoxLayout(size_hint=(None,None),size=(dp(110),dp(40)),spacing=dp(6))
            eb=Button(text="Edit",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(13))
            db=Button(text="Del",color=ERR,background_color=(0,0,0,0),font_size=sp(13))
            eb.bind(on_press=lambda *a,pr=p: self._open_form(pr))
            db.bind(on_press=lambda *a,pr=p: FB.del_doc("projects",pr.get("_id",""),ok=lambda: Clock.schedule_once(lambda dt: (toast(self,"Deleted"),self._load()),0)))
            bx.add_widget(eb); bx.add_widget(db); row.add_widget(info); row.add_widget(bx)
            self._list.add_widget(row)

# ── Admin Users ───────────────────────────────────

class AdminUsersScreen(Screen):
    def on_enter(self): self._all=[]; self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("Users", lambda: setattr(self.manager,"current","admin_dash")))
        sb=BoxLayout(size_hint=(1,None),height=dp(46),pos_hint={"top":0.88},padding=[dp(10),dp(5)])
        surface_bg(sb,NAVY_S)
        self._search=TextInput(hint_text="Search name / email / ID...",background_color=NAVY_C,
                                foreground_color=WHITE,font_size=sp(13),multiline=False)
        self._search.bind(text=lambda inst,val: self._apply())
        sb.add_widget(self._search); root.add_widget(sb)
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.78})
        self._list=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(8))
        self._list.bind(minimum_height=self._list.setter("height"))
        scroll.add_widget(self._list); root.add_widget(scroll)
        self._detail=self._build_detail(); self._detail.opacity=0; root.add_widget(self._detail)

    def _build_detail(self):
        p=FloatLayout(size_hint=(1,0.9),pos_hint={"y":0})
        with p.canvas.before:
            Color(*NAVY_S); r=Rectangle(pos=p.pos,size=p.size)
        p.bind(pos=lambda *a: setattr(r,"pos",p.pos),size=lambda *a: setattr(r,"size",p.size))
        close=Button(text="✕",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(18),
                      size_hint=(None,None),size=(dp(36),dp(36)),pos_hint={"right":0.97,"top":0.99})
        close.bind(on_press=lambda *a: setattr(self._detail,"opacity",0))
        scroll=ScrollView(size_hint=(1,0.95),pos_hint={"y":0})
        self._det_body=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(16),dp(16)],spacing=dp(10))
        self._det_body.bind(minimum_height=self._det_body.setter("height"))
        scroll.add_widget(self._det_body); p.add_widget(close); p.add_widget(scroll); return p

    def _load(self):
        FB.get_col("users",ok=lambda docs: Clock.schedule_once(lambda dt: self._on_loaded(docs),0))

    def _on_loaded(self,users):
        self._all=sorted(users,key=lambda u: -u.get("created_at",0)); self._apply()

    def _apply(self):
        q=self._search.text.lower()
        res=[u for u in self._all if not q or q in u.get("name","").lower() or q in u.get("email","").lower() or q in str(u.get("user_id",""))]
        self._render(res[:80])

    def _render(self,users):
        self._list.clear_widgets()
        for u in users:
            row=BoxLayout(orientation="horizontal",spacing=dp(8),padding=dp(10),size_hint_y=None,height=dp(56))
            with row.canvas.before:
                Color(*NAVY_C); RoundedRectangle(pos=row.pos,size=row.size,radius=[dp(10)])
            info=BoxLayout(orientation="vertical",spacing=dp(2))
            info.add_widget(Lbl(u.get("name","?"),WHITE,14,True,h=22))
            info.add_widget(Lbl(f"#{u.get('user_id','')} · {u.get('email','')}",T3,11,h=16))
            blocked=u.get("blocked",False)
            st=Lbl("🔴 Blocked" if blocked else "🟢 Active",ERR if blocked else OK,11,h=22,size_hint=(None,None),size=(dp(80),dp(22)))
            vb=Button(text="View",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(13),size_hint=(None,None),size=(dp(50),dp(36)))
            vb.bind(on_press=lambda *a,usr=u: self._view(usr))
            row.add_widget(info); row.add_widget(st); row.add_widget(vb)
            self._list.add_widget(row)

    def _view(self,u):
        self._det_body.clear_widgets(); uid=u.get("_id","")
        self._det_body.add_widget(Lbl(f"{u.get('name','')} (#{u.get('user_id','')})",WHITE,16,True,h=30))
        for lbl,val in [("Email",u.get("email","")),("Telegram",u.get("telegram","")),
                         ("Balance",f"৳{float(u.get('balance',0)):,.2f}"),("Total Earned",f"৳{float(u.get('total_earned',0)):,.2f}"),
                         ("Status","Blocked" if u.get("blocked") else "Active")]:
            row=BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(36),padding=[dp(6),0])
            row.add_widget(Lbl(lbl,T3,13,size_hint_x=0.4)); row.add_widget(Lbl(val,WHITE,13,"right",size_hint_x=0.6))
            self._det_body.add_widget(row)
        self._det_body.add_widget(Lbl("Edit Balance",GREEN_L,12,h=20))
        self._bal_in=TextInput(text=str(u.get("balance",0)),background_color=NAVY_C,foreground_color=WHITE,
                                font_size=sp(14),multiline=False,size_hint_y=None,height=dp(46))
        self._det_body.add_widget(self._bal_in)
        sb=Btn("Save Balance",h=44); sb.bind(on_press=lambda *a: FB.set_doc("users",uid,{"balance":float(self._bal_in.text or 0)},ok=lambda: Clock.schedule_once(lambda dt: toast(self,"Balance saved!"),0)))
        self._det_body.add_widget(sb)
        blocked=u.get("blocked",False)
        bb=Button(text="Unblock User" if blocked else "Block User",color=OK if blocked else ERR,
                   background_color=(0,0,0,0),font_size=sp(14),bold=True,size_hint_y=None,height=dp(44))
        bb.bind(on_press=lambda *a: FB.set_doc("users",uid,{"blocked":not blocked},
            ok=lambda: Clock.schedule_once(lambda dt: (toast(self,"Done"),setattr(self._detail,"opacity",0),self._load()),0)))
        self._det_body.add_widget(bb)
        self._detail.opacity=1

# ── Admin Withdrawals ─────────────────────────────

class AdminWithdrawScreen(Screen):
    def on_enter(self): self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("Withdrawals", lambda: setattr(self.manager,"current","admin_dash")))
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.88})
        self._list=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(10))
        self._list.bind(minimum_height=self._list.setter("height"))
        scroll.add_widget(self._list); root.add_widget(scroll)

    def _load(self):
        FB.get_col("withdrawals",ok=lambda docs: Clock.schedule_once(lambda dt:
            self._render(sorted(docs,key=lambda d: -d.get("timestamp",0))),0))

    def _render(self,ws):
        self._list.clear_widgets()
        for w in ws: self._list.add_widget(self._card(w))

    def _card(self,w):
        c=BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(12),size_hint_y=None,height=dp(108))
        with c.canvas.before:
            Color(*NAVY_C); RoundedRectangle(pos=c.pos,size=c.size,radius=[dp(12)])
        r1=BoxLayout(size_hint_y=None,height=dp(24))
        r1.add_widget(Lbl(w.get("username","?"),WHITE,14,True,h=22)); r1.add_widget(status_badge(w.get("status","pending")))
        r2=BoxLayout(size_hint_y=None,height=dp(20))
        r2.add_widget(Lbl(f"৳{w.get('amount',0):,.2f} → {w.get('bkash_number','')}",GREEN_L,13,True))
        r2.add_widget(Lbl(time.strftime('%d %b %H:%M',time.localtime(w.get('timestamp',0))),T3,11,"right"))
        brow=BoxLayout(spacing=dp(8),size_hint_y=None,height=dp(38))
        if w.get("status")=="pending":
            ab=Button(text="✓ Approve",background_color=OK,color=WHITE,font_size=sp(12),bold=True)
            rb=Button(text="✗ Reject",background_color=ERR,color=WHITE,font_size=sp(12),bold=True)
            ab.bind(on_press=lambda *a,wd=w: self._approve(wd)); rb.bind(on_press=lambda *a,wd=w: self._reject(wd))
            brow.add_widget(ab); brow.add_widget(rb)
        for widget in [r1,r2,brow]: c.add_widget(widget)
        return c

    def _approve(self,w):
        FB.set_doc("withdrawals",w.get("_id",""),{"status":"approved","processed_at":int(time.time())},
            ok=lambda: (FB.get_doc("users",w.get("user_id",""),ok=lambda u: FB.push(u.get("fcm_token",""),
                "Withdrawal Approved 💸",f"৳{w.get('amount',0):,.2f} sent to {w.get('bkash_number','')}")),
                Clock.schedule_once(lambda dt: (toast(self,"Approved"),self._load()),0)))

    def _reject(self,w):
        uid=w.get("user_id",""); amt=float(w.get("amount",0))
        FB.set_doc("withdrawals",w.get("_id",""),{"status":"rejected"},
            ok=lambda: (FB.incr("users",uid,"balance",amt),
                FB.get_doc("users",uid,ok=lambda u: FB.push(u.get("fcm_token",""),
                    "Withdrawal Rejected",f"৳{amt:,.2f} refunded to your balance.")),
                Clock.schedule_once(lambda dt: (toast(self,"Rejected & refunded"),self._load()),0)))

# ── Admin Chat ────────────────────────────────────

class AdminChatScreen(Screen):
    def on_enter(self): self._active_uid=None; self._msgs=[]; self._build(); self._load_convs()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("Chat", lambda: setattr(self.manager,"current","admin_dash")))
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.88})
        self._conv_list=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(6))
        self._conv_list.bind(minimum_height=self._conv_list.setter("height"))
        scroll.add_widget(self._conv_list); root.add_widget(scroll)
        self._chat_panel=self._build_chat(); self._chat_panel.opacity=0; root.add_widget(self._chat_panel)

    def _build_chat(self):
        p=FloatLayout(size_hint=(1,0.6),pos_hint={"y":0})
        with p.canvas.before:
            Color(*NAVY_S); r=Rectangle(pos=p.pos,size=p.size)
        p.bind(pos=lambda *a: setattr(r,"pos",p.pos),size=lambda *a: setattr(r,"size",p.size))
        close=Button(text="✕",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(18),
                      size_hint=(None,None),size=(dp(36),dp(36)),pos_hint={"right":0.98,"top":0.99})
        close.bind(on_press=lambda *a: setattr(self._chat_panel,"opacity",0))
        self._chat_scroll=ScrollView(size_hint=(1,0.80),pos_hint={"top":0.92})
        self._chat_msgs=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(4)],spacing=dp(6))
        self._chat_msgs.bind(minimum_height=self._chat_msgs.setter("height"))
        self._chat_scroll.add_widget(self._chat_msgs)
        inp_row=BoxLayout(size_hint=(1,None),height=dp(48),padding=[dp(8),dp(4)],spacing=dp(6),pos_hint={"y":0.01})
        self._a_inp=TextInput(hint_text="Reply as admin...",background_color=NAVY_C,foreground_color=WHITE,
                               font_size=sp(13),multiline=False,size_hint_x=0.8)
        send=Button(text="Send",background_color=GREEN_L,color=WHITE,font_size=sp(13),size_hint_x=0.2)
        send.bind(on_press=self._send_admin)
        inp_row.add_widget(self._a_inp); inp_row.add_widget(send)
        p.add_widget(close); p.add_widget(self._chat_scroll); p.add_widget(inp_row); return p

    def _load_convs(self):
        FB.get_col("chats",ok=lambda docs: Clock.schedule_once(lambda dt: self._render_convs(docs),0))

    def _render_convs(self,chats):
        self._conv_list.clear_widgets()
        for c in sorted(chats,key=lambda x: -x.get("last_timestamp",0)):
            row=BoxLayout(orientation="horizontal",spacing=dp(8),padding=dp(10),size_hint_y=None,height=dp(54))
            with row.canvas.before:
                Color(*NAVY_C); RoundedRectangle(pos=row.pos,size=row.size,radius=[dp(8)])
            info=BoxLayout(orientation="vertical",spacing=dp(2))
            info.add_widget(Lbl(c.get("username","?"),WHITE,14,True,h=22))
            info.add_widget(Lbl(c.get("last_message","")[:45],T3,11,h=16))
            ob=Button(text="Open",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(12),size_hint=(None,None),size=(dp(52),dp(36)))
            ob.bind(on_press=lambda *a,conv=c: self._open(conv))
            row.add_widget(info); row.add_widget(ob); self._conv_list.add_widget(row)

    def _open(self,conv):
        self._active_uid=conv.get("user_id",conv.get("_id",""))
        self._msgs=conv.get("messages",[])
        self._chat_msgs.clear_widgets()
        for m in self._msgs:
            is_admin=m.get("sender")=="admin"
            lbl=Lbl(f"{'[Admin] ' if is_admin else ''}{m.get('text','')}",
                     GREEN_L if is_admin else WHITE,13,"right" if is_admin else "left",h=26)
            self._chat_msgs.add_widget(lbl)
        self._chat_panel.opacity=1
        FB.set_doc("chats",self._active_uid,{"unread_admin":False})

    def _send_admin(self,*a):
        text=self._a_inp.text.strip()
        if not text or not self._active_uid: return
        self._a_inp.text=""
        msg={"text":text,"sender":"admin","timestamp":int(time.time())}
        self._msgs.append(msg)
        self._chat_msgs.add_widget(Lbl(f"[Admin] {text}",GREEN_L,13,"right",h=26))
        Clock.schedule_once(lambda dt: setattr(self._chat_scroll,"scroll_y",0),0.1)
        FB.set_doc("chats",self._active_uid,{"messages":self._msgs,"last_message":text,
            "last_timestamp":msg["timestamp"],"unread_user":True},merge=False)
        FB.get_doc("users",self._active_uid,ok=lambda u: FB.push(u.get("fcm_token",""),
            "New message from Admin",text),err=lambda e: None)

# ── Admin Settings ────────────────────────────────

class AdminSettingsScreen(Screen):
    def on_enter(self): self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("Settings", lambda: setattr(self.manager,"current","admin_dash")))
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.88})
        body=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(14),dp(8)],spacing=dp(10))
        body.bind(minimum_height=body.setter("height"))
        self._fi={}
        for key,lbl in [("groq_api_key","Groq API Key"),("imgbb_api_key","ImgBB API Key"),
                         ("sheets_url","Google Apps Script URL"),("fcm_server_key","FCM Server Key"),
                         ("app_version","App Version (e.g. 1.0.1)")]:
            inp=TextInput(hint_text=lbl,background_color=NAVY_C,foreground_color=WHITE,
                           cursor_color=GREEN_L,font_size=sp(13),multiline=False,size_hint_y=None,height=dp(46))
            self._fi[key]=inp
            body.add_widget(Lbl(lbl,T2,12,h=16)); body.add_widget(inp)
        tog=BoxLayout(size_hint_y=None,height=dp(46))
        tog.add_widget(Lbl("Midnight Auto-Approve",WHITE,13)); self._auto=Switch(active=True)
        tog.add_widget(self._auto); body.add_widget(tog)
        save=Btn("Save Settings"); save.bind(on_press=self._save); body.add_widget(save)
        scroll.add_widget(body); root.add_widget(scroll)

    def _load(self):
        s=FB.settings()
        Clock.schedule_once(lambda dt: [setattr(inp,"text",str(s.get(k,""))) for k,inp in self._fi.items()],0)

    def _save(self,*a):
        data={k:v.text.strip() for k,v in self._fi.items()}
        data["auto_approve"]=self._auto.active
        FB.set_doc("settings","app_settings",data,merge=False,
            ok=lambda: (FB._settings.update({"v":data}),
                        Clock.schedule_once(lambda dt: toast(self,"Settings saved!"),0)))

# ── Admin AI Profiles ─────────────────────────────

class AdminProfScreen(Screen):
    def on_enter(self): self._profiles=[]; self._build(); self._load()

    def _build(self):
        self.clear_widgets(); root=admin_root(self)
        root.add_widget(admin_hdr("AI Review Profiles", lambda: setattr(self.manager,"current","admin_dash")))
        add=Btn("+ Add Profile",h=40,size_hint=(None,None),size=(dp(160),dp(40)),pos_hint={"right":0.97,"top":0.89})
        add.bind(on_press=lambda *a: self._open_form()); root.add_widget(add)
        scroll=ScrollView(size_hint=(1,None),pos_hint={"top":0.80})
        self._list=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(10),dp(6)],spacing=dp(10))
        self._list.bind(minimum_height=self._list.setter("height"))
        scroll.add_widget(self._list)
        self._form=self._build_form(); self._form.opacity=0
        root.add_widget(scroll); root.add_widget(self._form)

    def _build_form(self):
        p=FloatLayout(size_hint=(1,0.7),pos_hint={"y":0})
        with p.canvas.before:
            Color(*NAVY_S); r=Rectangle(pos=p.pos,size=p.size)
        p.bind(pos=lambda *a: setattr(r,"pos",p.pos),size=lambda *a: setattr(r,"size",p.size))
        scroll=ScrollView(size_hint=(1,1))
        body=BoxLayout(orientation="vertical",size_hint_y=None,padding=[dp(14),dp(14)],spacing=dp(10))
        body.bind(minimum_height=body.setter("height"))
        self._pn=TextInput(hint_text="App Name",background_color=NAVY_C,foreground_color=WHITE,font_size=sp(14),multiline=False,size_hint_y=None,height=dp(46))
        self._pd=TextInput(hint_text="App Description",background_color=NAVY_C,foreground_color=WHITE,font_size=sp(14),multiline=True,size_hint_y=None,height=dp(72))
        self._pp=TextInput(hint_text="Custom AI instructions...",background_color=NAVY_C,foreground_color=WHITE,font_size=sp(14),multiline=True,size_hint_y=None,height=dp(72))
        for lbl,w in [("App Name *",self._pn),("Description",self._pd),("Custom Prompt",self._pp)]:
            body.add_widget(Lbl(lbl,T2,12,h=16)); body.add_widget(w)
        brow=BoxLayout(spacing=dp(10),size_hint_y=None,height=dp(50))
        cancel=OutBtn("Cancel"); cancel.bind(on_press=lambda *a: setattr(self._form,"opacity",0))
        save=Btn("Save Profile"); save.bind(on_press=self._save)
        brow.add_widget(cancel); brow.add_widget(save); body.add_widget(brow)
        scroll.add_widget(body); p.add_widget(scroll); return p

    def _open_form(self,pf=None,idx=None):
        self._editing_idx=idx
        self._pn.text=pf.get("app_name","") if pf else ""
        self._pd.text=pf.get("description","") if pf else ""
        self._pp.text=pf.get("custom_prompt","") if pf else ""
        self._form.opacity=1

    def _save(self,*a):
        if not self._pn.text.strip(): toast(self,"App name required",False); return
        nw={"app_name":self._pn.text.strip(),"description":self._pd.text.strip(),"custom_prompt":self._pp.text.strip()}
        if self._editing_idx is not None: self._profiles[self._editing_idx]=nw
        else: self._profiles.append(nw)
        FB.set_doc("settings","app_settings",{"app_profiles":self._profiles},
            ok=lambda: Clock.schedule_once(lambda dt: (setattr(self._form,"opacity",0),toast(self,"Saved!"),self._render()),0))

    def _load(self):
        FB.get_doc("settings","app_settings",ok=lambda d: Clock.schedule_once(lambda dt: (setattr(self,"_profiles",d.get("app_profiles",[])),self._render()),0))

    def _render(self):
        self._list.clear_widgets()
        for i,p in enumerate(self._profiles):
            row=BoxLayout(orientation="horizontal",spacing=dp(8),padding=dp(12),size_hint_y=None,height=dp(54))
            with row.canvas.before:
                Color(*NAVY_C); RoundedRectangle(pos=row.pos,size=row.size,radius=[dp(10)])
            info=BoxLayout(orientation="vertical",spacing=dp(3))
            info.add_widget(Lbl(p.get("app_name",""),WHITE,14,True,h=22))
            info.add_widget(Lbl(p.get("description","")[:50],T3,11,h=16))
            bx=BoxLayout(size_hint=(None,None),size=(dp(100),dp(36)),spacing=dp(6))
            eb=Button(text="Edit",color=GREEN_L,background_color=(0,0,0,0),font_size=sp(12))
            db=Button(text="Del",color=ERR,background_color=(0,0,0,0),font_size=sp(12))
            eb.bind(on_press=lambda *a,pr=p,idx=i: self._open_form(pr,idx))
            db.bind(on_press=lambda *a,idx=i: self._delete(idx))
            bx.add_widget(eb); bx.add_widget(db); row.add_widget(info); row.add_widget(bx)
            self._list.add_widget(row)

    def _delete(self,idx):
        self._profiles.pop(idx)
        FB.set_doc("settings","app_settings",{"app_profiles":self._profiles},ok=lambda: Clock.schedule_once(lambda dt: (toast(self,"Deleted"),self._render()),0))

# ══════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════

class ReviewPayApp(App):
    def build(self):
        self.title = "ReviewPay"
        sm = ScreenManager(transition=FadeTransition(duration=0.22))
        screens = [
            SplashScreen(name="splash"),
            AuthScreen(name="auth"),
            DashboardScreen(name="dashboard"),
            ProjectDetailScreen(name="project_detail"),
            ReviewGenScreen(name="review_gen"),
            WithdrawScreen(name="withdraw"),
            ProfileScreen(name="profile"),
            ChatScreen(name="chat"),
            AdminDashScreen(name="admin_dash"),
            AdminSubsScreen(name="admin_subs"),
            AdminProjScreen(name="admin_proj"),
            AdminUsersScreen(name="admin_users"),
            AdminWithdrawScreen(name="admin_w"),
            AdminChatScreen(name="admin_chat"),
            AdminSettingsScreen(name="admin_set"),
            AdminProfScreen(name="admin_prof"),
        ]
        for s in screens: sm.add_widget(s)
        sm.current = "splash"
        return sm

    def on_pause(self): return True
    def on_resume(self): pass

if __name__ == "__main__":
    ReviewPayApp().run()
