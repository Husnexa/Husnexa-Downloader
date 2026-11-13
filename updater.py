import os
import sys
import re
import json
import glob
import shutil
import zipfile
import io
import subprocess
import hashlib
from concurrent.futures import ThreadPoolExecutor
import requests

APP_VERSION = "1.2.1"
# App self-update is off for Husnexa (no release feed yet). Set "owner/repo" to turn it on.
GITHUB_REPO = ""
PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
EJS_PYPI_URL = "https://pypi.org/pypi/yt-dlp-ejs/{version}/json"

# Default fast timeout (connect_timeout, read_timeout) so background checks never hang for 10-20s
DEFAULT_CHECK_TIMEOUT = (3.05, 4.0)

# Cached yt-dlp version string to avoid repeated module imports on the bridge
_cached_ytdlp_ver = None


def get_local_appdata_dir():
    """Returns %LOCALAPPDATA%\\Husnexa."""
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    return os.path.join(base, "Husnexa")


def get_ytdlp_update_dir():
    """Returns %LOCALAPPDATA%\\Husnexa\\yt_dlp_update."""
    return os.path.join(get_local_appdata_dir(), "yt_dlp_update")


def is_ytdlp_custom():
    """Checks if an overridden yt-dlp package exists in the update directory."""
    d = get_ytdlp_update_dir()
    return os.path.isdir(os.path.join(d, "yt_dlp")) and os.path.isfile(
        os.path.join(d, "yt_dlp", "__init__.py")
    )


def setup_ytdlp_override():
    """
    At app startup, BEFORE importing yt_dlp or downloader:
    Check whether %LOCALAPPDATA%\\Husnexa\\yt_dlp_update\\yt_dlp exists,
    and if so, insert that folder at sys.path[0] so the updated yt-dlp overrides the bundled one.
    """
    target_dir = get_ytdlp_update_dir()
    init_file = os.path.join(target_dir, "yt_dlp", "__init__.py")
    if os.path.isfile(init_file):
        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)
        return True
    return False


def is_directory_writable(dir_path):
    """Tests if a directory has write permissions by creating and removing a temp file."""
    if not dir_path or not os.path.isdir(dir_path):
        return False
    test_file = os.path.join(dir_path, f".write_test_{os.getpid()}.tmp")
    try:
        with open(test_file, "w") as f:
            f.write("write_test")
        os.remove(test_file)
        return True
    except Exception:
        return False


def parse_version(v_str):
    """Parses version strings like '2026.10.21' or 'v1.0.0' for accurate comparison."""
    if not v_str:
        return (0,)
    clean = re.sub(r"^[vV]", "", str(v_str).strip())
    try:
        from packaging import version
        return version.parse(clean)
    except Exception:
        pass
    tokens = []
    for piece in re.split(r"[-._]", clean):
        try:
            tokens.append(int(piece))
        except ValueError:
            tokens.append(piece)
    return tuple(tokens)


def get_installed_versions():
    """Returns current App version, yt-dlp version, and whether yt-dlp is an override."""
    global _cached_ytdlp_ver
    if _cached_ytdlp_ver is None:
        try:
            # Read yt_dlp.version directly if already imported, or import lightweight version submodule
            import yt_dlp.version as _yt_ver
            _cached_ytdlp_ver = getattr(_yt_ver, "__version__", "Unknown")
        except Exception:
            try:
                import yt_dlp
                _cached_ytdlp_ver = getattr(yt_dlp.version, "__version__", "Unknown")
            except Exception:
                pass
    return {
        "app_version": APP_VERSION,
        "ytdlp_version": _cached_ytdlp_ver or "Unknown",
        "ytdlp_is_custom": is_ytdlp_custom(),
    }


def check_ytdlp_update(timeout=DEFAULT_CHECK_TIMEOUT):
    """
    Queries PyPI for the latest yt-dlp version and checks if an update is available.
    Uses a fast timeout (default 3–4s) so slow networks never stall for 10+ seconds.
    """
    current_ver = get_installed_versions()["ytdlp_version"]
    req_timeout = (3.05, float(timeout)) if isinstance(timeout, (int, float)) else timeout
    try:
        resp = requests.get(
            PYPI_URL,
            timeout=req_timeout,
            headers={"User-Agent": f"Husnexa/{APP_VERSION}"},
        )
        if resp.status_code != 200:
            return {
                "update_available": False,
                "current": current_ver,
                "latest": current_ver,
                "error": f"PyPI responded with status {resp.status_code}",
            }
        data = resp.json()
        latest_ver = data.get("info", {}).get("version", "")
        urls = data.get("urls", [])
        whl_urls = [u for u in urls if u.get("packagetype") == "bdist_wheel"]
        if not whl_urls:
            return {
                "update_available": False,
                "current": current_ver,
                "latest": latest_ver,
                "error": "No .whl package found on PyPI",
            }
        whl_url = whl_urls[0]["url"]
        whl_size = whl_urls[0].get("size", 0)
        whl_sha256 = (whl_urls[0].get("digests") or {}).get("sha256")
        has_update = parse_version(latest_ver) > parse_version(current_ver)
        return {
            "update_available": has_update,
            "current": current_ver,
            "latest": latest_ver,
            "wheel_url": whl_url,
            "wheel_sha256": whl_sha256,
            "size_mb": round(whl_size / 1048576, 2) if whl_size else None,
            "error": None,
        }
    except requests.exceptions.RequestException:
        return {
            "update_available": False,
            "current": current_ver,
            "latest": current_ver,
            "error": "Unable to connect to PyPI. Please check your internet connection.",
        }
    except Exception as e:
        return {
            "update_available": False,
            "current": current_ver,
            "latest": current_ver,
            "error": str(e),
        }


def check_app_update(timeout=DEFAULT_CHECK_TIMEOUT):
    """
    Calls the GitHub Releases API to check for new app versions.
    Extracts the Windows installer Setup asset (Husnexa_Setup_v*.exe).
    Uses a fast timeout (default 3–4s) so slow networks never stall for 10+ seconds.
    """
    if not GITHUB_REPO:
        return {
            "update_available": False,
            "current": APP_VERSION,
            "latest": APP_VERSION,
            "message": "You're up to date.",
            "error": None,
        }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    headers = {
        "User-Agent": f"Husnexa/{APP_VERSION}",
        "Accept": "application/vnd.github.v3+json",
    }
    req_timeout = (3.05, float(timeout)) if isinstance(timeout, (int, float)) else timeout
    try:
        resp = requests.get(url, timeout=req_timeout, headers=headers)
        if resp.status_code == 404:
            return {
                "update_available": False,
                "current": APP_VERSION,
                "latest": APP_VERSION,
                "message": "You're up to date.",
                "error": None,
            }
        if resp.status_code == 403:
            return {
                "update_available": False,
                "current": APP_VERSION,
                "latest": APP_VERSION,
                "error": "GitHub API rate limit exceeded. Please try again later.",
            }
        if resp.status_code != 200:
            return {
                "update_available": False,
                "current": APP_VERSION,
                "latest": APP_VERSION,
                "error": f"GitHub returned status {resp.status_code}",
            }
        data = resp.json()
        return _process_release_data(data)
    except requests.exceptions.RequestException:
        return {
            "update_available": False,
            "current": APP_VERSION,
            "latest": APP_VERSION,
            "error": "Unable to connect to GitHub. Please check your internet connection.",
        }
    except Exception as e:
        return {
            "update_available": False,
            "current": APP_VERSION,
            "latest": APP_VERSION,
            "error": str(e),
        }


def check_all_updates(timeout=4.0):
    """
    Executes check_ytdlp_update() and check_app_update() concurrently in a
    ThreadPoolExecutor so total network check time is bounded by max(t_pypi, t_github)
    instead of sum(t_pypi + t_github).
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_ytdlp = pool.submit(check_ytdlp_update, timeout)
        fut_app = pool.submit(check_app_update, timeout)
        try:
            ytdlp_res = fut_ytdlp.result(timeout=timeout + 2.0)
        except Exception as e:
            cur = get_installed_versions()["ytdlp_version"]
            ytdlp_res = {
                "update_available": False,
                "current": cur,
                "latest": cur,
                "error": str(e),
            }
        try:
            app_res = fut_app.result(timeout=timeout + 2.0)
        except Exception as e:
            app_res = {
                "update_available": False,
                "current": APP_VERSION,
                "latest": APP_VERSION,
                "error": str(e),
            }
    return {"ytdlp": ytdlp_res, "app": app_res}


def _process_release_data(data):
    """Processes release JSON data, strictly locating the Inno Setup installer asset."""
    tag_name = data.get("tag_name", "")
    clean_tag = tag_name.lstrip("vV")
    has_update = parse_version(clean_tag) > parse_version(APP_VERSION)
    assets = data.get("assets", [])
    setup_asset = None
    for a in assets:
        name = a.get("name", "")
        if name.startswith("Husnexa_Setup_v") and name.lower().endswith(".exe"):
            setup_asset = a
            break
    body = data.get("body", "") or ""
    expected_sha256 = None
    sha_match = re.search(r"(?:sha256|sha-256|hash)[\s:=*`\"']+([a-fA-F0-9]{64})", body, re.IGNORECASE)
    if sha_match:
        expected_sha256 = sha_match.group(1).lower()
    if not setup_asset:
        err_msg = (
            "No installer Setup asset found in the latest release (expected 'Husnexa_Setup_v*.exe')."
            if has_update
            else None
        )
        return {
            "update_available": has_update,
            "current": APP_VERSION,
            "latest": clean_tag,
            "tag_name": tag_name,
            "release_name": data.get("name", tag_name),
            "notes": body,
            "asset_url": None,
            "asset_name": None,
            "size_bytes": 0,
            "size_mb": None,
            "expected_sha256": expected_sha256,
            "html_url": data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
            "is_frozen": getattr(sys, "frozen", False),
            "can_auto_update": False,
            "error": err_msg,
        }
    asset_url = setup_asset.get("browser_download_url")
    asset_name = setup_asset.get("name", f"Husnexa_Setup_v{clean_tag}.exe")
    asset_size = setup_asset.get("size", 0)
    return {
        "update_available": has_update,
        "current": APP_VERSION,
        "latest": clean_tag,
        "tag_name": tag_name,
        "release_name": data.get("name", tag_name),
        "notes": body,
        "asset_url": asset_url,
        "asset_name": asset_name,
        "size_bytes": asset_size,
        "size_mb": round(asset_size / 1048576, 2) if asset_size else None,
        "expected_sha256": expected_sha256,
        "html_url": data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
        "is_frozen": getattr(sys, "frozen", False),
        "can_auto_update": True,
        "error": None,
    }


def _safe_extractall(zf, dest_dir):
    """Extracts a zip, rejecting any member that would escape dest_dir (zip-slip)."""
    root = os.path.realpath(dest_dir)
    for member in zf.namelist():
        target = os.path.realpath(os.path.join(root, member))
        if target != root and not target.startswith(root + os.sep):
            raise ValueError(f"Unsafe path in archive: {member}")
    zf.extractall(root)


def _required_ejs_version(wheel_dir):
    """Returns the yt-dlp-ejs version pinned by an extracted yt-dlp wheel, or None."""
    for metadata in glob.glob(os.path.join(wheel_dir, "yt_dlp-*.dist-info", "METADATA")):
        with open(metadata, "r", encoding="utf-8") as f:
            match = re.search(r"^Requires-Dist:\s*yt-dlp-ejs==([\w.]+)", f.read(), re.MULTILINE)
        if match:
            return match.group(1)
    return None


def _install_matching_ejs(wheel_dir):
    """Extracts the yt-dlp-ejs wheel that yt-dlp pins next to it, verified by SHA-256."""
    version = _required_ejs_version(wheel_dir)
    if not version:
        return
    headers = {"User-Agent": f"Husnexa/{APP_VERSION}"}
    resp = requests.get(EJS_PYPI_URL.format(version=version), timeout=30, headers=headers)
    resp.raise_for_status()
    wheels = [u for u in resp.json().get("urls", []) if u.get("packagetype") == "bdist_wheel"]
    if not wheels:
        raise ValueError(f"No yt-dlp-ejs {version} wheel found on PyPI.")
    expected_sha = (wheels[0].get("digests") or {}).get("sha256")
    if not expected_sha:
        raise ValueError("PyPI did not provide a SHA-256 digest for yt-dlp-ejs.")
    wheel = requests.get(wheels[0]["url"], timeout=60, headers=headers)
    wheel.raise_for_status()
    if hashlib.sha256(wheel.content).hexdigest().lower() != expected_sha.lower():
        raise ValueError("yt-dlp-ejs download failed SHA-256 verification.")
    with zipfile.ZipFile(io.BytesIO(wheel.content)) as z:
        _safe_extractall(z, wheel_dir)


def perform_ytdlp_update(progress_cb=None):
    """
    Downloads the latest yt-dlp wheel (.whl) from PyPI and extracts it to
    %LOCALAPPDATA%\\Husnexa\\yt_dlp_update\\.
    """
    global _cached_ytdlp_ver
    check_info = check_ytdlp_update()
    if check_info.get("error"):
        return {"error": check_info["error"]}
    whl_url = check_info.get("wheel_url")
    if not whl_url:
        return {"error": "Could not locate yt-dlp wheel package."}
    latest_ver = check_info.get("latest")
    try:
        if progress_cb:
            progress_cb(10, "Connecting to PyPI...")
        resp = requests.get(
            whl_url,
            stream=True,
            timeout=30,
            headers={"User-Agent": f"Husnexa/{APP_VERSION}"},
        )
        resp.raise_for_status()
        total_len = int(resp.headers.get("content-length", 0))
        buffer = bytearray()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            buffer.extend(chunk)
            downloaded += len(chunk)
            if total_len > 0 and progress_cb:
                pct = 10 + int((downloaded / total_len) * 70)
                down_mb = downloaded / 1048576
                tot_mb = total_len / 1048576
                progress_cb(pct, f"Downloading yt-dlp ({down_mb:.1f} / {tot_mb:.1f} MB)...")
        expected_sha = check_info.get("wheel_sha256")
        if not expected_sha:
            return {"error": "PyPI did not provide a SHA-256 digest; refusing to install unverified yt-dlp."}
        if hashlib.sha256(buffer).hexdigest().lower() != expected_sha.lower():
            return {"error": "yt-dlp download failed SHA-256 verification."}
        if progress_cb:
            progress_cb(85, "Extracting updated yt-dlp engine...")
        target_dir = get_ytdlp_update_dir()
        temp_dir = target_dir + "_temp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(buffer)) as z:
            _safe_extractall(z, temp_dir)
        if not os.path.isfile(os.path.join(temp_dir, "yt_dlp", "__init__.py")):
            return {"error": "Downloaded wheel is invalid (missing yt_dlp module)."}
        if progress_cb:
            progress_cb(90, "Matching YouTube components...")
        _install_matching_ejs(temp_dir)
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.move(temp_dir, target_dir)
        except Exception:
            for root, _, files in os.walk(temp_dir):
                rel = os.path.relpath(root, temp_dir)
                dest_sub = os.path.join(target_dir, rel)
                os.makedirs(dest_sub, exist_ok=True)
                for f in files:
                    try:
                        shutil.copy2(os.path.join(root, f), os.path.join(dest_sub, f))
                    except Exception:
                        pass
            shutil.rmtree(temp_dir, ignore_errors=True)
        _cached_ytdlp_ver = latest_ver
        if progress_cb:
            progress_cb(100, f"Updated to v{latest_ver}")
        return {"success": True, "version": latest_ver}
    except Exception as e:
        return {"error": str(e)}


def download_and_verify_app_update(
    asset_url, asset_name="", expected_size=None, expected_sha256=None, progress_cb=None
):
    """
    Downloads the GitHub Setup.exe installer asset to a temp staging directory,
    reporting progress and verifying size and SHA-256 digest (if provided).
    """
    temp_dir = os.path.join(
        os.environ.get("TEMP", os.path.expanduser("~\\AppData\\Local\\Temp")),
        "HusnexaUpdate",
    )
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except Exception as e:
        return {"error": f"Failed to create temp directory: {e}"}

    if not asset_name:
        asset_name = "Husnexa_Setup.exe"
    clean_name = re.sub(r"[^\w\.-]", "_", asset_name)
    target_path = os.path.join(temp_dir, f"setup_{os.getpid()}_{clean_name}")
    try:
        if progress_cb:
            progress_cb(5, "Connecting to download server...")
        if not str(asset_url).lower().startswith("https://"):
            raise ValueError("Update downloads must use HTTPS.")

        headers = {"User-Agent": f"Husnexa/{APP_VERSION}"}
        resp = requests.get(asset_url, stream=True, timeout=60, headers=headers)
        resp.raise_for_status()
        content_length = int(resp.headers.get("content-length", 0))
        target_size = expected_size or content_length
        downloaded = 0
        hasher = hashlib.sha256()
        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=131072):
                if not chunk:
                    continue
                f.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    pct = int((downloaded / target_size) * 90) if target_size > 0 else 50
                    pct = min(pct, 95)
                    down_mb = downloaded / 1048576
                    tot_mb = target_size / 1048576 if target_size > 0 else down_mb
                    progress_cb(pct, f"Downloading installer ({down_mb:.1f} / {tot_mb:.1f} MB)...")

        if target_size > 0 and downloaded != target_size:
            raise ValueError(f"Downloaded file incomplete ({downloaded} / {target_size} bytes)")

        actual_sha = hasher.hexdigest().lower()
        if not expected_sha256:
            try:
                os.remove(target_path)
            except Exception:
                pass
            raise ValueError("No SHA-256 published for this release; refusing to run an unverified installer.")
        if expected_sha256.lower() != actual_sha:
            try:
                os.remove(target_path)
            except Exception:
                pass
            raise ValueError(
                f"SHA-256 digest mismatch! Expected {expected_sha256}, got {actual_sha}"
            )

        if progress_cb:
            progress_cb(100, "Installer downloaded and verified!")
        return {
            "success": True,
            "file_path": target_path,
            "sha256": actual_sha,
            "size_bytes": downloaded,
        }
    except Exception as e:
        return {"error": str(e)}


def launch_installer_update(setup_exe_path):
    """
    Launches the downloaded Inno Setup installer with /CLOSEAPPLICATIONS and exits
    the current application immediately so Inno Setup can update files cleanly.
    """
    if not os.path.isfile(setup_exe_path):
        return {"error": f"Downloaded Setup installer was not found at: {setup_exe_path}"}
    try:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        subprocess.Popen([setup_exe_path, "/CLOSEAPPLICATIONS"], creationflags=flags)
        os._exit(0)
    except Exception as e:
        return {"error": f"Failed to launch installer: {e}"}


apply_portable_update = launch_installer_update


def download_app_asset(asset_url, asset_name="", progress_cb=None):
    """Fallback manual download into user's Downloads folder."""
    dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(dest_dir):
        dest_dir = os.getcwd()
    if not asset_name:
        asset_name = "Husnexa_Setup.exe"
    base, ext = os.path.splitext(asset_name)
    target_path = os.path.join(dest_dir, asset_name)
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        counter += 1
    try:
        if progress_cb:
            progress_cb(5, "Connecting to GitHub...")
        resp = requests.get(
            asset_url,
            stream=True,
            timeout=60,
            headers={"User-Agent": f"Husnexa/{APP_VERSION}"},
        )
        resp.raise_for_status()
        total_len = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=131072):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total_len > 0 and progress_cb:
                    pct = int((downloaded / total_len) * 100)
                    down_mb = downloaded / 1048576
                    tot_mb = total_len / 1048576
                    progress_cb(pct, f"Downloading {asset_name} ({down_mb:.1f} / {tot_mb:.1f} MB)...")
        if progress_cb:
            progress_cb(100, "Download complete!")
        return {"success": True, "file_path": target_path}
    except Exception as e:
        return {"error": str(e)}


def open_file_location(path):
    """Selects and reveals the file in Windows File Explorer."""
    try:
        if os.path.isfile(path):
            subprocess.Popen(["explorer", f"/select,{os.path.abspath(path)}"])
            return True
        if os.path.isdir(path):
            os.startfile(path)
            return True
        return False
    except Exception as e:
        print(f"Error opening explorer location: {e}")
        return False


def restart_app():
    """Relaunches the current application and cleanly terminates the old process."""
    try:
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
            flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            subprocess.Popen([exe_path, "--restarting"], creationflags=flags)
        else:
            subprocess.Popen([sys.executable, sys.argv[0], "--restarting"])
        os._exit(0)
    except Exception as e:
        print(f"Error restarting app: {e}")