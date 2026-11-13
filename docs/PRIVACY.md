# Privacy Policy

**Husnexa and its browser extension**
Last updated: 1 November 2026

Husnexa runs on your own PC. The developer has no server and receives none of your data. There are no accounts, analytics or advertising.

## What the browser extension handles

| Data | When | Where it goes |
|---|---|---|
| The YouTube video link, title and format you chose | When you click a download option | To the Husnexa app on your PC |
| Your YouTube cookies | Only when a download needs sign-in and automatic sign-in retry is on | To the app on your PC, for that download |

The extension can only read cookies for `youtube.com`. It does not read your cookies until a download you started needs them.

## What the app does with this data

- Cookies are filtered to the video's site and written to a temporary file for one download attempt. The file is deleted afterwards.
- The app uses the cookies to contact that site as you would in your browser. They are not sent anywhere else.
- If automatic sign-in retry is on, the app can also read cookies for the site from browsers installed on your PC. They are used the same way.
- If you import a `cookies.txt` file, it is stored in `%LOCALAPPDATA%\Husnexa` until you delete it.
- Your settings, download history and error log stay in that same folder on your PC. The log can include site names and error messages.

## Connections the app makes

The app connects to the sites you download from. It also contacts GitHub and PyPI to check for updates to the app and yt-dlp. Those services see your IP address, as with any web request.

## Your controls

- Turn off **Automatic sign-in retry** in the app's Anti-Bot window to stop automatic cookie use. Choosing **Disabled** there turns cookies off completely.
- Remove the extension from your browser at any time.
- Delete `%LOCALAPPDATA%\Husnexa` to remove your settings, history, log and any imported cookies.

## Changes and contact

Changes to this policy are published in the project's GitHub repository. Questions can be raised at <https://github.com/husnexa/husnexa/issues>.
