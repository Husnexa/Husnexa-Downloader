import os
import sys
import re
import json
import time
import shutil
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import imageio_ffmpeg
import yt_dlp

# Generic URL regex matching any web video / audio link
URL_REGEX = re.compile(r'https?://[^\s<>"]+')

# (platform label, hostnames matched exactly or as a parent domain)
PLATFORM_HOSTS = (
    ('YouTube', ('youtube.com', 'youtu.be')),
    ('X (Twitter)', ('twitter.com', 'x.com')),
    ('Facebook', ('facebook.com', 'fb.watch', 'fb.com')),
    ('Instagram', ('instagram.com',)),
    ('TikTok', ('tiktok.com',)),
    ('Reddit', ('reddit.com', 'redd.it')),
    ('Twitch', ('twitch.tv',)),
    ('SoundCloud', ('soundcloud.com',)),
    ('Vimeo', ('vimeo.com',)),
    ('Pinterest', ('pinterest.com', 'pin.it')),
    ('Dailymotion', ('dailymotion.com',)),
)

COOKIE_BROWSERS = ('chrome', 'edge', 'brave', 'firefox', 'opera', 'chromium', 'vivaldi')

# Error kinds that a signed-in session can fix
COOKIE_KINDS = ('bot', 'age', 'members', 'private', 'login')

TRIED_COOKIES_HINT = (
    "The app tried your saved sign-ins and they didn't work. "
    "Sign in to the site in Firefox and try again, or import a cookies.txt file."
)

# (kind, message for the user, lowercase text that identifies it), checked in order
ERROR_RULES = (
    ('cookies', "Couldn't read that browser's cookies. Close the browser and try again, or import a cookies.txt file.",
     ('could not copy chrome cookie', 'failed to decrypt', 'cookies database', 'failed to load cookies')),
    ('bot', "This site wants to confirm you're not a bot. Sign in to it in your browser and try again.",
     ('not a bot',)),
    ('age', "This video is age-restricted. Sign in to an adult account in your browser and try again.",
     ('confirm your age', 'age-restricted', 'age restricted', 'inappropriate for some users')),
    ('members', "This video is only for channel members or subscribers.",
     ('members-only', 'members only', 'join this channel', 'subscriber-only', 'subscribers only')),
    ('private', "This video is private. You need to be signed in to an account that can see it.",
     ('private video', 'video is private', 'content is private', 'account is private')),
    ('geo', "This video isn't available in your country.",
     ('available in your country', 'not available from your location', 'geo restriction', 'geo-restrict',
      'blocked it in your country')),
    ('rate', "This site is limiting requests right now. Wait a few minutes and try again.",
     ('too many requests', 'http error 429')),
    ('login', "This site needs you to be signed in. Sign in to it in your browser and try again.",
     ('sign in to', 'log in to', 'login required', 'you must log in', 'please log in', 'requires authentication',
      'use --cookies')),
    ('unavailable', "This video is unavailable. It may have been removed.",
     ('video unavailable', 'video is unavailable', 'has been removed', 'no longer available', 'does not exist', 'http error 404')),
    ('unsupported', "This link isn't supported. Check that it points to a video or audio page.",
     ('unsupported url',)),
    ('format', "That quality isn't available for this video. Choose another one.",
     ('requested format is not available',)),
    ('disk', "There isn't enough disk space. Free some space or choose another folder.",
     ('no space left', 'not enough space', 'errno 28')),
    ('network', "Couldn't reach the site. Check your internet connection and try again.",
     ('getaddrinfo', 'timed out', 'connection reset', 'connection was reset', 'recv failure', 'connection aborted',
      'network is unreachable', 'unable to download webpage', 'failed to resolve')),
)

# Cookie source that last worked for each site, kept until the app closes
_working_cookie_sources = {}

class FriendlyDownloadError(Exception):
    """A failed download or lookup whose message is ready to show to the user."""

def detect_platform(url):
    """Identify the source platform of a given URL for visual badging."""
    host = (urlparse(url.strip()).hostname or '').lower()
    for name, domains in PLATFORM_HOSTS:
        if any(host == d or host.endswith('.' + d) for d in domains):
            return name
    return 'Online Video'

def get_ffmpeg_path():
    """Locate ffmpeg executable from PyInstaller bundle, imageio-ffmpeg or system path."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        bundle_dir = getattr(sys, '_MEIPASS', exe_dir)
        for check_path in [
            bundle_dir,
            exe_dir,
            os.path.join(bundle_dir, 'imageio_ffmpeg', 'binaries'),
            os.path.join(exe_dir, 'imageio_ffmpeg', 'binaries'),
        ]:
            if os.path.isdir(check_path):
                for fname in os.listdir(check_path):
                    if fname.startswith('ffmpeg') and fname.endswith('.exe'):
                        return os.path.join(check_path, fname)
            f = os.path.join(check_path, 'ffmpeg.exe')
            if os.path.exists(f):
                return f

    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return "ffmpeg"

def get_cookie_file():
    """Check if cookies.txt exists in appdata, app dir, or current dir."""
    candidates = []
    try:
        import updater
        candidates.append(os.path.join(updater.get_local_appdata_dir(), 'cookies.txt'))
    except Exception:
        pass
    base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    candidates.append(os.path.join(base, 'Husnexa', 'cookies.txt'))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, 'cookies.txt'))
    if '__file__' in globals():
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'))
        
    for path in candidates:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path
    return None

def get_cookie_opts(cookie_source=None):
    """Returns yt-dlp cookie options for a browser name or 'file'; anything else uses no cookies."""
    source = str(cookie_source or '').lower()
    if source in COOKIE_BROWSERS:
        return {'cookiesfrombrowser': (source,)}
    if source == 'file':
        cookie_path = get_cookie_file()
        if cookie_path:
            return {'cookiefile': cookie_path}
    return {}

def find_installed_browsers():
    """Returns the supported browsers that have a profile folder on this PC, in the order to try them."""
    local = os.environ.get('LOCALAPPDATA', '')
    roaming = os.environ.get('APPDATA', '')
    profile_dirs = (
        ('firefox', (roaming, 'Mozilla', 'Firefox', 'Profiles')),
        ('chrome', (local, 'Google', 'Chrome', 'User Data')),
        ('edge', (local, 'Microsoft', 'Edge', 'User Data')),
        ('brave', (local, 'BraveSoftware', 'Brave-Browser', 'User Data')),
        ('opera', (roaming, 'Opera Software', 'Opera Stable')),
        ('vivaldi', (local, 'Vivaldi', 'User Data')),
        ('chromium', (local, 'Chromium', 'User Data')),
    )
    return [name for name, parts in profile_dirs if parts[0] and os.path.isdir(os.path.join(*parts))]

def netscape_cookies(cookies, url):
    """Returns cookies.txt text for the cookies that belong to url's site."""
    host = (urlparse(url).hostname or '').lower()
    lines = ['# Netscape HTTP Cookie File']
    for cookie in cookies:
        domain = str(cookie.get('domain') or '').lower()
        bare = domain.lstrip('.')
        fields = [str(cookie.get(key) or '') for key in ('path', 'name', 'value')]
        if '.' not in bare or not (host == bare or host.endswith('.' + bare)):
            continue
        if not fields[1] or any(c in field for field in fields for c in '\t\r\n'):
            continue
        lines.append('\t'.join((
            domain, 'TRUE' if domain.startswith('.') else 'FALSE', fields[0] or '/',
            'TRUE' if cookie.get('secure') else 'FALSE', str(int(cookie.get('expirationDate') or 0)),
            fields[1], fields[2],
        )))
    return '\n'.join(lines) + '\n' if len(lines) > 1 else None

def cookie_attempts(chosen=None, auto=True, remembered=None, extension=False):
    """
    Lists the cookie sources to try in order. None means no cookies, 'file' means cookies.txt,
    and 'extension' means cookies supplied by the browser extension.
    """
    chosen = str(chosen or '').lower()
    preferred = chosen if chosen in COOKIE_BROWSERS or chosen == 'file' else None
    if not auto:
        return [preferred]
    # Firefox comes before cookies.txt and Chromium browsers because it has no cookie encryption.
    installed = find_installed_browsers()
    firefox = [b for b in installed if b == 'firefox']
    others = [b for b in installed if b != 'firefox']
    cookie_file = ['file'] if get_cookie_file() else []
    order = [remembered] if remembered else []
    order.append(None)
    if extension:
        order.append('extension')
    order += ([preferred] if preferred else []) + firefox + cookie_file + others
    return list(dict.fromkeys(order))

def classify_error(error):
    """Sorts a yt-dlp error into a kind from ERROR_RULES, or 'other'."""
    text = str(error).lower()
    if type(error).__name__ == 'CookieLoadError':
        return 'cookies'
    for kind, _, fragments in ERROR_RULES:
        if any(fragment in text for fragment in fragments):
            return kind
    return 'other'

def friendly_error(error, tried_cookies=False):
    """Turns a yt-dlp error into a message for the user."""
    kind = classify_error(error)
    for rule_kind, message, _ in ERROR_RULES:
        if rule_kind == kind:
            if tried_cookies and kind in COOKIE_KINDS:
                return f"{message.split('. ')[0].rstrip('.')}. {TRIED_COOKIES_HINT}"
            return message
    text = re.sub(r'^ERROR:\s*', '', str(error).strip())
    if not text:
        return "The download failed. Please try again."
    return text[:297] + '...' if len(text) > 300 else text

def cookie_source_label(source):
    labels = {'file': 'cookies.txt', 'extension': 'browser extension'}
    return labels.get(source, str(source).capitalize())

def with_cookie_fallback(url, action, chosen=None, auto=True, on_retry=None, extension=False):
    """
    Runs action(cookie_source), moving to the next source when a site asks for a sign-in.
    Errors that cookies cannot help with stop straight away. Raises FriendlyDownloadError.
    """
    host = (urlparse(url).hostname or '').lower()
    attempts = cookie_attempts(chosen, auto, _working_cookie_sources.get(host), extension)
    failure = None
    tried_cookies = False
    for index, source in enumerate(attempts):
        if index and on_retry:
            on_retry(source)
        tried_cookies = tried_cookies or bool(source)
        try:
            result = action(source)
        except Exception as e:
            log_error(f"{host} [{source or 'no cookies'}] {e}")
            kind = classify_error(e)
            if kind != 'cookies' or failure is None:
                failure = e
            if kind != 'cookies' and kind not in COOKIE_KINDS:
                break
            continue
        if source == 'extension':
            pass  # Extension cookies are per-job, so there is nothing to reuse
        elif source:
            _working_cookie_sources[host] = source
        elif _working_cookie_sources.get(host):
            del _working_cookie_sources[host]
        return result
    raise FriendlyDownloadError(friendly_error(failure, tried_cookies)) from failure

def get_impersonate_args():
    """
    Returns options to impersonate a real Chrome browser TLS fingerprint
    if curl_cffi is available, bypassing Cloudflare anti-bot challenges (e.g. on Pixabay).
    """
    opts = {
        'extractor_args': {
            'generic': {
                'impersonate': ['chrome']
            }
        }
    }
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        opts['impersonate'] = ImpersonateTarget('chrome')
    except Exception:
        pass
    return opts

def find_js_runtimes():
    """Locates JavaScript runtimes for yt-dlp's YouTube solver: bundled deno, then installed ones."""
    runtimes = {}
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'deno', 'bin', 'deno.exe')
        if os.path.isfile(bundled):
            runtimes['deno'] = {'path': bundled}
    if 'deno' not in runtimes:
        try:
            import deno
            runtimes['deno'] = {'path': deno.find_deno_bin()}
        except Exception:
            pass
    for name in ('deno', 'node', 'bun'):
        path = shutil.which(name)
        if path and name not in runtimes:
            runtimes[name] = {'path': path}
    return runtimes

def get_js_runtime_opts():
    """Returns yt-dlp options enabling every JavaScript runtime found on this machine."""
    runtimes = find_js_runtimes()
    return {'js_runtimes': runtimes} if runtimes else {}

def get_single_item_opts(url):
    """Keeps a link to one video on that video when it also carries a list=... parameter."""
    return {'noplaylist': True} if 'list' in parse_qs(urlparse(url).query) else {}

def format_bytes(num_bytes):
    """Formats raw byte count into clean human readable string (~XX MB or ~X.X GB)."""
    if not num_bytes or num_bytes <= 0:
        return None
    mb = num_bytes / (1024 * 1024)
    if mb < 1.0:
        return f"~{int(round(num_bytes / 1024))} KB"
    elif mb < 1024.0:
        return f"~{int(round(mb))} MB" if mb >= 10 else f"~{mb:.1f} MB"
    else:
        return f"~{mb / 1024.0:.2f} GB"

def format_duration(seconds):
    if not seconds:
        return "Unknown"
    try:
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"
    except Exception:
        return "Unknown"

def parse_time_to_seconds(t_str):
    """Converts MM:SS, HH:MM:SS, or seconds string into float seconds."""
    if not t_str:
        return None
    s = str(t_str).strip()
    if not s:
        return None
    try:
        parts = s.split(":")
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except Exception:
        return None
    return None

def log_error(message):
    """Appends a diagnostic line to app.log in the app data folder (never raises)."""
    try:
        import updater
        appdata = updater.get_local_appdata_dir()
        os.makedirs(appdata, exist_ok=True)
        with open(os.path.join(appdata, "app.log"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass

def save_history(history):
    """Atomically writes history.json (up to 50 items) so a crash never corrupts it."""
    import updater
    appdata = updater.get_local_appdata_dir()
    os.makedirs(appdata, exist_ok=True)
    hfile = os.path.join(appdata, "history.json")
    tmp = hfile + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history[:50], f, indent=2)
    os.replace(tmp, hfile)

def append_to_history(title, platform, media_type, quality, file_path, url=None, duration=None):
    """Appends completed download entry to history.json (up to 50 items)."""
    if not file_path or not os.path.isfile(file_path):
        return
    try:
        import updater
        appdata = updater.get_local_appdata_dir()
        os.makedirs(appdata, exist_ok=True)
        hfile = os.path.join(appdata, "history.json")
        history = []
        if os.path.isfile(hfile):
            try:
                with open(hfile, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception as e:
                log_error(f"history.json unreadable, starting fresh: {e}")
                history = []

        fsize = format_bytes(os.path.getsize(file_path)) if os.path.isfile(file_path) else ""
        if media_type == 'audio':
            fmt_label = str(quality)
        elif str(quality).isdigit():
            fmt_label = f"{quality}p MP4"
        else:
            fmt_label = "Best MP4"
        item = {
            "id": str(int(time.time() * 1000)),
            "title": title or os.path.basename(file_path),
            "platform": platform or "Video",
            "url": url or "",
            "file_path": file_path,
            "format": fmt_label,
            "duration": duration or "--",
            "thumbnail": "",
            "size": fsize or "",
            "timestamp": datetime.now().strftime("%I:%M %p")
        }
        # Deduplicate existing records by file_path
        history = [h for h in history if h.get("file_path") != file_path]
        history.insert(0, item)
        save_history(history)
    except Exception as e:
        log_error(f"append_to_history failed: {e}")

def is_playlist_url(url):
    """Check if URL points to a playlist or contains a playlist parameter."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    if "/playlist" in path or "/sets/" in path:
        return True
    # A watch?v=... link with a list param is a single video; only bare list links are playlists.
    query = parse_qs(parsed.query)
    return "list" in query and "v" not in query

def extract_video_info(url, cookie_browser=None):
    """
    Extracts video details and sorted list of available resolutions
    from YouTube, X/Twitter, Facebook, Instagram, TikTok, Reddit, etc.
    """
    platform = detect_platform(url)
    
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    ydl_opts.update(get_impersonate_args())
    ydl_opts.update(get_cookie_opts(cookie_browser))
    ydl_opts.update(get_js_runtime_opts())
    ydl_opts.update(get_single_item_opts(url))

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if 'entries' in info:
            entries = list(info.get('entries', []))
            if not entries:
                raise ValueError("No video entries found in the provided URL.")
            info = entries[0]

        formats = info.get('formats', [])
        resolution_map = {}
        duration = info.get('duration') or 0

        # Calculate best audio stream size to add to video-only DASH streams
        best_audio_size = 0
        for f in formats:
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                asize = f.get('filesize') or f.get('filesize_approx') or 0
                if asize > best_audio_size:
                    best_audio_size = asize

        for f in formats:
            height = f.get('height')
            vcodec = f.get('vcodec', 'none')
            # Ensure it has video
            if height and vcodec != 'none':
                fps = f.get('fps') or 30
                
                if height >= 2160:
                    prefix = "4K • "
                elif height >= 1440:
                    prefix = "2K • "
                elif height >= 1080:
                    prefix = "FHD • "
                elif height >= 720:
                    prefix = "HD • "
                else:
                    prefix = ""
                
                label = f"{prefix}{height}p"
                if fps and fps >= 50:
                    label += f" ({int(fps)}fps)"

                # Compute estimated file size
                fsize = f.get('filesize') or f.get('filesize_approx')
                if not fsize and duration and (f.get('tbr') or f.get('vbr')):
                    bitrate = f.get('tbr') or (f.get('vbr', 0) + (f.get('abr') or 128))
                    fsize = int((bitrate * 1000 / 8) * duration)
                elif fsize and f.get('acodec') == 'none' and best_audio_size > 0:
                    fsize += best_audio_size

                fsize_str = format_bytes(fsize) if fsize else None
                
                if height not in resolution_map or (fps and fps > resolution_map[height]['fps']):
                    resolution_map[height] = {
                        'height': height,
                        'fps': fps,
                        'label': label,
                        'format_id': f.get('format_id'),
                        'filesize_str': fsize_str
                    }
        
        # Fallback if formats list lacked individual heights but main info has height
        if not resolution_map and info.get('height'):
            h = info['height']
            fsize = info.get('filesize') or info.get('filesize_approx')
            if not fsize and info.get('url'):
                try:
                    import requests
                    head_res = requests.head(
                        info['url'],
                        timeout=(1.5, 2.0),
                        allow_redirects=True,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if head_res.status_code == 200 and head_res.headers.get('content-length'):
                        fsize = int(head_res.headers['content-length'])
                except Exception:
                    pass
            resolution_map[h] = {
                'height': h,
                'fps': 30,
                'label': f"{h}p (Source)",
                'format_id': 'best',
                'filesize_str': format_bytes(fsize) if fsize else None
            }

        sorted_heights = sorted(resolution_map.keys(), reverse=True)
        resolutions = [resolution_map[h] for h in sorted_heights]

        # Estimated audio sizes based on duration
        audio_mp3_size = format_bytes(int(40000 * duration)) if duration else None
        audio_m4a_size = format_bytes(int(16000 * duration)) if duration else None
        audio_wav_size = format_bytes(int(176400 * duration)) if duration else None

        return {
            'id': info.get('id'),
            'platform': platform,
            'title': info.get('title') or f"{platform} Video",
            'channel': info.get('uploader') or info.get('channel') or info.get('creator') or platform,
            'duration': format_duration(info.get('duration')),
            'thumbnail': info.get('thumbnail'),
            'resolutions': resolutions,
            'audio_mp3_size': audio_mp3_size,
            'audio_m4a_size': audio_m4a_size,
            'audio_wav_size': audio_wav_size,
            'webpage_url': info.get('webpage_url', url)
        }

def extract_bulk_or_playlist_info(raw_text, cookie_browser=None):
    """
    Analyzes raw text containing a playlist link or multiple URLs across all supported platforms.
    """
    found_urls = URL_REGEX.findall(raw_text)
    if not found_urls:
        raise ValueError("No valid URLs found. Please check your links.")

    cookie_opts = get_cookie_opts(cookie_browser)

    # Check if single playlist URL
    if len(found_urls) == 1 and is_playlist_url(found_urls[0]):
        url = found_urls[0]
        platform = detect_platform(url)
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        ydl_opts.update(get_impersonate_args())
        ydl_opts.update(cookie_opts)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_entries = list(info.get('entries', []))
            if not raw_entries:
                raise ValueError("Playlist / Set is empty or unavailable.")

            items = []
            for i, e in enumerate(raw_entries):
                if not e:
                    continue
                v_id = e.get('id')
                v_url = e.get('url') or e.get('webpage_url')
                if not (v_url and v_url.startswith('http')):
                    if platform == 'YouTube' and (v_id or v_url):
                        v_url = f"https://www.youtube.com/watch?v={v_id or v_url}"
                    else:
                        v_url = e.get('webpage_url') or None
                
                if v_url:
                    items.append({
                        'title': e.get('title') or f"{platform} Item {len(items)+1}",
                        'url': v_url,
                        'duration': format_duration(e.get('duration')),
                        'platform': platform
                    })

            return {
                'type': 'playlist',
                'platform': platform,
                'title': info.get('title') or f"{platform} Playlist",
                'count': len(items),
                'items': items
            }

    # Multi-URL bulk list across any platform
    items = []
    seen = set()
    for u in found_urls:
        clean_u = u.split('&list=')[0] if 'watch?v=' in u and '&list=' in u else u
        clean_u = clean_u.rstrip('.,;)')
        if clean_u not in seen:
            seen.add(clean_u)
            plat = detect_platform(clean_u)
            items.append({
                'title': f"Item {len(items) + 1} ({plat})",
                'url': clean_u,
                'duration': "Unknown",
                'platform': plat
            })

    return {
        'type': 'bulk',
        'platform': 'Multi-Platform',
        'title': f"Bulk Queue ({len(items)} items)",
        'count': len(items),
        'items': items
    }

def download_media(url, media_type, quality_option, output_path, progress_hook=None,
                   turbo_threads=8, cancel_event=None, pause_event=None,
                   clip_start=None, clip_end=None, embed_subtitles=False,
                   embed_metadata=False, cookie_browser=None, cookie_file=None):
    """
    Downloads media across any supported site:
    - media_type: 'video' or 'audio'
    - quality_option: height int (e.g. 1080), 'best', or 'MP3'/'M4A'/'WAV' for audio
    - turbo_threads: number of parallel fragment download threads (default 8x)
    - cancel_event: threading.Event to abort download
    - pause_event: threading.Event to pause/resume download
    - clip_start / clip_end: optional trim points (seconds or 'MM:SS')
    - embed_subtitles: embed subtitles (CC) if available
    - embed_metadata: embed metadata & thumbnail artwork
    - cookie_browser: browser name to extract cookies from
    - cookie_file: path to a cookies.txt to use for this download
    """
    ffmpeg_exe = get_ffmpeg_path()
    outtmpl = os.path.join(output_path, '%(title).150B.%(ext)s')
    
    ydl_opts = {
        'outtmpl': outtmpl,
        'ffmpeg_location': ffmpeg_exe,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': False,
        'windowsfilenames': True,
    }
    ydl_opts.update(get_impersonate_args())
    ydl_opts.update(get_cookie_opts(cookie_browser))
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    ydl_opts.update(get_js_runtime_opts())
    ydl_opts.update(get_single_item_opts(url))

    # Multi-threaded turbo speed acceleration
    if turbo_threads and turbo_threads > 1:
        ydl_opts.update({
            'concurrent_fragment_downloads': turbo_threads,
            'http_chunk_size': 10485760,  # 10 MB chunk size to prevent throttling
            'buffersize': 16384,          # 16 KB socket buffer
        })

    # Optional clip trimmer
    start_sec = parse_time_to_seconds(clip_start) if clip_start else None
    end_sec = parse_time_to_seconds(clip_end) if clip_end else None
    if start_sec is not None or end_sec is not None:
        s_val = start_sec if start_sec is not None else 0
        e_val = end_sec if end_sec is not None else float('inf')
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(s_val, e_val)])
        ydl_opts['force_keyframes_at_cuts'] = True

    # Subtitles (Closed Captions)
    if embed_subtitles and media_type == 'video':
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitleslangs'] = ['en', 'orig']
        ydl_opts.setdefault('postprocessors', []).append({
            'key': 'FFmpegEmbedSubtitle',
            'already_have_subtitle': False,
        })

    # Embed Metadata & Thumbnail
    if embed_metadata:
        ydl_opts.setdefault('postprocessors', []).extend([
            {'key': 'FFmpegMetadata', 'add_chapters': True, 'add_infojson': 'if_exists'},
            {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
        ])
        ydl_opts['writethumbnail'] = True

    downloaded_files = []
    postprocessed_files = []
    partial_files = set()   # every file name seen while downloading, for cleanup on cancel

    def internal_hook(d):
        for key in ('filename', 'tmpfilename'):
            if d.get(key):
                partial_files.add(d[key])
        if d.get('status') == 'finished':
            fn = d.get('filename')
            if fn and fn not in downloaded_files:
                downloaded_files.append(fn)
        if cancel_event and cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")
        if pause_event:
            while not pause_event.is_set():
                if cancel_event and cancel_event.is_set():
                    raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")
                time.sleep(0.15)
        if progress_hook:
            progress_hook(d)

    def pp_hook(d):
        if d.get('status') == 'finished':
            info_dict = d.get('info_dict', {})
            fp = info_dict.get('filepath') or d.get('filepath')
            if fp and fp not in postprocessed_files:
                postprocessed_files.append(fp)

    ydl_opts['progress_hooks'] = [internal_hook]
    ydl_opts['postprocessor_hooks'] = [pp_hook]

    q_upper = str(quality_option).upper()
    if media_type == 'audio':
        if q_upper == 'WAV':
            ydl_opts['format'] = 'bestaudio/best'
            audio_pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}
        elif q_upper == 'M4A':
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            audio_pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}
        else:  # Default MP3 320 kbps
            ydl_opts['format'] = 'bestaudio/best'
            audio_pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}
        # Audio extraction must run before metadata/thumbnail embedding.
        ydl_opts['postprocessors'] = [audio_pp] + ydl_opts.get('postprocessors', [])
    else:
        # Video MP4 (Universal format selector)
        if quality_option == "best" or not str(quality_option).isdigit():
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })
        else:
            height = int(quality_option)
            ydl_opts.update({
                'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
                'merge_output_format': 'mp4',
            })

    audio_ext = 'wav' if q_upper == 'WAV' else ('m4a' if q_upper == 'M4A' else 'mp3')
    final_ext = audio_ext if media_type == 'audio' else 'mp4'
    final_file = None

    try:
        # Single-pass extract_info with download=True completely eliminates duplicate network requests
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info and 'entries' in info:
                entries = [e for e in (info.get('entries') or []) if e]
                info = entries[0] if entries else info

            # yt-dlp records the true post-processed path here.
            for dl in reversed((info or {}).get('requested_downloads') or []):
                fp = dl.get('filepath')
                if fp and os.path.isfile(fp):
                    final_file = fp
                    break

            if not final_file and info:
                try:
                    candidate = ydl.prepare_filename(info)
                    base, _ = os.path.splitext(candidate)
                    for fp in (candidate, f"{base}.{final_ext}"):
                        if os.path.isfile(fp):
                            final_file = fp
                            break
                except Exception:
                    pass

        # Fallback to hook-tracked files
        if not final_file:
            for fp in reversed(postprocessed_files + downloaded_files):
                base, _ = os.path.splitext(fp)
                for cand in (fp, f"{base}.{final_ext}"):
                    if os.path.isfile(cand):
                        final_file = cand
                        break
                if final_file:
                    break

        file_size = None
        if final_file:
            try:
                file_size = os.path.getsize(final_file)
            except OSError:
                pass
        return {
            "success": True,
            "file_path": os.path.abspath(final_file) if final_file else None,
            "file_size": file_size,
            "title": (info or {}).get('title')
        }
    except yt_dlp.utils.DownloadCancelled:
        _cleanup_partial_files(partial_files | set(downloaded_files))
        return {"cancelled": True}
    except Exception:
        if cancel_event and cancel_event.is_set():
            _cleanup_partial_files(partial_files | set(downloaded_files))
            return {"cancelled": True}
        raise

# yt-dlp stream files waiting to be merged, e.g. "Title.f401.mp4", "Title.f251-drc.webm", "Title.fhls-720p.mp4"
_FORMAT_PART_RE = re.compile(r"\.f(\d[\w-]*|hls-[\w-]+|dash-[\w-]+)\.[A-Za-z0-9]+$")


def _cleanup_partial_files(files):
    """Removes what a cancelled download leaves behind.

    That is .part/.ytdl files, fragment pieces, and finished single streams
    (like 'Title.f401.mp4') that were waiting to be merged. A finished, merged
    file is never touched.
    """
    import glob
    targets = set()
    for fp in files:
        if not fp:
            continue
        base = fp[:-5] if fp.endswith('.part') else fp
        targets.update({fp, base + '.part', base + '.ytdl', fp + '.ytdl'})
        targets.update(glob.glob(glob.escape(base) + '.part-Frag*'))
        targets.update(glob.glob(glob.escape(fp) + '-Frag*'))
    for path in targets:
        name = os.path.basename(path)
        removable = (name.endswith(('.part', '.ytdl')) or '.part-Frag' in name or '-Frag' in name
                     or _FORMAT_PART_RE.search(name))
        if not removable:
            continue
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

def download_bulk_queue(items, media_type, quality_option, output_path,
                        overall_hook=None, item_hook=None, cancel_event=None,
                        pause_event=None, turbo_threads=8, cookie_browser=None,
                        embed_subtitles=False, embed_metadata=False,
                        auto_cookies=True, on_cookie_retry=None):
    """
    Sequentially downloads a batch of items from any mix of platforms with optional Turbo acceleration.
    """
    total = len(items)
    successful = 0
    failed = []

    for idx, item in enumerate(items):
        if cancel_event and cancel_event.is_set():
            if overall_hook:
                overall_hook(idx, total, "Download Cancelled by User", "cancelled")
            break

        title = item.get('title', f"Video {idx+1}")
        url = item.get('url')

        if overall_hook:
            overall_hook(idx + 1, total, title, "downloading")

        try:
            res = with_cookie_fallback(
                url,
                lambda source: download_media(
                    url=url,
                    media_type=media_type,
                    quality_option=quality_option,
                    output_path=output_path,
                    progress_hook=item_hook,
                    turbo_threads=turbo_threads,
                    cancel_event=cancel_event,
                    pause_event=pause_event,
                    embed_subtitles=embed_subtitles,
                    embed_metadata=embed_metadata,
                    cookie_browser=source
                ),
                cookie_browser, auto_cookies, on_cookie_retry
            )
            if res and res.get('cancelled'):
                if overall_hook:
                    overall_hook(idx, total, "Download Cancelled by User", "cancelled")
                break
            successful += 1
            if overall_hook:
                overall_hook(idx + 1, total, title, "finished")

            # Append completed bulk download to history.json
            fp = res.get('file_path') if res else None
            if fp:
                append_to_history(
                    title=title,
                    platform=item.get('platform', 'Video'),
                    media_type=media_type,
                    quality=quality_option,
                    file_path=fp,
                    url=url,
                    duration=item.get('duration')
                )
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                if overall_hook:
                    overall_hook(idx, total, "Download Cancelled by User", "cancelled")
                break
            failed.append((title, str(e)))
            if overall_hook:
                overall_hook(idx + 1, total, title, "error")

    if overall_hook and not (cancel_event and cancel_event.is_set()):
        overall_hook(total, total, f"Completed: {successful}/{total} successful", "finished")

    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'cancelled': bool(cancel_event and cancel_event.is_set())
    }
