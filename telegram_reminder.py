"""
Telegram Group Reminder v4.1 - Multi-Profile Edition
Requires: pip install telethon
"""

import asyncio
import sys
import html
import json
import os
import re
import threading
import time
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
from telethon import TelegramClient, events
from telethon.tl.types import Chat, Channel
from telethon.errors import FloodWaitError

# ── VERSION ───────────────────────────────────────────────────────────────────
VERSION      = "4.1"

# ── LOGIN SYSTEM (Server-based) ───────────────────────────────────────────────
import urllib.request, urllib.error

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))

# !! Replace this with your Railway URL after deploying !!
AUTH_SERVER = "https://YOUR-APP.up.railway.app"

def _server_request(endpoint, data):
    """POST JSON to the auth server. Returns (ok, message)."""
    try:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            AUTH_SERVER + endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return body.get("ok", False), body.get("message", "")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
            return False, body.get("error", f"Server error {e.code}")
        except Exception:
            return False, f"Server error {e.code}"
    except Exception as ex:
        return False, f"Cannot reach server: {ex}"

def show_login():
    """Show login / register screen. Talks to the auth server."""
    DARK   = "#1e1e2e"
    PANEL  = "#2a2a3e"
    ACCENT = "#7c6af7"
    FG     = "#cdd6f4"
    MUTED  = "#6c7086"
    RED    = "#f38ba8"
    GREEN  = "#a6e3a1"

    result = {}

    root = tk.Tk()
    mode   = tk.StringVar(value="login")   # "login" or "register"
    root.title("Telegram Reminder")
    root.geometry("400x460")
    root.configure(bg=DARK)
    root.resizable(False, False)
    root.eval('tk::PlaceWindow . center')

    # Header
    hdr = tk.Frame(root, bg=ACCENT, height=70)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text="✈", font=("Segoe UI", 22), bg=ACCENT, fg="white").pack(side="left", padx=16)
    tk.Label(hdr, text="Telegram Reminder", font=("Segoe UI", 15, "bold"),
             bg=ACCENT, fg="white").pack(side="left")

    title_lbl = tk.Label(root, text="Welcome back", font=("Segoe UI", 12, "bold"), bg=DARK, fg=FG)
    title_lbl.pack(pady=(20, 2))
    sub_lbl = tk.Label(root, text="Enter your credentials to continue.",
                       font=("Segoe UI", 9), bg=DARK, fg=MUTED, wraplength=340)
    sub_lbl.pack(pady=(0, 14))

    def _field(label, show=""):
        tk.Label(root, text=label, font=("Segoe UI", 9, "bold"),
                 bg=DARK, fg=FG, anchor="w").pack(fill="x", padx=40, pady=(6,2))
        e = tk.Entry(root, font=("Segoe UI", 11), bg=PANEL, fg=FG,
                     insertbackground=FG, relief="flat", bd=0, show=show)
        e.pack(fill="x", padx=40, ipady=7)
        return e

    e_user = _field("Username")
    e_pw   = _field("Password", show="●")

    # Confirm password — hidden unless registering
    confirm_frame = tk.Frame(root, bg=DARK)
    tk.Label(confirm_frame, text="Confirm Password", font=("Segoe UI", 9, "bold"),
             bg=DARK, fg=FG, anchor="w").pack(fill="x", pady=(6,2))
    e_pw2 = tk.Entry(confirm_frame, font=("Segoe UI", 11), bg=PANEL, fg=FG,
                     insertbackground=FG, relief="flat", bd=0, show="●")
    e_pw2.pack(fill="x", ipady=7)

    err_lbl = tk.Label(root, text="", font=("Segoe UI", 9), bg=DARK, fg=RED, wraplength=320)
    err_lbl.pack(pady=(8, 0))

    submit_btn = tk.Button(root, text="Login", font=("Segoe UI", 11, "bold"),
              bg=ACCENT, fg="white", relief="flat", pady=10, cursor="hand2")
    submit_btn.pack(fill="x", padx=40, pady=(12, 0))

    # Toggle between login / register
    toggle_frame = tk.Frame(root, bg=DARK)
    toggle_frame.pack(pady=(10, 0))
    tk.Label(toggle_frame, text="Don't have an account?", font=("Segoe UI", 9),
             bg=DARK, fg=MUTED).pack(side="left", padx=(0,4))
    toggle_lbl = tk.Label(toggle_frame, text="Register", font=("Segoe UI", 9, "bold"),
                          bg=DARK, fg=ACCENT, cursor="hand2")
    toggle_lbl.pack(side="left")

    def _set_mode(m):
        mode.set(m)
        if m == "register":
            title_lbl.config(text="Create an account")
            sub_lbl.config(text="Choose a username and password.")
            confirm_frame.pack(fill="x", padx=40, before=err_lbl)
            submit_btn.config(text="Register")
            toggle_lbl.config(text="Login instead")
            tk.Label(toggle_frame.winfo_children()[0], text="Already have an account?")
            toggle_frame.winfo_children()[0].config(text="Already have an account?")
        else:
            title_lbl.config(text="Welcome back")
            sub_lbl.config(text="Enter your credentials to continue.")
            confirm_frame.pack_forget()
            submit_btn.config(text="Login")
            toggle_frame.winfo_children()[0].config(text="Don't have an account?")
            toggle_lbl.config(text="Register")
        err_lbl.config(text="")

    toggle_lbl.bind("<Button-1>",
        lambda e: _set_mode("login" if mode.get() == "register" else "register"))

    def _submit():
        username = e_user.get().strip()
        password = e_pw.get()
        err_lbl.config(text="", fg=RED)

        if not username or not password:
            err_lbl.config(text="Username and password required.")
            return

        if mode.get() == "register":
            if password != e_pw2.get():
                err_lbl.config(text="Passwords do not match.")
                return
            if len(password) < 4:
                err_lbl.config(text="Password must be at least 4 characters.")
                return
            submit_btn.config(state="disabled", text="Registering...")
            root.update()
            ok, msg = _server_request("/register", {"username": username, "password": password})
            submit_btn.config(state="normal", text="Register")
            if ok:
                err_lbl.config(text="Account created! Logging in...", fg=GREEN)
                root.update()
                result["ok"] = True
                root.after(800, root.destroy)
            else:
                err_lbl.config(text=msg)
        else:
            submit_btn.config(state="disabled", text="Logging in...")
            root.update()
            ok, msg = _server_request("/login", {"username": username, "password": password})
            submit_btn.config(state="normal", text="Login")
            if ok:
                result["ok"] = True
                root.destroy()
            else:
                err_lbl.config(text=msg)
                e_pw.delete(0, "end")

    submit_btn.config(command=_submit)
    e_user.bind("<Return>", lambda e: e_pw.focus())
    e_pw.bind("<Return>",   lambda e: (e_pw2.focus() if mode.get()=="register" else _submit()))
    e_pw2.bind("<Return>",  lambda e: _submit())

    e_user.focus()
    root.mainloop()

    if not result.get("ok"):
        sys.exit(0)

# ── BOOT ──────────────────────────────────────────────────────────────────────
show_login()

# Credentials & paths (single user, stored in script directory)
def _get_config_path():
    return os.path.join(BASE_DIR, "config.json")

def _load_config():
    cfg_path = _get_config_path()
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_config(cfg):
    with open(_get_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def _show_setup_wizard():
    DARK = "#1e1e2e"; PANEL = "#2a2a3e"; ACCENT = "#7c6af7"; FG = "#cdd6f4"; MUTED = "#6c7086"
    root = tk.Tk()
    root.title("Telegram Reminder - Setup")
    root.geometry("460x480")
    root.configure(bg=DARK)
    root.resizable(False, False)
    tk.Label(root, text="✈  Telegram Reminder Setup", font=("Segoe UI", 14, "bold"),
             bg=ACCENT, fg="white").pack(fill="x", pady=0, ipady=12)
    tk.Label(root, text="Enter your Telegram credentials. Get API ID and Hash from my.telegram.org",
             font=("Segoe UI", 9), bg=DARK, fg=MUTED, justify="center", wraplength=400).pack(pady=(12,4))
    def field(label, show=""):
        tk.Label(root, text=label, font=("Segoe UI", 9, "bold"), bg=DARK, fg=FG, anchor="w").pack(fill="x", padx=24, pady=(8,2))
        e = tk.Entry(root, font=("Segoe UI", 10), bg=PANEL, fg=FG, insertbackground=FG, relief="flat", bd=0, show=show)
        e.pack(fill="x", padx=24, ipady=5)
        return e
    e_api_id   = field("API ID  (from my.telegram.org)")
    e_api_hash = field("API Hash")
    e_phone    = field("Phone Number  (e.g. +1234567890)")
    e_bot1     = field("Bot 1 Token  (from @BotFather)")
    e_bot2     = field("Bot 2 Token  (optional)")
    result = {}
    def save():
        api_id = e_api_id.get().strip(); api_hash = e_api_hash.get().strip()
        phone  = e_phone.get().strip();  bot1 = e_bot1.get().strip(); bot2 = e_bot2.get().strip()
        if not api_id or not api_hash or not phone or not bot1:
            messagebox.showwarning("Missing Fields", "API ID, Hash, Phone and Bot 1 Token are required.")
            return
        if not api_id.isdigit():
            messagebox.showwarning("Invalid API ID", "API ID must be a number.")
            return
        result["api_id"] = int(api_id); result["api_hash"] = api_hash
        result["phone"]  = phone; result["bot_token"] = bot1; result["bot_token2"] = bot2
        _save_config(result)
        root.destroy()
    tk.Button(root, text="Save & Launch", font=("Segoe UI", 11, "bold"),
              bg=ACCENT, fg="white", relief="flat", pady=10, cursor="hand2",
              command=save).pack(fill="x", padx=24, pady=20)
    root.mainloop()
    return result

_cfg = _load_config()
if not _cfg.get("api_id") or not _cfg.get("phone") or not _cfg.get("bot_token"):
    _cfg = _show_setup_wizard()
    if not _cfg:
        sys.exit(0)

API_ID     = _cfg["api_id"]
API_HASH   = _cfg["api_hash"]
PHONE      = _cfg["phone"]
BOT_TOKEN  = _cfg["bot_token"]
BOT_TOKEN2 = _cfg.get("bot_token2", "")
DIR        = BASE_DIR
SESSION    = os.path.join(DIR, "reminder_session")
BOT_SES    = os.path.join(DIR, "bot_session")
BOT_SES2   = os.path.join(DIR, "bot2_session")
PREFS      = os.path.join(DIR, "reminder_prefs.json")
SESSIONS   = os.path.join(DIR, "reminder_sessions.json")
PROXY_F    = os.path.join(DIR, "proxy.json")
TEMPLATES  = os.path.join(DIR, "reminder_templates.json")
HISTORY    = os.path.join(DIR, "reminder_history.json")
TARGETS_F  = os.path.join(DIR, "bot_targets.json")
TARGETS_F2 = os.path.join(DIR, "bot2_targets.json")

# ── COLORS ────────────────────────────────────────────────────────────────────
DARK   = "#1e1e2e"
PANEL  = "#2a2a3e"
ACCENT = "#7c6af7"
FG     = "#cdd6f4"
MUTED  = "#6c7086"
GREEN  = "#a6e3a1"
RED    = "#f38ba8"
YELLOW = "#f9e2af"

# ── PROXY LOADER ──────────────────────────────────────────────────────────────
def _load_proxy():
    """Load proxy settings from proxy.json. Returns None if disabled or missing."""
    if not os.path.exists(PROXY_F):
        return None
    try:
        import socks
        with open(PROXY_F, "r", encoding="utf-8") as f:
            p = json.load(f)
        if not p.get("enabled"):
            return None
        ptype = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4,
                 "http":   socks.HTTP}.get(p.get("type", "socks5"), socks.SOCKS5)
        return (ptype, p["host"], int(p.get("port", 1080)),
                True,
                p.get("username") or None,
                p.get("password") or None)
    except Exception as e:
        print(f"[PROXY] Failed to load proxy settings: {e}")
        return None

_proxy = _load_proxy()

# ── CLIENTS ───────────────────────────────────────────────────────────────────
user_client = TelegramClient(SESSION, API_ID, API_HASH, proxy=_proxy)
bot_client  = TelegramClient(BOT_SES,  API_ID, API_HASH, proxy=_proxy)
bot_client2 = TelegramClient(BOT_SES2, API_ID, API_HASH, proxy=_proxy)

# ── GLOBAL STATE ──────────────────────────────────────────────────────────────
group_cooldowns  = {}
detected_delays  = {}
owner_id         = None

# Per-bot forwarder state, keyed by bot number (1 or 2)
class BotState:
    def __init__(self, client, targets_file):
        self.client        = client
        self.groups        = []
        self.targets       = None   # None = all groups
        self.schedules     = {}
        self.counter       = 0
        self.user_state    = {}
        self.targets_file  = targets_file

bot1_state = BotState(bot_client,  TARGETS_F)
bot2_state = BotState(bot_client2, TARGETS_F2)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def fmt_time(secs):
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    if h > 0:   return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0: return f"{m}m {s:02d}s"
    else:       return f"{s}s"

def parse_interval(text):
    text = text.lower().strip()
    total = 0
    for val, unit in re.findall(r'(\d+)\s*([hms])', text):
        val = int(val)
        if unit == 'h': total += val * 3600
        elif unit == 'm': total += val * 60
        elif unit == 's': total += val
    return total if total > 0 else None

def get_send_targets(state):
    return state.targets if state.targets is not None else state.groups

def save_targets(state):
    data = None if state.targets is None else [g["title"] for g in state.targets]
    with open(state.targets_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_targets(state):
    if not os.path.exists(state.targets_file):
        return
    try:
        with open(state.targets_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        state.targets = None if data is None else [g for g in state.groups if g["title"] in data]
    except Exception:
        pass




# ── FETCH GROUPS ──────────────────────────────────────────────────────────────

async def fetch_user_groups():
    groups = []
    try:
        async for dialog in user_client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, (Chat, Channel)):
                if isinstance(entity, Channel) and entity.broadcast:
                    continue
                groups.append({"title": dialog.name, "entity": entity})
    except Exception as e:
        print(f"[ERROR] fetch_user_groups: {e}")
    return groups

async def fetch_bot_groups(state, label="Bot"):
    """Fetch groups the given bot (state.client) is a member of, using
    the user session to enumerate dialogs and resolve entities."""
    groups = []
    client = state.client
    try:
        from telethon.tl.types import InputPeerChannel, InputPeerChat
        async for dialog in user_client.iter_dialogs():
            entity = dialog.entity
            if not isinstance(entity, (Chat, Channel)):
                continue
            if isinstance(entity, Channel) and entity.broadcast:
                continue
            bot_entity = None
            # Method 1: use username
            try:
                username = getattr(entity, 'username', None)
                if username:
                    bot_entity = await client.get_entity(username)
            except Exception:
                pass
            # Method 2: use InputPeerChannel with access_hash from user session
            if not bot_entity:
                try:
                    if isinstance(entity, Channel):
                        peer = InputPeerChannel(entity.id, entity.access_hash)
                    else:
                        peer = InputPeerChat(entity.id)
                    bot_entity = await client.get_entity(peer)
                except Exception:
                    pass
            # Method 3: plain id
            if not bot_entity:
                try:
                    bot_entity = await client.get_entity(entity.id)
                except Exception:
                    pass
            if bot_entity:
                groups.append({"title": dialog.name, "entity": bot_entity})
                print(f"[{label}] Found: {dialog.name}")
            else:
                print(f"[{label}] Skip: {dialog.name}")
    except Exception as e:
        print(f"[ERROR] fetch_bot_groups ({label}): {e}")
    state.groups = groups
    print(f"[INFO] {label} is in {len(groups)} group(s)")
    return groups


# ── SEND FUNCTIONS ────────────────────────────────────────────────────────────

async def send_to_group(client, g, message, log_cb, respect_timer=True, restart_after=True):
    entity_id = g["entity"].id
    while respect_timer:
        wait_until = group_cooldowns.get(entity_id, 0)
        remaining  = wait_until - time.time()
        if remaining <= 0:
            break
        log_cb(f"⳿  {g['title']} - waiting {fmt_time(remaining)}...", YELLOW)
        await asyncio.sleep(min(remaining, 10))
    try:
        send_coro = client.send_message(g["entity"], message, parse_mode="md")
        await asyncio.wait_for(send_coro, timeout=30)
        group_cooldowns.pop(entity_id, None)
        if restart_after and entity_id in detected_delays:
            group_cooldowns[entity_id] = time.time() + detected_delays[entity_id]
        return True
    except asyncio.TimeoutError:
        log_cb(f"⭕  {g['title']} - timed out", YELLOW)
        return False
    except FloodWaitError as e:
        group_cooldowns[entity_id] = time.time() + e.seconds
        detected_delays[entity_id] = e.seconds
        log_cb(f"⳿  {g['title']} - flood wait {fmt_time(e.seconds)}", YELLOW)
        return False
    except Exception as e:
        err = str(e)
        if not hasattr(send_to_group, "_last_err"):
            send_to_group._last_err = {}
        send_to_group._last_err[entity_id] = err
        if "wait" in err.lower() and "second" in err.lower():
            nums = re.findall(r'\d+', err)
            secs = int(nums[0]) if nums else 60
            group_cooldowns[entity_id] = time.time() + secs
            detected_delays[entity_id] = secs
            log_cb(f"⳿  {g['title']} - cooldown {fmt_time(secs)}", YELLOW)
            return False
        log_cb(f"✗  {g['title']} - {err}", RED)
        return False

async def send_messages(client, targets, message, log_cb, done_cb,
                        respect_timers=True, restart_timer=True, stop_event=None):
    round_num = 1
    total     = len(targets)
    perm_failed = set()
    success = 0
    try:
        while True:
            if stop_event and stop_event.is_set():
                break

            active = [g for g in targets if g["entity"].id not in perm_failed]
            log_cb(f"── Round {round_num} ({len(active)} groups) ──", YELLOW)
            success = 0

            for g in active:
                if stop_event and stop_event.is_set():
                    break
                entity_id  = g["entity"].id
                wait_until = group_cooldowns.get(entity_id, 0)
                if respect_timers and time.time() < wait_until:
                    log_cb(f"⭕  {g['title']} - skipped (cooldown {fmt_time(wait_until - time.time())})", MUTED)
                    continue
                ok = await send_to_group(client, g, message, log_cb,
                                         respect_timer=respect_timers,
                                         restart_after=restart_timer)
                if ok:
                    idx = active.index(g) + 1
                    log_cb(f"✓  [{idx}/{len(active)}]  {g['title']}", GREEN)
                    success += 1
                    await asyncio.sleep(3)
                else:
                    last_err = getattr(send_to_group, "_last_err", {}).get(entity_id, "")
                    if "can't write" in last_err.lower() or "forbidden" in last_err.lower():
                        perm_failed.add(entity_id)
                        log_cb(f"⛔  {g['title']} - removed from loop (can't write)", RED)

            if stop_event and stop_event.is_set():
                break

            log_cb(f"── Round {round_num} done: {success}/{len(active)} ──", YELLOW)
            round_num += 1
            print(f"[LOOP] Round done, sleeping 10s before round {round_num}")
            await asyncio.sleep(10)
            print(f"[LOOP] Starting round {round_num}")

    except asyncio.CancelledError:
        pass
    except Exception as e:
        log_cb(f"✗  Loop error: {e}", RED)
    finally:
        done_cb(success, total)


# ── FORWARDER SEND ────────────────────────────────────────────────────────────

async def send_to_groups_fwd(state, targets, message, media=None):
    client = state.client
    success, failed, waiting = [], [], []
    for g in targets:
        entity_id  = g["entity"].id
        wait_until = group_cooldowns.get(entity_id, 0)
        if time.time() < wait_until:
            waiting.append(f"{g['title']} (ready in {fmt_time(wait_until - time.time())})")
            continue
        try:
            if media:
                await client.send_file(g["entity"], media, caption=message or "", parse_mode="md")
            else:
                await client.send_message(g["entity"], message, parse_mode="md")
            success.append(g["title"])
            await asyncio.sleep(3)
        except FloodWaitError as e:
            group_cooldowns[entity_id] = time.time() + e.seconds
            waiting.append(f"{g['title']} (flood {fmt_time(e.seconds)})")
        except Exception as e:
            err = str(e)
            if "wait" in err.lower() and "second" in err.lower():
                nums = re.findall(r'\d+', err)
                secs = int(nums[0]) if nums else 60
                group_cooldowns[entity_id] = time.time() + secs
                waiting.append(f"{g['title']} (cooldown {fmt_time(secs)})")
            else:
                failed.append(f"{g['title']}: {err[:50]}")
    return success, failed, waiting

async def delete_from_groups_fwd(state, targets):
    client = state.client
    deleted, failed = [], []
    bot_me = await client.get_me()
    for g in targets:
        try:
            found = None
            async for msg in client.iter_messages(g["entity"], limit=50):
                if msg.sender_id == bot_me.id:
                    found = msg
                    break
            if found:
                await client.delete_messages(g["entity"], [found.id])
                deleted.append(g["title"])
            else:
                failed.append(f"{g['title']}: no recent message found")
        except Exception as e:
            failed.append(f"{g['title']}: {str(e)[:50]}")
    return deleted, failed

async def retry_after_cooldown(state, sid, targets, message):
    client = state.client
    while targets:
        if sid not in state.schedules:
            return
        next_retry = []
        for g in targets:
            entity_id = g["entity"].id
            if time.time() < group_cooldowns.get(entity_id, 0):
                next_retry.append(g)
            else:
                try:
                    await client.send_message(g["entity"], message, parse_mode="md")
                    print(f"[RETRY] Sent to {g['title']}")
                    try:
                        await client.send_message(owner_id, f"Retry sent to {g['title']}")
                    except Exception:
                        pass
                    await asyncio.sleep(3)
                except FloodWaitError as e:
                    group_cooldowns[entity_id] = time.time() + e.seconds
                    next_retry.append(g)
                except Exception as e:
                    print(f"[RETRY] Failed {g['title']}: {e}")
        targets = next_retry
        if targets:
            await asyncio.sleep(30)

async def run_schedule(state, sid):
    client = state.client
    while sid in state.schedules:
        s = state.schedules[sid]
        remaining = s["next_send"] - time.time()
        if remaining > 0:
            await asyncio.sleep(min(remaining, 10))
            continue
        targets = get_send_targets(state)
        success, failed, waiting = await send_to_groups_fwd(state, targets, s["message"])
        retry_targets = [g for g in targets if any(g["title"] in w for w in waiting)]
        if retry_targets:
            asyncio.ensure_future(retry_after_cooldown(state, sid, retry_targets, s["message"]))
        state.schedules[sid]["next_send"] = time.time() + s["interval_secs"]
        report = f"Schedule #{sid} fired!\nSent: {len(success)}/{len(targets)}"
        if retry_targets: report += f"\nRetrying {len(retry_targets)} after cooldown"
        if failed:        report += f"\nFailed: {len(failed)}"
        try:
            await client.send_message(owner_id, report)
        except Exception:
            pass


# ── BOT KEEPALIVE ─────────────────────────────────────────────────────────────

async def _bot_keepalive(client, label="Bot"):
    print(f"[INFO] {label} forwarder listener started")
    await client.run_until_disconnected()


# ── BOT MESSAGE HANDLER ───────────────────────────────────────────────────────

def make_bot_handler(state, label):
    """Create a message handler bound to this bot's state (groups, targets, schedules)."""

    async def handle_message(event):
        global owner_id

        try:
            sender = await event.get_sender()
            print(f"[{label}] From {sender.id}: {(event.text or '')[:40]}")
            if owner_id is None:
                owner_id = sender.id
            elif sender.id != owner_id:
                await event.reply("Not authorized.")
                return
        except Exception as e:
            print(f"[{label}] Error: {e}")
            return

        client = state.client
        uid  = sender.id
        text = (event.message.text or "").strip()
        msg  = event.message
        conv_state = state.user_state.get(uid, {}).get("state")

        # ── Conversation states (must check BEFORE commands) ──
        if conv_state == "awaiting_targets":
            del state.user_state[uid]
            if text.lower() == "all":
                state.targets = None
                save_targets(state)
                await event.reply(f"Done - sending to all {len(state.groups)} groups.")
            else:
                selected = []
                for part in text.replace(" ", "").split(","):
                    if part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(state.groups):
                            selected.append(state.groups[idx])
                if not selected:
                    await event.reply("No valid numbers. Try /settargets again.")
                    return
                state.targets = selected
                save_targets(state)
                names = "\n".join([f"- {g['title']}" for g in state.targets])
                await event.reply(f"Done! Sending to {len(state.targets)} group(s):\n\n{names}")
            return

        if conv_state == "awaiting_schedule_message":
            interval_secs = state.user_state[uid]["data"]["interval_secs"]
            del state.user_state[uid]
            state.counter += 1
            sid = state.counter
            state.schedules[sid] = {"message": text, "interval_secs": interval_secs,
                              "next_send": time.time() + 5, "task": None}
            state.schedules[sid]["task"] = asyncio.ensure_future(run_schedule(state, sid))
            await event.reply(f"Schedule #{sid} created!\nEvery {fmt_time(interval_secs)}\n"
                              f"Groups: {len(get_send_targets(state))}\nMessage: {text[:80]}")
            return

        # ── Commands ──
        if text in ("/start", "/help"):
            await event.reply(
                f"Forwarder Bot ({label})\n\n"
                "BASIC\nSend any message/photo/video to forward to groups.\n\n"
                "SCHEDULES\n"
                "/schedule 1h - repeat every 1 hour\n"
                "/schedule 30m Your message - every 30 min\n"
                "/schedules - list active schedules\n"
                "/cancel 1 - cancel schedule #1\n"
                "/cancelall - cancel all\n\n"
                "TARGETS\n"
                "/settargets - pick groups for scheduled messages\n"
                "/targets - see current targets\n"
                "/cleartargets - reset to all groups\n\n"
                "DELETE\n/delete - delete last bot message from target groups\n\n"
                "MODERATION\n"
                "/kickbots - kick all bots from all groups\n\n"
                "OTHER\n"
                "/groups - list groups\n"
                "/refresh - reload group list\n"
                "/cooldowns - check cooldown timers"
            )
            return

        if text == "/groups":
            if not state.groups:
                await event.reply("No groups. Use /refresh.")
                return
            lines = [f"{i}. {g['title']}" for i, g in enumerate(state.groups, 1)]
            await event.reply(f"Groups ({len(state.groups)}):\n\n" + "\n".join(lines))
            return

        if text == "/refresh":
            await event.reply("Refreshing...")
            await fetch_bot_groups(state, label)
            load_targets(state)
            await event.reply(f"Done! Found {len(state.groups)} group(s).")
            return

        if text == "/cooldowns":
            if not state.groups:
                await event.reply("No groups loaded.")
                return
            lines = []
            for g in state.groups:
                wait = group_cooldowns.get(g["entity"].id, 0) - time.time()
                lines.append(f"{'⳿ ' + fmt_time(wait) if wait > 0 else '✅ Ready'} - {g['title']}")
            await event.reply("Cooldowns:\n\n" + "\n".join(lines))
            return

        if text == "/settargets":
            if not state.groups:
                await event.reply("No groups. Use /refresh first.")
                return
            lines = ["Reply with numbers (comma separated).\nExample: 1,3,5\nOr 'all' for all groups.\n"]
            for i, g in enumerate(state.groups, 1):
                lines.append(f"{i}. {g['title']}")
            state.user_state[uid] = {"state": "awaiting_targets"}
            await event.reply("\n".join(lines))
            return

        if text == "/targets":
            if state.targets is None:
                await event.reply(f"Sending to ALL {len(state.groups)} groups.")
            else:
                names = "\n".join([f"- {g['title']}" for g in state.targets])
                await event.reply(f"Sending to {len(state.targets)} group(s):\n\n{names}")
            return

        if text == "/cleartargets":
            state.targets = None
            save_targets(state)
            await event.reply(f"Reset - sending to all {len(state.groups)} groups.")
            return

        if text == "/delete":
            targets = get_send_targets(state)
            if not targets:
                await event.reply("No groups.")
                return
            await event.reply(f"Deleting from {len(targets)} group(s)...")
            deleted, failed = await delete_from_groups_fwd(state, targets)
            report = f"Deleted from {len(deleted)} group(s)."
            if failed: report += "\nFailed:\n" + "\n".join(failed)
            await event.reply(report)
            return

        if text == "/schedules":
            active = {k: v for k, v in state.schedules.items() if isinstance(k, int)}
            if not active:
                await event.reply("No active schedules.")
                return
            lines = [f"#{sid} every {fmt_time(s['interval_secs'])} - next in "
                     f"{fmt_time(max(0, s['next_send'] - time.time()))}\n  {s['message'][:50]}"
                     for sid, s in active.items()]
            await event.reply("Active schedules:\n\n" + "\n\n".join(lines))
            return

        if text.startswith("/cancel "):
            try:
                sid = int(text.split()[1])
                if sid in state.schedules:
                    t = state.schedules[sid].get("task")
                    if t: t.cancel()
                    del state.schedules[sid]
                    await event.reply(f"Schedule #{sid} cancelled.")
                else:
                    await event.reply(f"No schedule #{sid}.")
            except Exception:
                await event.reply("Usage: /cancel 1")
            return

        if text == "/cancelall":
            for s in list(state.schedules.values()):
                if isinstance(s, dict):
                    t = s.get("task")
                    if t: t.cancel()
            state.schedules.clear()
            await event.reply("All schedules cancelled.")
            return

        if text.startswith("/schedule"):
            parts = text[len("/schedule"):].strip()
            if not parts:
                await event.reply("Example: /schedule 1h or /schedule 30m Your message")
                return
            first = parts.split()[0]
            interval_secs = parse_interval(first)
            if not interval_secs:
                await event.reply("Example: /schedule 1h or /schedule 30m Your message")
                return
            rest = parts[len(first):].strip()
            if rest:
                state.counter += 1
                sid = state.counter
                state.schedules[sid] = {"message": rest, "interval_secs": interval_secs,
                                  "next_send": time.time() + 5, "task": None}
                state.schedules[sid]["task"] = asyncio.ensure_future(run_schedule(state, sid))
                await event.reply(f"Schedule #{sid} created!\nEvery {fmt_time(interval_secs)}\n"
                                  f"Groups: {len(get_send_targets(state))}\nMessage: {rest[:80]}")
            else:
                state.user_state[uid] = {"state": "awaiting_schedule_message", "data": {"interval_secs": interval_secs}}
                await event.reply(f"Interval: {fmt_time(interval_secs)}.\nNow send the message to repeat.")
            return

        if text == "/kickbots":
            await event.reply("Scanning for bots to kick...")
            kicked = []
            failed = []
            for g in state.groups:
                try:
                    async for member in client.iter_participants(g["entity"]):
                        if member.bot and member.id != (await client.get_me()).id:
                            try:
                                await client.kick_participant(g["entity"], member)
                                kicked.append(f"{g['title']}: @{member.username or member.id}")
                                await asyncio.sleep(1)
                            except Exception as e:
                                failed.append(f"{g['title']}: @{member.username or member.id} - {str(e)[:40]}")
                except Exception as e:
                    failed.append(f"{g['title']}: {str(e)[:50]}")
            report = f"Kicked {len(kicked)} bot(s)."
            if kicked:  report += "\n\nKicked:\n" + "\n".join(kicked)
            if failed:  report += "\n\nFailed:\n" + "\n".join(failed)
            await event.reply(report)
            return

        # ── Regular message - forward once ──
        targets = get_send_targets(state)
        if not targets:
            await event.reply("No groups. Use /refresh first.")
            return
        await event.reply(f"Forwarding to {len(targets)} group(s)...")
        success, failed, waiting = await send_to_groups_fwd(state, targets, text, media=msg.media if msg.media else None)
        report = f"Sent to {len(success)}/{len(targets)} groups."
        if waiting: report += f"\nSkipped (cooldown): {len(waiting)}"
        if failed:  report += "\nFailed:\n" + "\n".join(failed)
        await event.reply(report)

    return handle_message


def make_new_member_handler(state, label):
    async def handle_new_member(event):
        """Auto-kick any bot that joins a group, silently."""
        try:
            me = await state.client.get_me()
            for user in event.users:
                if user.bot and user.id != me.id:
                    try:
                        await state.client.kick_participant(event.chat_id, user)
                        print(f"[{label}] Kicked bot @{user.username or user.id}")
                    except Exception as e:
                        print(f"[{label}] Failed to kick: {e}")
        except Exception as e:
            print(f"[{label}] Error: {e}")
    return handle_new_member

# Register handlers for both bots
bot_client.add_event_handler(make_bot_handler(bot1_state, "Bot1"), events.NewMessage(incoming=True))
bot_client2.add_event_handler(make_bot_handler(bot2_state, "Bot2"), events.NewMessage(incoming=True))
bot_client.add_event_handler(make_new_member_handler(bot1_state, "Bot1"), events.ChatAction())
bot_client2.add_event_handler(make_new_member_handler(bot2_state, "Bot2"), events.ChatAction())


# ── GROUP PANEL ───────────────────────────────────────────────────────────────

class GroupPanel(tk.Frame):
    def __init__(self, parent, label, color, app, **kwargs):
        super().__init__(parent, bg=DARK, **kwargs)
        self.app             = app
        self.label           = label
        self.color           = color
        self.groups          = []
        self.check_vars      = []
        self.checkbuttons    = []
        self.cooldown_labels = []
        self.timer_mins      = []
        self.timer_secs      = []
        self.repeat_vars     = {}
        self.repeat_intervals = {}
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=self.color, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        self.label_lbl = tk.Label(hdr, text=self.label, font=("Segoe UI", 10, "bold"),
                 bg=self.color, fg="white")
        self.label_lbl.pack(side="left", padx=10)
        self.status_lbl = tk.Label(hdr, text="Connecting...",
                                   font=("Segoe UI", 8), bg=self.color, fg="#ddd")
        self.status_lbl.pack(side="right", padx=8)

        btn_row = tk.Frame(self, bg=DARK)
        btn_row.pack(fill="x", pady=(4, 2))
        btn_s = {"font": ("Segoe UI", 8), "bg": PANEL, "fg": MUTED,
                 "relief": "flat", "cursor": "hand2", "padx": 6, "pady": 2}
        tk.Button(btn_row, text="Select All",       command=self._select_all,       **btn_s).pack(side="right", padx=(2,0))
        tk.Button(btn_row, text="Deselect All",     command=self._deselect_all,     **btn_s).pack(side="right", padx=2)
        tk.Button(btn_row, text="Clear All Timers", command=self._clear_all_timers, **btn_s).pack(side="right", padx=2)
        tk.Button(btn_row, text="Set All Timers",   command=self._set_all_timers,   **btn_s).pack(side="right", padx=2)

        gt = tk.Frame(self, bg=DARK)
        gt.pack(fill="x", padx=4, pady=(0, 2))
        tk.Label(gt, text="Set all to:", font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(side="left", padx=(0,4))
        self.global_h = tk.IntVar(value=0)
        self.global_m = tk.IntVar(value=0)
        self.global_s = tk.IntVar(value=0)
        self.global_repeat = tk.BooleanVar(value=False)
        sp = {"bg": "#3a3a5e", "fg": FG, "buttonbackground": "#4a4a6e", "relief": "flat", "font": ("Segoe UI", 9), "width": 3}
        tk.Spinbox(gt, from_=0, to=23, textvariable=self.global_h, **sp).pack(side="left")
        tk.Label(gt, text="h", font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(side="left", padx=(1,4))
        tk.Spinbox(gt, from_=0, to=59, textvariable=self.global_m, **sp).pack(side="left")
        tk.Label(gt, text="m", font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(side="left", padx=(1,4))
        tk.Spinbox(gt, from_=0, to=59, textvariable=self.global_s, **sp).pack(side="left")
        tk.Label(gt, text="s", font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(side="left", padx=(1,6))
        tk.Checkbutton(gt, text="Repeat", variable=self.global_repeat,
                       bg=DARK, fg=MUTED, selectcolor="#3a3a5e", activebackground=DARK,
                       activeforeground=FG, relief="flat", font=("Segoe UI", 8), cursor="hand2"
                       ).pack(side="left")

        sf = tk.Frame(self, bg=PANEL)
        sf.pack(fill="x", padx=4, pady=(0, 2))
        tk.Label(sf, text="🔍", bg=PANEL).pack(side="left", padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        tk.Entry(sf, textvariable=self.search_var, font=("Segoe UI", 9),
                 bg=PANEL, fg=FG, insertbackground=FG, relief="flat", bd=0
                 ).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(sf, text="✕", font=("Segoe UI", 8), bg=PANEL, fg=MUTED,
                  relief="flat", cursor="hand2",
                  command=lambda: self.search_var.set("")).pack(side="right", padx=2)

        list_outer = tk.Frame(self, bg=PANEL)
        list_outer.pack(fill="both", expand=True, padx=4)
        self.canvas = tk.Canvas(list_outer, bg=PANEL, highlightthickness=0)
        sb = tk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        self.checkbox_frame = tk.Frame(self.canvas, bg=PANEL)
        self.checkbox_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>",
            lambda ev: self.canvas.yview_scroll(int(-1*(ev.delta/120)), "units")))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.loading_lbl = tk.Label(self.checkbox_frame, text="Loading...",
                                    font=("Segoe UI", 9), bg=PANEL, fg=MUTED)
        self.loading_lbl.pack(pady=10)

    def populate(self, groups):
        self.groups          = groups
        self.check_vars      = []
        self.checkbuttons    = []
        self.cooldown_labels = []
        self.timer_mins      = []
        self.timer_secs      = []
        self.repeat_vars     = {}
        self.repeat_intervals = {}
        for w in self.checkbox_frame.winfo_children():
            w.destroy()

        btn_s = {"bg": "#3a3a5e", "fg": FG, "relief": "flat",
                 "font": ("Segoe UI", 7), "cursor": "hand2", "padx": 4, "pady": 1}

        for g in groups:
            var = tk.BooleanVar(value=False)
            self.check_vars.append(var)
            gf  = tk.Frame(self.checkbox_frame, bg=PANEL)
            gf.pack(fill="x")
            row = tk.Frame(gf, bg=PANEL)
            row.pack(fill="x")
            cb = tk.Checkbutton(row, text=g["title"], variable=var,
                                font=("Segoe UI", 9), bg=PANEL, fg=FG,
                                selectcolor="#3a3a5e", activebackground=PANEL,
                                activeforeground=FG, relief="flat",
                                anchor="w", padx=6, pady=2, cursor="hand2")
            cb.pack(side="left")
            self.checkbuttons.append(cb)
            cd_lbl = tk.Label(row, text="", font=("Segoe UI", 7), bg=PANEL, fg=MUTED, anchor="w")
            cd_lbl.pack(side="left", padx=(2,4))
            self.cooldown_labels.append(cd_lbl)

            sub = tk.Frame(gf, bg=PANEL)
            sub.pack(fill="x", pady=(0,2))
            h_var = tk.IntVar(value=0)
            m_var = tk.IntVar(value=0)
            s_var = tk.IntVar(value=0)
            self.timer_mins.append(m_var)
            self.timer_secs.append(s_var)
            cd_timer = tk.Label(sub, text="", font=("Segoe UI", 7, "bold"),
                                bg=PANEL, fg=YELLOW, width=12, anchor="w")
            cd_timer.pack(side="left", padx=(20,2))
            repeat_var = tk.BooleanVar(value=False)
            self.repeat_vars[g["entity"].id]      = repeat_var
            self.repeat_intervals[g["entity"].id] = 0

            sp = {"bg": "#3a3a5e", "fg": FG, "buttonbackground": "#4a4a6e", "relief": "flat", "font": ("Segoe UI", 8)}
            tk.Label(sub, text="H:", font=("Segoe UI", 7), bg=PANEL, fg=MUTED).pack(side="left")
            tk.Spinbox(sub, from_=0, to=23, textvariable=h_var, width=2, **sp).pack(side="left")
            tk.Label(sub, text="M:", font=("Segoe UI", 7), bg=PANEL, fg=MUTED).pack(side="left", padx=(3,0))
            tk.Spinbox(sub, from_=0, to=59, textvariable=m_var, width=2, **sp).pack(side="left")
            tk.Label(sub, text="S:", font=("Segoe UI", 7), bg=PANEL, fg=MUTED).pack(side="left", padx=(3,0))
            tk.Spinbox(sub, from_=0, to=59, textvariable=s_var, width=2, **sp).pack(side="left")
            tk.Button(sub, text="Set",
                      command=lambda g=g, hv=h_var, mv=m_var, sv=s_var, cl=cd_timer, rv=repeat_var: self._set_timer(g, hv, mv, sv, cl, rv),
                      **btn_s).pack(side="left", padx=(4,1))
            tk.Button(sub, text="Clear",
                      command=lambda g=g, hv=h_var, mv=m_var, sv=s_var, lbl=cd_lbl, cl=cd_timer: self._clear_timer(g, hv, mv, sv, lbl, cl),
                      **btn_s).pack(side="left", padx=1)
            tk.Checkbutton(sub, text="↻", variable=repeat_var,
                           bg=PANEL, fg=MUTED, selectcolor="#3a3a5e",
                           activebackground=PANEL, relief="flat",
                           font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=(3,0))

            # ── Daily-at-clock-time row ──
            sub2 = tk.Frame(gf, bg=PANEL)
            sub2.pack(fill="x", pady=(0,3))
            daily_h = tk.IntVar(value=9)
            daily_m = tk.IntVar(value=0)
            daily_lbl = tk.Label(sub2, text="", font=("Segoe UI", 7, "bold"),
                                 bg=PANEL, fg="#89b4fa", width=12, anchor="w")
            daily_lbl.pack(side="left", padx=(20,2))
            tk.Label(sub2, text="Daily at:", font=("Segoe UI", 7), bg=PANEL, fg=MUTED).pack(side="left", padx=(0,2))
            tk.Spinbox(sub2, from_=0, to=23, textvariable=daily_h, width=2, **sp).pack(side="left")
            tk.Label(sub2, text=":", font=("Segoe UI", 7), bg=PANEL, fg=MUTED).pack(side="left")
            tk.Spinbox(sub2, from_=0, to=59, textvariable=daily_m, width=2, **sp).pack(side="left", padx=(0,4))
            tk.Button(sub2, text="Set Daily",
                      command=lambda g=g, hv=daily_h, mv=daily_m, cl=daily_lbl, rv=repeat_var: self._set_daily(g, hv, mv, cl, rv),
                      **btn_s).pack(side="left", padx=1)
            tk.Button(sub2, text="Clear",
                      command=lambda g=g, lbl=cd_lbl, cl=daily_lbl: self._clear_daily(g, lbl, cl),
                      **btn_s).pack(side="left", padx=1)

            var.trace_add("write", lambda *a, g=g, lbl=cd_lbl: self.app._fetch_cooldown(g, lbl))

        self.app.after(500, lambda: self.app._fetch_all_cooldowns(self))

    def get_selected(self):
        return [g for g, v in zip(self.groups, self.check_vars) if v.get()]

    def _select_all(self):
        for v in self.check_vars: v.set(True)

    def _deselect_all(self):
        for v in self.check_vars: v.set(False)

    def _set_timer(self, g, h_var, m_var, s_var, countdown_lbl, repeat_var=None):
        secs = h_var.get() * 3600 + m_var.get() * 60 + s_var.get()
        if secs > 0:
            entity_id = g["entity"].id
            group_cooldowns[entity_id] = time.time() + secs
            self.repeat_intervals[entity_id] = secs
            self._start_countdown(g, countdown_lbl, repeat_var)

    def _clear_timer(self, g, h_var, m_var, s_var, lbl, countdown_lbl):
        h_var.set(0); m_var.set(0); s_var.set(0)
        group_cooldowns.pop(g["entity"].id, None)
        lbl.config(text="✓ Ready", fg=GREEN)
        countdown_lbl.config(text="")

    def _next_daily_timestamp(self, hour, minute):
        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        return target.timestamp()

    def _set_daily(self, g, h_var, m_var, daily_lbl, repeat_var=None):
        hour, minute = h_var.get(), m_var.get()
        entity_id = g["entity"].id
        target_ts = self._next_daily_timestamp(hour, minute)
        group_cooldowns[entity_id] = target_ts
        self.repeat_intervals[entity_id] = 86400
        if repeat_var:
            repeat_var.set(True)
        self._start_daily_countdown(g, daily_lbl, hour, minute, repeat_var)

    def _clear_daily(self, g, lbl, daily_lbl):
        group_cooldowns.pop(g["entity"].id, None)
        self.repeat_intervals[g["entity"].id] = 0
        lbl.config(text="✓ Ready", fg=GREEN)
        daily_lbl.config(text="")

    def _start_daily_countdown(self, g, daily_lbl, hour, minute, repeat_var=None):
        def tick():
            if not self.app.winfo_exists(): return
            entity_id = g["entity"].id
            remaining = group_cooldowns.get(entity_id, 0) - time.time()
            if remaining > 0:
                daily_lbl.config(text=f"⏰ {fmt_time(remaining)}", fg="#89b4fa")
                self.app.after(1000, tick)
            else:
                daily_lbl.config(text="✅ Sending!", fg=GREEN)
                group_cooldowns[entity_id] = self._next_daily_timestamp(hour, minute)
                self.app._send_daily_message(self, g, daily_lbl, hour, minute, repeat_var)
        tick()

    def _clear_all_timers(self):
        for g in self.groups: group_cooldowns.pop(g["entity"].id, None)
        for lbl in self.cooldown_labels: lbl.config(text="✓ Ready", fg=GREEN)
        for mv in self.timer_mins: mv.set(0)
        for sv in self.timer_secs: sv.set(0)
        for rv in self.repeat_vars.values(): rv.set(False)
        self.app._log("── All timers cleared ──", YELLOW)

    def _set_all_timers(self):
        secs = self.global_h.get()*3600 + self.global_m.get()*60 + self.global_s.get()
        if secs == 0:
            messagebox.showwarning("No time set", "Set hours, minutes or seconds first.")
            return
        count = 0
        for g, v in zip(self.groups, self.check_vars):
            if not v.get(): continue
            entity_id = g["entity"].id
            group_cooldowns[entity_id] = time.time() + secs
            self.repeat_intervals[entity_id] = secs
            rv = self.repeat_vars.get(entity_id)
            if self.global_repeat.get() and rv: rv.set(True)
            idx = self.groups.index(g)
            gframes = [w for w in self.checkbox_frame.winfo_children() if isinstance(w, tk.Frame)]
            if idx < len(gframes):
                subs = [w for w in gframes[idx].winfo_children() if isinstance(w, tk.Frame)]
                if len(subs) > 1:
                    for widget in subs[1].winfo_children():
                        if isinstance(widget, tk.Label) and widget.cget("width") == 12:
                            self._start_countdown(g, widget, rv)
                            break
            count += 1
        self.app._log(f"── Timer set for {count} group(s): {fmt_time(secs)} ──", YELLOW)

    def _start_countdown(self, g, countdown_lbl, repeat_var=None):
        def tick():
            if not self.app.winfo_exists(): return
            entity_id = g["entity"].id
            remaining = group_cooldowns.get(entity_id, 0) - time.time()
            if remaining > 0:
                countdown_lbl.config(text=f"⳿ {fmt_time(remaining)}", fg=YELLOW)
                self.app.after(1000, tick)
            else:
                countdown_lbl.config(text="✅ Sending!", fg=GREEN)
                group_cooldowns.pop(entity_id, None)
                self.app._send_timer_message(self, g, countdown_lbl, repeat_var)
        tick()

    def _on_search(self, *args):
        query = self.search_var.get().lower()
        for cb, g in zip(self.checkbuttons, self.groups):
            gf = cb.master.master
            if query in g["title"].lower(): gf.pack(fill="x")
            else: gf.pack_forget()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


# ── MAIN APP ──────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Telegram Reminder")
        self.geometry("1300x900")
        self.resizable(True, True)
        self.configure(bg=DARK)
        self.loop       = asyncio.new_event_loop()
        self._stop_user = None
        self._stop_bot1 = None
        self._stop_bot2 = None
        self._active_tab = "user"
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._start_loop, daemon=True).start()
        self._auto_start = "--auto" in sys.argv
        self.after(300, self._login)
        self.after(60000, self._auto_save)

    def _auto_save(self):
        self._save_prefs()
        self.after(60000, self._auto_save)

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _add_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0, bg=PANEL, fg=FG,
                       activebackground=ACCENT, activeforeground="white",
                       relief="flat", bd=0)
        menu.add_command(label="Cut",        command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",       command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste",      command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.tag_add("sel", "1.0", "end"))
        menu.add_command(label="Clear",      command=lambda: widget.delete("1.0", "end"))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _build_format_toolbar(self, parent, row, col, box_id):
        toolbar = tk.Frame(parent, bg=DARK)
        toolbar.grid(row=row, column=col, sticky="w", pady=(2,2),
                     padx=(0,4) if col==0 else (4,0))
        btn_s = {"font": ("Segoe UI", 8, "bold"), "relief": "flat", "cursor": "hand2",
                 "padx": 6, "pady": 2, "bg": PANEL, "fg": FG,
                 "activebackground": "#3a3a5e", "activeforeground": FG}
        formats = [
            ("Bold",    "**{}**"),
            ("Italic",  "__{}__"),
            ("Strike",  "~~{}~~"),
            ("Spoiler", "||{}||"),
            ("Mono",    "`{}`"),
            ("Code",    "```\n{}\n```"),
        ]
        for label, fmt in formats:
            tk.Button(toolbar, text=label, **btn_s,
                      command=lambda f=fmt, b=box_id: self._apply_format(f, b)
                      ).pack(side="left", padx=1)

    def _apply_format(self, fmt, box_id):
        box = self.msg_box if box_id == "msg" else self.timer_msg_box
        try:
            sel = box.get("sel.first", "sel.last")
            box.delete("sel.first", "sel.last")
            box.insert("insert", fmt.format(sel))
        except tk.TclError:
            box.insert("insert", fmt.format("text"))

    def _build_ui(self):
        hdr = tk.Frame(self, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✈  Telegram Reminder", font=("Segoe UI", 13, "bold"),
                 bg=ACCENT, fg="white").pack(side="left", padx=16)
        tk.Button(hdr, text="💾 Save Settings", font=("Segoe UI", 9),
                  bg="#6a5ae0", fg="white", relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=lambda: self._save_prefs(show_confirmation=True)
                  ).pack(side="right", padx=(0,4))
        tk.Button(hdr, text="📂 Save Session", font=("Segoe UI", 9),
                  bg="#6a5ae0", fg="white", relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._save_session_as
                  ).pack(side="right", padx=(0,4))
        self.session_btn = tk.Button(hdr, text="🔄 Load Session", font=("Segoe UI", 9),
                  bg="#6a5ae0", fg="white", relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._show_session_menu)
        self.session_btn.pack(side="right", padx=(12,4))
        tk.Button(hdr, text="⚙ Settings", font=("Segoe UI", 9),
                  bg="#6a5ae0", fg="white", relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._open_account_settings
                  ).pack(side="right", padx=(0,4))
        tk.Button(hdr, text="🔒 Proxy", font=("Segoe UI", 9),
                  bg="#6a5ae0", fg="white", relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._open_proxy_settings
                  ).pack(side="right", padx=(0,4))


        self.tab_bar = tk.Frame(self, bg=DARK)
        self.tab_bar.pack(fill="x", padx=8, pady=(8,0))

        self._tab_defs = [
            ("user", "👤  User Mode", "#5a4ad0"),
            ("bot1", "🤖  Bot 1",      "#2a7a2a"),
            ("bot2", "🤖  Bot 2",      "#d08a2a"),
        ]
        self._tab_buttons = {}
        for key, label, color in self._tab_defs:
            btn = tk.Button(self.tab_bar, text=label, font=("Segoe UI", 10, "bold"),
                            relief="flat", cursor="hand2", padx=16, pady=8,
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side="left", padx=(0,2))
            self._tab_buttons[key] = (btn, color)

        self._user_tab_hidden = False
        self.toggle_user_tab_btn = tk.Button(self.tab_bar, text="Hide User Mode",
            font=("Segoe UI", 9), bg=PANEL, fg=MUTED, relief="flat",
            cursor="hand2", padx=10, pady=8, command=self._toggle_user_tab)
        self.toggle_user_tab_btn.pack(side="right", padx=(2,0))

        panel_container = tk.Frame(self, bg=DARK)
        panel_container.pack(fill="both", expand=True, padx=8, pady=(0,8))

        self.user_panel = GroupPanel(panel_container, "👤  User Mode", "#5a4ad0", self)
        self.bot_panel  = GroupPanel(panel_container, "🤖  Bot 1 - @???",  "#2a7a2a", self)
        self.bot_panel2 = GroupPanel(panel_container, "🤖  Bot 2 - @???",  "#d08a2a", self)
        self._panel_container = panel_container
        self._panels = {"user": self.user_panel, "bot1": self.bot_panel, "bot2": self.bot_panel2}

        self._switch_tab("user")

        opts = tk.Frame(self, bg=DARK)
        opts.pack(fill="x", padx=16, pady=(0,4))
        self.opt_respect = tk.BooleanVar(value=True)
        self.opt_restart = tk.BooleanVar(value=True)
        cb_s = {"bg": DARK, "fg": MUTED, "selectcolor": "#3a3a5e",
                "activebackground": DARK, "activeforeground": FG,
                "relief": "flat", "font": ("Segoe UI", 9), "cursor": "hand2"}
        tk.Checkbutton(opts, text="Respect each group's timer before sending",
                       variable=self.opt_respect, **cb_s).pack(side="left", padx=(0,16))
        tk.Checkbutton(opts, text="After sending, restart timer using detected delay",
                       variable=self.opt_restart, **cb_s).pack(side="left")

        msg_frame = tk.Frame(self, bg=DARK)
        msg_frame.pack(fill="x", padx=16)
        msg_frame.columnconfigure(0, weight=1)
        msg_frame.columnconfigure(1, weight=1)

        tk.Label(msg_frame, text="Message", font=("Segoe UI", 10, "bold"),
                 bg=DARK, fg=FG).grid(row=0, column=0, sticky="w")
        self._build_format_toolbar(msg_frame, 1, 0, "msg")
        self.msg_box = scrolledtext.ScrolledText(msg_frame, height=12,
            font=("Segoe UI", 10), bg=PANEL, fg=FG, insertbackground=FG,
            relief="flat", bd=0, wrap="word", padx=6, pady=4)
        self.msg_box.grid(row=2, column=0, sticky="ew", padx=(0,4))
        self._add_context_menu(self.msg_box)

        tk.Label(msg_frame, text="Timer Message", font=("Segoe UI", 10, "bold"),
                 bg=DARK, fg=YELLOW).grid(row=0, column=1, sticky="w")
        self._build_format_toolbar(msg_frame, 1, 1, "timer")
        self.timer_msg_box = scrolledtext.ScrolledText(msg_frame, height=12,
            font=("Segoe UI", 10), bg=PANEL, fg=FG, insertbackground=FG,
            relief="flat", bd=0, wrap="word", padx=6, pady=4)
        self.timer_msg_box.grid(row=2, column=1, sticky="ew", padx=(4,0))
        self._add_context_menu(self.timer_msg_box)

        mgmt_bar = tk.Frame(self, bg=DARK)
        mgmt_bar.pack(fill="x", padx=16, pady=(6,0))
        btn_s = {"font": ("Segoe UI", 9), "bg": PANEL, "fg": FG,
                 "relief": "flat", "cursor": "hand2", "padx": 10, "pady": 4}
        tk.Button(mgmt_bar, text="💾 Save Template",
                  command=self._save_template, **btn_s).pack(side="left", padx=(0,4))
        self.history_btn = tk.Button(mgmt_bar, text="⏱ History",
                  command=self._show_history, **btn_s)
        self.history_btn.pack(side="left", padx=4)
        tk.Button(mgmt_bar, text="👁 Preview",
                  command=self._preview_message, **btn_s).pack(side="left", padx=4)

        tmpl_row = tk.Frame(self, bg=DARK)
        tmpl_row.pack(fill="x", padx=16, pady=(4,0))
        tk.Label(tmpl_row, text="Templates:", font=("Segoe UI", 8),
                 bg=DARK, fg=MUTED).pack(side="left", padx=(0,6))
        self.template_btn_frame = tk.Frame(tmpl_row, bg=DARK)
        self.template_btn_frame.pack(side="left", fill="x", expand=True)
        self._refresh_templates()

        btn_row = tk.Frame(self, bg=DARK)
        btn_row.pack(fill="x", padx=16, pady=8)
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)
        btn_row.columnconfigure(3, weight=1)
        self.user_send_btn = tk.Button(btn_row, text="Send (User)",
            font=("Segoe UI", 10, "bold"), bg="#5a4ad0", fg="white",
            relief="flat", activebackground="#4a3ac0", pady=8, cursor="hand2",
            command=lambda: self._on_send("user"))
        self.user_send_btn.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.bot1_send_btn = tk.Button(btn_row, text="Send (Bot 1)",
            font=("Segoe UI", 10, "bold"), bg="#2a7a2a", fg="white",
            relief="flat", activebackground="#1a6a1a", pady=8, cursor="hand2",
            command=lambda: self._on_send("bot1"))
        self.bot1_send_btn.grid(row=0, column=1, sticky="ew", padx=4)
        self.bot2_send_btn = tk.Button(btn_row, text="Send (Bot 2)",
            font=("Segoe UI", 10, "bold"), bg="#d08a2a", fg="white",
            relief="flat", activebackground="#a06a1a", pady=8, cursor="hand2",
            command=lambda: self._on_send("bot2"))
        self.bot2_send_btn.grid(row=0, column=2, sticky="ew", padx=4)
        self.send_all_btn = tk.Button(btn_row, text="⚡ Send All (Bots)",
            font=("Segoe UI", 10, "bold"), bg=ACCENT, fg="white",
            relief="flat", activebackground="#6a5ad0", pady=8, cursor="hand2",
            command=self._on_send_all)
        self.send_all_btn.grid(row=0, column=3, sticky="ew", padx=(4,0))

        self.log_box = scrolledtext.ScrolledText(self, height=8,
            font=("Segoe UI", 9), bg="#11111b", fg=GREEN,
            relief="flat", bd=0, state="disabled", padx=8, pady=4)
        self.log_box.tag_config("green",  foreground=GREEN)
        self.log_box.tag_config("red",    foreground=RED)
        self.log_box.tag_config("yellow", foreground=YELLOW)
        self.log_box.pack(fill="x", padx=16, pady=(0,10))

    def _switch_tab(self, key):
        if key == "user" and getattr(self, "_user_tab_hidden", False):
            key = "bot1"
        self._active_tab = key
        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
            else:
                panel.pack_forget()
        for k, (btn, color) in self._tab_buttons.items():
            if k == key:
                btn.config(bg=color, fg="white")
            else:
                btn.config(bg=PANEL, fg=MUTED)

    def _toggle_user_tab(self):
        self._user_tab_hidden = not self._user_tab_hidden
        user_btn, _ = self._tab_buttons["user"]
        if self._user_tab_hidden:
            user_btn.pack_forget()
            self.toggle_user_tab_btn.config(text="Show User Mode")
            if self._active_tab == "user":
                self._switch_tab("bot1")
        else:
            user_btn.pack(side="left", padx=(0,2), before=self.tab_bar.winfo_children()[0])
            self.toggle_user_tab_btn.config(text="Hide User Mode")

    def _login(self):
        async def do_login():
            global owner_id
            try:
                await user_client.start(phone=lambda: PHONE)
                me   = await user_client.get_me()
                owner_id = me.id
                name = f"@{me.username}" if me.username else me.first_name or "Unknown"
                print(f"[INFO] Owner id set: {owner_id}")
                self.after(0, lambda: self.user_panel.status_lbl.config(text=f"✓ {name}"))
                ugroups = await fetch_user_groups()
                self.after(0, lambda: self.user_panel.populate(ugroups))
                self.after(100, lambda: self._load_prefs(self.user_panel, "user_checked"))
            except Exception as e:
                self.after(0, lambda err=str(e): self.user_panel.status_lbl.config(text=f"❌ {err}"))

            tasks = [self._login_bot(bot_client, BOT_TOKEN, bot1_state, self.bot_panel, "bot1", "Bot 1")]
            if BOT_TOKEN2:
                tasks.append(self._login_bot(bot_client2, BOT_TOKEN2, bot2_state, self.bot_panel2, "bot2", "Bot 2"))
            else:
                self.after(0, lambda: self.bot_panel2.status_lbl.config(text="No token set"))
            await asyncio.gather(*tasks)

        self._run(do_login())

    async def _login_bot(self, client, token, state, panel, auto_key, label):
        try:
            await client.start(bot_token=token)
            bot_me = await client.get_me()
            self.after(0, lambda: panel.status_lbl.config(text=f"✓ @{bot_me.username}"))
            self.after(0, lambda: panel.label_lbl.config(text=f"🤖  {label} - @{bot_me.username}"))
            await asyncio.sleep(8)
            groups = await fetch_bot_groups(state, label)
            self.after(0, lambda: panel.populate(groups))
            self.after(100, lambda: self._load_prefs(panel, f"{auto_key}_checked"))
            load_targets(state)
            self.loop.create_task(_bot_keepalive(client, label))
            if self._auto_start and groups:
                self.after(2000, lambda: self._auto_start_all(auto_key))
            await asyncio.sleep(20)
            groups2 = await fetch_bot_groups(state, label)
            if len(groups2) > len(groups):
                self.after(0, lambda: panel.populate(groups2))
            if self._auto_start:
                self.after(2000, lambda: self._auto_start_all(auto_key))
        except Exception as e:
            self.after(0, lambda err=str(e): panel.status_lbl.config(text=f"❌ {err}"))

    def _fetch_cooldown(self, g, lbl):
        async def check():
            wait_until = group_cooldowns.get(g["entity"].id, 0)
            remaining  = wait_until - time.time()
            if remaining > 0:
                self.after(0, lambda: lbl.config(text=f"⳿ {fmt_time(remaining)}", fg=YELLOW))
            else:
                self.after(0, lambda: lbl.config(text="✓ Ready", fg=GREEN))
        self._run(check())

    def _fetch_all_cooldowns(self, panel):
        async def check_all():
            for g, lbl in zip(panel.groups, panel.cooldown_labels):
                if not self.winfo_exists(): break
                wait_until = group_cooldowns.get(g["entity"].id, 0)
                remaining  = wait_until - time.time()
                if remaining > 0:
                    self.after(0, lambda lbl=lbl, r=remaining: lbl.config(
                        text=f"⳿ {fmt_time(r)}", fg=YELLOW))
                else:
                    self.after(0, lambda lbl=lbl: lbl.config(text="✓ Ready", fg=GREEN))
                await asyncio.sleep(0.3)
        self._run(check_all())

    def _client_for_panel(self, panel):
        if panel is self.bot_panel:  return bot_client
        if panel is self.bot_panel2: return bot_client2
        return user_client

    def _send_timer_message(self, panel, g, countdown_lbl, repeat_var=None):
        timer_msg = self.timer_msg_box.get("1.0", "end").strip()
        if not timer_msg:
            self.after(1000, lambda: countdown_lbl.config(text=""))
            return
        entity_id = g["entity"].id
        interval  = panel.repeat_intervals.get(entity_id, 0)
        cli = self._client_for_panel(panel)
        async def do_send():
            try:
                await cli.send_message(g["entity"], timer_msg, parse_mode="md")
                self.after(0, lambda: self._log(f"✓  Timer fired - {g['title']}", GREEN))
            except Exception as e:
                self.after(0, lambda err=str(e): self._log(f"✗  Timer send failed - {g['title']} - {err}", RED))
            if repeat_var and repeat_var.get() and interval > 0:
                group_cooldowns[entity_id] = time.time() + interval
                self.after(0, lambda: panel._start_countdown(g, countdown_lbl, repeat_var))
            else:
                self.after(0, lambda: countdown_lbl.config(text=""))
        self._run(do_send())

    def _send_daily_message(self, panel, g, daily_lbl, hour, minute, repeat_var=None):
        timer_msg = self.timer_msg_box.get("1.0", "end").strip()
        if not timer_msg:
            self.after(1000, lambda: daily_lbl.config(text=""))
            return
        cli = self._client_for_panel(panel)
        async def do_send():
            try:
                await cli.send_message(g["entity"], timer_msg, parse_mode="md")
                self.after(0, lambda: self._log(f"✓  Daily message fired - {g['title']}", GREEN))
            except Exception as e:
                self.after(0, lambda err=str(e): self._log(f"✗  Daily send failed - {g['title']} - {err}", RED))
            self.after(0, lambda: panel._start_daily_countdown(g, daily_lbl, hour, minute, repeat_var))
        self._run(do_send())

    def _log(self, text, color=None):
        tag = {"#a6e3a1": "green", "#f38ba8": "red", "#f9e2af": "yellow"}.get(color, "green")
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _mode_config(self, mode):
        if mode == "user":
            return (self.user_panel, self.user_send_btn, "_stop_user",
                    user_client, "#5a4ad0", "User", "Send (User)")
        if mode == "bot1":
            return (self.bot_panel, self.bot1_send_btn, "_stop_bot1",
                    bot_client, "#2a7a2a", "Bot 1", "Send (Bot 1)")
        if mode == "bot2":
            return (self.bot_panel2, self.bot2_send_btn, "_stop_bot2",
                    bot_client2, "#d08a2a", "Bot 2", "Send (Bot 2)")
        raise ValueError(mode)

    def _start_send(self, mode, message, silent_if_empty=False):
        panel, btn, stop_attr, cli, color, dlabel, orig_text = self._mode_config(mode)
        stop_event = getattr(self, stop_attr)
        if stop_event and not stop_event.is_set():
            stop_event.set()
            btn.config(bg="#555", text="Stopping...", state="disabled")
            return False
        targets = panel.get_selected()
        if not targets:
            if silent_if_empty:
                self._log(f"── [{dlabel.upper()}] Skipped - no groups selected ──", YELLOW)
            else:
                messagebox.showwarning("No groups", f"Select at least one group in {dlabel}.")
            return False
        new_stop = asyncio.Event()
        setattr(self, stop_attr, new_stop)
        btn.config(bg="#e05a5a", text=f"⏹ Stop ({dlabel})", state="normal", activebackground="#c04040")
        self._log(f"── [{dlabel.upper()}] Loop started - {len(targets)} group(s) ──", YELLOW)
        def done_cb(success, total):
            self.after(0, lambda: self._log(f"── [{dlabel.upper()}] Loop stopped ──", YELLOW))
            self.after(0, lambda: btn.config(state="normal", text=orig_text,
                                              bg=color, activebackground=color))
            setattr(self, stop_attr, None)
        self._run(send_messages(
            cli, targets, message,
            lambda t, c: self.after(0, lambda t=t, c=c: self._log(t, c)),
            done_cb,
            respect_timers=self.opt_respect.get(),
            restart_timer=self.opt_restart.get(),
            stop_event=new_stop
        ))
        return True

    def _on_send(self, mode):
        panel, btn, stop_attr, cli, color, dlabel, orig_text = self._mode_config(mode)
        stop_event = getattr(self, stop_attr)
        if stop_event and not stop_event.is_set():
            self._start_send(mode, "")
            return
        targets = panel.get_selected()
        message = self.msg_box.get("1.0", "end").strip()
        if not targets:
            messagebox.showwarning("No groups", f"Select at least one group in {dlabel}.")
            return
        if not message:
            messagebox.showwarning("No message", "Type a message first.")
            return
        self._add_to_history(message)
        if not messagebox.askyesno("Confirm",
                f"Send to {len(targets)} group(s) via {dlabel} - loop until stopped?\n\n{message[:200]}"):
            return
        self._start_send(mode, message)

    def _on_send_all(self):
        message = self.msg_box.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("No message", "Type a message first.")
            return
        targets1 = self.bot_panel.get_selected()
        targets2 = self.bot_panel2.get_selected()
        if not targets1 and not targets2:
            messagebox.showwarning("No groups", "Select at least one group in Bot 1 and/or Bot 2.")
            return
        total = len(targets1) + len(targets2)
        if not messagebox.askyesno("Confirm",
                f"Send to {len(targets1)} group(s) via Bot 1 and {len(targets2)} group(s) via Bot 2 "
                f"({total} total) - loop until stopped?\n\n{message[:200]}"):
            return
        self._add_to_history(message)
        self._start_send("bot1", message, silent_if_empty=True)
        self._start_send("bot2", message, silent_if_empty=True)

    # ── TEMPLATES ─────────────────────────────────────────────────────────────

    def _load_templates(self):
        try:
            with open(TEMPLATES, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_templates_file(self, templates):
        with open(TEMPLATES, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

    def _save_template(self):
        msg = self.msg_box.get("1.0", "end").strip()
        if not msg:
            messagebox.showwarning("Empty", "Type a message first.")
            return
        win = tk.Toplevel(self)
        win.title("Save Template")
        win.geometry("320x120")
        win.configure(bg=DARK)
        win.grab_set()
        tk.Label(win, text="Template name:", font=("Segoe UI", 10),
                 bg=DARK, fg=FG).pack(pady=(16,4))
        entry = tk.Entry(win, font=("Segoe UI", 10), bg=PANEL, fg=FG,
                         insertbackground=FG, relief="flat", bd=0)
        entry.pack(fill="x", padx=20, ipady=5)
        entry.focus()
        def save():
            name = entry.get().strip()
            if not name: return
            templates = self._load_templates()
            templates[name] = msg
            self._save_templates_file(templates)
            self._refresh_templates()
            win.destroy()
        tk.Button(win, text="Save", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", pady=6,
                  command=save).pack(fill="x", padx=20, pady=10)
        win.bind("<Return>", lambda e: save())

    def _refresh_templates(self):
        for w in self.template_btn_frame.winfo_children():
            w.destroy()
        templates = self._load_templates()
        if not templates:
            tk.Label(self.template_btn_frame, text="No templates saved yet.",
                     font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(side="left", padx=4)
            return
        for name, msg in templates.items():
            btn = tk.Button(self.template_btn_frame, text=name,
                            font=("Segoe UI", 9), bg=PANEL, fg=FG,
                            relief="flat", cursor="hand2", padx=8, pady=3,
                            command=lambda m=msg: self._load_template(m))
            btn.pack(side="left", padx=2)
            btn.bind("<Button-3>", lambda e, n=name: self._delete_template(n))

    def _load_template(self, msg):
        self.msg_box.delete("1.0", "end")
        self.msg_box.insert("1.0", msg)

    def _delete_template(self, name):
        if messagebox.askyesno("Delete", f"Delete template '{name}'?"):
            templates = self._load_templates()
            templates.pop(name, None)
            self._save_templates_file(templates)
            self._refresh_templates()

    # ── HISTORY ───────────────────────────────────────────────────────────────

    def _add_to_history(self, msg):
        try:
            history = self._load_history()
            if msg in history:
                history.remove(msg)
            history.insert(0, msg)
            history = history[:20]
            with open(HISTORY, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            self._refresh_history()
        except Exception:
            pass

    def _load_history(self):
        try:
            with open(HISTORY, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _refresh_history(self):
        history = self._load_history()
        menu = tk.Menu(self.history_btn, tearoff=0, bg=PANEL, fg=FG,
                       activebackground=ACCENT, activeforeground="white")
        if not history:
            menu.add_command(label="No history yet", state="disabled")
        for msg in history:
            preview = msg[:50].replace("\n", " ") + ("..." if len(msg) > 50 else "")
            menu.add_command(label=preview, command=lambda m=msg: self._load_template(m))
        self._history_menu = menu

    def _show_history(self):
        self._refresh_history()
        self._history_menu.tk_popup(
            self.history_btn.winfo_rootx(),
            self.history_btn.winfo_rooty() + self.history_btn.winfo_height()
        )

    # ── PREVIEW ───────────────────────────────────────────────────────────────

    def _preview_message(self):
        msg = self.msg_box.get("1.0", "end").strip()
        if not msg:
            messagebox.showinfo("Preview", "Nothing to preview.")
            return
        win = tk.Toplevel(self)
        win.title("Message Preview")
        win.geometry("500x400")
        win.configure(bg=DARK)
        tk.Label(win, text="Preview (formatting rendered)",
                 font=("Segoe UI", 10, "bold"), bg=DARK, fg=FG).pack(pady=(12,4))
        preview_box = tk.Text(win, font=("Segoe UI", 11), bg=PANEL, fg=FG,
                              relief="flat", bd=0, wrap="word", padx=12, pady=8,
                              state="normal")
        preview_box.pack(fill="both", expand=True, padx=16, pady=(0,12))
        preview_box.tag_config("bold",    font=("Segoe UI", 11, "bold"))
        preview_box.tag_config("italic",  font=("Segoe UI", 11, "italic"))
        preview_box.tag_config("strike",  overstrike=True)
        preview_box.tag_config("spoiler", background="#555", foreground="#555")
        preview_box.tag_config("mono",    font=("Consolas", 10), background="#11111b")
        import re as _re
        patterns = [
            (r'\*\*(.+?)\*\*', "bold"),
            (r'__(.+?)__',     "italic"),
            (r'~~(.+?)~~',     "strike"),
            (r'\|\|(.+?)\|\|', "spoiler"),
            (r'`([^`]+)`',     "mono"),
        ]
        remaining = msg
        segments = []
        while remaining:
            earliest = None
            for pattern, tag in patterns:
                m = _re.search(pattern, remaining, _re.DOTALL)
                if m and (earliest is None or m.start() < earliest[0]):
                    earliest = (m.start(), m.end(), m.group(1), tag)
            if earliest:
                start, end, inner, tag = earliest
                if start > 0:
                    segments.append((remaining[:start], None))
                segments.append((inner, tag))
                remaining = remaining[end:]
            else:
                segments.append((remaining, None))
                break
        for text, tag in segments:
            if tag:
                preview_box.insert("end", text, tag)
            else:
                preview_box.insert("end", text)
        preview_box.config(state="disabled")
        tk.Button(win, text="Close", font=("Segoe UI", 10),
                  bg=PANEL, fg=FG, relief="flat", cursor="hand2",
                  command=win.destroy).pack(pady=(0,12))

    def _auto_start_all(self, key="bot1"):
        if not hasattr(self, "_auto_started"):
            self._auto_started = set()
        if key in self._auto_started:
            return
        panel = self.bot_panel if key == "bot1" else self.bot_panel2
        if not panel.groups:
            self.after(3000, lambda: self._auto_start_all(key))
            return
        self._auto_started.add(key)
        panel._select_all()
        for g in panel.groups:
            entity_id = g["entity"].id
            secs = 3600
            group_cooldowns[entity_id] = time.time() + secs
            panel.repeat_intervals[entity_id] = secs
            rv = panel.repeat_vars.get(entity_id)
            if rv:
                rv.set(True)
            idx = panel.groups.index(g)
            gframes = [w for w in panel.checkbox_frame.winfo_children() if isinstance(w, tk.Frame)]
            if idx < len(gframes):
                subs = [w for w in gframes[idx].winfo_children() if isinstance(w, tk.Frame)]
                if len(subs) > 1:
                    for widget in subs[1].winfo_children():
                        if isinstance(widget, tk.Label) and widget.cget("width") == 12:
                            panel._start_countdown(g, widget, rv)
                            break
        self._log(f"── AUTO START ({key.upper()}): Timer set for all {len(panel.groups)} groups (1h repeat) ──", YELLOW)

    # ── ACCOUNT SETTINGS ──────────────────────────────────────────────────────

    def _open_account_settings(self):
        cfg = _load_config()
        win = tk.Toplevel(self)
        win.title("Account Settings")
        win.geometry("420x420")
        win.configure(bg=DARK)
        win.grab_set()
        win.resizable(False, False)
        tk.Label(win, text="Account Settings", font=("Segoe UI", 12, "bold"),
                 bg=ACCENT, fg="white").pack(fill="x", ipady=10)
        def field(label, default="", show=""):
            tk.Label(win, text=label, font=("Segoe UI", 9, "bold"),
                     bg=DARK, fg=FG, anchor="w").pack(fill="x", padx=20, pady=(8,2))
            e = tk.Entry(win, font=("Segoe UI", 10), bg=PANEL, fg=FG,
                         insertbackground=FG, relief="flat", bd=0, show=show)
            e.insert(0, str(default))
            e.pack(fill="x", padx=20, ipady=4)
            return e
        e_api_id   = field("API ID",   cfg.get("api_id", ""))
        e_api_hash = field("API Hash", cfg.get("api_hash", ""))
        e_phone    = field("Phone Number", cfg.get("phone", ""))
        e_bot1     = field("Bot 1 Token", cfg.get("bot_token", ""))
        e_bot2     = field("Bot 2 Token (optional)", cfg.get("bot_token2", ""))
        tk.Label(win, text="Changes take effect after restarting the app.",
                 font=("Segoe UI", 8), bg=DARK, fg=MUTED).pack(pady=(8,0))
        def save():
            new_cfg = {
                "api_id":     int(e_api_id.get().strip()),
                "api_hash":   e_api_hash.get().strip(),
                "phone":      e_phone.get().strip(),
                "bot_token":  e_bot1.get().strip(),
                "bot_token2": e_bot2.get().strip(),
            }
            _save_config(new_cfg)
            self._log("── Account settings saved. Restart to apply. ──", YELLOW)
            win.destroy()
        tk.Button(win, text="Save", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", pady=8, cursor="hand2",
                  command=save).pack(fill="x", padx=20, pady=14)

    # ── PROXY SETTINGS ────────────────────────────────────────────────────────

    def _open_proxy_settings(self):
        try:
            with open(PROXY_F, "r", encoding="utf-8") as f:
                p = json.load(f)
        except Exception:
            p = {"enabled": False, "type": "socks5", "host": "", "port": "1080",
                 "username": "", "password": ""}
        win = tk.Toplevel(self)
        win.title("Proxy Settings")
        win.geometry("380x320")
        win.configure(bg=DARK)
        win.grab_set()
        win.resizable(False, False)
        def row(label, default="", show=""):
            tk.Label(win, text=label, font=("Segoe UI", 9), bg=DARK, fg=MUTED).pack(anchor="w", padx=20, pady=(6,0))
            e = tk.Entry(win, font=("Segoe UI", 10), bg=PANEL, fg=FG,
                         insertbackground=FG, relief="flat", bd=0, show=show)
            e.insert(0, default)
            e.pack(fill="x", padx=20, ipady=4)
            return e
        enabled_var = tk.BooleanVar(value=p.get("enabled", False))
        tk.Checkbutton(win, text="Enable Proxy", variable=enabled_var,
                       bg=DARK, fg=FG, selectcolor="#3a3a5e",
                       activebackground=DARK, font=("Segoe UI", 10, "bold"),
                       relief="flat", cursor="hand2").pack(anchor="w", padx=20, pady=(12,0))
        type_var = tk.StringVar(value=p.get("type", "socks5"))
        tf = tk.Frame(win, bg=DARK)
        tf.pack(anchor="w", padx=20, pady=(4,0))
        tk.Label(tf, text="Type:", font=("Segoe UI", 9), bg=DARK, fg=MUTED).pack(side="left", padx=(0,8))
        for t in ["socks5", "socks4", "http"]:
            tk.Radiobutton(tf, text=t.upper(), variable=type_var, value=t,
                           bg=DARK, fg=FG, selectcolor="#3a3a5e",
                           activebackground=DARK, font=("Segoe UI", 9),
                           relief="flat", cursor="hand2").pack(side="left", padx=4)
        e_host = row("Host / IP", p.get("host", ""))
        e_port = row("Port", p.get("port", "1080"))
        e_user = row("Username (optional)", p.get("username", ""))
        e_pass = row("Password (optional)", p.get("password", ""), show="*")
        def save():
            cfg = {
                "enabled":  enabled_var.get(),
                "type":     type_var.get(),
                "host":     e_host.get().strip(),
                "port":     e_port.get().strip(),
                "username": e_user.get().strip(),
                "password": e_pass.get().strip(),
            }
            with open(PROXY_F, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            self._log("── Proxy saved. Restart the app to apply. ──", YELLOW)
            win.destroy()
        tk.Button(win, text="Save & Close", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", pady=6, cursor="hand2",
                  command=save).pack(fill="x", padx=20, pady=12)

    # ── SESSION MANAGEMENT ────────────────────────────────────────────────────

    def _get_current_state(self):
        existing = {}
        if os.path.exists(PREFS):
            try:
                with open(PREFS, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        return {
            "message":         self.msg_box.get("1.0", "end").strip(),
            "timer_message":   self.timer_msg_box.get("1.0", "end").strip(),
            "respect":         self.opt_respect.get(),
            "restart":         self.opt_restart.get(),
            "active_tab":      self._active_tab,
            "user_tab_hidden": getattr(self, "_user_tab_hidden", False),
            "user_checked":   ([g["title"] for g, v in zip(self.user_panel.groups, self.user_panel.check_vars) if v.get()]
                               if self.user_panel.groups else existing.get("user_checked", [])),
            "bot1_checked":   ([g["title"] for g, v in zip(self.bot_panel.groups, self.bot_panel.check_vars) if v.get()]
                               if self.bot_panel.groups else existing.get("bot1_checked", [])),
            "bot2_checked":   ([g["title"] for g, v in zip(self.bot_panel2.groups, self.bot_panel2.check_vars) if v.get()]
                               if self.bot_panel2.groups else existing.get("bot2_checked", [])),
        }

    def _load_sessions(self):
        try:
            with open(SESSIONS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_sessions(self, sessions):
        with open(SESSIONS, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    def _save_session_as(self):
        win = tk.Toplevel(self)
        win.title("Save Session")
        win.geometry("340x130")
        win.configure(bg=DARK)
        win.grab_set()
        tk.Label(win, text="Session name:", font=("Segoe UI", 10),
                 bg=DARK, fg=FG).pack(pady=(16,4))
        entry = tk.Entry(win, font=("Segoe UI", 10), bg=PANEL, fg=FG,
                         insertbackground=FG, relief="flat", bd=0)
        entry.pack(fill="x", padx=20, ipady=5)
        entry.focus()
        def save():
            name = entry.get().strip()
            if not name: return
            sessions = self._load_sessions()
            sessions[name] = self._get_current_state()
            self._save_sessions(sessions)
            self._refresh_session_menu()
            self._log(f"── Session saved: {name} ──", GREEN)
            win.destroy()
        tk.Button(win, text="Save", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", pady=6,
                  command=save).pack(fill="x", padx=20, pady=10)
        win.bind("<Return>", lambda e: save())

    def _load_session(self, name):
        sessions = self._load_sessions()
        if name not in sessions:
            return
        state = sessions[name]
        self.msg_box.delete("1.0", "end")
        if state.get("message"): self.msg_box.insert("1.0", state["message"])
        self.timer_msg_box.delete("1.0", "end")
        if state.get("timer_message"): self.timer_msg_box.insert("1.0", state["timer_message"])
        self.opt_respect.set(state.get("respect", True))
        self.opt_restart.set(state.get("restart", True))
        for panel, key in [(self.user_panel, "user_checked"),
                           (self.bot_panel, "bot1_checked"),
                           (self.bot_panel2, "bot2_checked")]:
            checked = set(state.get(key, []))
            for g, v in zip(panel.groups, panel.check_vars):
                v.set(g["title"] in checked)
        saved_tab = state.get("active_tab")
        if saved_tab in self._panels:
            self._switch_tab(saved_tab)
        self._log(f"── Session loaded: {name} ──", GREEN)

    def _delete_session(self, name):
        if not messagebox.askyesno("Delete Session", f"Delete session '{name}'?"):
            return
        sessions = self._load_sessions()
        sessions.pop(name, None)
        self._save_sessions(sessions)
        self._refresh_session_menu()
        self._log(f"── Session deleted: {name} ──", YELLOW)

    def _refresh_session_menu(self):
        menu = tk.Menu(self.session_btn, tearoff=0, bg=PANEL, fg=FG,
                       activebackground=ACCENT, activeforeground="white")
        sessions = self._load_sessions()
        if not sessions:
            menu.add_command(label="No sessions saved", state="disabled")
        else:
            for name in sessions:
                sub = tk.Menu(menu, tearoff=0, bg=PANEL, fg=FG,
                              activebackground=ACCENT, activeforeground="white")
                sub.add_command(label="Load", command=lambda n=name: self._load_session(n))
                sub.add_command(label="Delete", command=lambda n=name: self._delete_session(n))
                menu.add_cascade(label=name, menu=sub)
        self._session_menu = menu

    def _show_session_menu(self):
        self._refresh_session_menu()
        self._session_menu.tk_popup(
            self.session_btn.winfo_rootx(),
            self.session_btn.winfo_rooty() + self.session_btn.winfo_height()
        )

    def _save_prefs(self, show_confirmation=False):
        try:
            existing = {}
            if os.path.exists(PREFS):
                with open(PREFS, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            prefs = {
                "message":         self.msg_box.get("1.0", "end").strip(),
                "timer_message":   self.timer_msg_box.get("1.0", "end").strip(),
                "respect":         self.opt_respect.get(),
                "restart":         self.opt_restart.get(),
                "active_tab":      self._active_tab,
                "user_tab_hidden": getattr(self, "_user_tab_hidden", False),
                "user_checked": ([g["title"] for g, v in zip(self.user_panel.groups, self.user_panel.check_vars) if v.get()]
                                  if self.user_panel.groups else existing.get("user_checked", [])),
                "bot1_checked": ([g["title"] for g, v in zip(self.bot_panel.groups, self.bot_panel.check_vars) if v.get()]
                                  if self.bot_panel.groups else existing.get("bot1_checked", [])),
                "bot2_checked": ([g["title"] for g, v in zip(self.bot_panel2.groups, self.bot_panel2.check_vars) if v.get()]
                                  if self.bot_panel2.groups else existing.get("bot2_checked", [])),
            }
            with open(PREFS, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
            if show_confirmation:
                self._log("── Settings saved ──", GREEN)
        except Exception as e:
            if show_confirmation:
                self._log(f"── Save failed: {e} ──", RED)

    def _load_prefs(self, panel, key):
        if not os.path.exists(PREFS): return
        try:
            with open(PREFS, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            checked = set(prefs.get(key, []))
            for g, v in zip(panel.groups, panel.check_vars):
                if g["title"] in checked: v.set(True)
            if key == "user_checked":
                msg = prefs.get("message", "")
                if msg: self.msg_box.insert("1.0", msg)
                tmsg = prefs.get("timer_message", "")
                if tmsg: self.timer_msg_box.insert("1.0", tmsg)
                self.opt_respect.set(prefs.get("respect", True))
                self.opt_restart.set(prefs.get("restart", True))
                if prefs.get("user_tab_hidden", False) and not self._user_tab_hidden:
                    self._toggle_user_tab()
                saved_tab = prefs.get("active_tab")
                if saved_tab in self._panels:
                    self._switch_tab(saved_tab)
        except Exception:
            pass

    def _on_close(self):
        for s in [self._stop_user, self._stop_bot1, self._stop_bot2]:
            if s and not s.is_set(): s.set()
        self._save_prefs()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
