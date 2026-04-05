"""Matter API client for authentication and article fetching."""

import httpx

BASE_URL = "https://api.getmatter.app/api/v11"


def parse_feed_entry(entry: dict) -> dict:
    content = entry["content"]
    author_obj = content.get("author")
    publisher_obj = content.get("publisher")
    library_obj = content.get("library")
    note_obj = content.get("my_note")

    article = {
        "id": entry["id"],
        "title": content["title"],
        "url": content["url"],
        "author": author_obj["any_name"] if author_obj else None,
        "publisher": publisher_obj["any_name"] if publisher_obj else None,
        "published_date": content.get("publication_date"),
        "note": note_obj.get("note") if note_obj else None,
        "library_state": library_obj["library_state"] if library_obj else None,
    }

    tags = [
        {"name": t["name"], "created_date": t.get("created_date")}
        for t in (content.get("tags") or [])
    ]

    highlights = [
        {
            "text": a["text"],
            "note": a.get("note"),
            "created_date": a.get("created_date"),
        }
        for a in (content.get("my_annotations") or [])
    ]

    return {"article": article, "tags": tags, "highlights": highlights}


class MatterClient:
    def __init__(self, access_token: str | None = None, refresh_token: str | None = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.http = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def trigger_qr_login(self) -> str:
        resp = self.http.post(
            f"{BASE_URL}/qr_login/trigger/",
            json={"client_type": "integration"},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["session_token"]

    def exchange_token(self, session_token: str) -> dict | None:
        resp = self.http.post(
            f"{BASE_URL}/qr_login/exchange/",
            json={"session_token": session_token},
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 408:
            return None
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def refresh_access_token(self) -> dict:
        resp = self.http.post(
            f"{BASE_URL}/token/refresh/",
            json={"refresh_token": self.refresh_token},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def fetch_all_articles(self) -> list[dict]:
        url = f"{BASE_URL}/library_items/updates_feed/"
        all_entries = []
        while url:
            resp = self.http.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            all_entries.extend(data.get("feed", []))
            url = data.get("next")
        return all_entries
