import os
import sys
import time

# Prevent Windows GPU Watchdog / TDR timeouts in WebView2
curr_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
safe_flags = "--disable-features=CalculateNativeWinOcclusion,ElasticOverscroll --disable-gpu-process-crash-limit"
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{safe_flags} {curr_args}".strip()

# Initialize yt-dlp update override BEFORE importing downloader or yt_dlp
import updater
updater.setup_ytdlp_override()

import single_instance

def forward_to_running_copy(request):
    """Hands a launch request to the copy that is already running. Returns True if it arrived."""
    for _ in range(5):
        try:
            single_instance.send_request(request)
            return True
        except OSError:
            time.sleep(0.2)
    return False

def main():
    """Main launcher: starts the Liquid Glass engine, or defers to a copy already running."""
    request, restarting = single_instance.parse_launch_args(sys.argv[1:])
    # A restart overlaps the old process for a moment, so give it time to exit.
    listener = single_instance.claim(wait_seconds=10 if restarting else 0)
    if listener is None:
        if forward_to_running_copy(request):
            sys.exit(0)
        listener = single_instance.claim()
        if listener is None:
            sys.exit(1)

    try:
        import app_glass
        app_glass.main(listener=listener, initial_request=request)
    except Exception as e:
        try:
            import traceback
            log_file = os.path.join(updater.get_local_appdata_dir(), "app.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[LiquidGlass Fatal Error] {e}\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
