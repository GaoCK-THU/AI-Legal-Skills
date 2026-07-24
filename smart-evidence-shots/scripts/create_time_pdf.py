#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


@dataclass(frozen=True)
class LabelStyle:
    font_name: str = "Helvetica"
    font_size: float = 28
    position: str = "top-left"
    margin: float = 18
    pad_x: float = 10
    pad_y: float = 6
    fill_color: str = "white"
    stroke_color: str = "black"
    text_color: str = "black"
    stroke_width: float = 1


DEFAULT_STYLE = LabelStyle()
POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a full-bleed screenshot PDF with time labels."
    )
    parser.add_argument(
        "--shot-dir",
        required=True,
        type=Path,
        help="Directory containing evidence_manifest.csv and screenshots.",
    )
    parser.add_argument("--out", required=True, type=Path, help="Output PDF path.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest CSV path. Defaults to <shot-dir>/evidence_manifest.csv.",
    )
    parser.add_argument(
        "--style-config",
        type=Path,
        help=(
            "Optional JSON file overriding label style defaults. Supported keys: "
            + ", ".join(asdict(DEFAULT_STYLE))
        ),
    )
    return parser.parse_args()


def rows_from_manifest(manifest: Path) -> list[dict[str, str]]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows found in {manifest}")
    for required in ("timecode", "filename"):
        if required not in rows[0]:
            raise RuntimeError(f"Manifest missing required column: {required}")
    return rows


def _number(value: Any, name: str, minimum: float, *, strictly_greater: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Style key {name!r} must be a number")
    result = float(value)
    valid = result > minimum if strictly_greater else result >= minimum
    if not valid:
        operator = ">" if strictly_greater else ">="
        raise ValueError(f"Style key {name!r} must be {operator} {minimum}")
    return result


def load_style(config_path: Path | None) -> LabelStyle:
    values: dict[str, Any] = asdict(DEFAULT_STYLE)
    if config_path is not None:
        with config_path.open("r", encoding="utf-8") as handle:
            overrides = json.load(handle)
        if not isinstance(overrides, dict):
            raise ValueError("Style config must contain one JSON object")
        unknown = sorted(set(overrides) - set(values))
        if unknown:
            raise ValueError(f"Unknown style key(s): {', '.join(unknown)}")
        values.update(overrides)

    font_name = values["font_name"]
    position = values["position"]
    if not isinstance(font_name, str) or not font_name.strip():
        raise ValueError("Style key 'font_name' must be a non-empty string")
    if not isinstance(position, str) or position not in POSITIONS:
        raise ValueError(
            "Style key 'position' must be one of: " + ", ".join(sorted(POSITIONS))
        )

    for color_key in ("fill_color", "stroke_color", "text_color"):
        color_value = values[color_key]
        if not isinstance(color_value, str) or not color_value.strip():
            raise ValueError(f"Style key {color_key!r} must be a non-empty color string")
        try:
            colors.toColor(color_value)
        except Exception as exc:
            raise ValueError(f"Invalid color for {color_key!r}: {color_value!r}") from exc

    return LabelStyle(
        font_name=font_name.strip(),
        font_size=_number(values["font_size"], "font_size", 0, strictly_greater=True),
        position=position,
        margin=_number(values["margin"], "margin", 0, strictly_greater=False),
        pad_x=_number(values["pad_x"], "pad_x", 0, strictly_greater=False),
        pad_y=_number(values["pad_y"], "pad_y", 0, strictly_greater=False),
        fill_color=values["fill_color"],
        stroke_color=values["stroke_color"],
        text_color=values["text_color"],
        stroke_width=_number(
            values["stroke_width"], "stroke_width", 0, strictly_greater=False
        ),
    )


def time_label(timecode: str) -> str:
    text = timecode.strip()
    if not re.fullmatch(r"\d+:\d{2}(?::\d{2})?", text):
        raise ValueError(f"Unexpected timecode: {timecode!r}")
    parts = [int(part) for part in text.split(":")]
    if len(parts) == 2:
        _, seconds = parts
        if seconds >= 60:
            raise ValueError(f"Unexpected timecode: {timecode!r}")
    else:
        _, minutes, seconds = parts
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"Unexpected timecode: {timecode!r}")
    return text


def draw_time_box(
    pdf: canvas.Canvas,
    label: str,
    page_width: float,
    page_height: float,
    style: LabelStyle,
) -> None:
    try:
        pdf.setFont(style.font_name, style.font_size)
    except Exception as exc:
        raise ValueError(
            f"Unavailable PDF font {style.font_name!r}; use a registered ReportLab font"
        ) from exc

    text_width = pdf.stringWidth(label, style.font_name, style.font_size)
    ascent = pdfmetrics.getAscent(style.font_name, style.font_size)
    descent = pdfmetrics.getDescent(style.font_name, style.font_size)
    text_height = ascent - descent
    box_width = text_width + style.pad_x * 2
    box_height = text_height + style.pad_y * 2

    if box_width + style.margin * 2 > page_width or box_height + style.margin * 2 > page_height:
        raise ValueError("Time label box does not fit on the PDF page with the selected style")

    if style.position.endswith("left"):
        x = style.margin
    else:
        x = page_width - style.margin - box_width
    if style.position.startswith("top"):
        y = page_height - style.margin - box_height
    else:
        y = style.margin

    pdf.setFillColor(colors.toColor(style.fill_color))
    pdf.setStrokeColor(colors.toColor(style.stroke_color))
    pdf.setLineWidth(style.stroke_width)
    pdf.rect(x, y, box_width, box_height, fill=1, stroke=int(style.stroke_width > 0))

    pdf.setFillColor(colors.toColor(style.text_color))
    pdf.drawString(x + style.pad_x, y + style.pad_y - descent, label)


def main() -> None:
    args = parse_args()
    shot_dir = args.shot_dir.expanduser().resolve()
    manifest = (args.manifest or shot_dir / "evidence_manifest.csv").expanduser().resolve()
    output_pdf = args.out.expanduser().resolve()
    style = load_style(args.style_config.expanduser().resolve() if args.style_config else None)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    rows = rows_from_manifest(manifest)
    pdf: canvas.Canvas | None = None
    written = 0

    for row in rows:
        filename = row["filename"].strip()
        if not filename:
            raise ValueError("Manifest contains an empty filename")
        image_path = shot_dir / filename
        if not image_path.exists():
            raise FileNotFoundError(image_path)

        with Image.open(image_path) as image:
            page_width, page_height = image.size

        if pdf is None:
            pdf = canvas.Canvas(
                str(output_pdf),
                pagesize=(page_width, page_height),
                pageCompression=1,
            )
        else:
            pdf.setPageSize((page_width, page_height))

        pdf.drawImage(
            str(image_path),
            0,
            0,
            width=page_width,
            height=page_height,
            preserveAspectRatio=False,
            mask="auto",
        )
        draw_time_box(
            pdf,
            time_label(row["timecode"]),
            page_width,
            page_height,
            style,
        )
        pdf.showPage()
        written += 1

    if pdf is None:
        raise RuntimeError("No PDF pages were created")
    pdf.save()
    print(f"Wrote {written} pages: {output_pdf}")


if __name__ == "__main__":
    main()
