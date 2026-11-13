# Store Listing Notes

Before submitting, publish [PRIVACY.md](PRIVACY.md) at a public link and upload
`installer_output/Husnexa_Extension_v<version>.zip`.

After a store accepts the extension, add its assigned ID to `native_host_chromium.json`
(`allowed_origins`) and release a new app version. The extension can't reach the helper until then.

## Risk by store

| Store | Relevant rule | Outlook |
|---|---|---|
| Chrome Web Store | No enabling unauthorized download of copyrighted media | Rejection likely |
| Microsoft Edge Add-ons | Same rule, plus no circumventing login restrictions | Rejection possible |
| Firefox Add-ons | Consent and data rules cover native messaging | Best chance; not yet run in Firefox |

## Name

Husnexa

## Short description

Adds a download button to YouTube videos. Requires the free Husnexa desktop app for Windows.

## Full description

Adds a Download button to the YouTube player. Choose a quality or MP3 audio, and the video joins the queue in the Husnexa desktop app, so you can keep watching.

This extension doesn't download anything by itself. It needs the free Husnexa app for Windows, which runs on your PC.

If a video needs sign-in, the extension can pass your YouTube cookies to the app on your PC for that one download. They aren't sent to the developer, and you can turn this off in the app.

Only download content you have the right to download.

## Permission reasons

- **nativeMessaging:** sends your download request to the desktop app.
- **cookies and youtube.com access:** passes your YouTube sign-in to the app when a download you started requires it.

## Notes for reviewers

1. Install the Windows app from the project's Releases page.
2. Open a YouTube video, hover over the player, and click Download.
3. Choose an option. The video appears in the app's queue.
