import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen
from PIL import Image

SCRIPT = Path("content/script.json")
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
        if tag == "a":
            href = data.get("href", "")
            if href:
                self.links.append(href)
        if tag == "meta":
            prop = (data.get("property") or data.get("name") or "").lower()
            content = data.get("content", "")
            if prop in ("og:image", "twitter:image") and content:
                self.images.append(content)


def get(url, attempts=3):
    last_error = None
    for attempt in range(attempts):
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        })
        try:
            with urlopen(req, timeout=25) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429 and exc.code < 500:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else (10, 30, 60)[attempt]
            print(f"HTTP {exc.code}; waiting {delay}s before retry {attempt + 1}/{attempts}")
            if attempt + 1 < attempts:
                time.sleep(delay)
        except (URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep((5, 15, 30)[attempt])
    raise RuntimeError(f"Could not fetch {url} after {attempts} attempts: {last_error}")


def official_post(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == "www.irasutoya.com" and parsed.path.startswith("/")


def approved_image_host(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = ("blogspot.com", "googleusercontent.com")
    return parsed.scheme == "https" and any(host == domain or host.endswith("." + domain) for domain in allowed)


def find_post(keyword):
    search_url = SITE + "search?q=" + quote(keyword)
    raw, _ = get(search_url)
    parser = PageParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    candidates = []
    for link in parser.links:
        absolute = urljoin(SITE, link).split("#")[0]
        if official_post(absolute) and re.search(r"/\d{4}/\d{2}/", absolute):
            if absolute not in candidates:
                candidates.append(absolute)
    for candidate in candidates[:3]:
        page_raw, page_type = get(candidate)
        if "html" not in page_type.lower():
            continue
        detail = PageParser()
        detail.feed(page_raw.decode("utf-8", errors="replace"))
        for image_url in detail.images:
            if approved_image_host(image_url):
                return candidate, image_url
        time.sleep(2)
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
            try:
                post, image_url = find_post(keyword)
            except Exception as exc:
                print(f"Could not search '{keyword}': {exc}")
                if "429" in str(exc):
                    raise RuntimeError(
                        "Irasutoya temporarily rate-limited this workflow (HTTP 429). "
                        "The build stopped without trying to bypass the site's limit."
                    ) from exc
                continue
            if not image_url or image_url in used:
                continue
            try:
                image_data, image_type = get(image_url)
                if not image_type.lower().startswith("image/") or len(image_data) < 1000:
                    continue
                from io import BytesIO
                with Image.open(BytesIO(image_data)) as check:
                    check.verify()
            except Exception as exc:
                print(f"Skip invalid image for '{keyword}': {exc}")
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
            time.sleep(3)
        if downloaded >= MAX_IMAGES:
            break

    if downloaded == 0:
        raise RuntimeError("No suitable official Irasutoya images were found.")
    print(f"Downloaded {downloaded} images temporarily for this video build.")


if __name__ == "__main__":
    main()
