#!/usr/bin/env python3
"""Upload the completed short to YouTube as PRIVATE for a manual test."""
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    client_id = os.environ["YT_CLIENT_ID"]
    client_secret = os.environ["YT_CLIENT_SECRET"]
    refresh_token = os.environ["YT_REFRESH_TOKEN"]

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    credentials.refresh(Request())

    script = json.loads(Path("content/script.json").read_text(encoding="utf-8"))
    title = str(script.get("title", "今日の雑学"))[:100]
    source_lines = []
    for source in script.get("sources", []):
        url = source.get("url", "").strip()
        name = source.get("title", "参考情報")
        if url.startswith("https://"):
            source_lines.append(f"{name}: {url}")
    description = (
        str(script.get("topic", "日本語の雑学ショート動画"))
        + "\n\n" + str(script.get("narration", ""))
        + ("\n\n参考情報:\n" + "\n".join(source_lines) if source_lines else "")
        + "\n\n#Shorts #雑学"
    )[:5000]

    video_path = Path("output/final-video.mp4")
    if not video_path.is_file():
        raise FileNotFoundError(f"Completed video not found: {video_path}")

    youtube = build("youtube", "v3", credentials=credentials)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "27",
                "defaultLanguage": "ja",
                "defaultAudioLanguage": "ja",
                "tags": ["雑学", "豆知識", "Shorts"],
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(
            str(video_path), mimetype="video/mp4", chunksize=-1, resumable=True
        ),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()
    print("Private YouTube test upload completed.")
    print("Video ID:", response.get("id", "(not returned)"))
    print("Privacy status: private")


if __name__ == "__main__":
    main()
