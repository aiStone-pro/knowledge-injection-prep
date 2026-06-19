import json
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: run_ocr_pages.py <ocr_binary> <image_dir> <json_dir> <text_dir>",
            file=sys.stderr,
        )
        return 2

    ocr_binary = Path(sys.argv[1])
    image_dir = Path(sys.argv[2])
    json_dir = Path(sys.argv[3])
    text_dir = Path(sys.argv[4])
    json_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(image_dir.glob("math-course-*.png"))
    if not images:
        print("no math-course images found", file=sys.stderr)
        return 1

    for index, image in enumerate(images, 1):
        match = re.search(r"(\d+)\.png$", image.name)
        page = match.group(1) if match else f"{index:03d}"
        json_path = json_dir / f"page_{page}.ocr.json"
        text_path = text_dir / f"page_{page}.txt"

        if json_path.exists() and text_path.exists():
            print(f"skip {image.name}")
            continue

        result = subprocess.run(
            [str(ocr_binary), str(image)],
            check=True,
            text=True,
            capture_output=True,
        )
        observations = json.loads(result.stdout)
        json_path.write_text(
            json.dumps(observations, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        text = "\n".join(item["text"] for item in observations)
        text_path.write_text(text + "\n", encoding="utf-8")
        print(f"ocr {image.name}: {len(observations)} lines")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
