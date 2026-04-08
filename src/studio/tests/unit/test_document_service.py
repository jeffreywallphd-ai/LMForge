import types

from src.studio.application.services.document_service import DocumentService, ScrapedPayload


class _FakeParsed:
    def __init__(self, *, extracted_title="", file_type="html", content=""):
        self.extracted_title = extracted_title
        self.file_type = file_type
        self.content = content


class _FakeScraper:
    def __init__(self, parsed):
        self._parsed = parsed

    def scrape(self, _url):
        return self._parsed


def test_remove_emojis_strips_unicode_emoji():
    service = DocumentService(generic_web_scraper=_FakeScraper(_FakeParsed()))
    assert service.remove_emojis("Hello 😀 world 🚀") == "Hello  world "


def test_split_text_chunks_by_word_count_without_tokenizer():
    service = DocumentService(generic_web_scraper=_FakeScraper(_FakeParsed()))
    text = "one two\n\nthree four five\n\nsix"

    chunks = service.split_text(text, max_tokens=4)

    assert chunks == ["one two", "three four five\n\nsix"]


def test_split_text_uses_tokenizer_when_provided():
    service = DocumentService(generic_web_scraper=_FakeScraper(_FakeParsed()))

    class Tok:
        def encode(self, text):
            return text.split()

    chunks = service.split_text("a b\n\nc d e", max_tokens=2, tokenizer=Tok())
    assert chunks == ["a b", "c d e"]


def test_scrape_generic_url_prefers_explicit_title_and_strips_emoji():
    parsed = _FakeParsed(extracted_title="FromPage", file_type="html", content="Clean 😀 text")
    service = DocumentService(generic_web_scraper=_FakeScraper(parsed))

    payload = service.scrape_generic_url("https://example.com", title=" Given Title ")

    assert payload == ScrapedPayload(
        url="https://example.com",
        file_type="html",
        title=" Given Title ",
        content="Clean  text",
    )


def test_scrape_generic_url_uses_extracted_title_or_url_fallback():
    parsed = _FakeParsed(extracted_title="", file_type="pdf", content="x")
    service = DocumentService(generic_web_scraper=_FakeScraper(parsed))

    payload = service.scrape_generic_url("https://example.com/abc", title="")

    assert payload.title == "https://example.com/abc"
    assert payload.file_type == "pdf"


def test_persist_source_document_calls_model_manager(monkeypatch):
    created = {}

    def _create(**kwargs):
        created.update(kwargs)
        return types.SimpleNamespace(id=7, **kwargs)

    monkeypatch.setattr(
        "src.studio.application.services.document_service.SourceDocument.objects.create",
        _create,
    )

    service = DocumentService(generic_web_scraper=_FakeScraper(_FakeParsed()))
    payload = ScrapedPayload(url="u", file_type="html", title="t", content="c")

    saved = service.persist_source_document(payload)

    assert saved.id == 7
    assert created == {"url": "u", "file_type": "html", "content": "c", "title": "t"}
