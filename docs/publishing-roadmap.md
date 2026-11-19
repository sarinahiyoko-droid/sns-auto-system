# Publishing roadmap

The video-generation pipeline is now separate from platform publishing. Do not add platform credentials until the account owner has created the required developer apps and approved permissions.

## Platform requirements

| Platform | Official publishing route | Account / approval requirements | Cost and blockers |
|---|---|---|---|
| YouTube Shorts | YouTube Data API `videos.insert` | Google OAuth authorization with the `youtube.upload` scope | The default quota includes 100 video uploads per day. API quota is not a per-upload fee. |
| TikTok | Content Posting API Direct Post | Developer app, Content Posting API product, approved `video.publish` scope, and user authorization | Unaudited apps can only post privately. Public posting requires TikTok's audit. |
| Instagram Reels | Instagram API / Reels publishing | Instagram Professional account (Creator or Business), app authorization, and publishing permission | The video must be reachable by Meta's servers at a public URL for the URL-based upload flow. Instagram Login can avoid the linked-Facebook-Page requirement; Facebook Login uses a linked Page. |
| Facebook Reels | Graph API Page Video Reels endpoint | Facebook Page, Page access token, and Page content permissions such as `pages_manage_posts` | Requires the user to have the Page's CREATE_CONTENT task. |
| X | X API create-post endpoint | X developer app and user authorization | Pay-per-use pricing currently lists $0.015 per post creation, so X is not compatible with a strict ¥0 budget. |

## Recommended order

1. **YouTube Shorts first** — simplest route for a fully automated public upload.
2. **Instagram and Facebook next** — one Meta developer app can support both, but account type, Page permissions, and media hosting must be configured.
3. **TikTok after app audit** — without approval, direct posts remain private.
4. **X last or omit** — each post has a usage charge.

## Required credentials (store only in GitHub Actions Secrets)

- YouTube: OAuth client ID, client secret, and refresh token.
- TikTok: client key, client secret, and authorized user access token.
- Meta: app ID, app secret, Instagram account ID, Page ID where applicable, and long-lived access token.
- X: client credentials and user access token (only if paid posting is accepted).

Never paste access tokens, app secrets, or refresh tokens into chat or commit them to the repository.

## Official documentation

- [YouTube Data API overview and quota](https://developers.google.com/youtube/data/getting-started)
- [YouTube video upload endpoint](https://developers.google.com/youtube/v3/docs/videos/insert)
- [TikTok Content Posting API — Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started)
- [TikTok Direct Post API reference](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)
- [TikTok content-sharing guidelines and audit restrictions](https://developers.tiktok.com/docs/en/content-sharing-guidelines)
- [Meta Instagram API documentation](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta Instagram API login options](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/changelog/)
- [Facebook Page publishing permissions](https://developers.facebook.com/docs/graph-api/reference/page/feed/)
- [Facebook Page Reels publishing endpoint](https://developers.facebook.com/docs/graph-api/reference/page/video_reels/)
- [X Developer Platform pricing](https://developer.x.com/)
