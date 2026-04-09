from __future__ import annotations

from studio.infrastructure.scraping.content_extractor import clean_plaintext_anysite, extract_article_content


def test_extract_article_content_returns_metadata_and_clean_body_for_basic_article_html():
    html = b"""
    <html>
      <head>
        <title>Useful guide | Example Site</title>
        <meta name='author' content='A. Writer'>
        <meta property='og:site_name' content='Example Site'>
        <meta property='article:modified_time' content='2026-01-02T10:11:12Z'>
      </head>
      <body>
        <nav role='navigation'>Skip to content</nav>
        <main>
          <h1>Useful guide</h1>
          <p>First substantive paragraph.</p>
          <h2>Related articles</h2>
          <p>Read more links.</p>
        </main>
      </body>
    </html>
    """

    result = extract_article_content(html, "https://example.com/docs/3.2/guide")

    assert result["title"] == "Useful guide"
    assert result["author"] == "A. Writer"
    assert result["publisher"] == "Example Site"
    assert result["version"] == "3.2"
    assert result["body"].startswith("Author: A. Writer")
    assert "Last Updated: 2026-01-02" in result["body"]
    assert "Skip to content" not in result["body"]


def test_extract_article_content_formats_code_blocks_with_language_fences():
    html = b"""
    <html>
      <head><title>Code docs - Site</title></head>
      <body>
        <main>
          <h1>Code docs</h1>
          <p>Run this:</p>
          <pre class='language-python'>print('hello')\nprint('world')</pre>
        </main>
      </body>
    </html>
    """

    result = extract_article_content(html, "https://docs.example.com/reference")

    assert "```python" in result["body"]
    assert "print('hello')" in result["body"]
    assert "```" in result["body"]


def test_extract_article_content_handles_malformed_html_without_crashing():
    html = b"<html><head><title>X</title></head><body><main><h1>Broken<p>still content"

    result = extract_article_content(html, "https://example.org/post")

    assert result["title"] == "X"
    assert "Source: https://example.org/post" in result["body"]
    assert "still content" in result["body"]


def test_clean_plaintext_anysite_removes_noise_dedupes_and_stops_at_cutoff_heading():
    raw_text = """
    Intro paragraph with value.

    Intro paragraph with value.

    Copyright 2026, all rights reserved.

    References

    This part should be trimmed.
    """

    cleaned = clean_plaintext_anysite(raw_text)

    assert "Intro paragraph with value." in cleaned
    assert cleaned.count("Intro paragraph with value.") == 1
    assert "Copyright" not in cleaned
    assert "This part should be trimmed" not in cleaned
