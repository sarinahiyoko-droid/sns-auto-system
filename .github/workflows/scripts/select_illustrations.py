
import json
import re
from pathlib import Path

SCRIPT_PATH = Path("content/script.json")
MAP_PATH = Path("content/illustration-map.json")
ASSET_DIR = Path("assets/illustrations")
OUTPUT_PATH = Path("content/selected-illustrations.json")


def normalize(text):
    return re.sub(r"\s+", "", text).lower()


def main():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError("content/script.json がありません。")

    if not MAP_PATH.exists():
        raise FileNotFoundError(
            "content/illustration-map.json がありません。"
        )

    with SCRIPT_PATH.open(encoding="utf-8") as f:
        script = json.load(f)

    with MAP_PATH.open(encoding="utf-8") as f:
        illustration_map = json.load(f)

    results = []

    for index, scene in enumerate(script["scenes"], start=1):
        keywords = scene.get("illustration_keywords", [])
        matches = []

        for item in illustration_map:
            tags = item.get("keywords", [])
            score = sum(
                1 for keyword in keywords
                if any(
                    normalize(keyword) in normalize(tag)
                    or normalize(tag) in normalize(keyword)
                    for tag in tags
                )
            )

            if score > 0:
                image_path = ASSET_DIR / item["file"]

                if image_path.exists():
                    matches.append({
                        "file": str(image_path),
                        "score": score,
                        "name": item["name"]
                    })

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        results.append({
            "scene": index,
            "text": scene["text"],
            "illustration_keywords": keywords,
            "selected_illustrations": matches[:2],
            "visual_note": scene.get("visual_note", ""),
            "highlight": scene.get("highlight", ""),
            "motion": scene.get("motion", "")
        })

    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("イラスト選択が完了しました。")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
