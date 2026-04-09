from studio.application.services.export_service import ExportService


def test_as_json_text_preserves_unicode():
    service = ExportService()
    text = service.as_json_text([{"greeting": "Olá"}])
    assert '"Olá"' in text


def test_as_csv_text_returns_empty_for_no_rows():
    service = ExportService()
    assert service.as_csv_text([]) == ""


def test_as_csv_text_writes_union_of_sorted_fields():
    service = ExportService()
    csv_text = service.as_csv_text([{"b": 2, "a": 1}, {"c": 3, "a": 9}])
    lines = csv_text.strip().splitlines()
    assert lines[0] == "a,b,c"
    assert "1,2," in lines[1]
    assert "9,,3" in lines[2]
