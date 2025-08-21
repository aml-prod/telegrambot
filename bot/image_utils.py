from __future__ import annotations

import io
from typing import List

from PIL import Image, ImageDraw, ImageFont


def _load_font(image_width: int) -> ImageFont.ImageFont:
    base_size = max(18, int(image_width * 0.06))
    try:
        # Попробуем системный шрифт, затем встроенный DejaVuSans
        return ImageFont.truetype("DejaVuSans.ttf", base_size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", base_size)
        except OSError:
            return ImageFont.load_default()


def _wrap_text_by_width(
    text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    max_width: int,
) -> List[str]:
    words = text.split()
    if not words:
        return [""]

    lines: List[str] = []
    current_line = words[0]

    for word in words[1:]:
        trial = f"{current_line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current_line = trial
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def render_text_on_image_bottom(image_bytes: bytes, text: str) -> bytes:
    """Накладывает текст снизу изображения с полупрозрачной плашкой. Возвращает JPEG-байты."""
    if not text:
        return image_bytes

    with Image.open(io.BytesIO(image_bytes)) as im:
        image = im.convert("RGBA")

    draw = ImageDraw.Draw(image, "RGBA")
    font = _load_font(image.width)

    padding = max(10, int(image.width * 0.03))
    spacing = max(4, int(font.size * 0.3))
    max_text_width = image.width - 2 * padding

    lines = _wrap_text_by_width(text, draw, font, max_text_width)
    block = "\n".join(lines)

    bbox = draw.multiline_textbbox(
        (0, 0),
        block,
        font=font,
        spacing=spacing,
        stroke_width=2,
    )
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    bar_h = text_h + 2 * padding

    y0 = max(0, image.height - bar_h)

    # Полупрозрачная плашка по низу
    draw.rectangle([(0, y0), (image.width, image.height)], fill=(0, 0, 0, 160))

    x = int((image.width - text_w) / 2)
    y = int(y0 + padding)

    draw.multiline_text(
        (x, y),
        block,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=spacing,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 200),
        align="center",
    )

    out = io.BytesIO()
    image.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
    return out.getvalue()
