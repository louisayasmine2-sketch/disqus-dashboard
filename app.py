import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, abort, redirect, render_template, request, url_for

from database import close_db, get_cached_posts, get_cached_threads, get_subscribers, init_db, save_posts, save_subscriber, save_threads
from disqus_client import DisqusClient, DisqusClientError


load_dotenv()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.teardown_appcontext(close_db)


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


@app.route("/tools")
def tools():
    return render_template("tools.html", tools=TOOLS, canonical_url=absolute_url("tools"))


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


@app.route("/contact")
def contact():
    return render_template("contact.html", canonical_url=absolute_url("contact"))


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html", canonical_url=absolute_url("privacy_policy"))


@app.route("/affiliate-disclosure")
def affiliate_disclosure():
    return render_template("affiliate_disclosure.html", canonical_url=absolute_url("affiliate_disclosure"))


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
        {"loc": absolute_url("articles"), "priority": "0.9"},
        {"loc": absolute_url("tools"), "priority": "0.8"},
        {"loc": absolute_url("about"), "priority": "0.6"},
        {"loc": absolute_url("contact"), "priority": "0.6"},
        {"loc": absolute_url("privacy_policy"), "priority": "0.5"},
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
def dashboard():
    error = None
    subscribers = get_subscribers()

    try:
        threads = client.get_threads()
        save_threads(threads)
    except DisqusClientError as exc:
        error = str(exc)
        threads = get_cached_threads()

    return render_template("dashboard.html", threads=threads, subscribers=subscribers, error=error)


@app.route("/thread/<thread_id>")
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
