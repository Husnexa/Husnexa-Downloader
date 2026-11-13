# Husnexa

![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)

A Windows desktop app for downloading video and audio from many sites, with a
liquid-glass interface. Paste a link, pick a quality, and download. It also handles
playlists and bulk lists. yt-dlp (the download engine) updates itself in one click.

<img src="husnexa_logo.png" width="160" alt="Husnexa logo">

## Download

Run the installer you were sent, `Husnexa_Setup_v<version>.exe`. That's it. No Python needed.

## What it does

- **Many sites** — video and audio from the sites yt-dlp supports.
- **Single or bulk** — one link, a whole playlist, or a pasted list of links.
- **Download queue** — add more downloads while one is running.
- **YouTube button** — download from the player with the browser extension.
- **Turbo mode** — downloads a video's fragments in parallel for more speed.
- **Control** — pause, resume and cancel any download.
- **Login-only videos** — retries automatically with your browser sign-in, or import a `cookies.txt` file.
- **Engine update** — one click to get the newest yt-dlp.
- **Light and dark mode** — glass look, animated background, wave progress bar.

## YouTube download button

1. In the app, open **Anti-Bot** and click **Open folder** under **YouTube download button**.
2. In your browser, open the extensions page (`edge://extensions` or `chrome://extensions`).
3. Turn on **Developer mode**, choose **Load unpacked**, and select the folder from step 1.
4. Hover over a YouTube video and click **Download**.

It's tested in Microsoft Edge. Chrome and Brave use the same engine. Firefox support is included but untested.
See the [privacy policy](docs/PRIVACY.md) for how the extension handles your data.

## Screenshots

| | |
|---|---|
| ![Dark mode](docs/home-dark.png)<br>**Dark mode** | ![Light mode](docs/home-light.png)<br>**Light mode** |
| ![Batch queue](docs/batch-queue.png)<br>**Batch queue** | ![Updates](docs/updates.png)<br>**Updates** |

## Quick start

1. Open the app and paste a link.
2. Choose video or audio, and the quality.
3. Pick a save folder and press **Download**.

## Run from source

Needs Windows and Python 3.10+.

```bash
git clone https://github.com/husnexa/husnexa.git
cd husnexa
pip install -r requirements.txt
python app.py
```

To use the browser extension from source, run `python native_host_setup.py register` once.

## Build it yourself

| Goal | Command | Output |
|---|---|---|
| Portable exe | `build_exe.bat` | `dist/` |
| Installer | `build_installer.bat` (needs Inno Setup) | `installer_output/` |

## Where things are

| | Installed | From source |
|---|---|---|
| App | `%LOCALAPPDATA%\Programs\Husnexa` | the cloned folder |
| Downloads | the folder you pick in Settings | same |

## Credits and license

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and FFmpeg.
Released under the MIT License.

Only download content you have the right to download.
