"""
Telegram Reminder - Auth Server
Deploy on Railway. Set environment variable: ADMIN_PASSWORD=yourpassword
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import json, os, hashlib, secrets, datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")
USERS_FILE     = "users.json"

# ── Data helpers ──────────────────────────────────────────────────────────────

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_pw(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt

# ── App API endpoints ─────────────────────────────────────────────────────────

@app.route("/register", methods=["POST"])
def register():
    data     = request.get_json()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password required."}), 400
    if len(username) < 3:
        return jsonify({"ok": False, "error": "Username must be at least 3 characters."}), 400
    if len(password) < 4:
        return jsonify({"ok": False, "error": "Password must be at least 4 characters."}), 400

    users = load_users()
    if username in users:
        return jsonify({"ok": False, "error": "Username already taken."}), 409

    pw_hash, salt = hash_pw(password)
    users[username] = {
        "pw_hash":    pw_hash,
        "salt":       salt,
        "banned":     False,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "last_login": None,
    }
    save_users(users)
    return jsonify({"ok": True, "message": "Account created."})

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    users = load_users()
    user  = users.get(username)

    if not user:
        return jsonify({"ok": False, "error": "Wrong username or password."}), 401
    if user.get("banned"):
        return jsonify({"ok": False, "error": "Your account has been banned."}), 403

    h, _ = hash_pw(password, user["salt"])
    if h != user["pw_hash"]:
        return jsonify({"ok": False, "error": "Wrong username or password."}), 401

    # Update last login
    users[username]["last_login"] = datetime.datetime.utcnow().isoformat()
    save_users(users)
    return jsonify({"ok": True, "message": "Login successful."})

# ── Admin dashboard ───────────────────────────────────────────────────────────

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Telegram Reminder - Admin</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
    .header { background: #7c6af7; padding: 16px 32px; display: flex; align-items: center; gap: 16px; }
    .header h1 { font-size: 20px; color: white; }
    .header span { font-size: 13px; color: #ddd; margin-left: auto; }
    .header a { color: #ddd; font-size: 13px; text-decoration: none; background: rgba(0,0,0,0.2); padding: 6px 12px; border-radius: 4px; }
    .container { max-width: 960px; margin: 32px auto; padding: 0 24px; }
    .stats { display: flex; gap: 16px; margin-bottom: 24px; }
    .stat { background: #2a2a3e; border-radius: 8px; padding: 16px 24px; flex: 1; }
    .stat .num { font-size: 32px; font-weight: bold; color: #7c6af7; }
    .stat .lbl { font-size: 12px; color: #6c7086; margin-top: 4px; }
    .card { background: #2a2a3e; border-radius: 8px; overflow: hidden; }
    .card-header { padding: 14px 20px; font-weight: bold; font-size: 14px; border-bottom: 1px solid #3a3a5e; color: #a6adc8; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 10px 20px; font-size: 12px; color: #6c7086; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #3a3a5e; }
    td { padding: 12px 20px; font-size: 13px; border-bottom: 1px solid #313244; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #313244; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; }
    .badge-active { background: #1e3a2a; color: #a6e3a1; }
    .badge-banned { background: #3a1e1e; color: #f38ba8; }
    .btn { display: inline-block; padding: 5px 14px; border-radius: 4px; font-size: 12px; font-weight: bold; cursor: pointer; border: none; text-decoration: none; }
    .btn-ban   { background: #f38ba8; color: #1e1e2e; }
    .btn-unban { background: #a6e3a1; color: #1e1e2e; }
    .btn-delete { background: #45475a; color: #cdd6f4; margin-left: 4px; }
    .empty { text-align: center; padding: 40px; color: #6c7086; }
    /* Login page */
    .login-wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    .login-box { background: #2a2a3e; border-radius: 12px; padding: 40px; width: 360px; }
    .login-box h2 { margin-bottom: 24px; font-size: 20px; }
    .login-box input { width: 100%; background: #1e1e2e; border: none; border-radius: 6px; padding: 12px; color: #cdd6f4; font-size: 14px; margin-bottom: 14px; outline: none; }
    .login-box button { width: 100%; background: #7c6af7; color: white; border: none; border-radius: 6px; padding: 12px; font-size: 15px; font-weight: bold; cursor: pointer; }
    .error { color: #f38ba8; font-size: 13px; margin-bottom: 12px; }
  </style>
</head>
<body>
{% if not logged_in %}
  <div class="login-wrap">
    <div class="login-box">
      <h2>✈ Admin Login</h2>
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="POST" action="/admin/login">
        <input type="password" name="password" placeholder="Admin password" autofocus>
        <button type="submit">Login</button>
      </form>
    </div>
  </div>
{% else %}
  <div class="header">
    <h1>✈ Telegram Reminder — Admin</h1>
    <span>{{ total }} users registered</span>
    <a href="/admin/logout">Logout</a>
  </div>
  <div class="container">
    <div class="stats">
      <div class="stat"><div class="num">{{ total }}</div><div class="lbl">Total Users</div></div>
      <div class="stat"><div class="num">{{ active }}</div><div class="lbl">Active</div></div>
      <div class="stat"><div class="num">{{ banned }}</div><div class="lbl">Banned</div></div>
    </div>
    <div class="card">
      <div class="card-header">All Users</div>
      {% if users %}
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Status</th>
            <th>Registered</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for u in users %}
          <tr>
            <td><strong>{{ u.username }}</strong></td>
            <td>
              <span class="badge {{ 'badge-banned' if u.banned else 'badge-active' }}">
                {{ 'Banned' if u.banned else 'Active' }}
              </span>
            </td>
            <td>{{ u.created_at[:10] if u.created_at else '—' }}</td>
            <td>{{ u.last_login[:10] if u.last_login else 'Never' }}</td>
            <td>
              {% if u.banned %}
                <a class="btn btn-unban" href="/admin/unban/{{ u.username }}">Unban</a>
              {% else %}
                <a class="btn btn-ban" href="/admin/ban/{{ u.username }}">Ban</a>
              {% endif %}
              <a class="btn btn-delete" href="/admin/delete/{{ u.username }}"
                 onclick="return confirm('Delete {{ u.username }}?')">Delete</a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="empty">No users registered yet.</div>
      {% endif %}
    </div>
  </div>
{% endif %}
</body>
</html>
"""

@app.route("/admin", methods=["GET"])
def admin():
    logged_in = session.get("admin")
    if not logged_in:
        return render_template_string(ADMIN_TEMPLATE, logged_in=False, error=None)
    users_raw = load_users()
    users = [{"username": k, **v} for k, v in users_raw.items()]
    total  = len(users)
    banned = sum(1 for u in users if u.get("banned"))
    active = total - banned
    return render_template_string(ADMIN_TEMPLATE, logged_in=True,
                                  users=users, total=total, active=active, banned=banned)

@app.route("/admin/login", methods=["POST"])
def admin_login():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect("/admin")
    return render_template_string(ADMIN_TEMPLATE, logged_in=False, error="Wrong password.")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

@app.route("/admin/ban/<username>")
def admin_ban(username):
    if not session.get("admin"):
        return redirect("/admin")
    users = load_users()
    if username in users:
        users[username]["banned"] = True
        save_users(users)
    return redirect("/admin")

@app.route("/admin/unban/<username>")
def admin_unban(username):
    if not session.get("admin"):
        return redirect("/admin")
    users = load_users()
    if username in users:
        users[username]["banned"] = False
        save_users(users)
    return redirect("/admin")

@app.route("/admin/delete/<username>")
def admin_delete(username):
    if not session.get("admin"):
        return redirect("/admin")
    users = load_users()
    users.pop(username, None)
    save_users(users)
    return redirect("/admin")

@app.route("/")
def index():
    return jsonify({"status": "ok", "app": "Telegram Reminder Auth Server"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
