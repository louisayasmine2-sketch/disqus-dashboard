import json
import hmac
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from database import close_db, get_cached_posts, get_cached_threads, get_contact_requests, get_subscribers, init_db, save_contact_request, save_posts, save_subscriber, save_threads
from disqus_client import DisqusClient, DisqusClientError


load_dotenv()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.teardown_appcontext(close_db)

PROJECT_ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = PROJECT_ROOT / "public"

client = DisqusClient(
    api_key=os.getenv("DISQUS_API_KEY", ""),
    forum=os.getenv("DISQUS_FORUM", ""),
)


CONTENT_PATH = Path(__file__).parent / "content" / "articles.json"
TOOLS_PATH = Path(__file__).parent / "content" / "tools.json"


def load_articles():
    with CONTENT_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def load_tools():
    with TOOLS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


ARTICLES = load_articles()
TOOLS = load_tools()


def get_site_url():
    configured_url = os.getenv("SITE_URL", "").strip().rstrip("/")
    if configured_url:
        return configured_url
    return request.url_root.rstrip("/")


def absolute_url(endpoint, **values):
    path = url_for(endpoint, **values)
    return f"{get_site_url()}{path}"


def get_admin_password():
    return os.getenv("ADMIN_PASSWORD", "").strip()


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("admin_authenticated"):
            return view(*args, **kwargs)

        return redirect(url_for("login", next=request.path))

    return wrapped_view


def sitemap_date(value):
    if not value:
        return ""

    for date_format in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            pass

    return ""


@app.context_processor
def inject_site_settings():
    return {
        "site_url": os.getenv("SITE_URL", "").strip().rstrip("/"),
        "google_analytics_id": os.getenv("GOOGLE_ANALYTICS_ID", "").strip(),
        "tool_finder_url": os.getenv("TOOL_FINDER_URL", "https://ai-tool-finder-web.onrender.com").strip(),
    }


@app.route("/public/<path:filename>")
def public_file(filename):
    return send_from_directory(PUBLIC_DIR, filename)


@app.before_request
def prepare_database():
    init_db()


def get_article(slug):
    for article in ARTICLES:
        if article["slug"] == slug:
            return article
    return None


@app.route("/")
def home():
    return render_template("home.html", articles=ARTICLES[:3], canonical_url=absolute_url("home"))


@app.route("/articles")
def articles():
    return render_template("articles.html", articles=ARTICLES, canonical_url=absolute_url("articles"))


@app.route("/workflows")
def workflows():
    return render_template("workflows.html", canonical_url=absolute_url("workflows"))


@app.route("/tools")
def tools():
    return render_template("tools.html", tools=TOOLS, canonical_url=absolute_url("tools"))


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", canonical_url=absolute_url("pricing"))


@app.route("/security")
def security():
    return render_template("security.html", canonical_url=absolute_url("security"))


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip()
    source = request.form.get("source", "homepage").strip()

    if "@" in email and "." in email:
        save_subscriber(email, source)
        return redirect(url_for("home", subscribed="1"))

    return redirect(url_for("home", subscribed="0"))


@app.route("/about")
def about():
    return render_template("about.html", canonical_url=absolute_url("about"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    status = request.args.get("status")
    selected_workflow = request.args.get("workflow", "").strip()
    source = request.args.get("source", "").strip()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        company = request.form.get("company", "").strip()
        workflow = request.form.get("workflow", "").strip()
        message = request.form.get("message", "").strip()
        source = request.form.get("source", "").strip() or source or "contact_page"

        if name and "@" in email and "." in email and message:
            save_contact_request(name, email, company, workflow, source, message)
            save_subscriber(email, source)
            return redirect(url_for("contact", status="sent", workflow=workflow, source=source))

        return redirect(url_for("contact", status="error", workflow=workflow, source=source))

    return render_template(
        "contact.html",
        canonical_url=absolute_url("contact"),
        status=status,
        selected_workflow=selected_workflow,
        source=source,
    )


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html", canonical_url=absolute_url("privacy_policy"))


@app.route("/terms-of-use")
def terms_of_use():
    return render_template("terms_of_use.html", canonical_url=absolute_url("terms_of_use"))


@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html", canonical_url=absolute_url("disclaimer"))


@app.route("/affiliate-disclosure")
def affiliate_disclosure():
    return render_template("affiliate_disclosure.html", canonical_url=absolute_url("affiliate_disclosure"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    admin_password = get_admin_password()

    if request.method == "POST":
        password = request.form.get("password", "")
        if admin_password and hmac.compare_digest(password, admin_password):
            session["admin_authenticated"] = True
            next_url = request.args.get("next") or url_for("dashboard")
            if not next_url.startswith("/"):
                next_url = url_for("dashboard")
            return redirect(next_url)

        if admin_password:
            error = "The password is incorrect."
        else:
            error = "Admin password is not configured yet."

    return render_template("login.html", canonical_url=absolute_url("login"), error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_authenticated", None)
    return redirect(url_for("login"))


@app.route("/article")
def legacy_article():
    return redirect(url_for("article_detail", slug=ARTICLES[0]["slug"]))


@app.route("/article/<slug>")
def article_detail(slug):
    article = get_article(slug)
    if article is None:
        abort(404)

    return render_template(
        "article_detail.html",
        article=article,
        disqus_forum=os.getenv("DISQUS_FORUM", ""),
        canonical_url=absolute_url("article_detail", slug=slug),
    )


@app.route("/robots.txt")
def robots_txt():
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /dashboard",
            "Disallow: /thread/",
            f"Sitemap: {absolute_url('sitemap_xml')}",
            "",
        ]
    )
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    urls = [
        {"loc": absolute_url("home"), "priority": "1.0"},
        {"loc": absolute_url("workflows"), "priority": "0.9"},
        {"loc": absolute_url("tools"), "priority": "0.9"},
        {"loc": absolute_url("pricing"), "priority": "0.8"},
        {"loc": absolute_url("articles"), "priority": "0.9"},
        {"loc": absolute_url("security"), "priority": "0.7"},
        {"loc": absolute_url("about"), "priority": "0.6"},
        {"loc": absolute_url("contact"), "priority": "0.6"},
        {"loc": absolute_url("privacy_policy"), "priority": "0.5"},
        {"loc": absolute_url("terms_of_use"), "priority": "0.5"},
        {"loc": absolute_url("disclaimer"), "priority": "0.5"},
        {"loc": absolute_url("affiliate_disclosure"), "priority": "0.5"},
    ]
    urls.extend(
        {
            "loc": absolute_url("article_detail", slug=article["slug"]),
            "lastmod": sitemap_date(article.get("updated", "")),
            "priority": "0.8",
        }
        for article in ARTICLES
    )

    items = []
    for item in urls:
        lastmod = f"<lastmod>{item['lastmod']}</lastmod>" if item.get("lastmod") else ""
        items.append(
            f"<url><loc>{item['loc']}</loc>{lastmod}<changefreq>weekly</changefreq><priority>{item['priority']}</priority></url>"
        )

    body = '<?xml version="1.0" encoding="UTF-8"?>'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    body += "".join(items)
    body += "</urlset>"
    return Response(body, mimetype="application/xml")


@app.route("/dashboard")
@admin_required
def dashboard():
    error = None
    subscribers = get_subscribers()
    source_filter = request.args.get("source", "").strip()
    workflow_filter = request.args.get("workflow", "").strip()
    contact_requests = get_contact_requests(source=source_filter or None, workflow=workflow_filter or None)

    try:
        threads = client.get_threads()
        save_threads(threads)
    except DisqusClientError as exc:
        error = str(exc)
        threads = get_cached_threads()

    return render_template(
        "dashboard.html",
        threads=threads,
        subscribers=subscribers,
        contact_requests=contact_requests,
        source_filter=source_filter,
        workflow_filter=workflow_filter,
        error=error,
    )


@app.route("/thread/<thread_id>")
@admin_required
def thread_detail(thread_id):
    error = None
    thread = None

    for item in get_cached_threads():
        if str(item["id"]) == str(thread_id):
            thread = item
            break

    try:
        posts = client.get_posts(thread_id)
        save_posts(thread_id, posts)
    except DisqusClientError as exc:
        error = str(exc)
        posts = get_cached_posts(thread_id)

    if thread is None and not posts:
        abort(404)

    return render_template(
        "thread_detail.html",
        thread=thread,
        posts=posts,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
