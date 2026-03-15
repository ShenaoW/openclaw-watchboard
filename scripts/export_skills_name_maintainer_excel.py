#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import sqlite3
import zipfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "skills.db"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "skills" / "skills_name_maintainer.xlsx"


def excel_column_name(index: int) -> str:
    name = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        name = chr(65 + remainder) + name
    return name


def make_inline_cell(ref: str, value: str) -> str:
    escaped = html.escape(value or "")
    return (
        f'<c r="{ref}" t="inlineStr">'
        f"<is><t>{escaped}</t></is>"
        f"</c>"
    )


def build_sheet_xml(rows: list[tuple[str, str]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{excel_column_name(col_index)}{row_index}"
            cells.append(make_inline_cell(ref, value))
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + "".join(xml_rows)
        + "</sheetData>"
        "</worksheet>"
    )


def write_xlsx(output_path: Path, rows: list[tuple[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="skills" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""

    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>OpenClaw Watchboard</Application>
</Properties>
"""

    core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Skills Name Maintainer Export</dc:title>
  <dc:creator>Codex</dc:creator>
</cp:coreProperties>
"""

    sheet_xml = build_sheet_xml(rows)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
      archive.writestr("[Content_Types].xml", content_types)
      archive.writestr("_rels/.rels", root_rels)
      archive.writestr("xl/workbook.xml", workbook)
      archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
      archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
      archive.writestr("docProps/app.xml", app)
      archive.writestr("docProps/core.xml", core)


def export_rows(db_path: Path) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
              COALESCE(name, '') AS name,
              COALESCE(NULLIF(TRIM(maintainer), ''), 'Unknown') AS maintainer
            FROM skills
            ORDER BY maintainer COLLATE NOCASE ASC, name COLLATE NOCASE ASC
            """
        ).fetchall()
    finally:
        conn.close()

    return [("名称", "开发者"), *[(str(name), str(maintainer)) for name, maintainer in rows]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export all skills name and maintainer rows to an Excel file.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to skills.db")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output .xlsx path")
    args = parser.parse_args()

    rows = export_rows(args.db_path)
    write_xlsx(args.output, rows)
    print(f"exported {len(rows) - 1} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
