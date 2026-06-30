import os

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


ARTICLES = [
    {
        "slug": "best-ai-tools-for-small-business",
        "title": "Best AI Tools for Small Business Teams",
        "category": "AI Tools",
        "summary": "A practical starter guide to AI tools that can help small teams save time, publish faster, and serve customers better.",
        "read_time": "5 min read",
        "published": "June 30, 2026",
        "body": [
            "Small businesses do not need a huge technical team to benefit from AI. The best starting point is choosing tools that remove repetitive work from daily operations.",
            "For content, AI writing assistants can help draft articles, summarize research, and create social posts. For customer support, chat assistants can answer common questions and collect leads while the owner focuses on higher value work.",
            "The most useful AI stack is simple: one tool for writing, one tool for automation, one tool for analytics, and one shared workflow your team can repeat every week.",
            "Before paying for anything, test each tool against a real business task. If it saves time, improves quality, or helps you publish more consistently, it is worth considering.",
        ],
    },
    {
        "slug": "ai-automation-workflows-for-beginners",
        "title": "AI Automation Workflows for Beginners",
        "category": "Automation",
        "summary": "How to turn simple business tasks into repeatable AI-assisted workflows without overcomplicating your stack.",
        "read_time": "6 min read",
        "published": "June 30, 2026",
        "body": [
            "Automation works best when it starts with a boring, repeated task. Examples include collecting form submissions, summarizing customer messages, drafting email replies, or turning notes into publishable content.",
            "A beginner workflow should have three steps: input, AI processing, and review. The review step matters because it keeps quality high and prevents the system from publishing weak output.",
            "Once the workflow is reliable, document it. A documented workflow is easier to improve, delegate, and measure.",
            "The goal is not to replace judgment. The goal is to give people more time for strategy, relationships, and creative decisions.",
        ],
    },
    {
        "slug": "how-ai-agents-help-content-sites-grow",
        "title": "How AI Agents Help Content Sites Grow",
        "category": "Growth",
        "summary": "A professional workflow for using AI agents to research topics, draft articles, optimize SEO, and learn from reader comments.",
        "read_time": "7 min read",
        "published": "June 30, 2026",
        "body": [
            "A content site grows faster when production is organized. AI agents can act like a small editorial team: one researches topics, one writes drafts, one edits, one checks SEO, and one studies audience feedback.",
            "Reader comments are especially valuable. They reveal objections, questions, and demand for follow-up content. A community agent can summarize comments and turn them into new article ideas.",
            "The professional approach is to publish consistently, measure what earns attention, and improve the next article based on data.",
            "AI does not remove the need for positioning. The site still needs a clear niche, useful content, and trust with readers.",
        ],
    },
]


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
