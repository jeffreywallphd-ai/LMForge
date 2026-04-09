import json
from pathlib import Path

from studio.infrastructure.scraping.generic_web import GenericWebScraper
from studio.infrastructure.scraping.reddit import RedditScraper
from studio.infrastructure.storage.exports import export_records_json
from studio.infrastructure.storage.files import write_text


class _FakeResponse:
    def __init__(self, *, headers=None, text="", json_data=None, content=b""):
        self.headers = headers or {}
        self.text = text
        self._json_data = json_data
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


def test_generic_web_to_export_to_file_pipeline(monkeypatch, tmp_path: Path):
    html = b"<html><head><title>Pipeline</title></head><body><main><p>Pipeline body</p></main></body></html>"

    monkeypatch.setattr(
        "studio.infrastructure.scraping.generic_web.requests.get",
        lambda *_a, **_k: _FakeResponse(headers={"content-type": "text/html"}, content=html),
    )

    scraper = GenericWebScraper()
    scraped = scraper.scrape("https://example.com/pipeline")

    exported = export_records_json(
        [{"file_type": scraped.file_type, "title": scraped.extracted_title, "content": scraped.content}]
    )
    out = write_text(tmp_path / "exports" / "pipeline.json", exported)

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved[0]["file_type"] == "html"
    assert "Pipeline body" in saved[0]["content"]


def test_reddit_subreddit_scrape_collects_unique_posts(monkeypatch):
    scraper = RedditScraper()

    listing_payload = {
        "data": {
            "children": [
                {"data": {"id": "1", "title": "One", "permalink": "/r/test/comments/1/one"}},
                {"data": {"id": "1", "title": "One dup", "permalink": "/r/test/comments/1/one"}},
            ]
        }
    }
    post_payload = [
        {"data": {"children": [{"data": {"title": "One", "author": "alice", "selftext": "Body"}}]}},
        {"data": {"children": []}},
    ]

    call_index = {"i": 0}

    def _fake_get(url, **_kwargs):
        if "hot.json" in url or "new.json" in url or "rising.json" in url or "best.json" in url or "top.json" in url:
            return _FakeResponse(json_data=listing_payload)
        call_index["i"] += 1
        return _FakeResponse(json_data=post_payload)

    monkeypatch.setattr("studio.infrastructure.scraping.reddit.requests.get", _fake_get)
    monkeypatch.setattr("studio.infrastructure.scraping.reddit.time.sleep", lambda *_a, **_k: None)

    result = scraper.scrape("https://www.reddit.com/r/test", delay_seconds=0)

    assert result.file_type == "reddit_subreddit_full"
    assert result.extracted_title == "Scrape of r/test"
    assert result.content.count("POST: One") == 1
