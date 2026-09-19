from __future__ import annotations

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.seed import reset_and_seed  # noqa: E402


def main() -> None:
    reset_and_seed()
    print("Demo 資料已重設為林小竹／app_demo_001。")


if __name__ == "__main__":
    main()
