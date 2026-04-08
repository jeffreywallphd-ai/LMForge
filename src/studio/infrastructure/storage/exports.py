"""Export helpers for scraped/document content."""

from __future__ import annotations

import csv
import io
import json
from typing import Iterable


def export_records_json(records: Iterable[dict]) -> str:
    return json.dumps(list(records), indent=2, ensure_ascii=False)


def export_records_csv(records: Iterable[dict]) -> str:
    records_list = list(records)
    if not records_list:
        return ""

    headers = sorted({key for row in records_list for key in row.keys()})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in records_list:
        writer.writerow(row)
    return buffer.getvalue()
