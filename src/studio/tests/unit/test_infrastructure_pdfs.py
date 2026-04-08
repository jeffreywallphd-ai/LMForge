from types import SimpleNamespace

from src.studio.infrastructure.scraping.pdfs import convert_pdf_text, extract_pdf_text


class _FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


def test_extract_pdf_text_collects_non_empty_pages(monkeypatch):
    fake_pdf = _FakePdf([_FakePage("page one"), _FakePage(None), _FakePage("page three")])
    monkeypatch.setattr("src.studio.infrastructure.scraping.pdfs.pdfplumber.open", lambda _file: fake_pdf)

    text = extract_pdf_text(SimpleNamespace(name="any.pdf"))

    assert text == "page one\n\npage three"


def test_convert_pdf_text_supports_text_html_json():
    body = "Hello **PDF**"

    text_payload, text_type = convert_pdf_text(body, "text")
    html_payload, html_type = convert_pdf_text(body, "html")
    json_payload, json_type = convert_pdf_text(body, "json")

    assert (text_payload, text_type) == (body, "text")
    assert html_type == "html" and "<p>Hello <strong>PDF</strong></p>" in html_payload
    assert json_type == "json" and '"text": "Hello **PDF**"' in json_payload


def test_convert_pdf_text_unknown_format_defaults_to_text():
    payload, fmt = convert_pdf_text("x", "yaml")
    assert payload == "x"
    assert fmt == "text"
