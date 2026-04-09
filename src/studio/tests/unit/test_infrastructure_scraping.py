import json

import pytest
from bs4 import BeautifulSoup

from studio.infrastructure.scraping.content_extractor import (
    _process_list_recursive,
    clean_plaintext_anysite,
    extract_article_content,
)
from studio.infrastructure.scraping.generic_web import GenericWebScraper
from studio.infrastructure.scraping.reddit import RedditScraper


class _FakeResponse:
    def __init__(self, *, headers=None, text="", json_data=None, content=b"", status_ok=True):
        self.headers = headers or {}
        self.text = text
        self._json_data = json_data
        self.content = content
        self.status_ok = status_ok

    def raise_for_status(self):
        if not self.status_ok:
            raise RuntimeError("bad status")

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


def test_clean_plaintext_anysite_dedupes_and_applies_cutoff():
    text = "Intro\n\nDetails\n\nDetails\n\nRelated Articles\n\nShould be removed"

    cleaned = clean_plaintext_anysite(text)

    assert cleaned == "Intro\n\nDetails"


def test_extract_article_content_includes_metadata_and_removes_ui_chrome():
    html = b"""
    <html>
      <head>
        <title>Example Article | Example Site</title>
        <meta name=\"author\" content=\"Jane Writer\" />
        <meta property=\"article:published_time\" content=\"2024-01-02T01:02:03Z\" />
      </head>
      <body>
        <main>
          <h1>Main Heading</h1>
          <p>Important content paragraph one.</p>
          <p>Share</p>
          <p>Follow</p>
        </main>
      </body>
    </html>
    """

    result = extract_article_content(html, "https://example.com/path")

    assert result["title"] == "Example Article"
    assert "Author: Jane Writer" in result["body"]
    assert "Last Updated: 2024-01-02" in result["body"]
    assert "Source: https://example.com/path" in result["body"]
    assert "Important content paragraph one." in result["body"]
    assert "\nShare\n" not in result["body"]
    assert "\nFollow\n" not in result["body"]


def test_process_list_recursive_formats_nested_lists():
    soup = BeautifulSoup(
        """
        <ol>
          <li>First</li>
          <li>Second<ul><li>Nested A</li><li>Nested B</li></ul></li>
        </ol>
        """,
        "html.parser",
    )

    lines = _process_list_recursive(soup.find("ol"), depth=0)

    assert lines[0] == "1. First"
    assert lines[1] == "2. Second"
    assert lines[2] == "  - Nested A"
    assert lines[3] == "  - Nested B"


def test_generic_web_scraper_supports_structured_and_plain_types(monkeypatch):
    scraper = GenericWebScraper()

    fake_json = _FakeResponse(headers={"content-type": "application/json"}, json_data={"a": 1}, text='{"a":1}')
    fake_xml = _FakeResponse(headers={"content-type": "application/xml"}, text="<root />")
    fake_txt = _FakeResponse(headers={"content-type": "text/plain"}, text="hello")
    fake_csv = _FakeResponse(headers={"content-type": "text/csv"}, text="a,b")

    responses = [fake_json, fake_xml, fake_txt, fake_csv]
    monkeypatch.setattr("studio.infrastructure.scraping.generic_web.requests.get", lambda *_a, **_k: responses.pop(0))

    json_result = scraper.scrape("https://e.com/data")
    xml_result = scraper.scrape("https://e.com/feed")
    txt_result = scraper.scrape("https://e.com/file.txt")
    csv_result = scraper.scrape("https://e.com/file.csv")

    assert json.loads(json_result.content) == {"a": 1}
    assert json_result.file_type == "json"
    assert xml_result == type(xml_result)(file_type="xml", content="<root />", extracted_title="")
    assert txt_result.file_type == "text" and txt_result.content == "hello"
    assert csv_result.file_type == "csv" and csv_result.content == "a,b"


def test_generic_web_scraper_html_fallback_when_extractor_fails(monkeypatch):
    scraper = GenericWebScraper()

    raw_html = b"<html><head><title>T</title></head><body><main><p>Hello fallback</p></main></body></html>"
    response = _FakeResponse(headers={"content-type": "text/html"}, content=raw_html)

    monkeypatch.setattr("studio.infrastructure.scraping.generic_web.requests.get", lambda *_a, **_k: response)
    monkeypatch.setattr(
        "studio.infrastructure.scraping.generic_web.extract_article_content",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = scraper.scrape("https://e.com/page")

    assert result.file_type == "html"
    assert "Hello fallback" in result.content
    assert result.extracted_title == "T"


def test_reddit_scraper_dispatch_and_append_comments(monkeypatch):
    scraper = RedditScraper()

    post_payload = [
        {"data": {"children": [{"data": {"title": "Post", "author": "alice", "selftext": "Body"}}]}},
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "author": "bob",
                            "body": "Top comment",
                            "replies": {
                                "data": {
                                    "children": [{"kind": "t1", "data": {"author": "carol", "body": "Nested"}}]
                                }
                            },
                        },
                    }
                ]
            }
        },
    ]
    monkeypatch.setattr(
        "studio.infrastructure.scraping.reddit.requests.get",
        lambda *_a, **_k: _FakeResponse(json_data=post_payload),
    )

    result = scraper.scrape("https://www.reddit.com/r/test/comments/123/post", delay_seconds=0)

    assert result.file_type == "reddit_post"
    assert "Title: Post" in result.content
    assert "> u/bob:" in result.content
    assert "  > u/carol:" in result.content


def test_reddit_scraper_rejects_invalid_urls():
    scraper = RedditScraper()
    with pytest.raises(ValueError, match="Invalid Reddit URL"):
        scraper.scrape("https://www.reddit.com/user/someone")
