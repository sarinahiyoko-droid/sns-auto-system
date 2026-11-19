import json
import os
import re
import time
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen
from PIL import Image

SCRIPT = Path("content/script.json")
MAP = Path("content/illustration-map.json")
OUT = Path("assets/illustrations")
MAX_IMAGES = 20
SITE = "https://www.irasutoya.com/"
USER_AGENT = "Mozilla/5.0 (compatible; IllustrationFetcher/1.0)"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
        if tag == "meta":
            prop = (data.get("property") or data.get("name") or "").lower()
            image = data.get("content", "")
            if prop in ("og:image", "twitter:image") and image:
                self.images.append(image)


def get(url, attempts=3):
    last_error = None
    for attempt in range(attempts):
        request = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        })
        try:
            with urlopen(request, timeout=30) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except HTTPError as error:
            last_error = error
            if error.code != 429 and error.code < 500:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else (10, 30, 60)[attempt]
            print(f"HTTP {error.code}; waiting {delay}s before retry {attempt + 1}/{attempts}")
            if attempt + 1 < attempts:
                time.sleep(delay)
        except (URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep((5, 15, 30)[attempt])
    raise RuntimeError(f"Could not fetch {url} after {attempts} attempts: {last_error}")


def approved_image_host(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = ("blogspot.com", "googleusercontent.com")
    return parsed.scheme == "https" and any(
        host == domain or host.endswith("." + domain) for domain in allowed
    )


def find_live_image(keyword):
    # Optional fallback only. Disabled by default to avoid repeated search requests.
    search_url = SITE + "search?q=" + quote(keyword)
    raw, _ = get(search_url)
    parser = PageParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    posts = []
    for link in parser.links:
        page_url = urljoin(SITE, link).split("#")[0]
        parsed = urlparse(page_url)
        if parsed.scheme == "https" and parsed.hostname == "www.irasutoya.com":
            if re.search(r"/\d{4}/\d{2}/", parsed.path) and page_url not in posts:
                posts.append(page_url)
    for page_url in posts[:2]:
        page_raw, content_type = get(page_url)
        if "html" not in content_type.lower():
            continue
        detail = PageParser()
        detail.feed(page_raw.decode("utf-8", errors="replace"))
        for image_url in detail.images:
            if approved_image_host(image_url):
                return {"name": keyword, "source_page": page_url, "image_url": image_url}
        time.sleep(3)
    return None


def download_image(image_url, filename):
    if not approved_image_host(image_url):
        raise ValueError(f"Image host is not approved: {urlparse(image_url).hostname}")
    data, mime_type = get(image_url)
    if not mime_type.lower().startswith("image/") or len(data) < 500:
        raise ValueError(f"Unexpected image response: {mime_type}, {len(data)} bytes")
    with Image.open(BytesIO(data)) as image:
        image.verify()
    suffix = ".png" if "png" in mime_type.lower() else ".jpg"
    path = OUT / (filename + suffix)
    path.write_bytes(data)
    return path


def main():
    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    illustration_map = json.loads(MAP.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    allow_live_search = os.environ.get("ALLOW_LIVE_IRASUTOYA_SEARCH", "").lower() == "true"
    downloaded = 0
    used_urls = set()

    for scene_no, scene in enumerate(script.get("scenes", []), 1):
        matched = []
        for keyword in scene.get("illustration_keywords", []):
            keyword = str(keyword).strip()
            for item in illustration_map:
                if keyword in item.get("keywords", []) and item.get("image_url"):
                    if item["image_url"] not in used_urls and item not in matched:
                        matched.append(item)

        # Two images per scene fit the current vertical layout.
        for image_no, item in enumerate(matched[:2], 1):
            if downloaded >= MAX_IMAGES:
                break
            try:
                path = download_image(item["image_url"], f"scene{scene_no}-image{image_no}")
                used_urls.add(item["image_url"])
                downloaded += 1
                print(f"Downloaded {path.name}: {item['name']} ({item['source_page']})")
            except Exception as error:
                print(f"Could not download curated image '{item.get('name')}': {error}")

        if not matched and allow_live_search:
            for keyword in scene.get("illustration_keywords", []):
                try:
                    item = find_live_image(str(keyword))
                    if item and item["image_url"] not in used_urls:
                        path = download_image(item["image_url"], f"scene{scene_no}-image1")
                        used_urls.add(item["image_url"])
                        downloaded += 1
                        print(f"Downloaded live result {path.name}: {item['source_page']}")
                        break
                except Exception as error:
                    print(f"Live search skipped for '{keyword}': {error}")

    if downloaded == 0:
        raise RuntimeError(
            "No curated Irasutoya images matched this script. "
            "Add the relevant official image to content/illustration-map.json."
        )
    print(f"Downloaded {downloaded} official Irasutoya images.")


if __name__ == "__main__":
    main()
