from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from gen_all_item_textures import load_lang_map, shorten_name
from gen_weak_minecraft_text import make_square_texture


def collect_block_item_ids(vanilla_items_dir: Path, lang_map: dict[str, str]) -> list[str]:
    block_item_ids: list[str] = []
    force_include = {
        "shield",
    }

    for item_json in sorted(vanilla_items_dir.glob("*.json")):
        item_id = item_json.stem
        if item_id in {"air", "cave_air", "void_air"}:
            continue

        try:
            data = json.loads(item_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        has_block_lang = f"block.minecraft.{item_id}" in lang_map

        model = data.get("model")
        model_ref = model.get("model") if isinstance(model, dict) else None
        is_block_model_ref = isinstance(model_ref, str) and model_ref.startswith("minecraft:block/")

        if has_block_lang or is_block_model_ref or item_id in force_include:
            block_item_ids.append(item_id)

    return block_item_ids


def pick_label(item_id: str, lang_map: dict[str, str]) -> str:
    key = f"block.minecraft.{item_id}"
    name = lang_map.get(key)
    if not name:
        return "ぶろっく"
    return shorten_name(name)


def render_one_texture(
    item_id: str,
    label: str,
    texture_out_dir: str,
    font_path: str,
    size: int,
    padding_ratio: float,
    shear_x: float,
    rotation_deg: float,
    stroke_ratio: float,
    supersample: int,
) -> None:
    out = Path(texture_out_dir) / f"{item_id}.png"
    make_square_texture(
        text=label,
        font_path=font_path,
        out_path=str(out),
        size=size,
        padding_ratio=padding_ratio,
        shear_x=shear_x,
        rotation_deg=rotation_deg,
        stroke_ratio=stroke_ratio,
        scale_up_if_small=True,
        supersample=supersample,
    )


def render_one_texture_from_args(args: tuple[str, str, str, str, int, float, float, float, float, int]) -> None:
    render_one_texture(*args)


def write_model_json(models_dir: Path, item_id: str) -> None:
    model_path = models_dir / f"{item_id}.json"
    payload = {
        "parent": "minecraft:item/generated",
        "textures": {
            "layer0": f"minecraft:item/{item_id}",
        },
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_item_json(items_dir: Path, item_id: str) -> None:
    item_path = items_dir / f"{item_id}.json"
    payload = {
        "model": {
            "type": "minecraft:model",
            "model": f"minecraft:item/honyagana_block/{item_id}",
        }
    }
    item_path.parent.mkdir(parents=True, exist_ok=True)
    item_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate honyagana textures/models for block items only (inventory/hand view)."
    )
    parser.add_argument(
        "--vanilla-items-dir",
        type=Path,
        default=Path(".tmp_mc_1_21_11/client/assets/minecraft/items"),
        help="Path to vanilla assets/minecraft/items",
    )
    parser.add_argument(
        "--lang",
        type=Path,
        default=Path("Honyagana/assets/minecraft/lang/ja_jp.json"),
        help="ja_jp.json path",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=Path("851CHIKARA-YOWAKU_002.ttf"),
        help="Path to font file",
    )
    parser.add_argument(
        "--texture-out-dir",
        type=Path,
        default=Path("Honyagana/assets/minecraft/textures/item"),
        help="Output directory for block item textures",
    )
    parser.add_argument(
        "--items-out-dir",
        type=Path,
        default=Path("Honyagana/assets/minecraft/items"),
        help="Output directory for items/*.json overrides",
    )
    parser.add_argument(
        "--models-out-dir",
        type=Path,
        default=Path("Honyagana/assets/minecraft/models/item/honyagana_block"),
        help="Output directory for models/item/*.json",
    )
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--padding", type=float, default=0.18)
    parser.add_argument("--shear", type=float, default=0.08)
    parser.add_argument("--rotate", type=float, default=-4.0)
    parser.add_argument("--stroke-ratio", type=float, default=0.05)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument(
        "--jobs",
        type=int,
        default=max(1, (os.cpu_count() or 2) // 2),
        help="Parallel worker count for texture rendering",
    )
    parser.add_argument(
        "--skip-existing-textures",
        action="store_true",
        help="Skip rendering if target texture PNG already exists",
    )
    args = parser.parse_args()

    if not args.vanilla_items_dir.exists():
        raise FileNotFoundError(f"vanilla items dir not found: {args.vanilla_items_dir}")

    lang_map = load_lang_map(args.lang)
    block_item_ids = collect_block_item_ids(args.vanilla_items_dir, lang_map)

    tasks: list[tuple[str, str, str, str, int, float, float, float, float, int]] = []
    for item_id in block_item_ids:
        texture_path = args.texture_out_dir / f"{item_id}.png"
        if args.skip_existing_textures and texture_path.exists():
            continue
        label = pick_label(item_id, lang_map)
        tasks.append(
            (
                item_id,
                label,
                str(args.texture_out_dir),
                str(args.font),
                args.size,
                args.padding,
                args.shear,
                args.rotate,
                args.stroke_ratio,
                args.supersample,
            )
        )

    if args.jobs <= 1:
        for task in tasks:
            render_one_texture(*task)
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            list(executor.map(render_one_texture_from_args, tasks))

    for item_id in block_item_ids:
        write_model_json(args.models_out_dir, item_id)
        write_item_json(args.items_out_dir, item_id)

    print(f"block items found: {len(block_item_ids)}")
    print(f"textures rendered: {len(tasks)}")
    print(f"item overrides written: {len(block_item_ids)}")
    print(f"model files written: {len(block_item_ids)}")


if __name__ == "__main__":
    main()
