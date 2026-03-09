from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


FONT_PATH = Path("851CHIKARA-YOWAKU_002.ttf")
OUT_DIR = Path("Honyagana/assets/minecraft/textures/gui/title")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def _centered_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, canvas: tuple[int, int]) -> tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), text, font=font, stroke_width=max(2, font.size // 18))
    w = r - l
    h = b - t
    x = (canvas[0] - w) // 2 - l
    y = (canvas[1] - h) // 2 - t
    return x, y


def _render_text_sprite(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke_fill: tuple[int, int, int, int],
    stroke: int,
) -> Image.Image:
    tmp = Image.new("RGBA", (2048, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    # Generous offset prevents glyph descenders from being clipped.
    d.text((220, 120), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    bbox = tmp.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return tmp.crop(bbox)


def make_logo(
    filename: str,
    size: tuple[int, int],
    text: str,
    font_size: int,
    top_align: bool = False,
    top_margin: int = 0,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (0, 0, 0, 0))

    font = _load_font(font_size)
    stroke = max(2, font_size // 18)
    text_sprite = _render_text_sprite(
        text=text,
        font=font,
        fill=(244, 244, 244, 255),
        stroke_fill=(32, 32, 32, 255),
        stroke=stroke,
    )
    shadow_sprite = _render_text_sprite(
        text=text,
        font=font,
        fill=(0, 0, 0, 170),
        stroke_fill=(0, 0, 0, 220),
        stroke=stroke,
    ).filter(ImageFilter.GaussianBlur(radius=max(1, stroke // 2)))

    x = (size[0] - text_sprite.width) // 2
    y = top_margin if top_align else (size[1] - text_sprite.height) // 2
    img.alpha_composite(shadow_sprite, (x + stroke + 2, y + stroke + 2))
    img.alpha_composite(text_sprite, (x, y))

    img.save(OUT_DIR / filename)


def main() -> None:
    # Minecraft title logo is sampled from the upper area of the texture,
    # so keep text near the top to avoid in-game clipping.
    make_logo("minecraft.png", (1024, 256), "まいんくらふと", 180, top_align=True, top_margin=4)
    make_logo("minceraft.png", (1024, 256), "まいんくらふと", 180, top_align=True, top_margin=4)
    make_logo("edition.png", (512, 64), "じゃばえでぃしょん", 46)
    print("saved: minecraft.png, minceraft.png, edition.png")


if __name__ == "__main__":
    main()
