from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
OCR_BIN = BASE / "tmp" / "apple_vision_ocr"
PAGES_DIR = BASE / "tmp" / "pdf_pages"
OCR_DIR = BASE / "tmp" / "pdf_ocr"
TEXT_DIR = BASE / "tmp" / "pdf_text"


def page_number(path: Path) -> int:
    match = re.search(r"-(\d+)\.png$", path.name)
    if not match:
        raise ValueError(f"cannot parse page number from {path.name}")
    return int(match.group(1))


def line_text(items: list[dict]) -> str:
    lines: list[str] = []
    current: list[dict] = []
    current_y: float | None = None

    for item in sorted(items, key=lambda obj: (-float(obj["y"]), float(obj["x"]))):
        y = float(item["y"])
        if current_y is None or abs(y - current_y) <= 0.012:
            current.append(item)
            current_y = y if current_y is None else (current_y + y) / 2
            continue
        lines.append(" ".join(str(obj["text"]).strip() for obj in sorted(current, key=lambda obj: float(obj["x"])) if str(obj["text"]).strip()))
        current = [item]
        current_y = y

    if current:
        lines.append(" ".join(str(obj["text"]).strip() for obj in sorted(current, key=lambda obj: float(obj["x"])) if str(obj["text"]).strip()))

    return "\n".join(line for line in lines if line.strip())


def main() -> int:
    if not OCR_BIN.exists():
        print(f"missing OCR binary: {OCR_BIN}", file=sys.stderr)
        return 2

    OCR_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    pages = sorted(PAGES_DIR.glob("physics-*.png"), key=page_number)
    if not pages:
        print(f"no rendered pages found in {PAGES_DIR}", file=sys.stderr)
        return 2

    for index, page in enumerate(pages, start=1):
        num = page_number(page)
        ocr_path = OCR_DIR / f"page_{num:03d}.ocr.json"
        text_path = TEXT_DIR / f"page_{num:03d}.txt"
        if ocr_path.exists() and text_path.exists() and text_path.stat().st_size > 0:
            print(f"[{index}/{len(pages)}] skip page {num:03d}")
            continue

        print(f"[{index}/{len(pages)}] OCR page {num:03d}", flush=True)
        result = subprocess.run([str(OCR_BIN), str(page)], capture_output=True, text=True, check=True)
        items = json.loads(result.stdout)
        ocr_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        text_path.write_text(line_text(items) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
