"""Native messaging helper: connects the browser extension to the app.

The browser keeps this process open while a job is pending, because the app cannot start a
conversation with the extension. If the job hits a login wall, the helper relays the request
for cookies and passes the extension's answer straight to the app. Cookies are never stored here.
"""
import json
import os
import queue
import struct
import subprocess
import sys
import threading
import time

import download_queue
import single_instance

MAX_MESSAGE_BYTES = single_instance.MAX_MESSAGE_BYTES
MAX_TITLE_LENGTH = 300
APP_EXE_NAME = "Husnexa.exe"
APP_START_SECONDS = 20
POLL_SECONDS = 1.0
FINISHED_STATUSES = download_queue.FINISHED_STATUSES + ("missing",)


def read_message(stream):
    """Reads one length-prefixed JSON message, or returns None when the browser closes the pipe."""
    header = stream.read(4)
    if len(header) < 4:
        return None
    length = struct.unpack("<I", header)[0]
    if length > MAX_MESSAGE_BYTES:
        raise ValueError("Message too large")
    return json.loads(stream.read(length).decode("utf-8"))


def write_message(stream, message):
    body = json.dumps(message).encode("utf-8")
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def app_command():
    """Returns the command that starts the app."""
    if getattr(sys, "frozen", False):
        return [os.path.join(os.path.dirname(sys.executable), APP_EXE_NAME)]
    return [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")]


def launch_app():
    """Starts the app outside the browser's process job."""
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB
    subprocess.Popen(
        app_command(), creationflags=flags, close_fds=True, cwd=os.path.dirname(os.path.abspath(__file__)),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def send_once_running(request, send, wait_seconds):
    """Keeps trying while the app starts up."""
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return send(request)
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def handle_message(message, send=single_instance.send_request, launch=launch_app,
                   start_seconds=APP_START_SECONDS):
    """Validates a request and hands it to the running app, starting the app if needed."""
    if not isinstance(message, dict) or message.get("action") != "download":
        return {"error": "Unknown request"}
    try:
        url, media_type, quality = download_queue.normalize_request(
            message.get("url"), message.get("media_type", "video"), message.get("quality", "best")
        )
    except ValueError as e:
        return {"error": str(e)}
    request = {
        "action": "enqueue",
        "url": url,
        "media_type": media_type,
        "quality": quality,
        "title": str(message.get("title") or "")[:MAX_TITLE_LENGTH],
        "from_extension": True,
    }
    try:
        return send(request) or {"error": "The app did not reply."}
    except OSError:
        pass
    try:
        launch()
        return send_once_running(request, send, start_seconds) or {"error": "The app did not reply."}
    except OSError:
        return {"error": "Couldn't start Husnexa."}


def follow_job(job_id, inbox, output, send=single_instance.send_request, poll_seconds=POLL_SECONDS):
    """Stays connected until the job ends, relaying one cookie request if the job makes it."""
    asked = False
    while True:
        try:
            state = send({"action": "job_state", "job_id": job_id}) or {}
        except OSError:
            return
        if state.get("status") in FINISHED_STATUSES:
            return
        if state.get("needs_cookies") and not asked:
            asked = True
            write_message(output, {"type": "need_cookies"})
        elif not state.get("needs_cookies"):
            asked = False
        try:
            message = inbox.get(timeout=poll_seconds)
        except queue.Empty:
            continue
        if message is None:
            inbox.put(None)
            return
        if isinstance(message, dict) and message.get("type") == "cookies":
            try:
                send({"action": "submit_cookies", "job_id": job_id, "cookies": message.get("cookies")})
            except OSError:
                return


def read_into(inbox, stream):
    """Moves browser messages to the inbox. None marks the browser going away."""
    try:
        while True:
            message = read_message(stream)
            inbox.put(message)
            if message is None:
                return
    except (ValueError, OSError):
        inbox.put(None)


def main():
    output = sys.stdout.buffer
    inbox = queue.Queue()
    threading.Thread(target=read_into, args=(inbox, sys.stdin.buffer), daemon=True).start()
    while True:
        message = inbox.get()
        if message is None:
            return
        reply = handle_message(message)
        write_message(output, reply)
        if reply.get("job_id"):
            follow_job(reply["job_id"], inbox, output)
            write_message(output, {"type": "finished"})


if __name__ == "__main__":
    main()
