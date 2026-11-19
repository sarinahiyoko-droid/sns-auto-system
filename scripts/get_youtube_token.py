#!/usr/bin/env python3
"""One-time local OAuth helper for YouTube uploads.

Usage:
  python3 scripts/get_youtube_token.py /path/to/client_secret_....json

The downloaded OAuth client JSON and the resulting refresh token must never be
committed to the repository or pasted into chat.
"""
import json
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("必要なライブラリがありません。次を実行してください:")
    print("python3 -m pip install --user google-auth-oauthlib")
    raise SystemExit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    if len(sys.argv) != 2:
        print("使い方: python3 scripts/get_youtube_token.py /path/to/client_secret.json")
        raise SystemExit(2)

    client_file = Path(sys.argv[1]).expanduser()
    if not client_file.is_file():
        print(f"JSONファイルが見つかりません: {client_file}")
        raise SystemExit(2)

    try:
        data = json.loads(client_file.read_text(encoding="utf-8"))
        if "installed" not in data and "web" not in data:
            raise ValueError("OAuthクライアントJSONではありません")
    except Exception as exc:
        print(f"JSONファイルを読み込めません: {exc}")
        raise SystemExit(2)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
    )

    if not credentials.refresh_token:
        print("Refresh Tokenを取得できませんでした。Google認証をもう一度確認してください。")
        raise SystemExit(1)

    print("\n認証成功。以下の値をGitHub Actions Secretに登録してください。")
    print("\nYT_CLIENT_ID=" + credentials.client_id)
    print("YT_CLIENT_SECRET=" + credentials.client_secret)
    print("YT_REFRESH_TOKEN=" + credentials.refresh_token)
    print("\nこの画面の値をチャットに貼らないでください。")


if __name__ == "__main__":
    main()
