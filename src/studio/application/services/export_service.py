"""Application service: export helpers for generated artifacts."""

from __future__ import annotations

import csv
import io
import json


class ExportService:
    """Export JSON/CSV flows migrated from legacy dataset generation views."""

    def as_json_text(self, data: list[dict] | dict) -> str:
        return json.dumps(data, indent=4, ensure_ascii=False)

    def as_csv_text(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        output = io.StringIO()
        fieldnames = sorted({k for row in rows for k in row.keys()})
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
