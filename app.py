import os

from dotenv import load_dotenv
from flask import Flask, abort, render_template

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


@app.before_request
def prepare_database():
    init_db()


@app.route("/")
def dashboard():
    error = None

    try:
        threads = client.get_threads()
        save_threads(threads)
    except DisqusClientError as exc:
        error = str(exc)
        threads = get_cached_threads()

    return render_template("dashboard.html", threads=threads, error=error)

@app.route("/article")
def article():
    return render_template(
        "article.html",
        disqus_forum=os.getenv("DISQUS_FORUM", "")
    )

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
