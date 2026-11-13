import os
import re
import sys
import json
import time
import shutil
import ctypes
from ctypes import wintypes
import threading
import subprocess
import contextlib
import tempfile
from concurrent.futures import ThreadPoolExecutor

import updater
updater.setup_ytdlp_override()

import webview

import download_queue
import single_instance

# Pre-compiled URL regex for instant, zero-import clipboard URL checks
_CLIPBOARD_URL_REGEX = re.compile(r'https?://[^\s<>"]+')

EXTENSION_COOKIE_WAIT_SECONDS = 15

# File types the UI may open; anything else (e.g. .exe, .bat) is refused by play_file
_PLAYABLE_EXTENSIONS = frozenset((
    ".mp4", ".m4v", ".mkv", ".webm", ".mov", ".avi", ".flv", ".ts", ".3gp",
    ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac",
))

# Lazy-loaded downloader module reference (avoids blocking window creation on yt_dlp import)
_downloader_mod = None
_downloader_lock = threading.Lock()


def _get_downloader():
    """Lazily imports and returns the downloader module so startup UI creation is instant."""
    global _downloader_mod
    if _downloader_mod is None:
        with _downloader_lock:
            if _downloader_mod is None:
                import downloader as _dl
                _downloader_mod = _dl
    return _downloader_mod


# Native Win32 Clipboard constants and 64-bit safe function signatures
CF_UNICODETEXT = 13

if sys.platform == "win32":
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    _user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    _user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

    _user32.OpenClipboard.argtypes = [wintypes.HWND]
    _user32.OpenClipboard.restype = wintypes.BOOL

    _user32.GetClipboardData.argtypes = [wintypes.UINT]
    _user32.GetClipboardData.restype = wintypes.HANDLE

    _user32.CloseClipboard.argtypes = []
    _user32.CloseClipboard.restype = wintypes.BOOL

    _kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalLock.restype = wintypes.LPVOID

    _kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalUnlock.restype = wintypes.BOOL


def _read_win32_clipboard_text() -> str:
    """
    Reads Unicode text from the Windows clipboard using direct Win32 API calls.
    Avoids initializing Tkinter (Tcl/Tk) inside a pywebview/WebView2 STA process,
    preventing COM/OLE clipboard deadlocks and thread-apartment stalls.
    """
    if sys.platform != "win32":
        return ""

    if not _user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return ""

    opened = False
    for _ in range(3):
        if _user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.005)

    if not opened:
        return ""

    try:
        h_data = _user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data:
            return ""

        ptr = _kernel32.GlobalLock(h_data)
        if not ptr:
            return ""
        try:
            text = ctypes.wstring_at(ptr)
            return text or ""
        finally:
            _kernel32.GlobalUnlock(h_data)
    except Exception:
        return ""
    finally:
        _user32.CloseClipboard()


class _UiPusher:
    """Runs window.evaluate_js on its own thread.

    pywebview's evaluate_js waits for the page with no timeout. Called from a download
    thread, a slow or closed page froze the download for good (and kept the process
    alive after the window closed). Downloads now hand scripts here and never wait.
    Scripts pushed with the same key replace each other, so only the newest progress is sent.
    """

    def __init__(self):
        self.window = None
        self.closed = False
        self._lock = threading.Lock()
        self._pending = {}
        self._ready = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def push(self, js, key=None):
        if self.closed or not self.window:
            return
        with self._lock:
            k = key if key is not None else object()
            self._pending.pop(k, None)
            self._pending[k] = js
        self._ready.set()

    def _loop(self):
        while True:
            self._ready.wait()
            self._ready.clear()
            while True:
                with self._lock:
                    if not self._pending:
                        break
                    k = next(iter(self._pending))
                    js = self._pending.pop(k)
                window = self.window
                if self.closed or not window or not window.events.loaded.is_set():
                    continue
                try:
                    window.evaluate_js(js)
                except Exception:
                    pass


class DownloaderApi:
    # Prevent pywebview from recursively serializing non-method attributes
    _serializable = True

    def __init__(self):
        # Prefix internal state attributes with '_' so pywebview's inject_pywebview ->
        # get_functions() skips them and NEVER recurses into the Window or .NET BrowserForm!
        self._window = None
        self._ui = _UiPusher()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._update_check_lock = threading.Lock()
        self._last_update_result = None
        self._verified_installer = None
        # Held for the length of every download, manual or queued, so they never overlap
        self._download_gate = threading.Lock()
        self._cookie_requests = {}
        self._queue = download_queue.DownloadQueue(
            self._run_queue_job, self._push_queue_state, gate=self._download_gate
        )

    def _set_window(self, window):
        """Internal setter for the pywebview Window instance (prefixed with '_' to hide from JS bridge)."""
        self._window = window
        self._ui.window = window

    def set_window(self, window):
        """Backwards-compatible setter; stores window on private attribute self._window."""
        self._set_window(window)

    def _shutdown(self):
        """Stops any running download when the window closes."""
        self._ui.closed = True
        self._cancel_event.set()
        self._pause_event.set()

    def get_settings(self):
        """Retrieves user settings from %LOCALAPPDATA%\\Husnexa\\settings.json."""
        sfile = os.path.join(updater.get_local_appdata_dir(), "settings.json")
        defaults = {
            "download_dir": self.get_default_download_dir(),
            "theme": "dark",
            "turbo_enabled": True,
            "cookie_browser": "none",
            "auto_cookies": True,
            "embed_metadata": False,
            "embed_subtitles": False,
        }
        if not os.path.isfile(sfile):
            return defaults
        try:
            with open(sfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                defaults.update(data)
            return defaults
        except Exception:
            return defaults

    def save_settings(self, settings_dict):
        """Saves user settings to %LOCALAPPDATA%\\Husnexa\\settings.json."""
        appdata = updater.get_local_appdata_dir()
        os.makedirs(appdata, exist_ok=True)
        sfile = os.path.join(appdata, "settings.json")
        try:
            current = self.get_settings()
            if isinstance(settings_dict, dict):
                current.update(settings_dict)
            with open(sfile, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            return {"success": True, "settings": current}
        except Exception as e:
            return {"error": str(e)}

    def set_cookie_browser(self, browser_name):
        """Sets the browser to extract cookies from. 'none' turns cookies off, including automatic retries."""
        browser = str(browser_name).lower()
        changes = {"cookie_browser": browser}
        if browser == "none":
            changes["auto_cookies"] = False
        self.save_settings(changes)
        return {"success": True, "cookie_browser": browser}

    def set_auto_cookies(self, enabled):
        """Turns automatic cookie retries on or off."""
        self.save_settings({"auto_cookies": bool(enabled)})
        return {"success": True, "auto_cookies": bool(enabled)}

    def _cookie_args(self, cookie_browser=None):
        """Returns (chosen source, auto retries on) from the caller or saved settings."""
        settings = self.get_settings()
        return cookie_browser or settings.get("cookie_browser"), bool(settings.get("auto_cookies", True))

    def _push_cookie_retry(self, source):
        """Shows which cookie source is being tried."""
        if not self._window:
            return
        label = _get_downloader().cookie_source_label(source)
        message = json.dumps(f"Sign-in needed. Trying {label} cookies...")
        self._ui.push(f"window.update_progress(0, '', '', '', '', {message});", key="progress")

    def pause_download(self):
        """Pauses the active fragment download."""
        self._pause_event.clear()
        return {"paused": True}

    def resume_download(self):
        """Resumes the paused download."""
        self._pause_event.set()
        return {"resumed": True}

    def cancel_download(self):
        """Aborts and cancels the current download immediately."""
        self._cancel_event.set()
        self._pause_event.set()
        return {"cancelled": True}

    def get_default_download_dir(self):
        """Returns the system Downloads folder or current working directory."""
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads):
            return downloads
        return os.getcwd()

    def select_directory(self):
        """Opens a native Windows folder selector."""
        if not self._window:
            return ""
        try:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                return result[0]
            return ""
        except Exception as e:
            print(f"Error opening folder dialog: {e}")
            return ""

    def open_directory(self, path=""):
        """Opens the specified directory in Windows File Explorer."""
        if not path or not os.path.isdir(path):
            path = self.get_default_download_dir()
        try:
            os.startfile(path)
            return True
        except Exception as e:
            print(f"Error opening explorer: {e}")
            return False

    def open_extension_folder(self):
        """Opens the bundled browser extension folder so it can be loaded into a browser."""
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        folder = os.path.join(base, "extension")
        if not os.path.isdir(folder):
            return {"error": "Extension folder not found. Reinstall the app."}
        try:
            os.startfile(folder)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def open_download_dir(self, path=""):
        """Alias for open_directory to support alternative JS callers."""
        return self.open_directory(path)

    def check_cookies(self):
        """Checks if a valid cookies.txt file or browser cookie configuration is present."""
        settings = self.get_settings()
        cb = settings.get("cookie_browser", "none")
        if cb and cb not in ("none", "file"):
            return {"active": True, "source": cb, "label": f"{cb.capitalize()} Active"}
        cookie_file = _get_downloader().get_cookie_file() if cb == "file" else None
        if cookie_file:
            return {"active": True, "source": "file", "path": cookie_file, "label": "cookies.txt Active"}
        return {"active": False, "source": "none", "label": "Disabled"}

    def import_cookies(self):
        """Prompts user to select cookies.txt and copies it to the app folder."""
        if not self._window:
            return {"error": "Window not initialized"}
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("Text files (*.txt)", "All files (*.*)"),
            )
            if not result or len(result) == 0:
                return {"error": "No file chosen"}
            src = result[0]
            appdata_dir = updater.get_local_appdata_dir()
            os.makedirs(appdata_dir, exist_ok=True)
            dest = os.path.join(appdata_dir, "cookies.txt")
            shutil.copyfile(src, dest)
            self.save_settings({"cookie_browser": "file"})
            return {"success": True, "path": dest}
        except Exception as e:
            return {"error": str(e)}

    def get_clipboard_text(self):
        """Safely gets text from the Windows clipboard using non-blocking Win32 ctypes."""
        try:
            return _read_win32_clipboard_text()
        except Exception:
            return ""

    def analyze_url(self, url="", cookie_browser=None):
        """Analyzes a single media link across YouTube, Twitter, FB, IG, etc."""
        if not url or not url.strip():
            return {"error": "URL cannot be empty"}
        chosen, auto = self._cookie_args(cookie_browser)
        url = url.strip()
        downloader = _get_downloader()
        try:
            return downloader.with_cookie_fallback(
                url, lambda source: downloader.extract_video_info(url, cookie_browser=source), chosen, auto
            )
        except Exception as e:
            return {"error": str(e)}

    def analyze_bulk(self, raw_text="", cookie_browser=None):
        """Analyzes a playlist link or multiple URLs."""
        if not raw_text or not raw_text.strip():
            return {"error": "No text provided"}
        chosen, auto = self._cookie_args(cookie_browser)
        text = raw_text.strip()
        downloader = _get_downloader()
        try:
            first_url = (downloader.URL_REGEX.findall(text) or [""])[0]
            return downloader.with_cookie_fallback(
                first_url,
                lambda source: downloader.extract_bulk_or_playlist_info(text, cookie_browser=source),
                chosen, auto
            )
        except Exception as e:
            return {"error": str(e)}

    def _make_progress_hook(self, single):
        """Builds a yt-dlp progress hook that pushes throttled progress to the UI.

        single=True is the one-file flow (shows status text and a 'Finalizing' state);
        single=False is the per-item hook inside a bulk queue (status text left to the queue).
        """
        last_eval_time = 0.0

        def push(js_code):
            self._ui.push(js_code, key="progress")

        def hook(d):
            nonlocal last_eval_time
            if not self._window:
                return
            status = d.get("status")
            if status == "downloading":
                now = time.monotonic()
                if now - last_eval_time < 0.12:
                    return
                last_eval_time = now

                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                percent = (downloaded / total) * 100 if total > 0 else 0
                if not total and single and "_percent_str" in d:
                    try:
                        percent = float(d["_percent_str"].replace("%", "").strip())
                    except Exception:
                        percent = 0
                speed_str = d.get("_speed_str", "-- MB/s" if single else "")
                eta_str = d.get("_eta_str", "--" if single else "")
                down_mb = f"{downloaded / 1048576:.1f} MB"
                total_mb = f"{total / 1048576:.1f} MB" if total > 0 else ("Unknown" if single else "")
                label = "'Downloading...'" if single else "null"
                push(
                    f"window.update_progress({percent:.1f}, "
                    f"{json.dumps(speed_str)}, {json.dumps(eta_str)}, "
                    f"{json.dumps(down_mb)}, {json.dumps(total_mb)}, {label});"
                )
            elif status == "finished" and single:
                push("window.update_progress(100, '', '', '', '', 'Processing & Finalizing...');")

        return hook

    def download_single(self, url, media_type, quality, output_dir, is_turbo,
                        clip_start=None, clip_end=None,
                        embed_subtitles=False, embed_metadata=False,
                        cookie_browser=None):
        """Downloads a single video or audio file with throttled progress callbacks."""
        if not self._download_gate.acquire(blocking=False):
            return {"error": "Another download is running. Add this one to the queue instead."}
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = self.get_default_download_dir()
        threads = 8 if is_turbo else 1
        self._cancel_event.clear()
        self._pause_event.set()

        chosen, auto = self._cookie_args(cookie_browser)
        progress_hook = self._make_progress_hook(single=True)
        downloader = _get_downloader()

        try:
            res = downloader.with_cookie_fallback(
                url,
                lambda source: downloader.download_media(
                    url=url,
                    media_type=media_type,
                    quality_option=quality,
                    output_path=output_dir,
                    progress_hook=progress_hook,
                    turbo_threads=threads,
                    cancel_event=self._cancel_event,
                    pause_event=self._pause_event,
                    clip_start=clip_start,
                    clip_end=clip_end,
                    embed_subtitles=embed_subtitles,
                    embed_metadata=embed_metadata,
                    cookie_browser=source,
                ),
                chosen, auto, self._push_cookie_retry,
            )
            if res and res.get("cancelled"):
                return {"cancelled": True}
            return res
        except Exception as e:
            if self._cancel_event.is_set():
                return {"cancelled": True}
            return {"error": str(e)}
        finally:
            self._download_gate.release()

    def download_bulk(self, items, media_type, quality, output_dir, is_turbo, cookie_browser=None,
                      embed_subtitles=False, embed_metadata=False):
        """Downloads a list of queued videos/audio items with overall & throttled item status."""
        if not self._download_gate.acquire(blocking=False):
            return {"error": "Another download is running. Add these to the queue instead."}
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = self.get_default_download_dir()
        threads = 8 if is_turbo else 1
        self._cancel_event.clear()
        self._pause_event.set()

        settings = self.get_settings()
        chosen, auto = self._cookie_args(cookie_browser)
        embed_subtitles = embed_subtitles or bool(settings.get("embed_subtitles"))
        embed_metadata = embed_metadata or bool(settings.get("embed_metadata"))

        def overall_hook(idx, total, title, status):
            if not self._window:
                return
            js = (
                f"window.update_bulk_progress({idx}, {total}, "
                f"{json.dumps(title)}, {json.dumps(status)});"
            )
            self._ui.push(js)

        item_hook = self._make_progress_hook(single=False)

        try:
            result = _get_downloader().download_bulk_queue(
                items=items,
                media_type=media_type,
                quality_option=quality,
                output_path=output_dir,
                overall_hook=overall_hook,
                item_hook=item_hook,
                cancel_event=self._cancel_event,
                pause_event=self._pause_event,
                turbo_threads=threads,
                cookie_browser=chosen,
                embed_subtitles=embed_subtitles,
                embed_metadata=embed_metadata,
                auto_cookies=auto,
                on_cookie_retry=self._push_cookie_retry,
            )
            return result
        except Exception as e:
            if self._cancel_event.is_set():
                return {"cancelled": True}
            return {"error": str(e)}
        finally:
            self._download_gate.release()

    def enqueue_download(self, url, media_type="video", quality="best", title="", options=None):
        """Adds a download to the background queue."""
        options = options if isinstance(options, dict) else {}
        kept = {k: options[k] for k in ("clip_start", "clip_end", "embed_subtitles", "embed_metadata") if k in options}
        if options.get("from_extension") is True:
            kept["from_extension"] = True
        try:
            job = self._queue.add(url, media_type, quality, title=title, options=kept)
            return {"success": True, "job_id": job["id"]}
        except ValueError as e:
            return {"error": str(e)}

    def get_queue(self):
        """Returns all queued, active and recently finished jobs."""
        return self._queue.snapshot()

    def remove_queue_job(self, job_id):
        """Removes a job that is not currently downloading."""
        return {"success": self._queue.remove(job_id)}

    def clear_finished_queue_jobs(self):
        """Removes finished jobs from the queue list."""
        self._queue.clear_finished()
        return {"success": True}

    def _handle_pipe_request(self, request):
        """Answers a request from another process, such as a second launch of the app."""
        action = request.get("action")
        if action == "activate":
            self._bring_to_front()
            return {"success": True}
        if action == "enqueue":
            return self.enqueue_download(
                request.get("url"), request.get("media_type", "video"), request.get("quality", "best"),
                title=str(request.get("title") or "")[:300],
                options={"from_extension": request.get("from_extension") is True},
            )
        if action == "job_state":
            return self._job_state(request.get("job_id"))
        if action == "submit_cookies":
            return self._receive_cookies(request.get("job_id"), request.get("cookies"))
        return {"error": "Unknown request"}

    def _job_state(self, job_id):
        """Tells the helper whether a job is still running and whether it is waiting for cookies."""
        job = next((j for j in self._queue.snapshot() if j["id"] == job_id), None)
        return {
            "status": job["status"] if job else "missing",
            "needs_cookies": job_id in self._cookie_requests,
        }

    def _receive_cookies(self, job_id, cookies):
        """Hands cookies to the job that asked for them. Unrequested cookies are dropped."""
        waiting = self._cookie_requests.get(job_id)
        if not waiting:
            return {"error": "No job is waiting for cookies"}
        waiting["cookies"] = cookies if isinstance(cookies, list) else []
        waiting["ready"].set()
        return {"success": True}

    @contextlib.contextmanager
    def _extension_cookie_file(self, job):
        """Asks the extension for cookies and provides them as a temporary cookies.txt."""
        waiting = {"ready": threading.Event(), "cookies": None}
        self._cookie_requests[job["id"]] = waiting
        try:
            deadline = time.monotonic() + EXTENSION_COOKIE_WAIT_SECONDS
            while time.monotonic() < deadline and not self._cancel_event.is_set():
                if waiting["ready"].wait(0.2):
                    break
        finally:
            self._cookie_requests.pop(job["id"], None)

        text = _get_downloader().netscape_cookies(waiting["cookies"] or [], job["url"])
        waiting["cookies"] = None
        if not text:
            raise RuntimeError("failed to load cookies from the browser extension")
        appdata = updater.get_local_appdata_dir()
        os.makedirs(appdata, exist_ok=True)
        descriptor, path = tempfile.mkstemp(prefix="extension_cookies_", suffix=".txt", dir=appdata)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                f.write(text)
            yield path
        finally:
            try:
                os.remove(path)
            except OSError as e:
                _get_downloader().log_error(f"Could not delete temporary cookies: {e}")

    def _bring_to_front(self):
        if not self._window:
            return
        try:
            self._window.restore()
            self._window.on_top = True
            self._window.on_top = False
        except Exception as e:
            print(f"Error focusing window: {e}")

    def _push_queue_state(self, jobs):
        """Sends the newest queue state to the page without waiting on it."""
        self._ui.push(f"window.on_queue_update({json.dumps(jobs)});", key="queue")

    def _run_queue_job(self, job):
        """Runs one queue job. The queue holds the download gate while this runs."""
        self._cancel_event.clear()
        self._pause_event.set()
        settings = self.get_settings()
        output_dir = settings.get("download_dir")
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = self.get_default_download_dir()
        options = job["options"]
        progress_hook = self._make_progress_hook(single=True)
        named = bool(job["title"])

        def hook(d):
            nonlocal named
            title = (d.get("info_dict") or {}).get("title")
            if title and not named:
                named = True
                self._queue.update(job["id"], title=title)
            progress_hook(d)

        downloader = _get_downloader()
        chosen, auto = self._cookie_args()

        def download(cookie_browser=None, cookie_file=None):
            return downloader.download_media(
                url=job["url"],
                media_type=job["media_type"],
                quality_option=job["quality"],
                output_path=output_dir,
                progress_hook=hook,
                turbo_threads=8 if settings.get("turbo_enabled") else 1,
                cancel_event=self._cancel_event,
                pause_event=self._pause_event,
                clip_start=options.get("clip_start"),
                clip_end=options.get("clip_end"),
                embed_subtitles=bool(options.get("embed_subtitles", settings.get("embed_subtitles"))),
                embed_metadata=bool(options.get("embed_metadata", settings.get("embed_metadata"))),
                cookie_browser=cookie_browser,
                cookie_file=cookie_file,
            )

        def attempt(source):
            if source == "extension":
                with self._extension_cookie_file(job) as path:
                    return download(cookie_file=path)
            return download(cookie_browser=source)

        try:
            res = downloader.with_cookie_fallback(
                job["url"], attempt, chosen, auto, self._push_cookie_retry,
                extension=bool(options.get("from_extension")),
            )
        except Exception as e:
            if self._cancel_event.is_set():
                return {"cancelled": True}
            return {"error": str(e)}
        if res and res.get("success"):
            downloader.append_to_history(
                title=job["title"] or res.get("title"),
                platform=downloader.detect_platform(job["url"]),
                media_type=job["media_type"],
                quality=job["quality"],
                file_path=res.get("file_path"),
                url=job["url"],
            )
        return res

    def get_versions(self):
        """Returns installed app version, yt-dlp version, and override state."""
        _get_downloader()  # finish the background yt-dlp import first; importing it from two threads at once can fail
        return updater.get_installed_versions()

    def check_updates(self):
        """
        Checks for both yt-dlp (PyPI) and app (GitHub) updates concurrently
        using a ThreadPoolExecutor with a fast per-request timeout so the bridge
        never stalls for 20 seconds.
        """
        with self._update_check_lock:
            res = updater.check_all_updates(timeout=4)
            self._last_update_result = res
            return res

    def check_updates_async(self):
        """
        Non-blocking fire-and-forget update check: returns immediately and pushes
        the result to `window.onBackgroundUpdateCheck(res)` when complete.
        """
        def _bg_worker():
            try:
                res = self.check_updates()
                if self._window:
                    js = (
                        "if (window.onBackgroundUpdateCheck) { "
                        f"window.onBackgroundUpdateCheck({json.dumps(res)}); "
                        "}"
                    )
                    self._ui.push(js)
            except Exception:
                pass

        threading.Thread(target=_bg_worker, daemon=True).start()
        return {"started": True}

    def update_ytdlp(self):
        """Downloads the latest yt-dlp wheel from PyPI and extracts it to %LOCALAPPDATA%."""
        def progress_cb(pct, status):
            if not self._window:
                return
            js = (
                "if (window.update_ytdlp_progress) { "
                f"window.update_ytdlp_progress({pct}, {json.dumps(status)}); }}"
            )
            self._ui.push(js, key="ytdlp_progress")

        return updater.perform_ytdlp_update(progress_cb=progress_cb)

    def download_app_update(self, asset_url, asset_name="", expected_size=0, expected_sha256=""):
        """Downloads and verifies the new app .exe release asset into a temp staging location.

        Only the asset from the latest update check is accepted, and its size and hash come
        from that check rather than from the caller.
        """
        app_info = (self._last_update_result or {}).get("app") or {}
        if not asset_url or asset_url != app_info.get("asset_url"):
            return {"error": "Update file does not match the latest update check."}

        def progress_cb(pct, status):
            if not self._window:
                return
            js = (
                "if (window.update_app_progress) { "
                f"window.update_app_progress({pct}, {json.dumps(status)}); }}"
            )
            self._ui.push(js, key="app_progress")

        res = updater.download_and_verify_app_update(
            asset_url=asset_url,
            asset_name=app_info.get("asset_name") or "",
            expected_size=app_info.get("size_bytes") or None,
            expected_sha256=app_info.get("expected_sha256"),
            progress_cb=progress_cb,
        )
        if res.get("success"):
            self._verified_installer = res.get("file_path")
        return res

    def apply_app_update(self, setup_exe_path):
        """Launches the verified installer setup and exits the current app."""
        verified = self._verified_installer
        if not verified or not setup_exe_path or (
            os.path.normcase(os.path.abspath(setup_exe_path)) != os.path.normcase(os.path.abspath(verified))
        ):
            return {"error": "Only a verified update installer can be launched."}
        return updater.launch_installer_update(verified)

    def play_file(self, file_path):
        """Plays/opens the downloaded file with the default Windows application."""
        if not file_path or not os.path.isfile(file_path):
            return {"error": "File not found on disk"}
        if os.path.splitext(file_path)[1].lower() not in _PLAYABLE_EXTENSIONS:
            return {"error": "This file type cannot be opened from the app"}
        try:
            os.startfile(file_path)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def show_in_folder(self, file_path):
        """Reveals and selects the file in Windows File Explorer."""
        if not file_path:
            return {"error": "No file path provided"}
        try:
            if os.path.isfile(file_path):
                subprocess.Popen(f'explorer /select,"{os.path.abspath(file_path)}"')
                return {"success": True}
            folder = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            if os.path.isdir(folder):
                os.startfile(folder)
                return {"success": True}
            return {"error": "Folder not found"}
        except Exception as e:
            return {"error": str(e)}

    def play_completion_sound(self):
        """Plays a gentle native Windows completion chime."""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return {"success": True}
        except Exception:
            return {"success": True}

    def check_clipboard_url(self):
        """Checks if the Windows clipboard currently holds a supported media URL."""
        try:
            text = self.get_clipboard_text().strip()
            if text and (text.startswith("http://") or text.startswith("https://")):
                match = _CLIPBOARD_URL_REGEX.search(text)
                if match:
                    return {"has_url": True, "url": match.group(0)}
            return {"has_url": False}
        except Exception:
            return {"has_url": False}

    def get_history(self):
        """Returns the list of recent downloads from history.json with disk existence check."""
        hfile = os.path.join(updater.get_local_appdata_dir(), "history.json")
        if not os.path.isfile(hfile):
            return []
        try:
            with open(hfile, "r", encoding="utf-8") as f:
                history = json.load(f)
            for item in history:
                fp = item.get("file_path", "")
                item["file_exists"] = bool(fp and os.path.isfile(fp))
            return history
        except Exception:
            return []

    def add_history(self, item):
        """Appends a new download record to history.json (keeps up to 50 items)."""
        appdata = updater.get_local_appdata_dir()
        os.makedirs(appdata, exist_ok=True)
        hfile = os.path.join(appdata, "history.json")
        history = self.get_history()
        fp = item.get("file_path")
        if fp:
            history = [h for h in history if h.get("file_path") != fp]
        history.insert(0, item)
        try:
            _get_downloader().save_history(history)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def delete_history_item(self, item_id):
        """Removes a single item by id or file_path from history.json."""
        hfile = os.path.join(updater.get_local_appdata_dir(), "history.json")
        try:
            history = self.get_history()
            history = [h for h in history if str(h.get("id")) != str(item_id) and str(h.get("file_path")) != str(item_id)]
            with open(hfile, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def clear_history(self):
        """Clears all download history records."""
        hfile = os.path.join(updater.get_local_appdata_dir(), "history.json")
        try:
            with open(hfile, "w", encoding="utf-8") as f:
                json.dump([], f)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def open_url(self, url):
        """Opens a web URL in the user's default browser."""
        import webbrowser
        if not str(url).lower().startswith(("https://", "http://")):
            return False
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def restart_app(self):
        """Restarts the application to load new updates."""
        def _do_restart():
            import time as _time
            _time.sleep(0.3)
            updater.restart_app()

        threading.Thread(target=_do_restart, daemon=True).start()
        return {"restarting": True}


def get_html_path():
    """Find index.html in dev environment or PyInstaller bundled environment."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        bundle_dir = getattr(sys, "_MEIPASS", exe_dir)
        for check in [bundle_dir, exe_dir]:
            p = os.path.join(check, "gui_liquid", "index.html")
            if os.path.isfile(p):
                return p
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "gui_liquid", "index.html")


def _clear_stale_page_cache(storage_dir):
    """Drops the page's cached scripts and styles once after each app update.

    WebView2 keeps serving the previous app.js / style.css from its HTTP cache, so an
    updated app could keep running the old screen code. Settings and history live in
    their own files and are not touched.
    """
    marker = os.path.join(storage_dir, "ui_version.txt")
    try:
        with open(marker, "r", encoding="utf-8") as f:
            if f.read().strip() == updater.APP_VERSION:
                return
    except OSError:
        pass
    profile = os.path.join(storage_dir, "EBWebView", "Default")
    for name in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
        shutil.rmtree(os.path.join(profile, name), ignore_errors=True)
    try:
        with open(marker, "w", encoding="utf-8") as f:
            f.write(updater.APP_VERSION)
    except OSError:
        pass


def main(listener=None, initial_request=None):
    api = DownloaderApi()
    html_file = get_html_path()
    if not os.path.exists(html_file):
        print(f"Error: Could not locate frontend file: {html_file}")
        sys.exit(1)

    window = webview.create_window(
        title=f"Husnexa v{updater.APP_VERSION} — by M.Husnan",
        url=html_file,
        js_api=api,
        width=1040,
        height=800,
        min_size=(880, 620),
        background_color="#090d16",
        text_select=True,
    )
    api._set_window(window)
    window.events.closing += api._shutdown

    if listener:
        single_instance.serve(listener, api._handle_pipe_request)
    if initial_request and initial_request.get("action") == "enqueue":
        api._handle_pipe_request(initial_request)

    # Warm up heavy downloader / yt_dlp imports in a background daemon thread after window creation
    threading.Thread(target=_get_downloader, daemon=True).start()

    storage_dir = os.path.join(updater.get_local_appdata_dir(), "webview_cache")
    try:
        os.makedirs(storage_dir, exist_ok=True)
    except Exception:
        storage_dir = None
    if storage_dir:
        _clear_stale_page_cache(storage_dir)

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = None

    try:
        webview.start(
            debug=False,
            private_mode=False,
            storage_path=storage_dir,
            icon=icon_path,
        )
    finally:
        # A download or page call can still be running on a non-daemon thread. Without a
        # hard exit the process lived on with no window, and every later launch was handed
        # to that invisible copy, so the app looked stuck even after a restart.
        api._shutdown()
        # Let a cancelled download remove its partial files before the hard exit.
        # A download stuck in ffmpeg or the network gets 4 seconds at most.
        if api._download_gate.acquire(timeout=4):
            api._download_gate.release()
        os._exit(0)


if __name__ == "__main__":
    main()
