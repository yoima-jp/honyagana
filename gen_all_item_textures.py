from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from PIL import Image

from gen_weak_minecraft_text import make_square_texture


KNOWN_SUFFIXES = (
    "_open_front",
    "_open_back",
    "_pulling_0",
    "_pulling_1",
    "_pulling_2",
    "_in_hand",
    "_overlay",
    "_model",
    "_base",
    "_head",
    "_arrow",
    "_firework",
    "_standby",
    "_broken",
    "_markings",
    "_cast",
)

SHORT_WORDS = {
    "すぽーんえっぐ": "たまご",
    "ちぇすとぼーと": "ぼーと",
    "ちぇすといかだ": "いかだ",
    "しんすみすんぐてんぷれーと": "がた",
    "すみすんぐてんぷれーと": "がた",
    "せんりょー": "いろ",
    "えんちゃんとのほん": "ほん",
    "かけたれこーど": "れこーど",
    "とらいでんと": "やり",
    "くろすぼー": "ぼー",
    "こんぱす": "こんぱす",
    "りかばりーこんぱす": "こんぱす",
}

ENDINGS = (
    "かけら",
    "たね",
    "ぼーと",
    "いかだ",
    "ばけつ",
    "ぼとる",
    "ろっど",
    "よろい",
    "ぼうし",
    "ずぼん",
    "くつ",
    "つるぎ",
    "おの",
    "くわ",
    "しゃべる",
    "つるはし",
    "こんぱす",
    "たまご",
    "はーねす",
    "ばんどる",
    "きー",
    "ほん",
    "かみ",
    "ぼー",
    "やり",
    "がた",
)


def load_lang_map(lang_path: Path) -> dict[str, str]:
    data = json.loads(lang_path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for key, value in data.items():
        if key.startswith("item.minecraft.") or key.startswith("block.minecraft."):
            out[key] = value
    return out


def normalize_texture_id(stem: str) -> list[str]:
    candidates = [stem]

    # e.g. compass_00 / clock_32
    base_no_num = re.sub(r"_\d+$", "", stem)
    if base_no_num != stem:
        candidates.append(base_no_num)

    expanded: list[str] = []
    for c in candidates:
        expanded.append(c)
        for suffix in KNOWN_SUFFIXES:
            if c.endswith(suffix):
                expanded.append(c[: -len(suffix)])

    # pottery_sherd texture names can map to pottery_shard keys
    final: list[str] = []
    for c in expanded:
        final.append(c)
        if "pottery_sherd" in c:
            final.append(c.replace("pottery_sherd", "pottery_shard"))

    # Keep order while de-duplicating
    seen: set[str] = set()
    ordered: list[str] = []
    for c in final:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def pick_name(texture_stem: str, lang_map: dict[str, str]) -> str:
    for item_id in normalize_texture_id(texture_stem):
        for prefix in ("item.minecraft.", "block.minecraft."):
            key = f"{prefix}{item_id}"
            if key in lang_map:
                return lang_map[key]
    return "あいてむ"


def shorten_name(name: str) -> str:
    s = name.strip()

    if "の" in s:
        s = s.split("の", 1)[1]

    s = SHORT_WORDS.get(s, s)

    for ending in ENDINGS:
        if s.endswith(ending):
            s = ending
            break

    if len(s) > 6:
        s = s[:6]
    return s or "もの"


def generate_one_item(
    texture_path: str,
    font_path: str,
    min_size: int,
    padding_ratio: float,
    shear_x: float,
    rotation_deg: float,
    stroke_ratio: float,
    supersample: int,
    text: str,
) -> None:
    texture_file = Path(texture_path)
    with Image.open(texture_file) as img:
        size = max(img.width, img.height, min_size)

    make_square_texture(
        text=text,
        font_path=font_path,
        out_path=texture_path,
        size=size,
        padding_ratio=padding_ratio,
        shear_x=shear_x,
        rotation_deg=rotation_deg,
        stroke_ratio=stroke_ratio,
        scale_up_if_small=True,
        supersample=supersample,
    )


def generate_one_item_from_args(args: tuple[str, str, int, float, float, float, float, int, str]) -> None:
    generate_one_item(*args)


def generate_all_items(
    texture_dir: Path,
    lang_map: dict[str, str],
    font_path: Path,
    min_size: int,
    skip_if_large_enough: bool,
    padding_ratio: float,
    shear_x: float,
    rotation_deg: float,
    stroke_ratio: float,
    supersample: int,
    jobs: int,
) -> tuple[int, int]:
    tasks: list[tuple[str, str, int, float, float, float, float, int, str]] = []
    unknown = 0
    for texture_path in sorted(texture_dir.glob("*.png")):
        with Image.open(texture_path) as img:
            if skip_if_large_enough and img.width >= min_size and img.height >= min_size:
                continue

        src_name = pick_name(texture_path.stem, lang_map)
        if src_name == "あいてむ":
            unknown += 1
        text = shorten_name(src_name)
        tasks.append(
            (
                str(texture_path),
                str(font_path),
                min_size,
                padding_ratio,
                shear_x,
                rotation_deg,
                stroke_ratio,
                supersample,
                text,
            )
        )

    if jobs <= 1:
        for task in tasks:
            generate_one_item(*task)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            list(executor.map(generate_one_item_from_args, tasks))

    return len(tasks), unknown


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate weak-hiragana text textures for all item PNGs."
    )
    parser.add_argument(
        "--texture-dir",
        type=Path,
        default=Path("minecraft-1.21.11-resourcepack/assets/minecraft/textures/item"),
        help="Directory containing item textures (*.png)",
    )
    parser.add_argument(
        "--lang",
        type=Path,
        default=Path("minecraft-1.21.11-resourcepack/assets/minecraft/lang/ja_jp.json"),
        help="ja_jp.json path",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=Path("851CHIKARA-YOWAKU_002.ttf"),
        help="Path to font file",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=512,
        help="Minimum output resolution per texture (default: 512)",
    )
    parser.add_argument(
        "--no-skip-large",
        action="store_true",
        help="Regenerate textures even when they are already >= min-size",
    )
    parser.add_argument("--padding", type=float, default=0.18)
    parser.add_argument("--shear", type=float, default=0.08)
    parser.add_argument("--rotate", type=float, default=-4.0)
    parser.add_argument("--stroke-ratio", type=float, default=0.05)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument(
        "--jobs",
        type=int,
        default=max(1, (os.cpu_count() or 2) // 2),
        help="Parallel worker count",
    )
    args = parser.parse_args()

    lang_map = load_lang_map(args.lang)
    total, unknown = generate_all_items(
        texture_dir=args.texture_dir,
        lang_map=lang_map,
        font_path=args.font,
        min_size=args.min_size,
        skip_if_large_enough=not args.no_skip_large,
        padding_ratio=args.padding,
        shear_x=args.shear,
        rotation_deg=args.rotate,
        stroke_ratio=args.stroke_ratio,
        supersample=args.supersample,
        jobs=args.jobs,
    )
    print(f"generated: {total} textures")
    print(f"fallback label used: {unknown}")


if __name__ == "__main__":
    main()
