import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

SCRIPT = Path("content/script.json")
OUT = Path("assets/illustrations")
MAX_IMAGES = 20
SITE = "https://www.irasutoya.com/"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a":
            href = data.get("href", "")
            if href:
                self.links.append(href)
        if tag == "meta":
            prop = (data.get("property") or data.get("name") or "").lower()
            content = data.get("content", "")
            if prop in ("og:image", "twitter:image") and content:
                self.images.append(content)


def get(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as response:
        return response.read(), response.headers.get("Content-Type", "")


def official_post(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == "www.irasutoya.com" and parsed.path.startswith("/")


def find_post(keyword):
    search_url = SITE + "search?q=" + quote(keyword)
    raw, content_type = get(search_url)
    parser = PageParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    candidates = []
    for link in parser.links:
        absolute = urljoin(SITE, link).split("#")[0]
        if official_post(absolute) and re.search(r"/\d{4}/\d{2}/", absolute):
            if absolute not in candidates:
                candidates.append(absolute)
    for candidate in candidates[:5]:
        page_raw, page_type = get(candidate)
        if "html" not in page_type.lower():
            continue
        detail = PageParser()
        detail.feed(page_raw.decode("utf-8", errors="replace"))
        for image_url in detail.images:
            host = urlparse(image_url).hostname or ""
            if image_url.startswith("https://") and (
                host.endswith("blogspot.com") or host.endswith("googleusercontent.com")
            ):
                return candidate, image_url
        time.sleep(0.5)
    return None, None


def main():
    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    used = set()
    downloaded = 0

    for scene_no, scene in enumerate(script.get("scenes", []), 1):
        keywords = scene.get("illustration_keywords", [])
        found_for_scene = 0
        for keyword in keywords:
            keyword = str(keyword).strip()
            if not keyword:
                continue
            post, image_url = find_post(keyword)
            if not image_url or image_url in used:
                continue
            try:
                image_data, image_type = get(image_url)
            except Exception as exc:
                print(f"Skip {keyword}: {exc}")
                continue
            if not image_type.lower().startswith("image/") or len(image_data) < 1000:
                continue
            suffix = ".png" if "png" in image_type.lower() else ".jpg"
            filename = f"scene{scene_no}-image{found_for_scene + 1}{suffix}"
            (OUT / filename).write_bytes(image_data)
            used.add(image_url)
            downloaded += 1
            found_for_scene += 1
            print(f"Downloaded {filename} from {post}")
            if found_for_scene >= 2 or downloaded >= MAX_IMAGES:
                break
            time.sleep(1)
        if downloaded >= MAX_IMAGES:
            break

    if downloaded == 0:
        raise RuntimeError("No suitable official Irasutoya images were found.")
    print(f"Downloaded {downloaded} images temporarily for this video build.")


if __name__ == "__main__":
    main()
