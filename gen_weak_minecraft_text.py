
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def crop_to_alpha(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    if bbox is None:
        return img
    return img.crop(bbox)


def add_transparent_border(img: Image.Image, border: int) -> Image.Image:
    if border <= 0:
        return img
    out = Image.new(
        "RGBA",
        (img.width + border * 2, img.height + border * 2),
        (0, 0, 0, 0),
    )
    out.alpha_composite(img, (border, border))
    return out


def render_transformed_text(
    text: str,
    font_path: str,
    font_size: int,
    shear_x: float,
    rotation_deg: float,
    stroke_ratio: float,
    inner_padding_px: int,
) -> Image.Image:
    if not text:
        raise ValueError("text is empty")

    stroke_width = max(1, round(font_size * stroke_ratio))

    font = ImageFont.truetype(font_path, font_size)

    dummy = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(dummy)
    l, t, r, b = d.textbbox((0, 0), text, font=font, stroke_width=stroke_width)

    text_w = max(1, r - l)
    text_h = max(1, b - t)
    margin = stroke_width * 4 + inner_padding_px

    base = Image.new(
        "RGBA",
        (text_w + margin * 2, text_h + margin * 2),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(base)
    draw.text(
        (margin - l, margin - t),
        text,
        font=font,
        fill=(0, 0, 0, 255),
        stroke_width=stroke_width,
        stroke_fill=(255, 255, 255, 255),
    )
    base = crop_to_alpha(base)

    w, h = base.size
    extra_w = int(abs(shear_x) * h) + 2
    sheared = Image.new("RGBA", (w + extra_w, h), (0, 0, 0, 0))

    if shear_x >= 0:
        matrix = (1, shear_x, 0, 0, 1, 0)
    else:
        matrix = (1, shear_x, -shear_x * h, 0, 1, 0)

    sheared = base.transform(
        sheared.size,
        Image.Transform.AFFINE,
        matrix,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0, 0),
    )
    sheared = crop_to_alpha(sheared)

    rotated = sheared.rotate(
        rotation_deg,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    rotated = crop_to_alpha(rotated)
    safety_border = max(4, round(font_size * 0.1))
    return add_transparent_border(rotated, safety_border)


def fits_inside(img: Image.Image, target_size: int, padding_ratio: float) -> bool:
    inner = int(round(target_size * (1 - padding_ratio * 2)))
    return img.width <= inner and img.height <= inner


def find_best_font_size(
    text: str,
    font_path: str,
    target_size: int,
    padding_ratio: float,
    shear_x: float,
    rotation_deg: float,
    stroke_ratio: float,
) -> Tuple[int, Image.Image]:
    low = 4
    high = max(32, target_size * 4)
    best_size = low
    best_img = render_transformed_text(
        text, font_path, low, shear_x, rotation_deg, stroke_ratio, int(target_size * padding_ratio)
    )

    while low <= high:
        mid = (low + high) // 2
        img = render_transformed_text(
            text,
            font_path,
            mid,
            shear_x,
            rotation_deg,
            stroke_ratio,
            int(target_size * padding_ratio),
        )
        if fits_inside(img, target_size, padding_ratio):
            best_size = mid
            best_img = img
            low = mid + 1
        else:
            high = mid - 1

    return best_size, best_img


def make_square_texture(
    text: str,
    font_path: str,
    out_path: str,
    size: int = 1024,
    padding_ratio: float = 0.12,
    shear_x: float = 0.08,
    rotation_deg: float = -4.0,
    stroke_ratio: float = 0.05,
    scale_up_if_small: bool = True,
    supersample: int = 4,
) -> Path:
    working_size = max(size, size * max(1, supersample))
    _, rendered = find_best_font_size(
        text=text,
        font_path=font_path,
        target_size=working_size,
        padding_ratio=padding_ratio,
        shear_x=shear_x,
        rotation_deg=rotation_deg,
        stroke_ratio=stroke_ratio,
    )

    inner = int(round(working_size * (1 - padding_ratio * 2)))
    rw, rh = rendered.size

    if scale_up_if_small and (rw < inner or rh < inner):
        scale = min(inner / rw, inner / rh)
        new_size = (max(1, round(rw * scale)), max(1, round(rh * scale)))
        rendered = rendered.resize(new_size, Image.Resampling.LANCZOS)
        rendered = crop_to_alpha(rendered)
        rw, rh = rendered.size

    canvas = Image.new("RGBA", (working_size, working_size), (0, 0, 0, 0))
    x = (working_size - rw) // 2
    y = (working_size - rh) // 2
    canvas.alpha_composite(rendered, (x, y))
    if working_size != size:
        canvas = canvas.resize((size, size), Image.Resampling.LANCZOS)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a square Minecraft-style high-resolution text texture with black fill, white outline, and a weak/slanted look."
    )
    parser.add_argument("text", help="Text to render, e.g. めいす")
    parser.add_argument(
        "--font",
        default="851CHIKARA-YOWAKU_002.ttf",
        help="Path to the .ttf font file",
    )
    parser.add_argument(
        "--out",
        default="output.png",
        help="Output PNG file path",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Square output size in px (default: 1024)",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.18,
        help="Outer padding ratio, e.g. 0.08 = 8%%",
    )
    parser.add_argument(
        "--shear",
        type=float,
        default=0.08,
        help="Italic-like horizontal shear amount",
    )
    parser.add_argument(
        "--rotate",
        type=float,
        default=-4.0,
        help="Rotation in degrees",
    )
    parser.add_argument(
        "--stroke-ratio",
        type=float,
        default=0.05,
        help="Outline thickness relative to font size",
    )
    parser.add_argument(
        "--supersample",
        type=int,
        default=4,
        help="Internal render scale before downsampling",
    )

    args = parser.parse_args()

    out = make_square_texture(
        text=args.text,
        font_path=args.font,
        out_path=args.out,
        size=args.size,
        padding_ratio=args.padding,
        shear_x=args.shear,
        rotation_deg=args.rotate,
        stroke_ratio=args.stroke_ratio,
        supersample=args.supersample,
    )
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
