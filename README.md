# sns-auto-system

AI-powered Japanese trivia short-video pipeline.

## Automated weekday video production

- GitHub Actions is scheduled for **Monday–Friday at 19:00 Taiwan time (UTC+8)**.
- Each weekday gets a different topic from `content/weekday-topics.json`.
- The finished video is prepared one hour before the planned posting window.
- The intended publishing slot is **Monday–Friday at 20:00 Taiwan time** (21:00 Japan time).
- A manual build is also available from the repository's **Actions** tab → **Build Complete Japanese Trivia Video** → **Run workflow**.
- The current automation builds videos; public posting is not enabled until the platform credentials and app approvals are configured.

## Required repository secret

Add `GEMINI_API_KEY` under **Settings → Secrets and variables → Actions**.
The script-generation workflow uses this key to create the Japanese trivia script.

## Current pipeline

- Generate a 4-scene Japanese trivia script with Gemini, rotating five source-backed weekday topics.
- Generate Japanese narration with Gemini 3.8 Flash-Lite TTS using the upbeat male voice Puck.
- Retrieve illustrations from the official Irasutoya site.
- Render a 1080×1920, 30 fps vertical video.
- Merge narration and video into `final-video.mp4`.

## Current limitations

- Irasutoya currently returned HTTP 429 (rate limit) to the automated search request. The downloader retries politely and stops rather than bypassing the site's limit. The full build is not considered complete until official illustrations are retrieved successfully.
- The renderer has passed a 20-second smoke test using temporary test artwork. This verifies video layout and encoding, not the real illustration-download step.
- Gemini 3.8 Flash-Lite TTS with the Puck male voice has passed an automated audio-generation test. Google's free tier is free of charge, but free-tier content may be used to improve Google products; only send non-sensitive narration text.
- Automatic publishing is not yet enabled. The target platforms are YouTube Shorts, Instagram Reels, Facebook Reels, and TikTok only. Each requires separate OAuth credentials and permissions; TikTok public posting requires an approved/audited app.
- The current verified illustration and research library is focused on panda trivia. Expand the curated image map and verified source list before broadening to unrelated trivia topics.
- GitHub Actions usage is subject to GitHub's plan and repository usage limits. A ¥0 monthly target cannot be guaranteed for unlimited runs.

## Illustration usage

For commercial use, Irasutoya's official FAQ allows up to 20 illustrations per video, including the thumbnail, for YouTube. Other use cases should follow the current official terms. Do not redistribute the illustration files as standalone assets.

- [Irasutoya usage terms](https://www.irasutoya.com/p/terms.html)
- [Irasutoya official FAQ](https://www.irasutoya.com/p/faq.html)
