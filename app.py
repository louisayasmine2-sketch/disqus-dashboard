import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, url_for

from database import close_db, get_cached_posts, get_cached_threads, init_db, save_posts, save_threads
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


def load_articles():
    with CONTENT_PATH.open(encoding="utf-8") as file:
        return json.load(file)


ARTICLES = load_articles()


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
    return render_template("home.html", articles=ARTICLES[:3])


@app.route("/articles")
def articles():
    return render_template("articles.html", articles=ARTICLES)


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
        canonical_url=request.url,
    )


@app.route("/dashboard")
def dashboard():
    error = None

    try:
        threads = client.get_threads()
        save_threads(threads)
    except DisqusClientError as exc:
        error = str(exc)
        threads = get_cached_threads()

    return render_template("dashboard.html", threads=threads, error=error)


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
