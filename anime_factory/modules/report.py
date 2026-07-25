from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def write_report(candidates: list[dict[str, Any]], output_paths: list[Path], report_path: Path) -> Path:
    output_by_id = {index + 1: path for index, path in enumerate(output_paths)}
    rows: list[str] = []
    for candidate in candidates:
        short_id = int(candidate["id"])
        crop = candidate.get("crop", {})
        preview_path = candidate.get("preview_path", "")
        preview_cell = _video_cell(preview_path, report_path.parent) if preview_path else ""
        comparison_path = candidate.get("comparison_preview_path", "")
        comparison_cell = _video_cell(comparison_path, report_path.parent) if comparison_path else escape(candidate.get("comparison_labels", ""))
        subtitles = "<br>".join(escape(segment.get("text", "")) for segment in candidate.get("subtitle_segments", []))
        reasons = "<br>".join(escape(reason) for reason in candidate.get("reason", []))
        warnings = "<br>".join(escape(item) for item in candidate.get("warnings", []) + crop.get("warnings", []))
        breakdown = "<br>".join(
            f"{escape(str(key))}: {escape(str(value))}" for key, value in candidate.get("score_breakdown", {}).items()
        )
        output = escape(str(candidate.get("output_path") or output_by_id.get(short_id, "")))
        selected_line = escape(f'"selected_candidate_ids": [{short_id}]')
        rows.append(
            "<tr>"
            f"<td>{short_id}</td>"
            f"<td>{preview_cell}</td>"
            f"<td>{comparison_cell}</td>"
            f"<td>{candidate['start']:.2f} - {candidate['end']:.2f}<br>{candidate['duration']:.2f}s</td>"
            f"<td>{candidate['score']:.4f}</td>"
            f"<td>{breakdown}</td>"
            f"<td>{reasons}</td>"
            f"<td>{warnings}</td>"
            f"<td>{escape(str(crop.get('crop_mode', '')))}</td>"
            f"<td>{escape(str(crop.get('crop_quality', '')))}</td>"
            f"<td>{output}</td>"
            f"<td><code>{selected_line}</code></td>"
            f"<td>{subtitles}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Anime Factory Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; vertical-align: top; }}
    th {{ background: #f2f2f2; text-align: left; position: sticky; top: 0; }}
    video {{ width: 220px; max-height: 390px; background: #111; }}
    code {{ white-space: nowrap; }}
  </style>
</head>
<body>
  <h1>Anime Factory Review</h1>
  <p>Выберите лучшие candidate id и сохраните их в selected.json.</p>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Preview</th>
        <th>Crop comparison</th>
        <th>Таймкод</th>
        <th>Score</th>
        <th>Score breakdown</th>
        <th>Reason</th>
        <th>Warnings</th>
        <th>Crop mode</th>
        <th>Crop quality</th>
        <th>Output</th>
        <th>selected.json строка</th>
        <th>Реплики</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    print(f"HTML-отчет сохранен: {report_path}")
    return report_path


def _video_cell(path: str, report_dir: Path) -> str:
    raw_path = Path(path)
    try:
        src = raw_path.resolve().relative_to(report_dir.resolve()).as_posix()
    except ValueError:
        src = raw_path.as_posix()
    escaped_src = escape(src)
    escaped_label = escape(str(path))
    return f'<video src="{escaped_src}" controls preload="metadata"></video><br><small>{escaped_label}</small>'
