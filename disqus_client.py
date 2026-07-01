import requests


class DisqusClientError(Exception):
    pass


class DisqusClient:
    BASE_URL = "https://disqus.com/api/3.0"

    def __init__(self, api_key, forum):
        self.api_key = api_key
        self.forum = forum

    def _request(self, endpoint, params=None):
        if not self.api_key or not self.forum:
            raise DisqusClientError("DISQUS_API_KEY and DISQUS_FORUM must be set in .env.")

        query = {
            "api_key": self.api_key,
            "forum": self.forum,
        }
        query.update(params or {})

        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=query,
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DisqusClientError(f"Could not connect to Disqus: {exc}") from exc

        payload = response.json()
        code = payload.get("code")
        if code != 0:
            message = payload.get("response") or payload.get("error") or "Unknown Disqus error."
            raise DisqusClientError(str(message))

        return payload.get("response", [])

    def get_threads(self, limit=25):
        data = self._request(
            "forums/listThreads.json",
            {
                "limit": limit,
                "order": "desc",
                "related": "forum",
            },
        )

        return [
            {
                "id": str(item.get("id", "")),
                "title": item.get("title") or "Untitled thread",
                "link": item.get("link") or "",
                "posts": item.get("posts") or 0,
                "likes": item.get("likes") or 0,
                "created_at": item.get("createdAt") or "",
            }
            for item in data
        ]

    def get_posts(self, thread_id, limit=50):
        data = self._request(
            "threads/listPosts.json",
            {
                "thread": thread_id,
                "limit": limit,
                "order": "desc",
                "include": "approved",
            },
        )

        return [
            {
                "id": str(item.get("id", "")),
                "author": (item.get("author") or {}).get("name") or "Anonymous",
                "message": item.get("message") or "",
                "created_at": item.get("createdAt") or "",
                "likes": item.get("likes") or 0,
            }
            for item in data
        ]
