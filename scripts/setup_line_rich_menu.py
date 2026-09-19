from __future__ import annotations

import argparse
import asyncio
import json
import struct
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.line_service import (  # noqa: E402
    LineMessagingError,
    RICH_MENU_SIZE,
    create_and_set_default_rich_menu,
    rich_menu_spec,
)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise LineMessagingError(f"Rich Menu 圖片不是有效 PNG：{path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def validate_image(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise LineMessagingError(f"找不到 Rich Menu 圖片：{path}")
    width, height = png_dimensions(path)
    if {"width": width, "height": height} != RICH_MENU_SIZE:
        raise LineMessagingError(
            f"Rich Menu 圖片尺寸必須為 {RICH_MENU_SIZE['width']}x{RICH_MENU_SIZE['height']}，實際為 {width}x{height}。"
        )
    if path.stat().st_size > 1024 * 1024:
        raise LineMessagingError("Rich Menu 圖片必須小於 1MB。")
    return width, height


def print_dry_run(image: Path, width: int, height: int) -> None:
    spec = rich_menu_spec()
    print(json.dumps(spec, ensure_ascii=False, indent=2))
    print(f"mode=dry-run apply=false image={image} bytes={image.stat().st_size} size={width}x{height}")
    print(
        "planned=list existing menus, reuse exact name and spec if found, "
        "otherwise create then upload then set default; delete only a menu created in this run if upload or set-default fails"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="建立並設定竹青安心GO 的 LINE Rich Menu。預設 dry-run，不會呼叫 LINE API。")
    parser.add_argument(
        "--image",
        type=Path,
        default=ROOT_DIR / "assets" / "line-rich-menu.png",
        help="Rich Menu PNG 路徑。",
    )
    parser.add_argument("--dry-run", action="store_true", help="只驗證規格與圖片，不呼叫 LINE API（預設行為）。")
    parser.add_argument("--apply", action="store_true", help="真正呼叫 LINE API 建立或重用 Rich Menu。")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        print("不可同時使用 --dry-run 與 --apply。", file=sys.stderr)
        return 2

    try:
        width, height = validate_image(args.image)
    except LineMessagingError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.apply:
        print_dry_run(args.image, width, height)
        return 0
    try:
        rich_menu_id = asyncio.run(create_and_set_default_rich_menu(args.image))
    except LineMessagingError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Rich Menu 已設為預設：{rich_menu_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
