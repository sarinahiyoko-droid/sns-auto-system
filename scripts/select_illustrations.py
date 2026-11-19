import json
import re
from pathlib import Path

SCRIPT_PATH = Path("content/script.json")
MAP_PATH = Path("content/illustration-map.json")
ASSET_DIR = Path("assets/illustrations")
OUTPUT_PATH = Path("content/selected-illustrations.json")
MAX_ILLUSTRATIONS_PER_VIDEO = 20


def normalize(value):
    return re.sub(r"\s+", "", str(value)).casefold()


def main():
    for path in (SCRIPT_PATH, MAP_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    if not isinstance(catalog, list):
        raise ValueError("illustration-map.json must contain a JSON list.")

    selected_files = set()
    results = []

    for index, scene in enumerate(script.get("scenes", []), start=1):
        keywords = scene.get("illustration_keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        ranked = []
        for item in catalog:
            filename = item.get("file", "")
            tags = item.get("keywords", [])
            if not filename or Path(filename).name != filename:
                continue

            image_path = ASSET_DIR / filename
            if not image_path.is_file():
                continue

            score = 0
            for keyword in keywords:
                key = normalize(keyword)
                if key and any(
                    key in normalize(tag) or normalize(tag) in key
                    for tag in tags
                ):
                    score += 1

            if score:
                ranked.append({
                    "file": str(image_path),
                    "name": item.get("name", Path(filename).stem),
                    "score": score,
                    "source_page": item.get("source_page", ""),
                })

        ranked.sort(key=lambda item: (-item["score"], item["name"]))

        scene_selection = []
        for candidate in ranked:
            if candidate["file"] in selected_files:
                continue
            if len(selected_files) >= MAX_ILLUSTRATIONS_PER_VIDEO:
                break
            selected_files.add(candidate["file"])
            scene_selection.append(candidate)
            if len(scene_selection) == 2:
                break

        results.append({
            "scene": index,
            "text": scene.get("text", ""),
            "start": scene.get("start", 0),
            "end": scene.get("end", 0),
            "illustration_keywords": keywords,
            "selected_illustrations": scene_selection,
            "visual_note": scene.get("visual_note", ""),
            "highlight": scene.get("highlight", ""),
            "motion": scene.get("motion", ""),
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    missing = [
        {"scene": item["scene"], "keywords": item["illustration_keywords"]}
        for item in results if not item["selected_illustrations"]
    ]

    print(f"Illustration selection complete: {len(selected_files)} unique files.")
    print(f"Scenes without a matching downloaded image: {len(missing)}")
    if missing:
        print(json.dumps(missing, ensure_ascii=False, indent=2))
    print(f"Selection manifest saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
