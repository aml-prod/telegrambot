from __future__ import annotations

import io
from typing import List

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

def _load_font(image_width: int) -> ImageFont.ImageFont:
    base_size = max(18, int(image_width * 0.06))
    here = Path(__file__).resolve().parent.parent
    candidates = []

    env_path = os.getenv("WATERMARK_FONT_PATH")
    if env_path:
        candidates.append(Path(env_path))

    candidates += [
        here / "fonts" / "NotoSans-Regular.ttf",
        here / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    ]

    for p in candidates:
        try:
            if p and p.exists():
                return ImageFont.truetype(str(p), base_size)
        except Exception:
            continue

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
    """Оставлено для совместимости: подпись снизу с плашкой."""
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


def render_watermark_center(image_bytes: bytes, text: str) -> bytes:
    """Накладывает полупрозрачный водяной знак (текст) по центру, под углом.

    Параметры подобраны по умолчанию: угол ~30°, белый текст с чёрной обводкой,
    прозрачность ~25%.
    """
    if not text:
        return image_bytes

    with Image.open(io.BytesIO(image_bytes)) as im:
        base = im.convert("RGBA")

    width, height = base.size

    # Размер шрифта от меньшей стороны изображения
    font_size = max(16, int(min(width, height) * 0.12))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Отрисуем текст на отдельном слое и повернём
    txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Предварительно посчитаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Создадим плитку под текст и изобразим на ней
    pad = max(8, font_size // 6)
    tile = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(tile)
    # Белый текст с мягкой чёрной обводкой
    tile_draw.text(
        (pad, pad),
        text,
        font=font,
        fill=(255, 255, 255, 64),  # полупрозрачный
        stroke_width=2,
        stroke_fill=(0, 0, 0, 96),
    )

    # Повернём текстовую плитку
    angle = 30
    rotated = tile.rotate(angle, expand=True, resample=Image.BICUBIC)

    # Позиционируем по центру
    rx, ry = rotated.size
    x = (width - rx) // 2
    y = (height - ry) // 2

    txt_layer.alpha_composite(rotated, (x, y))

    # Комбинируем
    watermarked = Image.alpha_composite(base, txt_layer)

    out = io.BytesIO()
    watermarked.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
    return out.getvalue()


def render_watermark_tiled(image_bytes: bytes, text: str) -> bytes:
    """Плиточный водяной знак по всей площади (диагонально).

    - Повторяющиеся полупрозрачные надписи по диагонали.
    - Умеренная плотность за счёт небольшого шага и смещения строк.
    """
    if not text:
        return image_bytes

    with Image.open(io.BytesIO(image_bytes)) as im:
        base = im.convert("RGBA")

    width, height = base.size

    # Делаем шрифт компактнее, чтобы паттерн был частым
    font_size = max(12, int(min(width, height) * 0.05))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Плитка с текстом
    pad = max(4, font_size // 8)
    tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dtmp = ImageDraw.Draw(tmp)
    bbox = dtmp.textbbox((0, 0), text, font=font, stroke_width=2)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    tile = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tile)
    tdraw.text(
        (pad, pad),
        text,
        font=font,
        fill=(255, 255, 255, 56),  # немного слабее
        stroke_width=2,
        stroke_fill=(0, 0, 0, 88),
    )

    # Поворачиваем плитку
    angle = 30
    rotated = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size

    # Создаём слой и заполняем; шаг делаем меньше ширины/высоты плитки,
    # чтобы паттерн точно повторялся заметно.
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    # Увеличиваем шаг до 1.0 * размер плитки (было 0.7),
    # это даёт примерно вдвое меньше повторов по площади
    step_x = max(1, int(rw * 1.0))
    step_y = max(1, int(rh * 1.0))

    # Шахматное смещение: каждый чётный ряд начинаем с полшага вправо
    start_y = -rh
    y = start_y
    row = 0
    while y < height + rh:
        offset_x = -rw + (step_x // 2 if row % 2 else 0)
        x = offset_x
        while x < width + rw:
            layer.alpha_composite(rotated, (x, y))
            x += step_x
        y += step_y
        row += 1

    out = io.BytesIO()
    Image.alpha_composite(base, layer).convert("RGB").save(
        out,
        format="JPEG",
        quality=95,
        optimize=True,
    )
    return out.getvalue()
