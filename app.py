from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, sqlite3, secrets, datetime

# -----------------------
# Config
# -----------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

DB_PATH = os.path.join("diary.db")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# -----------------------
# Helpers
# -----------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        entry_date TEXT NOT NULL,  -- ISO date YYYY-MM-DD
        title TEXT,
        content TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, entry_date),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        filename TEXT NOT NULL,         -- server filename (relative)
        original_name TEXT NOT NULL,    -- original file name
        created_at TEXT NOT NULL,
        FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def current_user_id():
    return session.get("user_id")

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Simple CSRF token
def get_csrf():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token

def validate_csrf():
    token = session.get("_csrf")
    form_token = request.form.get("_csrf")
    if not token or not form_token or token != form_token:
        abort(400, description="Invalid CSRF token")

def ensure_user_upload_dir(user_id, date_iso):
    # e.g., static/uploads/3/2025-08-15/
    dirpath = os.path.join(app.config["UPLOAD_FOLDER"], str(user_id), date_iso)
    os.makedirs(dirpath, exist_ok=True)
    return dirpath

# -----------------------
# Routes: Auth
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("register.html", csrf_token=get_csrf())
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                (username, generate_password_hash(password), datetime.datetime.utcnow().isoformat()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
            conn.close()
            return render_template("register.html", csrf_token=get_csrf())
        # Auto-login
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        user_id = cur.fetchone()["id"]
        conn.close()
        session["user_id"] = user_id
        session["username"] = username
        get_csrf()  # ensure token set
        return redirect(url_for("dashboard"))
    return render_template("register.html", csrf_token=get_csrf())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            get_csrf()
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html", csrf_token=get_csrf())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------
# Routes: UI pages
# -----------------------
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", csrf_token=get_csrf())

@app.route("/entry")
@login_required
def entry_page():
    # expects ?date=YYYY-MM-DD
    date_iso = request.args.get("date")
    try:
        datetime.date.fromisoformat(date_iso)  # validates format
    except Exception:
        flash("Invalid date.", "danger")
        return redirect(url_for("dashboard"))

    # Fetch or create entry shell for display
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM entries WHERE user_id=? AND entry_date=?",
        (current_user_id(), date_iso),
    )
    entry = cur.fetchone()
    images = []
    if entry:
        cur.execute("SELECT * FROM images WHERE entry_id=? ORDER BY id DESC", (entry["id"],))
        images = cur.fetchall()
    conn.close()
    return render_template("entry.html", date_iso=date_iso, entry=entry, images=images, csrf_token=get_csrf())

# -----------------------
# Routes: API for calendar + CRUD
# -----------------------
@app.route("/api/events")
@login_required
def api_events():
    """Return events for FullCalendar; we’ll send minimal info."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT entry_date, title, content FROM entries WHERE user_id=?", (current_user_id(),))
    rows = cur.fetchall()
    conn.close()
    events = []
    for r in rows:
        # Use title if present else excerpt of content
        display = (r["title"] or (r["content"] or "").strip()[:24]) or "Entry"
        events.append({
            "title": display,
            "start": r["entry_date"],
            "allDay": True
        })
    return jsonify(events)

@app.route("/entry/save", methods=["POST"])
@login_required
def save_entry():
    validate_csrf()
    date_iso = request.form.get("date")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    try:
        datetime.date.fromisoformat(date_iso)
    except Exception:
        abort(400, description="Invalid date")

    now = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    cur = conn.cursor()
    # Upsert
    cur.execute(
        "SELECT id FROM entries WHERE user_id=? AND entry_date=?",
        (current_user_id(), date_iso),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE entries SET title=?, content=?, updated_at=? WHERE id=?",
            (title, content, now, row["id"]),
        )
        entry_id = row["id"]
    else:
        cur.execute(
            "INSERT INTO entries(user_id, entry_date, title, content, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (current_user_id(), date_iso, title, content, now, now),
        )
        entry_id = cur.lastrowid
    conn.commit()
    conn.close()
    flash("Entry saved.", "success")
    return redirect(url_for("entry_page", date=date_iso))

@app.route("/entry/delete", methods=["POST"])
@login_required
def delete_entry():
    validate_csrf()
    date_iso = request.form.get("date")
    try:
        datetime.date.fromisoformat(date_iso)
    except Exception:
        abort(400, description="Invalid date")

    conn = get_db()
    cur = conn.cursor()
    # Get entry id to remove images from disk
    cur.execute("SELECT id FROM entries WHERE user_id=? AND entry_date=?", (current_user_id(), date_iso))
    row = cur.fetchone()
    if row:
        entry_id = row["id"]
        # delete images files
        cur.execute("SELECT filename FROM images WHERE entry_id=?", (entry_id,))
        for img in cur.fetchall():
            path = os.path.join(app.config["UPLOAD_FOLDER"], img["filename"])
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        cur.execute("DELETE FROM images WHERE entry_id=?", (entry_id,))
        cur.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        conn.commit()
        flash("Entry deleted.", "info")
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/entry/upload", methods=["POST"])
@login_required
def upload_images():
    validate_csrf()
    date_iso = request.form.get("date")
    try:
        datetime.date.fromisoformat(date_iso)
    except Exception:
        abort(400, description="Invalid date")

    # Ensure entry exists
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM entries WHERE user_id=? AND entry_date=?", (current_user_id(), date_iso))
    row = cur.fetchone()
    if not row:
        now = datetime.datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO entries(user_id, entry_date, title, content, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (current_user_id(), date_iso, "", "", now, now),
        )
        entry_id = cur.lastrowid
        conn.commit()
    else:
        entry_id = row["id"]

    files = request.files.getlist("images")
    saved = 0
    up_dir = ensure_user_upload_dir(current_user_id(), date_iso)

    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            flash(f"Skipped unsupported file: {f.filename}", "warning")
            continue
        fname = secure_filename(f.filename)
        # make unique
        unique = f"{secrets.token_hex(8)}_{fname}"
        rel_path = os.path.join(str(current_user_id()), date_iso, unique)  # stored relative under uploads/
        full_path = os.path.join(app.config["UPLOAD_FOLDER"], rel_path)
        f.save(full_path)
        cur.execute(
            "INSERT INTO images(entry_id, filename, original_name, created_at) VALUES(?,?,?,?)",
            (entry_id, rel_path, fname, datetime.datetime.utcnow().isoformat()),
        )
        saved += 1

    conn.commit()
    conn.close()
    if saved:
        flash(f"Uploaded {saved} image(s).", "success")
    return redirect(url_for("entry_page", date=date_iso))

@app.route("/image/delete", methods=["POST"])
@login_required
def delete_image():
    validate_csrf()
    image_id = request.form.get("image_id")
    date_iso = request.form.get("date")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT images.id, images.filename
        FROM images
        JOIN entries ON images.entry_id = entries.id
        WHERE images.id=? AND entries.user_id=?
    """, (image_id, current_user_id()))
    row = cur.fetchone()
    if row:
        img_path = os.path.join(app.config["UPLOAD_FOLDER"], row["filename"])
        if os.path.exists(img_path):
            try: os.remove(img_path)
            except Exception: pass
        cur.execute("DELETE FROM images WHERE id=?", (row["id"],))
        conn.commit()
        flash("Image deleted.", "info")
    conn.close()
    return redirect(url_for("entry_page", date=date_iso))

# Serve uploaded files safely (they’re under /static/uploads already)
@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    # Prevent path traversal by only serving from UPLOAD_FOLDER
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -----------------------
# App start
# -----------------------
if __name__ == "__main__":
    init_db()
    # For local use only; do NOT use debug=True for shared networks
    app.run(host="127.0.0.1", port=5000, debug=False)