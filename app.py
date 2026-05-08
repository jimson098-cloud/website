import json
import os
import time
from functools import wraps
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-in-production")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB upload limiet.

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(STATIC_DIR / "uploads")))
CONTENT_FILE = DATA_DIR / "site_content.json"
ADMIN_FILE = DATA_DIR / "admin.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "site-images")
ADMIN_PATH = os.getenv("ADMIN_PATH", "beheer-siteslim").strip("/")
ADMIN_ALLOWED_IPS = {ip.strip() for ip in os.getenv("ADMIN_ALLOWED_IPS", "").split(",") if ip.strip()}
LOGIN_ATTEMPTS_BY_IP: dict[str, dict[str, int]] = {}

DEFAULT_CONTENT = {
    "hero_tag": "Webdesign voor nieuwkomers en starters",
    "hero_title": "Premium websites die vertrouwen en klanten opleveren",
    "hero_text": (
        "SiteSlim bouwt professionele websites met een sterke uitstraling, snelle performance "
        "en directe koppeling met jouw social media. Zo groei je als starter met een merk dat "
        "meteen serieus overkomt."
    ),
    "price_title": "Vanaf €299",
    "price_text": "Basis website pakket met 1-3 pagina's",
    "portfolio_intro": "Enkele sfeerbeelden van moderne websites en creatieve studio-werkplekken.",
    "image_1_caption": "Modern webdesign",
    "image_2_caption": "Snelle ontwikkeling",
    "image_3_caption": "Website + social media",
    "image_1_src": "https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=1200&q=80",
    "image_2_src": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
    "image_3_src": "https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?auto=format&fit=crop&w=1200&q=80",
    "footer_about": "Betaalbare websites voor nieuwkomers en starters.",
    "footer_email": "info@siteslim.nl",
    "footer_phone": "+31 6 12 34 56 78",
    "social_instagram_url": "",
    "social_facebook_url": "",
    "social_tiktok_url": "",
    "social_linkedin_url": "",
    "footer_link_1_label": "",
    "footer_link_1_url": "",
    "footer_link_2_label": "",
    "footer_link_2_url": "",
    "footer_link_3_label": "",
    "footer_link_3_url": "",
    "home_custom_html": "",
    "diensten_custom_html": "",
    "portfolio_custom_html": "",
    "over_ons_custom_html": "",
    "contact_custom_html": "",
    "custom_css": "",
    "page_blocks": {
        "home": [],
        "diensten": [],
        "portfolio": [],
        "over_ons": [],
        "contact": [],
    },
}


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def supabase_request(path: str, method: str = "GET", payload: Optional[dict] = None) -> Any:
    if not supabase_enabled():
        return None

    url = f"{SUPABASE_URL}{path}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=15) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else None


def ensure_supabase_defaults() -> None:
    if not supabase_enabled():
        return
    try:
        supabase_request(
            "/rest/v1/site_content?on_conflict=id",
            method="POST",
            payload=[{"id": 1, "data": DEFAULT_CONTENT}],
        )
        supabase_request(
            "/rest/v1/admin_user?on_conflict=id",
            method="POST",
            payload=[{"id": 1, "username": "admin", "password_hash": generate_password_hash("admin123")}],
        )
    except (HTTPError, URLError, TimeoutError, ValueError):
        # Als Supabase nog niet correct is geconfigureerd, blijft lokale fallback actief.
        pass


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONTENT_FILE.exists():
        CONTENT_FILE.write_text(json.dumps(DEFAULT_CONTENT, indent=2), encoding="utf-8")
    if not ADMIN_FILE.exists():
        admin_data = {"username": "admin", "password_hash": generate_password_hash("admin123")}
        ADMIN_FILE.write_text(json.dumps(admin_data, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_content() -> dict:
    if supabase_enabled():
        try:
            result = supabase_request("/rest/v1/site_content?id=eq.1&select=data")
            if result and isinstance(result, list) and result[0].get("data"):
                content = DEFAULT_CONTENT.copy()
                content.update(result[0]["data"])
                content["page_blocks"] = normalize_page_blocks(content.get("page_blocks"))
                return content
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass

    content = DEFAULT_CONTENT.copy()
    content.update(read_json(CONTENT_FILE))
    content["page_blocks"] = normalize_page_blocks(content.get("page_blocks"))
    return content


def normalize_page_blocks(raw_blocks: Any) -> dict:
    default_keys = ["home", "diensten", "portfolio", "over_ons", "contact"]
    normalized = {key: [] for key in default_keys}
    if not isinstance(raw_blocks, dict):
        return normalized

    for key in default_keys:
        blocks = raw_blocks.get(key, [])
        if isinstance(blocks, list):
            cleaned = []
            for block in blocks:
                if isinstance(block, dict):
                    cleaned.append(
                        {
                            "type": str(block.get("type", "text")),
                            "title": str(block.get("title", "")),
                            "text": str(block.get("text", "")),
                            "image_url": str(block.get("image_url", "")),
                            "button_label": str(block.get("button_label", "")),
                            "button_url": str(block.get("button_url", "")),
                        }
                    )
            normalized[key] = cleaned
    return normalized


def save_content(content: dict) -> bool:
    if supabase_enabled():
        try:
            supabase_request(
                "/rest/v1/site_content?id=eq.1",
                method="PATCH",
                payload={"data": content},
            )
            return True
        except (HTTPError, URLError, TimeoutError, ValueError):
            return False

    try:
        write_json(CONTENT_FILE, content)
        return True
    except OSError:
        return False


def load_admin_data() -> dict:
    if supabase_enabled():
        try:
            result = supabase_request("/rest/v1/admin_user?id=eq.1&select=username,password_hash")
            if result and isinstance(result, list):
                return result[0]
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError):
            pass
    return read_json(ADMIN_FILE)


def save_admin_data(admin_data: dict) -> bool:
    if supabase_enabled():
        try:
            supabase_request(
                "/rest/v1/admin_user?id=eq.1",
                method="PATCH",
                payload={
                    "username": admin_data["username"],
                    "password_hash": admin_data["password_hash"],
                },
            )
            return True
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            return False

    try:
        write_json(ADMIN_FILE, admin_data)
        return True
    except OSError:
        return False


def upload_image(file_storage, slot: str) -> tuple[bool, str]:
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{slot}-{uuid4().hex}.{ext}")

    if supabase_enabled():
        try:
            content = file_storage.read()
            storage_path = f"{slot}/{filename}"
            encoded_path = quote(storage_path, safe="/")
            upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{encoded_path}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "x-upsert": "true",
                "Content-Type": file_storage.mimetype or "application/octet-stream",
            }
            req = Request(url=upload_url, method="POST", headers=headers, data=content)
            urlopen(req, timeout=30).read()
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{encoded_path}"
            return True, public_url
        except (HTTPError, URLError, TimeoutError, ValueError):
            return False, ""

    try:
        file_path = UPLOADS_DIR / filename
        file_storage.save(file_path)
        return True, url_for("uploaded_file", filename=filename)
    except OSError:
        return False, ""


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (request.remote_addr or "").strip()


def is_admin_ip_allowed() -> bool:
    if not ADMIN_ALLOWED_IPS:
        return True
    return get_client_ip() in ADMIN_ALLOWED_IPS


def login_blocked_for_ip(ip: str) -> bool:
    record = LOGIN_ATTEMPTS_BY_IP.get(ip, {})
    return int(record.get("blocked_until", 0)) > int(time.time())


def track_failed_login(ip: str) -> None:
    now = int(time.time())
    record = LOGIN_ATTEMPTS_BY_IP.get(ip, {"count": 0, "blocked_until": 0})
    if int(record.get("blocked_until", 0)) <= now:
        record["count"] = int(record.get("count", 0)) + 1
    if int(record.get("count", 0)) >= 5:
        record["blocked_until"] = now + 300
        record["count"] = 0
    LOGIN_ATTEMPTS_BY_IP[ip] = record


def clear_login_attempts(ip: str) -> None:
    LOGIN_ATTEMPTS_BY_IP.pop(ip, None)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_admin_ip_allowed():
            return redirect(url_for("home"))
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapped


try:
    ensure_data_files()
except OSError:
    # Vercel heeft soms een read-only filesystem; fallback naar /tmp.
    DATA_DIR = Path("/tmp/siteslim-data")
    UPLOADS_DIR = Path("/tmp/siteslim-uploads")
    CONTENT_FILE = DATA_DIR / "site_content.json"
    ADMIN_FILE = DATA_DIR / "admin.json"
    ensure_data_files()

ensure_supabase_defaults()


@app.route("/")
def home():
    return render_template("home.html", content=load_content())


@app.context_processor
def inject_site_content():
    return {"site_content": load_content()}


@app.route("/diensten")
def diensten():
    return render_template("diensten.html", content=load_content())


@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html", content=load_content())


@app.route("/over-ons")
def over_ons():
    return render_template("over_ons.html", content=load_content())


@app.route("/contact")
def contact():
    return render_template("contact.html", content=load_content())


@app.route(f"/{ADMIN_PATH}/login", methods=["GET", "POST"])
def admin_login():
    if not is_admin_ip_allowed():
        return redirect(url_for("home"))

    client_ip = get_client_ip()
    if login_blocked_for_ip(client_ip):
        flash("Te veel pogingen. Probeer zo opnieuw.", "error")
        return render_template("admin_login.html")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin_data = load_admin_data()
        if username == admin_data.get("username") and check_password_hash(
            admin_data.get("password_hash", ""), password
        ):
            session.clear()
            session["admin_logged_in"] = True
            clear_login_attempts(client_ip)
            return redirect(url_for("admin_dashboard"))
        track_failed_login(client_ip)
        flash("Onjuiste gebruikersnaam of wachtwoord.", "error")
    return render_template("admin_login.html")


@app.route(f"/{ADMIN_PATH}/logout")
@login_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route(f"/{ADMIN_PATH}", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    content = load_content()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "content":
            content["hero_tag"] = request.form.get("hero_tag", "").strip()
            content["hero_title"] = request.form.get("hero_title", "").strip()
            content["hero_text"] = request.form.get("hero_text", "").strip()
            content["price_title"] = request.form.get("price_title", "").strip()
            content["price_text"] = request.form.get("price_text", "").strip()
            content["portfolio_intro"] = request.form.get("portfolio_intro", "").strip()
            content["image_1_caption"] = request.form.get("image_1_caption", "").strip()
            content["image_2_caption"] = request.form.get("image_2_caption", "").strip()
            content["image_3_caption"] = request.form.get("image_3_caption", "").strip()
            content["footer_about"] = request.form.get("footer_about", "").strip()
            content["footer_email"] = request.form.get("footer_email", "").strip()
            content["footer_phone"] = request.form.get("footer_phone", "").strip()
            content["social_instagram_url"] = request.form.get("social_instagram_url", "").strip()
            content["social_facebook_url"] = request.form.get("social_facebook_url", "").strip()
            content["social_tiktok_url"] = request.form.get("social_tiktok_url", "").strip()
            content["social_linkedin_url"] = request.form.get("social_linkedin_url", "").strip()
            content["footer_link_1_label"] = request.form.get("footer_link_1_label", "").strip()
            content["footer_link_1_url"] = request.form.get("footer_link_1_url", "").strip()
            content["footer_link_2_label"] = request.form.get("footer_link_2_label", "").strip()
            content["footer_link_2_url"] = request.form.get("footer_link_2_url", "").strip()
            content["footer_link_3_label"] = request.form.get("footer_link_3_label", "").strip()
            content["footer_link_3_url"] = request.form.get("footer_link_3_url", "").strip()
            content["home_custom_html"] = request.form.get("home_custom_html", "").strip()
            content["diensten_custom_html"] = request.form.get("diensten_custom_html", "").strip()
            content["portfolio_custom_html"] = request.form.get("portfolio_custom_html", "").strip()
            content["over_ons_custom_html"] = request.form.get("over_ons_custom_html", "").strip()
            content["contact_custom_html"] = request.form.get("contact_custom_html", "").strip()
            content["custom_css"] = request.form.get("custom_css", "").strip()
            raw_page_blocks = request.form.get("page_blocks_json", "").strip()
            if raw_page_blocks:
                try:
                    parsed_blocks = json.loads(raw_page_blocks)
                    content["page_blocks"] = normalize_page_blocks(parsed_blocks)
                except ValueError:
                    flash("Page Builder data kon niet worden gelezen.", "error")
                    return redirect(url_for("admin_dashboard"))
            if save_content(content):
                flash("Teksten zijn opgeslagen.", "success")
            else:
                flash("Opslaan mislukt op deze hosting omgeving.", "error")
            return redirect(url_for("admin_dashboard"))

        if form_type == "upload":
            slot = request.form.get("slot")
            file = request.files.get("image_file")
            if slot in {"image_1_src", "image_2_src", "image_3_src"} and file and file.filename:
                if allowed_file(file.filename):
                    success, image_url = upload_image(file, slot)
                    if success:
                        content[slot] = image_url
                        if save_content(content):
                            flash("Foto succesvol geupload.", "success")
                        else:
                            flash("Foto geupload, maar inhoud opslaan is mislukt.", "error")
                    else:
                        flash("Uploaden mislukt op deze hosting omgeving.", "error")
                else:
                    flash("Bestandstype niet toegestaan. Gebruik png/jpg/jpeg/webp/gif.", "error")
            else:
                flash("Selecteer een slot en kies een afbeelding.", "error")
            return redirect(url_for("admin_dashboard"))

        if form_type == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            repeat_password = request.form.get("repeat_password", "")
            admin_data = load_admin_data()

            if not check_password_hash(admin_data.get("password_hash", ""), current_password):
                flash("Huidig wachtwoord klopt niet.", "error")
            elif len(new_password) < 8:
                flash("Nieuw wachtwoord moet minimaal 8 tekens hebben.", "error")
            elif new_password != repeat_password:
                flash("Nieuwe wachtwoorden komen niet overeen.", "error")
            else:
                admin_data["password_hash"] = generate_password_hash(new_password)
                if save_admin_data(admin_data):
                    flash("Wachtwoord succesvol gewijzigd.", "success")
                else:
                    flash("Wachtwoord opslaan mislukt op deze hosting omgeving.", "error")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin_dashboard.html", content=content)


@app.route("/media/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOADS_DIR, filename)


@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https: data:; "
        "script-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


if __name__ == "__main__":
    app.run(debug=True)
