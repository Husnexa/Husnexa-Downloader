import base64
import hashlib
import io
import json
import os
import queue
import sys
import threading
import time
import uuid
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_extension_package
import download_queue
import downloader
import native_host
import native_host_setup
import single_instance
import updater


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_project_json(*parts):
    with open(os.path.join(PROJECT_DIR, *parts), encoding="utf-8") as f:
        return json.load(f)


def test_extension_key_matches_the_allowed_id():
    digest = hashlib.sha256(base64.b64decode(read_project_json("extension", "manifest.json")["key"])).hexdigest()
    extension_id = "".join(chr(ord("a") + int(c, 16)) for c in digest[:32])
    assert extension_id == native_host_setup.CHROMIUM_EXTENSION_ID
    allowed = read_project_json("native_host_chromium.json")["allowed_origins"]
    assert allowed == [f"chrome-extension://{extension_id}/"]


def test_release_manifests_match_setup_constants():
    firefox = read_project_json("native_host_firefox.json")
    chromium = read_project_json("native_host_chromium.json")
    gecko = read_project_json("extension", "manifest.json")["browser_specific_settings"]["gecko"]
    assert firefox["allowed_extensions"] == [native_host_setup.FIREFOX_EXTENSION_ID] == [gecko["id"]]
    assert firefox["name"] == chromium["name"] == native_host_setup.HOST_NAME
    assert firefox["path"] == chromium["path"] == native_host_setup.HELPER_EXE_NAME


def test_store_package_has_no_fixed_key():
    with zipfile.ZipFile(build_extension_package.build()) as z:
        assert "key" not in json.loads(z.read("manifest.json"))
        assert {"background.js", "content.js", "icons/icon128.png"} <= set(z.namelist())


def test_native_message_round_trip():
    stream = io.BytesIO()
    native_host.write_message(stream, {"url": "https://x.com/é"})
    stream.seek(0)
    assert native_host.read_message(stream) == {"url": "https://x.com/é"}
    assert native_host.read_message(stream) is None


def test_native_message_rejects_oversized_length():
    with pytest.raises(ValueError):
        native_host.read_message(io.BytesIO(b"\xff\xff\xff\x7f"))


GOOD_DOWNLOAD = {"action": "download", "url": "https://www.youtube.com/watch?v=abc", "title": "T" * 500}


def test_native_host_forwards_to_running_app():
    sent = []
    reply = native_host.handle_message(GOOD_DOWNLOAD, send=lambda r: sent.append(r) or {"success": True})
    assert reply == {"success": True}
    assert sent[0]["action"] == "enqueue" and sent[0]["quality"] == "best"
    assert len(sent[0]["title"]) == 300


def test_native_host_starts_app_when_closed():
    started, sent = [], []

    def closed_until_started(request):
        if not started:
            raise FileNotFoundError("no pipe")
        sent.append(request)
        return {"success": True, "job_id": "j1"}

    reply = native_host.handle_message(
        GOOD_DOWNLOAD, send=closed_until_started, launch=lambda: started.append(True)
    )
    assert reply["job_id"] == "j1" and sent[0]["url"] == GOOD_DOWNLOAD["url"]
    assert sent[0]["from_extension"] is True


def test_native_host_reports_when_app_never_starts():
    def closed(request):
        raise FileNotFoundError("no pipe")

    reply = native_host.handle_message(GOOD_DOWNLOAD, send=closed, launch=lambda: None, start_seconds=0)
    assert "error" in reply


def fake_app(states):
    """Returns a fake pipe sender that walks through job states and records requests."""
    sent = []
    remaining = list(states)

    def send(request):
        sent.append(request)
        if request["action"] == "job_state":
            return remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return {"success": True}

    return send, sent


def test_follow_job_relays_cookies_once_when_asked():
    send, sent = fake_app([
        {"status": "downloading", "needs_cookies": False},
        {"status": "downloading", "needs_cookies": True},
        {"status": "downloading", "needs_cookies": True},
        {"status": "done", "needs_cookies": False},
    ])
    inbox, output = queue.Queue(), io.BytesIO()
    inbox.put({"type": "cookies", "cookies": [{"name": "a"}]})
    native_host.follow_job("j1", inbox, output, send=send, poll_seconds=0.01)
    output.seek(0)
    assert native_host.read_message(output) == {"type": "need_cookies"}
    assert native_host.read_message(output) is None
    assert [r for r in sent if r["action"] == "submit_cookies"] == [
        {"action": "submit_cookies", "job_id": "j1", "cookies": [{"name": "a"}]}
    ]


def test_follow_job_never_asks_when_job_needs_nothing():
    send, _ = fake_app([{"status": "done", "needs_cookies": False}])
    output = io.BytesIO()
    native_host.follow_job("j1", queue.Queue(), output, send=send)
    assert output.getvalue() == b""


def test_follow_job_stops_when_browser_goes_away():
    send, _ = fake_app([{"status": "queued", "needs_cookies": False}])
    inbox = queue.Queue()
    inbox.put(None)
    native_host.follow_job("j1", inbox, io.BytesIO(), send=send)
    assert inbox.get_nowait() is None


def test_netscape_cookies_keep_only_the_matching_site():
    cookies = [
        {"name": "SID", "value": "1", "domain": ".youtube.com", "path": "/", "secure": True, "expirationDate": 99.5},
        {"name": "other", "value": "2", "domain": ".google.com", "path": "/"},
        {"name": "wide", "value": "3", "domain": ".com", "path": "/"},
        {"name": "fake", "value": "4", "domain": "notyoutube.com", "path": "/"},
        {"name": "bad", "value": "a\tb", "domain": ".youtube.com", "path": "/"},
    ]
    text = downloader.netscape_cookies(cookies, "https://www.youtube.com/watch?v=a")
    assert text.splitlines()[1:] == [".youtube.com\tTRUE\t/\tTRUE\t99\tSID\t1"]
    assert text.startswith("# Netscape HTTP Cookie File")
    assert downloader.netscape_cookies(cookies[1:2], "https://www.youtube.com/watch?v=a") is None


def test_extension_source_comes_after_no_cookies_and_respects_disabled(monkeypatch, no_cookie_sources):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["firefox"])
    assert downloader.cookie_attempts("none", True, extension=True) == [None, "extension", "firefox"]
    assert downloader.cookie_attempts("none", False, extension=True) == [None]
    assert downloader.cookie_attempts("none", True) == [None, "firefox"]


def test_extension_cookies_are_not_remembered(no_cookie_sources):
    url = "https://www.youtube.com/watch?v=a"

    def action(source):
        if source is None:
            raise RuntimeError("Sign in to confirm you're not a bot")
        return {"success": True}

    downloader.with_cookie_fallback(url, action, "none", True, extension=True)
    assert downloader._working_cookie_sources == {}


@pytest.mark.parametrize("message", [
    "text", {"action": "activate"}, {"action": "enqueue", "url": "https://x.com/a"},
    {"action": "download", "url": "file:///C:/evil.exe"},
    {"action": "download", "url": "https://x.com/a", "media_type": "exe"},
])
def test_native_host_rejects_bad_requests(message):
    def must_not_run(request):
        raise AssertionError("request should not be forwarded")

    assert "error" in native_host.handle_message(message, send=must_not_run, launch=must_not_run)


@pytest.fixture
def no_cookie_sources(monkeypatch):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: [])
    monkeypatch.setattr(downloader, "get_cookie_file", lambda: None)
    downloader._working_cookie_sources.clear()
    yield
    downloader._working_cookie_sources.clear()


@pytest.mark.parametrize("message,kind", [
    ("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser", "bot"),
    ("ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate", "age"),
    ("ERROR: Join this channel to get access to members-only content", "members"),
    ("ERROR: Private video. Sign in if you've been granted access to this video", "private"),
    ("ERROR: [Instagram] abc: Requested content is not available, rate-limit reached or login required", "login"),
    ("ERROR: The uploader has not made this video available in your country", "geo"),
    ("ERROR: This video is not available in your country", "geo"),
    ("ERROR: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>", "network"),
    ("ERROR: Could not copy Chrome cookie database", "cookies"),
    ("ERROR: Failed to decrypt with DPAPI", "cookies"),
    ("ERROR: Unsupported URL: https://x.com", "unsupported"),
    ("something new", "other"),
])
def test_classify_error(message, kind):
    assert downloader.classify_error(message) == kind


def test_friendly_error_hides_raw_ytdlp_text():
    raw = "ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies"
    message = downloader.friendly_error(raw)
    assert "--cookies" not in message and "ERROR" not in message
    assert downloader.TRIED_COOKIES_HINT in downloader.friendly_error(raw, tried_cookies=True)
    assert downloader.friendly_error("ERROR: something new") == "something new"
    assert downloader.friendly_error("ERROR: ") == "The download failed. Please try again."
    assert downloader.classify_error("ERROR: \ncurl: (56) Recv failure: Connection was reset") == "network"


def test_cookie_opts_stay_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(downloader, "get_cookie_file", lambda: "cookies.txt")
    assert downloader.get_cookie_opts("none") == {}
    assert downloader.get_cookie_opts(None) == {}
    assert downloader.get_cookie_opts("file") == {"cookiefile": "cookies.txt"}
    assert downloader.get_cookie_opts("firefox") == {"cookiesfrombrowser": ("firefox",)}


def test_cookie_attempts_order(monkeypatch):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["firefox", "chrome", "edge"])
    monkeypatch.setattr(downloader, "get_cookie_file", lambda: "cookies.txt")
    assert downloader.cookie_attempts("none", True) == [None, "firefox", "file", "chrome", "edge"]
    assert downloader.cookie_attempts("edge", True) == [None, "edge", "firefox", "file", "chrome"]
    assert downloader.cookie_attempts("none", False) == [None]
    assert downloader.cookie_attempts("edge", False) == ["edge"]
    assert downloader.cookie_attempts("none", True, remembered="chrome")[:2] == ["chrome", None]


def test_fallback_retries_until_a_source_works(monkeypatch, no_cookie_sources):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["firefox", "chrome"])
    tried, retried = [], []

    def action(source):
        tried.append(source)
        if source == "chrome":
            return {"success": True}
        if source is None:
            raise RuntimeError("Sign in to confirm you're not a bot")
        raise RuntimeError("Could not copy Chrome cookie database")

    url = "https://www.youtube.com/watch?v=a"
    result = downloader.with_cookie_fallback(url, action, "none", True, retried.append)
    assert result == {"success": True}
    assert tried == [None, "firefox", "chrome"] and retried == ["firefox", "chrome"]

    tried.clear()
    downloader.with_cookie_fallback(url, action, "none", True)
    assert tried == ["chrome"]


def test_fallback_stops_on_errors_cookies_cannot_fix(monkeypatch, no_cookie_sources):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["firefox"])
    tried = []

    def action(source):
        tried.append(source)
        raise RuntimeError("This video is not available in your country")

    with pytest.raises(downloader.FriendlyDownloadError, match="your country"):
        downloader.with_cookie_fallback("https://x.com/a", action, "none", True)
    assert tried == [None]


def test_fallback_reports_login_failure_not_cookie_read_failure(monkeypatch, no_cookie_sources):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["chrome"])

    def action(source):
        raise RuntimeError("Failed to decrypt with DPAPI" if source else "Sign in to confirm you're not a bot")

    with pytest.raises(downloader.FriendlyDownloadError, match="not a bot") as caught:
        downloader.with_cookie_fallback("https://x.com/a", action, "none", True)
    assert downloader.TRIED_COOKIES_HINT in str(caught.value)


def test_fallback_disabled_makes_one_attempt(monkeypatch, no_cookie_sources):
    monkeypatch.setattr(downloader, "find_installed_browsers", lambda: ["firefox"])
    tried = []

    def action(source):
        tried.append(source)
        raise RuntimeError("Sign in to confirm you're not a bot")

    with pytest.raises(downloader.FriendlyDownloadError):
        downloader.with_cookie_fallback("https://x.com/a", action, "none", False)
    assert tried == [None]


def wait_until(condition, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def status_of(queue, job):
    return next(j["status"] for j in queue.snapshot() if j["id"] == job["id"])


@pytest.mark.parametrize("args", [
    ("not a link",), ("file:///C:/evil.exe",), ("javascript:alert(1)",),
    ("https://x.com/" + "a" * 3000,), ("https://x.com/a", "exe"),
    ("https://x.com/a", "audio", "EXE"), ("https://x.com/a", "video", "1080;rm"),
])
def test_normalize_request_rejects_bad_input(args):
    with pytest.raises(ValueError):
        download_queue.normalize_request(*args)


def test_queue_runs_jobs_one_at_a_time_in_order():
    ran, active, peak = [], [0], [0]

    def run(job):
        active[0] += 1
        peak[0] = max(peak[0], active[0])
        time.sleep(0.02)
        ran.append(job["url"])
        active[0] -= 1
        return {"success": True, "title": "Named"}

    queue = download_queue.DownloadQueue(run)
    for i in range(3):
        queue.add(f"https://x.com/{i}")
    assert wait_until(lambda: len(ran) == 3 and all(j["status"] == "done" for j in queue.snapshot()))
    assert ran == [f"https://x.com/{i}" for i in range(3)]
    assert peak[0] == 1
    assert queue.snapshot()[0]["title"] == "Named"


def test_queue_waits_for_gate_held_by_manual_download():
    gate, ran = threading.Lock(), []
    gate.acquire()
    queue = download_queue.DownloadQueue(lambda job: ran.append(1) or {"success": True}, gate=gate)
    job = queue.add("https://x.com/a")
    time.sleep(0.1)
    assert status_of(queue, job) == "queued" and not ran
    gate.release()
    assert wait_until(lambda: status_of(queue, job) == "done")


def test_queue_records_failure_and_keeps_going():
    def run(job):
        if job["url"].endswith("bad"):
            raise RuntimeError("boom")
        return {"cancelled": True} if job["url"].endswith("stop") else {"success": True}

    queue = download_queue.DownloadQueue(run)
    bad, stop, good = [queue.add(f"https://x.com/{n}") for n in ("bad", "stop", "good")]
    assert wait_until(lambda: status_of(queue, good) == "done")
    assert status_of(queue, bad) == "failed" and status_of(queue, stop) == "cancelled"
    assert next(j for j in queue.snapshot() if j["id"] == bad["id"])["error"] == "boom"


def test_queue_ignores_duplicates_and_removes_waiting_jobs():
    gate = threading.Lock()
    gate.acquire()
    queue = download_queue.DownloadQueue(lambda job: {"success": True}, gate=gate)
    first = queue.add("https://x.com/a")
    assert queue.add("https://x.com/a")["id"] == first["id"]
    assert queue.add("https://x.com/a", "audio", "MP3")["id"] != first["id"]
    assert queue.remove(first["id"]) is True
    assert len(queue.snapshot()) == 1


@pytest.mark.parametrize("argv,request_,restarting", [
    ([], {"action": "activate"}, False),
    (["--restarting"], {"action": "activate"}, True),
    (["https://x.com/a", "--media", "audio", "--quality", "MP3"],
     {"action": "enqueue", "url": "https://x.com/a", "media_type": "audio", "quality": "MP3"}, False),
    (["https://x.com/a", "--title", "A video"],
     {"action": "enqueue", "url": "https://x.com/a", "title": "A video"}, False),
])
def test_parse_launch_args(argv, request_, restarting):
    assert single_instance.parse_launch_args(argv) == (request_, restarting)


@pytest.fixture
def pipe():
    address = rf"\\.\pipe\HusnexaTest-{uuid.uuid4().hex}"
    listener = single_instance.claim(address=address)
    yield address, listener
    listener.close()


def test_only_first_copy_claims_the_pipe(pipe):
    address, listener = pipe
    assert listener is not None
    assert single_instance.claim(address=address) is None


def test_requests_reach_the_running_copy(pipe):
    address, listener = pipe
    single_instance.serve(listener, lambda request: {"echo": request["url"]})
    for i in range(3):
        url = f"https://x.com/{i}"
        assert single_instance.send_request({"url": url}, address) == {"echo": url}


def test_pipe_survives_bad_clients(pipe):
    from multiprocessing.connection import Client
    address, listener = pipe
    single_instance.serve(listener, lambda request: {"ok": True})
    for payload in (b"not json", b"[1, 2]", b"\x80\x04pickle"):
        with Client(address, family="AF_PIPE") as conn:
            conn.send_bytes(payload)
    assert single_instance.send_request({}, address) == {"ok": True}


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc", "YouTube"),
    ("https://youtu.be/abc", "YouTube"),
    ("https://x.com/user/status/1", "X (Twitter)"),
    ("https://www.box.com/file", "Online Video"),
    ("https://netflix.com/title/1", "Online Video"),
    ("https://vm.tiktok.com/abc", "TikTok"),
    ("https://example.org/video", "Online Video"),
])
def test_detect_platform(url, expected):
    assert downloader.detect_platform(url) == expected


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/playlist?list=PL123", True),
    ("https://www.youtube.com/watch?v=abc&list=RD123", False),
    ("https://www.youtube.com/watch?v=abc", False),
    ("https://soundcloud.com/user/sets/album", True),
])
def test_is_playlist_url(url, expected):
    assert downloader.is_playlist_url(url) is expected


@pytest.mark.parametrize("text,expected", [
    ("90", 90.0), ("1:30", 90.0), ("1:01:30", 3690.0), ("", None), ("abc", None),
])
def test_parse_time_to_seconds(text, expected):
    assert downloader.parse_time_to_seconds(text) == expected


def test_parse_version_ordering():
    assert updater.parse_version("v1.0.10") > updater.parse_version("1.0.9")
    assert updater.parse_version("2026.10.21") > updater.parse_version("2026.8.19")


def test_release_hash_parsed_from_markdown():
    h = "a" * 64
    data = {
        "tag_name": "v9.0.0",
        "body": f"**SHA256:** `{h}`",
        "assets": [{"name": "Husnexa_Setup_v9.0.0.exe",
                    "browser_download_url": "https://x/y.exe", "size": 10}],
    }
    assert updater._process_release_data(data)["expected_sha256"] == h


def test_safe_extractall_rejects_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../evil.txt", "x")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
        with pytest.raises(ValueError):
            updater._safe_extractall(z, str(tmp_path / "out"))
    assert not (tmp_path / "evil.txt").exists()


def test_app_update_rejects_local_paths(tmp_path):
    fake = tmp_path / "evil.exe"
    fake.write_bytes(b"x")
    res = updater.download_and_verify_app_update(str(fake), expected_sha256="a" * 64)
    assert "error" in res


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc&list=RD123", {"noplaylist": True}),
    ("https://youtu.be/abc?list=PL123", {"noplaylist": True}),
    ("https://www.youtube.com/watch?v=abc", {}),
    ("https://www.instagram.com/p/abc/", {}),
])
def test_single_item_opts(url, expected):
    assert downloader.get_single_item_opts(url) == expected


def test_open_ended_clip_range_is_accepted():
    ranges = downloader.yt_dlp.utils.download_range_func(None, [(30, float("inf"))])
    assert list(ranges({"duration": 100}, None))[0]["start_time"] == 30


def test_required_ejs_version_read_from_wheel_metadata(tmp_path):
    info = tmp_path / "yt_dlp-2026.9.1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Requires-Dist: yt-dlp-ejs==1.2.3; extra == 'default'\n")
    assert updater._required_ejs_version(str(tmp_path)) == "1.2.3"


def test_safe_extractall_allows_normal_files(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("yt_dlp/__init__.py", "")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
        updater._safe_extractall(z, str(tmp_path / "out"))
    assert (tmp_path / "out" / "yt_dlp" / "__init__.py").exists()


def test_cancel_cleanup_removes_leftovers_but_keeps_finished_files(tmp_path):
    def make(name):
        p = tmp_path / name
        p.write_bytes(b"x")
        return str(p)

    video_part = make("Film.f401.mp4.part")
    frag = make("Film.f401.mp4.part-Frag3")
    audio_stream = make("Film.f140.m4a")
    ytdl = make("Film.f401.mp4.ytdl")
    finished = make("Episode.final.mp4")
    other = make("Unrelated.mp4")

    downloader._cleanup_partial_files({video_part, str(tmp_path / "Film.f401.mp4"), audio_stream, finished})

    for gone in (video_part, frag, audio_stream, ytdl):
        assert not os.path.exists(gone), gone
    assert os.path.exists(finished)
    assert os.path.exists(other)
