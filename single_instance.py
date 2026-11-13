"""Keeps one running copy of the app and passes requests from later launches to it.

Requests travel over a per-user named pipe as JSON. Never use Connection.recv() here:
it unpickles, which would let anything that reaches the pipe run code in the app.
"""
import getpass
import hashlib
import json
import threading
import time
from multiprocessing.connection import Client, Listener

MAX_MESSAGE_BYTES = 262144
CLIENT_TIMEOUT_SECONDS = 2.0
REPLY_TIMEOUT_SECONDS = 5.0


def pipe_name():
    """Returns this user's pipe address, so separate Windows users each get their own app."""
    user = hashlib.sha256(getpass.getuser().encode("utf-8")).hexdigest()[:16]
    return rf"\\.\pipe\Husnexa-{user}"


def claim(wait_seconds=0, address=None):
    """Returns a Listener if this process is the first copy, otherwise None."""
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return Listener(address or pipe_name(), family="AF_PIPE")
        except OSError:
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.1)


def send_request(request, address=None):
    """Sends a request to the running copy and returns its reply, or None if there was no reply."""
    with Client(address or pipe_name(), family="AF_PIPE") as conn:
        conn.send_bytes(json.dumps(request).encode("utf-8"))
        if conn.poll(REPLY_TIMEOUT_SECONDS):
            return json.loads(conn.recv_bytes(MAX_MESSAGE_BYTES).decode("utf-8"))
    return None


def _serve_connection(conn, handler):
    with conn:
        if not conn.poll(CLIENT_TIMEOUT_SECONDS):
            return
        request = json.loads(conn.recv_bytes(MAX_MESSAGE_BYTES).decode("utf-8"))
        reply = handler(request) if isinstance(request, dict) else {"error": "Invalid request"}
        conn.send_bytes(json.dumps(reply).encode("utf-8"))


def serve(listener, handler):
    """Answers requests on a daemon thread. handler takes a dict and returns a JSON-safe dict."""
    def loop():
        while True:
            try:
                conn = listener.accept()
            except OSError:
                time.sleep(0.1)
                continue
            try:
                _serve_connection(conn, handler)
            except (OSError, EOFError, ValueError):
                pass

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def parse_launch_args(argv):
    """Turns command-line arguments into (request, restarting)."""
    request = {"action": "activate"}
    restarting = False
    args = iter(argv)
    for arg in args:
        if arg == "--restarting":
            restarting = True
        elif arg == "--media":
            request["media_type"] = next(args, "video")
        elif arg == "--quality":
            request["quality"] = next(args, "best")
        elif arg == "--title":
            request["title"] = next(args, "")
        elif arg.lower().startswith(("http://", "https://")):
            request["action"] = "enqueue"
            request["url"] = arg
    return request, restarting
