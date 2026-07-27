"""A simple figure drawn from the scene's own numbers, when no footage can be right.

Some scenes state a proportion. The confirmed run answered "nanoplastics were found at
54% of topsoil sites" with a border collie running through a field, because a stock
search for a statistic returns whatever the words happen to match. There is no footage
of a percentage, so searching for one is the wrong question.

This draws the figure instead: a static vertical SVG built only from values the scene
supplies. Deliberately small in scope - no animation, no motion framework, no new font
files (generic families only, so it renders the same on any machine), no copying of a
figure from a paper. Output is deterministic: the same spec always produces the same
bytes, which is what lets a project be rebuilt and compared.

The result is an ordinary local asset with ``generated_by_project`` provenance and
project-owned rights, so it travels through the existing rights report unchanged.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .models import AssetCandidate, AssetLicense, AssetProvenance

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
GENERATOR_ID = "project_infographic_v1"

# Neutral, high-contrast and readable at Shorts size. Not any organisation's palette.
_BACKGROUND = "#0d1b26"
_FOREGROUND = "#f2f6f8"
_ACCENT = "#4ea8de"
_MUTED = "#7b8e9b"
_FONT = "'DejaVu Sans', 'Segoe UI', Arial, Helvetica, sans-serif"


@dataclass
class InfographicSpec:
    """Everything the figure shows. No value is invented here."""

    title: str = ""
    headline_value: str = ""
    caption: str = ""
    # Dot grid: how many sample points, and how many of them are marked.
    total_points: int = 0
    active_points: int = 0
    points_label: str = ""
    # Two-layer cross-section: how many marks each layer carries.
    top_layer_label: str = ""
    top_layer_marks: int = 0
    deep_layer_label: str = ""
    deep_layer_marks: int = 0
    footnote: str = ""
    scene_id: str = ""

    def fingerprint(self) -> str:
        raw = "|".join(
            str(value)
            for value in (
                GENERATOR_ID, self.title, self.headline_value, self.caption,
                self.total_points, self.active_points, self.points_label,
                self.top_layer_label, self.top_layer_marks,
                self.deep_layer_label, self.deep_layer_marks, self.footnote,
            )
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "generator": GENERATOR_ID,
            "title": self.title,
            "headline_value": self.headline_value,
            "caption": self.caption,
            "total_points": self.total_points,
            "active_points": self.active_points,
            "points_label": self.points_label,
            "top_layer_label": self.top_layer_label,
            "top_layer_marks": self.top_layer_marks,
            "deep_layer_label": self.deep_layer_label,
            "deep_layer_marks": self.deep_layer_marks,
            "footnote": self.footnote,
            "fingerprint": self.fingerprint(),
        }


def spec_from_scene(scene: dict[str, Any]) -> InfographicSpec | None:
    """Read a figure spec off a scene's visual brief. ``None`` when the author gave none.

    Nothing is guessed from narration: a chart built from numbers this module inferred
    on its own would be a claim the script never made.
    """
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    data = brief.get("infographic") if isinstance(brief.get("infographic"), dict) else {}
    if not data:
        return None
    return InfographicSpec(
        title=str(data.get("title") or ""),
        headline_value=str(data.get("headline_value") or data.get("value") or ""),
        caption=str(data.get("caption") or ""),
        total_points=_int(data.get("total_points")),
        active_points=_int(data.get("active_points")),
        points_label=str(data.get("points_label") or ""),
        top_layer_label=str(data.get("top_layer_label") or ""),
        top_layer_marks=_int(data.get("top_layer_marks")),
        deep_layer_label=str(data.get("deep_layer_label") or ""),
        deep_layer_marks=_int(data.get("deep_layer_marks")),
        footnote=str(data.get("footnote") or ""),
        scene_id=str(scene.get("scene_id") or ""),
    )


def layout_operations(spec: InfographicSpec) -> list[dict[str, Any]]:
    """The figure as a list of primitive draw operations.

    One layout, two renderers. ``render_svg`` is the record of what was drawn and what
    the project has always written; ``render_png`` is what ffmpeg can actually put into
    a video (nothing in this repository rasterises SVG). Deriving both from the same
    ops is what stops the two from drifting apart.
    """
    ops: list[dict[str, Any]] = []
    cursor = 340
    if spec.title:
        ops.append(_text_op(spec.title, y=cursor, size=58, fill=_FOREGROUND, weight="600"))
        cursor += 150
    if spec.headline_value:
        ops.append(_text_op(spec.headline_value, y=cursor + 120, size=260, fill=_ACCENT, weight="700"))
        cursor += 250
    if spec.caption:
        ops.append(_text_op(spec.caption, y=cursor + 90, size=46, fill=_MUTED))
        cursor += 150

    if spec.total_points > 0:
        cursor += 90
        ops.extend(_dot_grid(spec, top=cursor))
        cursor += _dot_grid_height(spec.total_points)
        if spec.points_label:
            cursor += 60
            ops.append(_text_op(spec.points_label, y=cursor, size=38, fill=_MUTED))
            cursor += 30

    if spec.top_layer_marks or spec.deep_layer_marks:
        cursor += 110
        ops.extend(_cross_section(spec, top=cursor))
        cursor += 380

    if spec.footnote:
        ops.append(_text_op(spec.footnote, y=CANVAS_HEIGHT - 120, size=32, fill=_MUTED))
    return ops


def render_svg(spec: InfographicSpec) -> str:
    """The figure as a standalone SVG string. Pure - no filesystem, no clock."""
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" '
        f'viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" role="img">',
        f'<rect width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="{_BACKGROUND}"/>',
    ]
    parts.extend(_op_to_svg(op) for op in layout_operations(spec))
    parts.append("</svg>")
    return "\n".join(parts)


def render_png(spec: InfographicSpec) -> Image.Image:
    """The same figure as a raster frame the existing renderer can use.

    Deterministic: identical specs produce identical pixels on the same machine. Font
    selection falls back through the same candidates the story-card renderer uses, so
    no font binary is added to the repository.
    """
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), _BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    for op in layout_operations(spec):
        kind = op["op"]
        if kind == "text":
            font = _load_font(int(op["size"]), bold=str(op.get("weight") or "400") in {"600", "700"})
            anchor = "mm" if op.get("anchor") == "middle" else "lm"
            draw.text((op["x"], op["y"]), str(op["value"]), font=font, fill=op["fill"], anchor=anchor)
        elif kind == "circle":
            box = (
                op["cx"] - op["r"], op["cy"] - op["r"],
                op["cx"] + op["r"], op["cy"] + op["r"],
            )
            draw.ellipse(box, fill=op.get("fill"), outline=op.get("stroke"), width=int(op.get("stroke_width") or 1))
        elif kind == "rect":
            box = (op["x"], op["y"], op["x"] + op["width"], op["y"] + op["height"])
            draw.rounded_rectangle(
                box,
                radius=int(op.get("radius") or 0),
                fill=op.get("fill"),
                outline=op.get("stroke"),
                width=int(op.get("stroke_width") or 1),
            )
    return canvas


def backdrop_spec_for_scene(scene: dict[str, Any], *, label: str = "") -> InfographicSpec:
    """A neutral card for a scene nothing else could fill honestly.

    The last rung of the fallback ladder. It states nothing: no invented number, no
    claim about a place, no stand-in footage presented as the event. ``label`` is used
    only when the author already wrote it (the script's own ``on_screen_text``) - this
    function never composes a sentence of its own, and it never repeats the narration,
    which is already on screen as subtitles.
    """
    return InfographicSpec(title=str(label or "").strip(), scene_id=str(scene.get("scene_id") or ""))


def build_generated_asset(
    spec: InfographicSpec,
    *,
    project_root: str | Path,
    project_id: str,
    scene_id: str,
    variant: str = "infographic",
) -> dict[str, Any]:
    """Render the figure into the project and describe it as an ordinary asset.

    Two files are written: the SVG (the record of what was drawn, unchanged since the
    figure generator was introduced) and a PNG, which is what the asset actually points
    at. Nothing in this repository rasterises SVG, so before this the drawn figure could
    be selected but never rendered.
    """
    root = Path(project_root)
    generated_dir = root / "assets" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    # The specification is part of the filename, not only the logical asset id.
    # Adaptation may generate a revised figure before deciding whether to accept it;
    # a stable scene-only filename would overwrite the bytes referenced by the active
    # manifest while leaving its checksum and metadata stale.
    fingerprint = spec.fingerprint()
    stem = f"{scene_id or 'scene'}_{variant}_{fingerprint[:12]}"
    svg_path = generated_dir / f"{stem}.svg"
    destination = generated_dir / f"{stem}.png"
    svg = render_svg(spec)
    svg_path.write_text(svg, encoding="utf-8")
    render_png(spec).save(destination, format="PNG")
    with Image.open(destination) as rendered:
        if rendered.format != "PNG" or rendered.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            raise ValueError("Generated infographic is not a valid 1080x1920 PNG.")
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    asset_id = f"generated_{GENERATOR_ID}_{variant}_{fingerprint[:12]}"
    source_uri = f"project-generated://{project_id}/{scene_id}/{asset_id}"
    metadata = {
        "generated_by_project": True,
        "variant": variant,
        "svg_path": str(svg_path),
        "spec": spec.to_dict(),
    }
    candidate = AssetCandidate(
        asset_id=asset_id,
        provider="generated",
        provider_asset_id=fingerprint[:16],
        media_type="image",
        title=spec.title or "Project infographic",
        description=" ".join(part for part in (spec.title, spec.headline_value, spec.caption) if part),
        tags=[word.lower() for word in (spec.title or "").split() if word],
        tags_source="provider",
        source_page_url=source_uri,
        preview_url="",
        download_url=source_uri,
        author_name="AI-YouTube project generator",
        width=CANVAS_WIDTH,
        height=CANVAS_HEIGHT,
        duration_sec=0.0,
        orientation="vertical",
        search_query="",
        local_path=str(destination),
        original_filename=destination.name,
        checksum_sha256=checksum,
        project_id=project_id,
        scene_id=scene_id,
        license=AssetLicense(
            license_name="project_generated",
            rights_status="user_owned",
            commercial_use_allowed=True,
            modification_allowed=True,
            attribution_required=False,
            attribution_text="",
            allowed_for_render=True,
            review_required=False,
            notes="Drawn by this project from values stated in the scene's visual brief.",
        ),
        provenance=AssetProvenance(
            provider="generated",
            provider_asset_id=fingerprint[:16],
            source_page_url=source_uri,
            download_url=source_uri,
            original_filename=destination.name,
            checksum_sha256=checksum,
            project_id=project_id,
            scene_id=scene_id,
            search_query="",
            metadata_snapshot=dict(metadata),
        ),
        raw_metadata=dict(metadata),
        technical_validation={
            "status": "passed",
            "media_type": "image",
            "width": CANVAS_WIDTH,
            "height": CANVAS_HEIGHT,
            "orientation": "vertical",
            "codec": "png",
        },
        crop_suitability_score=100.0,
    )
    data = candidate.to_manifest_dict()
    data["selected_by"] = f"generated_{variant}"
    data["download_status"] = "generated"
    data["quality_score"] = 100.0
    data["vertical_score"] = 100.0
    data["svg_path"] = str(svg_path)
    return data


def _dot_grid(spec: InfographicSpec, *, top: int) -> list[dict[str, Any]]:
    columns = min(spec.total_points, 7) or 1
    radius = 34
    gap = 46
    span = columns * (radius * 2) + (columns - 1) * gap
    start_x = (CANVAS_WIDTH - span) // 2 + radius
    shapes: list[dict[str, Any]] = []
    for index in range(spec.total_points):
        row, column = divmod(index, columns)
        cx = start_x + column * (radius * 2 + gap)
        cy = top + row * (radius * 2 + gap)
        if index < spec.active_points:
            shapes.append({"op": "circle", "cx": cx, "cy": cy, "r": radius, "fill": _ACCENT})
        else:
            shapes.append(
                {"op": "circle", "cx": cx, "cy": cy, "r": radius - 3, "fill": None, "stroke": _MUTED, "stroke_width": 5}
            )
    return shapes


def _dot_grid_height(total_points: int) -> int:
    columns = min(total_points, 7) or 1
    rows = (total_points + columns - 1) // columns
    return rows * 114


def _cross_section(spec: InfographicSpec, *, top: int) -> list[dict[str, Any]]:
    left, width, height = 140, CANVAS_WIDTH - 280, 150
    shapes: list[dict[str, Any]] = []
    for offset, label, marks in (
        (0, spec.top_layer_label, spec.top_layer_marks),
        (height + 60, spec.deep_layer_label, spec.deep_layer_marks),
    ):
        y = top + offset
        shapes.append(
            {
                "op": "rect", "x": left, "y": y, "width": width, "height": height,
                "fill": None, "stroke": _MUTED, "stroke_width": 4, "radius": 10,
            }
        )
        for index in range(max(0, marks)):
            cx = left + 70 + (index % 9) * ((width - 140) // 8 if marks > 1 else 0)
            cy = y + 50 + (index // 9) * 50
            shapes.append({"op": "circle", "cx": cx, "cy": cy, "r": 13, "fill": _ACCENT})
        if label:
            shapes.append(
                {"op": "text", "value": label, "x": left, "y": y - 20, "size": 34, "fill": _MUTED,
                 "weight": "400", "anchor": "start"}
            )
    return shapes


def _text_op(value: str, *, y: int, size: int, fill: str, weight: str = "400") -> dict[str, Any]:
    return {
        "op": "text", "value": value, "x": CANVAS_WIDTH // 2, "y": y,
        "size": size, "fill": fill, "weight": weight, "anchor": "middle",
    }


def _op_to_svg(op: dict[str, Any]) -> str:
    kind = op["op"]
    if kind == "text":
        anchor = 'text-anchor="middle" ' if op.get("anchor") == "middle" else ""
        return (
            f'<text x="{op["x"]}" y="{op["y"]}" {anchor}font-family="{_FONT}" '
            f'font-size="{op["size"]}" font-weight="{op.get("weight", "400")}" '
            f'fill="{op["fill"]}">{_escape(op["value"])}</text>'
        )
    if kind == "circle":
        fill = op.get("fill") or "none"
        stroke = op.get("stroke")
        stroke_attrs = f' stroke="{stroke}" stroke-width="{op.get("stroke_width", 1)}"' if stroke else ""
        return f'<circle cx="{op["cx"]}" cy="{op["cy"]}" r="{op["r"]}" fill="{fill}"{stroke_attrs}/>'
    fill = op.get("fill") or "none"
    stroke = op.get("stroke")
    stroke_attrs = f' stroke="{stroke}" stroke-width="{op.get("stroke_width", 1)}"' if stroke else ""
    return (
        f'<rect x="{op["x"]}" y="{op["y"]}" width="{op["width"]}" height="{op["height"]}" '
        f'fill="{fill}"{stroke_attrs} rx="{op.get("radius", 0)}"/>'
    )


def _load_font(size: int, *, bold: bool = False) -> Any:
    """A usable font, or PIL's built-in one. Never installs or ships a font file.

    Same candidate order as ``src.production_plan.story_card_short_render`` - the two
    are independent renderers and this is the one fact they have to agree on.
    """
    candidates: list[str] = []
    if bold:
        candidates.extend(["DejaVuSans-Bold.ttf", "arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf"])
    candidates.extend(["DejaVuSans.ttf", "arial.ttf", "C:/Windows/Fonts/arial.ttf"])
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "CANVAS_HEIGHT",
    "CANVAS_WIDTH",
    "GENERATOR_ID",
    "InfographicSpec",
    "backdrop_spec_for_scene",
    "build_generated_asset",
    "layout_operations",
    "render_png",
    "render_svg",
    "spec_from_scene",
]
